from sqlalchemy.orm import Session
from datetime import datetime
import logging
from backend.app.config import settings
from backend.app.database import SessionLocal
from backend.app.models import User, BloodRequest, Match, Notification
from backend.app.ai_engine import rank_donors, get_city_coords

logger = logging.getLogger(__name__)

# Map digits to blood groups for the IVR menu
DTMF_BLOOD_GROUPS = {
    "1": "O+",
    "2": "O-",
    "3": "A+",
    "4": "A-",
    "5": "B+",
    "6": "B-",
    "7": "AB+",
    "8": "AB-"
}

def trigger_matching_and_alerts(db: Session, request_id: str):
    """
    Ranks donors based on compatibility and triggers mock call notifications.
    """
    # 1. Fetch request details
    req = db.query(BloodRequest).filter(BloodRequest.id == request_id).first()
    if not req:
        return
    
    # Get all active eligible donors from DB
    donors = db.query(User).filter(User.role == "donor").all()
    
    # Retrieve donor profiles containing current eligibility reports
    donor_profiles = []
    for d in donors:
        # Check latest report
        latest_report = sorted(d.medical_reports, key=lambda x: x.extracted_at, reverse=True)
        is_eligible = True
        if latest_report:
            is_eligible = latest_report[0].is_eligible
            
        donor_profiles.append({
            "id": d.id,
            "name": d.name,
            "phone": d.phone,
            "email": d.email,
            "blood_group": d.blood_group,
            "city": d.city,
            "state": d.state,
            "is_eligible": is_eligible,
            "coords": get_city_coords(d.city, d.state),
            "past_acceptance_rate": 0.75,
            "availability": True,
            "age": 28
        })

    # Rank donors
    patient_coords = get_city_coords(req.hospital_location)
    ranked = rank_donors(
        patient_blood_group=req.blood_group,
        patient_coords=patient_coords,
        urgency_level=req.urgency_level,
        donors_list=donor_profiles
    )
    
    # Save Top 5 Matches
    for rank_idx, donor_profile in enumerate(ranked[:5]):
        # Check if already matched
        existing = db.query(Match).filter(
            Match.request_id == req.id,
            Match.donor_id == donor_profile["id"]
        ).first()
        
        if not existing:
            # Predict ETA
            eta_val = f"{10 + rank_idx * 5} mins"
            match_entry = Match(
                request_id=req.id,
                donor_id=donor_profile["id"],
                score=donor_profile["final_score"],
                contact_status="contacted", # Auto-contacted
                eta=eta_val
            )
            db.add(match_entry)
            
            # Send Notification alert to donor
            notification = Notification(
                user_id=donor_profile["id"],
                title="EMERGENCY SOS: Blood Donation Request",
                message=(
                    f"Urgent request for {req.blood_group} blood at {req.hospital_name}, "
                    f"{req.hospital_location}. Estimated ETA is {eta_val}. Can you donate? "
                    "Please reply or check dashboard."
                ),
                type="emergency"
            )
            db.add(notification)
            logger.info(f"Notification sent to donor {donor_profile['name']} for request {req.id}")
            
    db.commit()

def simulate_toll_free_call(phone_number: str, blood_group: str, units_needed: int, location: str) -> dict:
    """
    Simulates the execution of a toll-free call intake process.
    Returns the dialog log history and the created blood request metadata.
    """
    db = SessionLocal()
    try:
        # Resolve coordinates
        lat, lon = get_city_coords(location)
        
        # 1. Save request in database
        blood_request = BloodRequest(
            blood_group=blood_group,
            units_needed=units_needed,
            hospital_name="Toll-Free Call Emergency Intake",
            hospital_location=location,
            latitude=lat,
            longitude=lon,
            urgency_level="critical", # Phone intake defaults to critical
            contact_number=phone_number,
            status="pending"
        )
        db.add(blood_request)
        db.commit()
        db.refresh(blood_request)
        
        # 2. Trigger donor matching and notification engine
        trigger_matching_and_alerts(db, blood_request.id)
        
        # Compile call dialog log
        transcript = [
            {"speaker": "IVR System", "text": "Welcome to LifeRush AI Emergency Toll-Free Line."},
            {"speaker": "IVR System", "text": "Please enter your required blood group. (User entered: " + blood_group + ")"},
            {"speaker": "IVR System", "text": "Please enter the number of units needed. (User entered: " + str(units_needed) + ")"},
            {"speaker": "IVR System", "text": "Please speak your city name. (User spoke: " + location + ")"},
            {"speaker": "IVR System", "text": "Thank you. Your emergency request has been registered. AI Donor Matching has been initiated, and local eligible donors have been notified. Stay on the line to monitor response status."}
        ]
        
        return {
            "success": True,
            "request_id": blood_request.id,
            "blood_group": blood_request.blood_group,
            "units_needed": blood_request.units_needed,
            "location": blood_request.hospital_location,
            "contact_number": blood_request.contact_number,
            "urgency_level": blood_request.urgency_level,
            "transcript": transcript,
            "created_at": blood_request.created_at.isoformat()
        }
    except Exception as e:
        logger.error(f"Simulated IVR call failed: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()

# Example TwiML Generater Functions (if Twilio is hooked up)
def generate_twiml_welcome() -> str:
    """
    Generates TwiML XML to welcome caller and collect blood group digits.
    """
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Response>'
        '  <Say voice="alice">Welcome to LifeRush AI Emergency Line.</Say>'
        '  <Gather action="/api/v1/telephony/collect-blood-group" numDigits="1" timeout="10">'
        '    <Say voice="alice">Press 1 for O positive, 2 for O negative, 3 for A positive, 4 for A negative, 5 for B positive, 6 for B negative, 7 for AB positive, 8 for AB negative.</Say>'
        '  </Gather>'
        '  <Say voice="alice">We did not receive any input. Goodbye.</Say>'
        '  <Hangup/>'
        '</Response>'
    )
