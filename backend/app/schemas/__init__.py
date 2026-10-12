from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from uuid import UUID
from app.models.user import UserRole
from app.models.prescription import PrescriptionStatus


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class UserBase(BaseModel):
    username: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: UserRole
    is_active: bool = True


class UserCreate(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: UserRole


class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ResidentBase(BaseModel):
    full_name: str
    dob: Optional[date] = None
    room_number: Optional[str] = None
    emergency_contact: Optional[str] = None
    allergies: Optional[str] = None
    care_notes: Optional[str] = None


class ResidentCreate(ResidentBase):
    user_id: Optional[UUID] = None


class ResidentUpdate(ResidentBase):
    full_name: Optional[str] = None
    dob: Optional[date] = None
    room_number: Optional[str] = None
    emergency_contact: Optional[str] = None
    allergies: Optional[str] = None
    care_notes: Optional[str] = None
    is_active: Optional[bool] = None


class ResidentResponse(ResidentBase):
    id: UUID
    user_id: Optional[UUID] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MedicineBase(BaseModel):
    name: str
    strength: Optional[str] = None
    form: Optional[str] = None
    manufacturer: Optional[str] = None


class MedicineCreate(MedicineBase):
    pass


class MedicineResponse(MedicineBase):
    id: UUID
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PrescriptionBase(BaseModel):
    medicine_id: UUID
    dosage: str
    route: Optional[str] = None
    frequency: str
    instructions: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None


class PrescriptionCreate(PrescriptionBase):
    resident_id: UUID


class PrescriptionUpdate(BaseModel):
    dosage: Optional[str] = None
    route: Optional[str] = None
    frequency: Optional[str] = None
    instructions: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[PrescriptionStatus] = None


class PrescriptionResponse(PrescriptionBase):
    id: UUID
    resident_id: UUID
    doctor_id: UUID
    status: PrescriptionStatus
    prescribed_at: datetime
    discontinued_at: Optional[datetime] = None
    discontinued_by: Optional[UUID] = None
    discontinuation_reason: Optional[str] = None

    class Config:
        from_attributes = True
