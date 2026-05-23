from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, date

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    user_name: str
    user_id: str

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    name: str
    phone: str
    role: str = "donor"  # donor, patient, admin
    blood_group: Optional[str] = None
    city: str
    state: str

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    new_password: str

class UserOut(UserBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True

# MedicalReport schemas
class MedicalReportBase(BaseModel):
    blood_group_extracted: Optional[str] = None
    hemoglobin: Optional[float] = None
    platelets: Optional[float] = None
    wbc_count: Optional[float] = None
    last_donation_date: Optional[date] = None
    diagnosis: Optional[str] = None
    is_eligible: bool = True
    ineligibility_reason: Optional[str] = None
    next_eligible_date: Optional[date] = None
    risk_level: str = "Low"

class MedicalReportOut(MedicalReportBase):
    id: str
    user_id: str
    file_path: Optional[str] = None
    extracted_at: datetime

    class Config:
        from_attributes = True

# BloodRequest schemas
class BloodRequestCreate(BaseModel):
    blood_group: str
    units_needed: int = 1
    hospital_name: str
    hospital_location: str
    hospital_address: Optional[str] = None
    hospital_place_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    urgency_level: str = "medium"  # low, medium, critical
    contact_number: str

class BloodRequestOut(BaseModel):
    id: str
    requester_id: Optional[str] = None
    blood_group: str
    units_needed: int
    hospital_name: str
    hospital_location: str
    hospital_address: Optional[str] = None
    hospital_place_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    urgency_level: str
    contact_number: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

# Match schemas
class MatchOut(BaseModel):
    id: str
    request_id: str
    donor_id: str
    score: float
    contact_status: str
    eta: Optional[str] = None
    notified_at: datetime
    response_at: Optional[datetime] = None
    donor_name: Optional[str] = None
    donor_phone: Optional[str] = None
    donor_blood_group: Optional[str] = None
    donor_city: Optional[str] = None
    distance_km: Optional[float] = None

    class Config:
        from_attributes = True

class MatchUpdate(BaseModel):
    contact_status: str  # contacted, accepted, declined
    eta: Optional[str] = None

# Notification schemas
class NotificationOut(BaseModel):
    id: str
    user_id: str
    title: str
    message: str
    type: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Chatbot schemas
class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

# Telephony call simulation schema
class CallSimulationRequest(BaseModel):
    phone_number: str
    blood_group: str
    units_needed: int
    location: str


class HospitalSearchOut(BaseModel):
    place_id: str
    name: str
    address: str
    city: Optional[str] = None
    state: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    distance_km: Optional[float] = None
    source: str
