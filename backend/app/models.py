import uuid
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="donor")  # donor, patient, admin
    blood_group = Column(String, nullable=True)             # A+, A-, B+, B-, AB+, AB-, O+, O-
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    medical_reports = relationship("MedicalReport", back_populates="user", cascade="all, delete-orphan")
    blood_requests = relationship("BloodRequest", back_populates="requester", cascade="all, delete-orphan")
    matches = relationship("Match", back_populates="donor", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")

class MedicalReport(Base):
    __tablename__ = "medical_reports"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    file_path = Column(String, nullable=True)
    blood_group_extracted = Column(String, nullable=True)
    hemoglobin = Column(Float, nullable=True)
    platelets = Column(Float, nullable=True)
    wbc_count = Column(Float, nullable=True)
    last_donation_date = Column(Date, nullable=True)
    diagnosis = Column(String, nullable=True)
    is_eligible = Column(Boolean, default=True)
    ineligibility_reason = Column(String, nullable=True)
    next_eligible_date = Column(Date, nullable=True)
    risk_level = Column(String, default="Low") # Low, Medium, High
    extracted_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="medical_reports")

class BloodRequest(Base):
    __tablename__ = "blood_requests"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    requester_id = Column(String, ForeignKey("users.id"), nullable=True)  # Nullable if request created via phone call
    blood_group = Column(String, nullable=False)
    units_needed = Column(Integer, nullable=False, default=1)
    hospital_name = Column(String, nullable=False)
    hospital_location = Column(String, nullable=False)  # City/Address
    hospital_address = Column(String, nullable=True)
    hospital_place_id = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    urgency_level = Column(String, nullable=False, default="medium")  # low, medium, critical
    contact_number = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending, partial, fulfilled, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    requester = relationship("User", back_populates="blood_requests")
    matches = relationship("Match", back_populates="blood_request", cascade="all, delete-orphan")

class Match(Base):
    __tablename__ = "matches"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    request_id = Column(String, ForeignKey("blood_requests.id"), nullable=False)
    donor_id = Column(String, ForeignKey("users.id"), nullable=False)
    score = Column(Float, nullable=False, default=0.0)
    contact_status = Column(String, default="pending")  # pending, contacted, accepted, declined, expired
    eta = Column(String, nullable=True)                 # e.g., "15 mins"
    notified_at = Column(DateTime, default=datetime.utcnow)
    response_at = Column(DateTime, nullable=True)
    
    # Relationships
    blood_request = relationship("BloodRequest", back_populates="matches")
    donor = relationship("User", back_populates="matches")

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    type = Column(String, default="system")  # emergency, reminder, system
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="notifications")
