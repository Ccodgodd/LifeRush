import os
import shutil
from datetime import datetime, date, timedelta
from typing import List, Optional
import requests
from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile, Form
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.database import engine, Base, get_db
from backend.app.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
    check_role
)
from backend.app.models import User, MedicalReport, BloodRequest, Match, Notification
from backend.app.ocr import extract_medical_report, determine_eligibility
from backend.app.ai_engine import rank_donors, get_city_coords
from backend.app.chatbot import query_chatbot
from backend.app.telephony import simulate_toll_free_call
import backend.app.schemas as schemas

# Initialize database tables
Base.metadata.create_all(bind=engine)


def run_startup_migrations():
    if not settings.DATABASE_URL.startswith("sqlite"):
        return

    migration_statements = [
        "ALTER TABLE blood_requests ADD COLUMN hospital_address VARCHAR",
        "ALTER TABLE blood_requests ADD COLUMN hospital_place_id VARCHAR",
    ]

    with engine.begin() as connection:
        for statement in migration_statements:
            try:
                connection.exec_driver_sql(statement)
            except Exception:
                pass


run_startup_migrations()

app = FastAPI(title=settings.PROJECT_NAME)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure folders exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


PLACE_TYPE_CONFIG = {
    "hospital": {
        "tags": [{"key": "amenity", "value": "hospital"}],
        "label": "Hospital",
    },
    "blood_bank": {
        "tags": [
            {"key": "healthcare", "value": "blood_donation"},
            {"key": "amenity", "value": "blood_bank"},
        ],
        "label": "Blood Bank",
    },
    "donation_camp": {
        "tags": [
            {"key": "healthcare", "value": "blood_donation"},
            {"key": "amenity", "value": "clinic"},
        ],
        "label": "Donation Camp",
    },
}


def geocode_place(city: str, state: str = ""):
    query = ", ".join(part for part in [city, state] if part).strip()
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "jsonv2", "limit": 1},
            headers={"User-Agent": "LifeRushAI/1.0"},
            timeout=8,
        )
        response.raise_for_status()
        results = response.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception:
        pass
    return get_city_coords(city, state)


def build_overpass_query(lat: float, lon: float, radius_m: int, place_types: List[str]) -> str:
    selectors = []
    for place_type in place_types:
        config = PLACE_TYPE_CONFIG.get(place_type)
        if not config:
            continue
        for tag in config["tags"]:
            selectors.extend([
                f'node["{tag["key"]}"="{tag["value"]}"](around:{radius_m},{lat},{lon});',
                f'way["{tag["key"]}"="{tag["value"]}"](around:{radius_m},{lat},{lon});',
                f'relation["{tag["key"]}"="{tag["value"]}"](around:{radius_m},{lat},{lon});',
            ])

    return f"""
    [out:json][timeout:12];
    (
      {' '.join(selectors)}
    );
    out center tags;
    """


def infer_place_type(tags: dict) -> str:
    amenity = tags.get("amenity")
    healthcare = tags.get("healthcare")

    if amenity == "hospital":
        return "Hospital"
    if amenity == "blood_bank":
        return "Blood Bank"
    if healthcare == "blood_donation":
        if amenity == "clinic":
            return "Donation Camp"
        return "Blood Bank"
    return "Healthcare Facility"


def fetch_nearby_osm_places(lat: float, lon: float, radius_km: int, place_types: List[str]):
    radius_m = max(1000, min(radius_km * 1000, 50000))
    query = build_overpass_query(lat, lon, radius_m, place_types)

    response = requests.post(
        "https://overpass-api.de/api/interpreter",
        data=query,
        headers={"User-Agent": "LifeRushAI/1.0"},
        timeout=15,
    )
    response.raise_for_status()
    elements = response.json().get("elements", [])

    places = []
    seen = set()

    for element in elements:
        tags = element.get("tags", {})
        place_lat = element.get("lat") or (element.get("center") or {}).get("lat")
        place_lon = element.get("lon") or (element.get("center") or {}).get("lon")
        if place_lat is None or place_lon is None:
            continue

        name = tags.get("name") or infer_place_type(tags)
        address_parts = [
            tags.get("addr:housename"),
            tags.get("addr:housenumber"),
            tags.get("addr:street"),
            tags.get("addr:suburb"),
            tags.get("addr:city"),
            tags.get("addr:state"),
        ]
        address = ", ".join(part for part in address_parts if part) or "Address unavailable"
        contact = tags.get("phone") or tags.get("contact:phone") or "Not listed"
        place_type = infer_place_type(tags)
        distance_km = round(calculate_haversine_distance(lat, lon, float(place_lat), float(place_lon)), 2)

        unique_key = (name, round(float(place_lat), 5), round(float(place_lon), 5))
        if unique_key in seen:
            continue
        seen.add(unique_key)

        places.append({
            "name": name,
            "type": place_type,
            "address": address,
            "lat": float(place_lat),
            "lon": float(place_lon),
            "contact": contact,
            "distance_km": distance_km,
            "source": "OpenStreetMap",
        })

    places.sort(key=lambda place: place["distance_km"])
    return places[:25]


def build_fallback_places(city: str, center_lat: float, center_lon: float):
    return [
        {
            "name": f"{city} Community Hospital",
            "type": "Hospital",
            "address": f"450 Health Ave, {city}",
            "lat": center_lat - 0.015,
            "lon": center_lon + 0.018,
            "contact": "Not listed",
            "distance_km": 2.41,
            "source": "Fallback",
        },
        {
            "name": f"{city} Red Cross Blood Center",
            "type": "Blood Bank",
            "address": f"100 Red Cross Way, {city}",
            "lat": center_lat + 0.008,
            "lon": center_lon - 0.012,
            "contact": "Not listed",
            "distance_km": 1.63,
            "source": "Fallback",
        },
        {
            "name": f"Unity Donation Camp - {city}",
            "type": "Donation Camp",
            "address": f"Central Park Pavilion, {city}",
            "lat": center_lat + 0.022,
            "lon": center_lon + 0.005,
            "contact": "Not listed",
            "distance_km": 2.52,
            "source": "Fallback",
        },
    ]


def reverse_geocode_osm(lat: float, lon: float):
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "jsonv2"},
            headers={"User-Agent": "LifeRushAI/1.0"},
            timeout=8,
        )
        response.raise_for_status()
        data = response.json()
        address = data.get("address", {})
        return {
            "city": address.get("city") or address.get("town") or address.get("village") or address.get("county"),
            "state": address.get("state"),
        }
    except Exception:
        return {"city": None, "state": None}


def search_google_hospitals(query: str, lat: Optional[float] = None, lon: Optional[float] = None):
    if not settings.GOOGLE_MAPS_API_KEY or settings.GOOGLE_MAPS_API_KEY == "YOUR_GOOGLE_MAPS_API_KEY":
        return []

    location_bias = None
    if lat is not None and lon is not None:
        location_bias = f"circle:15000@{lat},{lon}"

    params = {
        "input": query,
        "inputtype": "textquery",
        "fields": "place_id,name,formatted_address,geometry",
        "key": settings.GOOGLE_MAPS_API_KEY,
    }
    if location_bias:
        params["locationbias"] = location_bias

    response = requests.get(
        "https://maps.googleapis.com/maps/api/place/findplacefromtext/json",
        params=params,
        timeout=12,
    )
    response.raise_for_status()
    candidates = response.json().get("candidates", [])

    results = []
    for candidate in candidates:
        geometry = candidate.get("geometry", {}).get("location", {})
        c_lat = geometry.get("lat")
        c_lon = geometry.get("lng")
        city_state = reverse_geocode_osm(c_lat, c_lon) if c_lat is not None and c_lon is not None else {"city": None, "state": None}
        distance_km = None
        if lat is not None and lon is not None and c_lat is not None and c_lon is not None:
            distance_km = round(calculate_haversine_distance(lat, lon, c_lat, c_lon), 2)

        results.append({
            "place_id": candidate.get("place_id", ""),
            "name": candidate.get("name", query),
            "address": candidate.get("formatted_address", ""),
            "city": city_state.get("city"),
            "state": city_state.get("state"),
            "latitude": c_lat,
            "longitude": c_lon,
            "distance_km": distance_km,
            "source": "Google Maps",
        })

    return results


def search_fallback_hospitals(query: str, lat: Optional[float] = None, lon: Optional[float] = None, city: str = ""):
    if lat is not None and lon is not None:
        center_lat, center_lon = lat, lon
        area_name = city or "Nearby"
    else:
        center_lat, center_lon = geocode_place(city or "Mumbai")
        area_name = city or "Mumbai"

    hospitals = [
        {
            "place_id": "fallback-hospital-1",
            "name": f"{area_name} Community Hospital",
            "address": f"450 Health Ave, {area_name}",
            "city": area_name,
            "state": None,
            "latitude": center_lat - 0.015,
            "longitude": center_lon + 0.018,
            "source": "Fallback",
        },
        {
            "place_id": "fallback-hospital-2",
            "name": f"{area_name} General Hospital",
            "address": f"12 Medical Plaza, {area_name}",
            "city": area_name,
            "state": None,
            "latitude": center_lat - 0.005,
            "longitude": center_lon - 0.022,
            "source": "Fallback",
        },
        {
            "place_id": "fallback-hospital-3",
            "name": f"St. Jude Hospital - {area_name}",
            "address": f"88 Relief Road, {area_name}",
            "city": area_name,
            "state": None,
            "latitude": center_lat + 0.012,
            "longitude": center_lon - 0.003,
            "source": "Fallback",
        },
    ]

    query_lower = query.strip().lower()
    filtered = [h for h in hospitals if query_lower in h["name"].lower() or query_lower in h["address"].lower()] if query_lower else hospitals
    for hospital in filtered:
        if lat is not None and lon is not None:
            hospital["distance_km"] = round(calculate_haversine_distance(lat, lon, hospital["latitude"], hospital["longitude"]), 2)
        else:
            hospital["distance_km"] = None
    return filtered[:8]


# ==========================================
# SEED MOCK DATA ON STARTUP
# ==========================================
@app.on_event("startup")
def seed_mock_data():
    db = SessionLocal = Session(bind=engine)
    try:
        # Check if users already exist
        if db.query(User).count() == 0:
            print("Seeding database with default users and mock donors...")
            
            # Admin User
            admin = User(
                email="admin@liferush.ai",
                phone="1234567890",
                name="System Admin",
                password_hash=get_password_hash("admin123"),
                role="admin",
                city="San Francisco",
                state="CA"
            )
            db.add(admin)
            
            # Patient User
            patient = User(
                email="hospital@liferush.ai",
                phone="9876543210",
                name="St. Jude Hospital",
                password_hash=get_password_hash("hospital123"),
                role="patient",
                city="San Francisco",
                state="CA"
            )
            db.add(patient)

            # Mock Donors
            mock_donors = [
                {"name": "Alice Johnson", "email": "alice@gmail.com", "phone": "1112223333", "bg": "O+", "city": "San Francisco", "state": "CA", "hb": 14.2, "plt": 240000},
                {"name": "Bob Smith", "email": "bob@gmail.com", "phone": "4445556666", "bg": "O-", "city": "San Francisco", "state": "CA", "hb": 15.1, "plt": 180000},
                {"name": "Charlie Brown", "email": "charlie@gmail.com", "phone": "7778889999", "bg": "A+", "city": "Oakland", "state": "CA", "hb": 13.8, "plt": 290000},
                {"name": "David Miller", "email": "david@gmail.com", "phone": "2223334444", "bg": "B+", "city": "San Jose", "state": "CA", "hb": 14.8, "plt": 210000},
                {"name": "Emma Watson", "email": "emma@gmail.com", "phone": "5556667777", "bg": "AB+", "city": "Berkeley", "state": "CA", "hb": 13.0, "plt": 260000},
                {"name": "Frank Castle", "email": "frank@gmail.com", "phone": "8889990000", "bg": "O-", "city": "San Mateo", "state": "CA", "hb": 16.2, "plt": 270000},
                {"name": "Grace Hopper", "email": "grace@gmail.com", "phone": "9990001111", "bg": "A-", "city": "Oakland", "state": "CA", "hb": 11.5, "plt": 190000}, # Ineligible (hb low)
                {"name": "Henry Cavill", "email": "henry@gmail.com", "phone": "3334445555", "bg": "O+", "city": "Daly City", "state": "CA", "hb": 14.0, "plt": 130000}, # Ineligible (plt low)
            ]

            for d_info in mock_donors:
                donor = User(
                    name=d_info["name"],
                    email=d_info["email"],
                    phone=d_info["phone"],
                    password_hash=get_password_hash("donor123"),
                    role="donor",
                    blood_group=d_info["bg"],
                    city=d_info["city"],
                    state=d_info["state"]
                )
                db.add(donor)
                db.commit()
                db.refresh(donor)
                
                # Eligibility evaluation
                elig_status = (d_info["hb"] >= 12.5) and (d_info["plt"] >= 150000)
                reason = None
                if d_info["hb"] < 12.5:
                    reason = "Low Hemoglobin levels"
                if d_info["plt"] < 150000:
                    reason = "Low platelet count"
                    
                report = MedicalReport(
                    user_id=donor.id,
                    blood_group_extracted=d_info["bg"],
                    hemoglobin=d_info["hb"],
                    platelets=d_info["plt"],
                    wbc_count=6800.0,
                    last_donation_date=date.today() - timedelta(days=90),
                    is_eligible=elig_status,
                    ineligibility_reason=reason,
                    next_eligible_date=date.today(),
                    risk_level="Low" if elig_status else "Medium"
                )
                db.add(report)
                
            db.commit()
            print("Mock database seeding completed.")
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()


# ==========================================
# AUTH ENDPOINTS
# ==========================================

@app.post(f"{settings.API_V1_STR}/auth/register", response_model=schemas.UserOut)
async def register(
    email: str = Form(...),
    password: str = Form(...),
    name: str = Form(...),
    phone: str = Form(...),
    role: str = Form(...),
    blood_group: Optional[str] = Form(None),
    city: str = Form(...),
    state: str = Form(...),
    report: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    # Check duplicate email
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email is already registered")
        
    # Check duplicate phone
    if db.query(User).filter(User.phone == phone).first():
        raise HTTPException(status_code=400, detail="Phone number is already registered")

    # Hash Password
    pw_hash = get_password_hash(password)
    
    # Create User
    db_user = User(
        email=email,
        name=name,
        phone=phone,
        password_hash=pw_hash,
        role=role,
        blood_group=blood_group,
        city=city,
        state=state
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Process Uploaded Medical Report (if any)
    if report and role == "donor":
        # Save file to uploads folder
        file_ext = os.path.splitext(report.filename)[1]
        save_path = os.path.join(settings.UPLOAD_DIR, f"{db_user.id}_report{file_ext}")
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(report.file, buffer)
            
        # Analyze medical report
        raw_extraction = extract_medical_report(save_path)
        eligibility_results = determine_eligibility(raw_extraction)
        
        # Save Report in Database
        report_record = MedicalReport(
            user_id=db_user.id,
            file_path=save_path,
            blood_group_extracted=eligibility_results["blood_group_extracted"],
            hemoglobin=eligibility_results["hemoglobin"],
            platelets=eligibility_results["platelets"],
            wbc_count=eligibility_results["wbc_count"],
            last_donation_date=eligibility_results["last_donation_date"],
            diagnosis=eligibility_results["diagnosis"],
            is_eligible=eligibility_results["is_eligible"],
            ineligibility_reason=eligibility_results["ineligibility_reason"],
            next_eligible_date=eligibility_results["next_eligible_date"],
            risk_level=eligibility_results["risk_level"]
        )
        db.add(report_record)
        
        # Update User's Blood Group based on OCR if user blood group was not entered
        if not db_user.blood_group:
            db_user.blood_group = eligibility_results["blood_group_extracted"]
            
        db.commit()
        db.refresh(db_user)
        
    return db_user

@app.post(f"{settings.API_V1_STR}/auth/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
        
    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "user_name": user.name,
        "user_id": user.id
    }

@app.post(f"{settings.API_V1_STR}/auth/forgot-password")
def forgot_password(req: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email address not found")
    
    user.password_hash = get_password_hash(req.new_password)
    db.commit()
    return {"message": "Password updated successfully."}


# ==========================================
# DONOR MODULE ENDPOINTS
# ==========================================

@app.get(f"{settings.API_V1_STR}/donors/eligibility", response_model=schemas.MedicalReportOut)
def get_donor_eligibility(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Find latest medical report
    report = db.query(MedicalReport).filter(MedicalReport.user_id == current_user.id).order_by(MedicalReport.extracted_at.desc()).first()
    if not report:
        # Generate default empty report values
        return schemas.MedicalReportOut(
            id="none",
            user_id=current_user.id,
            blood_group_extracted=current_user.blood_group or "Not analyzed",
            hemoglobin=0.0,
            platelets=0.0,
            wbc_count=0.0,
            diagnosis="No medical report uploaded yet.",
            is_eligible=False,
            ineligibility_reason="Please upload a medical report.",
            next_eligible_date=date.today(),
            risk_level="Unknown",
            extracted_at=datetime.utcnow()
        )
    return report

@app.get(f"{settings.API_V1_STR}/donors/history")
def get_donor_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Fetch total successful matches accepted by donor
    accepted_matches = db.query(Match).filter(
        Match.donor_id == current_user.id,
        Match.contact_status == "accepted"
    ).all()
    
    total_donations = len(accepted_matches)
    
    # Estimated lives saved (each donation can save up to 3 lives)
    lives_saved = total_donations * 3
    
    # Fetch latest report for donation date
    report = db.query(MedicalReport).filter(MedicalReport.user_id == current_user.id).order_by(MedicalReport.extracted_at.desc()).first()
    last_don_date = report.last_donation_date if report else None
    
    # Synthetic details for high-fidelity charts
    chart_data = [
        {"month": "Dec", "donations": min(total_donations, 1)},
        {"month": "Jan", "donations": min(total_donations, 2)},
        {"month": "Feb", "donations": min(total_donations, 2)},
        {"month": "Mar", "donations": min(total_donations, 3)},
        {"month": "Apr", "donations": total_donations},
    ]

    return {
        "total_donations": total_donations,
        "last_donation_date": last_don_date,
        "estimated_lives_saved": lives_saved,
        "chart_data": chart_data
    }

@app.get(f"{settings.API_V1_STR}/donors/notifications", response_model=List[schemas.NotificationOut])
def get_donor_notifications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).order_by(Notification.created_at.desc()).all()
    return notifications

@app.put(f"{settings.API_V1_STR}/donors/notifications/read")
def mark_notifications_read(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Notification).filter(Notification.user_id == current_user.id).update({"is_read": True})
    db.commit()
    return {"message": "All notifications marked as read"}


# ==========================================
# PATIENT / HOSPITAL ENDPOINTS
# ==========================================

@app.post(f"{settings.API_V1_STR}/patients/request", response_model=schemas.BloodRequestOut)
def create_blood_request(req_data: schemas.BloodRequestCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lat = req_data.latitude
    lon = req_data.longitude
    if lat is None or lon is None:
        lat, lon = geocode_place(req_data.hospital_location)
    
    blood_request = BloodRequest(
        requester_id=current_user.id,
        blood_group=req_data.blood_group,
        units_needed=req_data.units_needed,
        hospital_name=req_data.hospital_name,
        hospital_location=req_data.hospital_location,
        hospital_address=req_data.hospital_address,
        hospital_place_id=req_data.hospital_place_id,
        latitude=lat,
        longitude=lon,
        urgency_level=req_data.urgency_level,
        contact_number=req_data.contact_number
    )
    db.add(blood_request)
    db.commit()
    db.refresh(blood_request)
    
    # Run AI Donor Matching and notification routing
    from backend.app.telephony import trigger_matching_and_alerts
    trigger_matching_and_alerts(db, blood_request.id)
    
    return blood_request

@app.post(f"{settings.API_V1_STR}/patients/sos", response_model=schemas.BloodRequestOut)
def trigger_sos(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Emergency SOS workflow: Retrieve saved hospital details and trigger SOS.
    """
    # Create request based on patient user profile
    bg = current_user.blood_group or "O+"  # Default to O+ if unknown
    
    blood_request = BloodRequest(
        requester_id=current_user.id,
        blood_group=bg,
        units_needed=2, # Default SOS to 2 units
        hospital_name=f"{current_user.name} (Emergency SOS)",
        hospital_location=f"{current_user.city}, {current_user.state}",
        latitude=None, # will resolve in ranking
        longitude=None,
        urgency_level="critical",
        contact_number=current_user.phone
    )
    db.add(blood_request)
    db.commit()
    db.refresh(blood_request)
    
    # Trigger ranking and notify
    from backend.app.telephony import trigger_matching_and_alerts
    trigger_matching_and_alerts(db, blood_request.id)
    
    return blood_request

@app.get(f"{settings.API_V1_STR}/patients/requests", response_model=List[schemas.BloodRequestOut])
def get_patient_requests(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(BloodRequest).filter(BloodRequest.requester_id == current_user.id).order_by(BloodRequest.created_at.desc()).all()


@app.get(f"{settings.API_V1_STR}/maps/hospitals/search", response_model=List[schemas.HospitalSearchOut])
def search_hospitals(
    q: str,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    city: str = "",
):
    trimmed_query = q.strip()
    if len(trimmed_query) < 2:
        return []

    try:
        results = search_google_hospitals(trimmed_query, lat=lat, lon=lon)
        if results:
            return results
    except Exception:
        pass

    return search_fallback_hospitals(trimmed_query, lat=lat, lon=lon, city=city)

@app.get(f"{settings.API_V1_STR}/patients/requests/{{request_id}}/matches", response_model=List[schemas.MatchOut])
def get_request_matches(request_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    matches = db.query(Match).filter(Match.request_id == request_id).all()
    
    output = []
    # Resolve distance and donor information details
    req = db.query(BloodRequest).filter(BloodRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    patient_coords = get_city_coords(req.hospital_location)
    
    for m in matches:
        d = m.donor
        d_coords = get_city_coords(d.city, d.state)
        
        # Calculate Haversine distance
        from backend.app.ai_engine import calculate_haversine_distance
        dist = calculate_haversine_distance(patient_coords[0], patient_coords[1], d_coords[0], d_coords[1])
        
        m_out = schemas.MatchOut(
            id=m.id,
            request_id=m.request_id,
            donor_id=m.donor_id,
            score=m.score,
            contact_status=m.contact_status,
            eta=m.eta,
            notified_at=m.notified_at,
            response_at=m.response_at,
            donor_name=d.name,
            donor_phone=d.phone,
            donor_blood_group=d.blood_group,
            donor_city=d.city,
            distance_km=round(dist, 2)
        )
        output.append(m_out)
        
    # Sort matches by AI score descending
    output.sort(key=lambda x: x.score, reverse=True)
    return output

@app.put(f"{settings.API_V1_STR}/patients/matches/{{match_id}}", response_model=schemas.MatchOut)
def update_match_status(match_id: str, match_update: schemas.MatchUpdate, db: Session = Depends(get_db)):
    match_entry = db.query(Match).filter(Match.id == match_id).first()
    if not match_entry:
        raise HTTPException(status_code=404, detail="Match not found")
        
    match_entry.contact_status = match_update.contact_status
    if match_update.eta:
        match_entry.eta = match_update.eta
    match_entry.response_at = datetime.utcnow()
    
    # If accepted, create a system notification for the patient requester
    if match_update.contact_status == "accepted":
        req = match_entry.blood_request
        donor = match_entry.donor
        if req.requester_id:
            notif = Notification(
                user_id=req.requester_id,
                title="Donor Accepted Blood Request",
                message=f"Donor {donor.name} ({donor.blood_group}) has accepted your request. ETA: {match_entry.eta}.",
                type="system"
            )
            db.add(notif)
            
    db.commit()
    db.refresh(match_entry)
    
    # Generate Output
    d = match_entry.donor
    req = match_entry.blood_request
    p_coords = get_city_coords(req.hospital_location)
    d_coords = get_city_coords(d.city, d.state)
    from backend.app.ai_engine import calculate_haversine_distance
    dist = calculate_haversine_distance(p_coords[0], p_coords[1], d_coords[0], d_coords[1])
    
    return schemas.MatchOut(
        id=match_entry.id,
        request_id=match_entry.request_id,
        donor_id=match_entry.donor_id,
        score=match_entry.score,
        contact_status=match_entry.contact_status,
        eta=match_entry.eta,
        notified_at=match_entry.notified_at,
        response_at=match_entry.response_at,
        donor_name=d.name,
        donor_phone=d.phone,
        donor_blood_group=d.blood_group,
        donor_city=d.city,
        distance_km=round(dist, 2)
    )


# ==========================================
# MAP MODULE ENDPOINTS
# ==========================================

@app.get(f"{settings.API_V1_STR}/maps/nearby")
def get_nearby_places(
    city: str = "",
    state: str = "",
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radius_km: int = 10,
    place_type: str = "all",
):
    """
    Returns nearby hospitals, blood banks, and donation centers using OpenStreetMap data.
    Falls back to seeded demo data if the external lookup fails.
    """
    if lat is not None and lon is not None:
        center_lat, center_lon = lat, lon
    elif city:
        center_lat, center_lon = geocode_place(city, state)
    else:
        raise HTTPException(status_code=400, detail="Provide either lat/lon or a city")

    selected_types = list(PLACE_TYPE_CONFIG.keys()) if place_type == "all" else [place_type]

    try:
        places = fetch_nearby_osm_places(center_lat, center_lon, radius_km, selected_types)
        source = "OpenStreetMap"
    except Exception:
        places = build_fallback_places(city or "Your area", center_lat, center_lon)
        if place_type != "all":
            label = PLACE_TYPE_CONFIG.get(place_type, {}).get("label")
            if label:
                places = [place for place in places if place["type"] == label]
        source = "Fallback"

    return {
        "center": {"lat": center_lat, "lon": center_lon},
        "places": places,
        "source": source,
    }


# ==========================================
# ADMIN DASHBOARD ENDPOINTS
# ==========================================

@app.get(f"{settings.API_V1_STR}/admin/stats", dependencies=[Depends(check_role(["admin"]))])
def get_admin_stats(db: Session = Depends(get_db)):
    total_donors = db.query(User).filter(User.role == "donor").count()
    total_patients = db.query(User).filter(User.role == "patient").count()
    active_requests = db.query(BloodRequest).filter(BloodRequest.status == "pending").count()
    
    # Successful match count
    successful_matches = db.query(Match).filter(Match.contact_status == "accepted").count()
    
    # Group requests by blood group
    requests_by_bg = {}
    for bg in ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"]:
        count = db.query(BloodRequest).filter(BloodRequest.blood_group == bg).count()
        requests_by_bg[bg] = count

    # Group donors by location
    donors_by_city = {}
    donors = db.query(User).filter(User.role == "donor").all()
    for d in donors:
        donors_by_city[d.city] = donors_by_city.get(d.city, 0) + 1

    return {
        "total_donors": total_donors,
        "total_patients": total_patients,
        "active_requests": active_requests,
        "successful_matches": successful_matches,
        "requests_by_bg": requests_by_bg,
        "donors_by_city": donors_by_city
    }


# ==========================================
# CHATBOT & TELEPHONY SIMULATOR ENDPOINTS
# ==========================================

@app.post(f"{settings.API_V1_STR}/chatbot/query", response_model=schemas.ChatResponse)
def chatbot_query(chat_msg: schemas.ChatMessage):
    reply = query_chatbot(chat_msg.message)
    return {"reply": reply}

@app.post(f"{settings.API_V1_STR}/telephony/simulate")
def telephony_simulate(req: schemas.CallSimulationRequest):
    return simulate_toll_free_call(
        phone_number=req.phone_number,
        blood_group=req.blood_group,
        units_needed=req.units_needed,
        location=req.location
    )
