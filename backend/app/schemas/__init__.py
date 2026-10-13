from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing import Optional
from datetime import date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from app.models.user import UserRole
from app.models.prescription import PrescriptionStatus


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UserBase(BaseModel):
    username: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: UserRole
    is_active: bool = True


class UserCreate(InputModel):
    username: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=12, max_length=72)
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: UserRole

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        username = value.strip()
        if not username:
            raise ValueError("username must not be blank")
        return username

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("password must be at most 72 UTF-8 bytes")
        return value


class UserStatusUpdate(InputModel):
    is_active: bool


class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    last_login_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ResidentBase(InputModel):
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

    model_config = ConfigDict(from_attributes=True)


class MedicineBase(InputModel):
    name: str
    strength: Optional[str] = None
    form: Optional[str] = None
    manufacturer: Optional[str] = None
    reorder_level: int = Field(default=0, ge=0, le=1000000)


class MedicineCreate(MedicineBase):
    pass


class MedicineResponse(MedicineBase):
    id: UUID
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PrescriptionBase(InputModel):
    medicine_id: UUID
    dosage: str
    route: Optional[str] = None
    frequency: str
    scheduled_times: list[str] = Field(min_length=1, max_length=12)
    timezone: str = "UTC"
    instructions: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None

    @model_validator(mode="after")
    def validate_schedule(self):
        if any(
            len(value) != 5 or value[2] != ":" or not value[:2].isdigit()
            or not value[3:].isdigit() or int(value[:2]) > 23 or int(value[3:]) > 59
            for value in self.scheduled_times
        ):
            raise ValueError("scheduled_times must use 24-hour HH:MM values")
        if len(set(self.scheduled_times)) != len(self.scheduled_times):
            raise ValueError("scheduled_times must not contain duplicates")
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("timezone must be a valid IANA time zone")
        return self


class PrescriptionCreate(PrescriptionBase):
    resident_id: UUID


class PrescriptionUpdate(InputModel):
    dosage: Optional[str] = None
    route: Optional[str] = None
    frequency: Optional[str] = None
    scheduled_times: Optional[list[str]] = Field(default=None, min_length=1, max_length=12)
    timezone: Optional[str] = None
    instructions: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.scheduled_times is not None and any(
            len(value) != 5 or value[2] != ":" or not value[:2].isdigit()
            or not value[3:].isdigit() or int(value[:2]) > 23 or int(value[3:]) > 59
            for value in self.scheduled_times
        ):
            raise ValueError("scheduled_times must use 24-hour HH:MM values")
        if self.scheduled_times is not None and len(set(self.scheduled_times)) != len(self.scheduled_times):
            raise ValueError("scheduled_times must not contain duplicates")
        if self.timezone is not None:
            try:
                ZoneInfo(self.timezone)
            except (ZoneInfoNotFoundError, ValueError):
                raise ValueError("timezone must be a valid IANA time zone")
        return self


class PrescriptionDiscontinue(InputModel):
    reason: str


class AssignmentCreate(InputModel):
    user_id: UUID


class FamilyConsentCreate(InputModel):
    family_member_id: UUID
    relationship_type: Optional[str] = None
    can_view_profile: bool
    can_view_prescriptions: bool

    @model_validator(mode="after")
    def require_access_scope(self):
        if not self.can_view_profile and not self.can_view_prescriptions:
            raise ValueError("Grant at least one family access permission")
        return self


class FamilyConsentUpdate(InputModel):
    can_view_profile: bool
    can_view_prescriptions: bool

    @model_validator(mode="after")
    def require_access_scope(self):
        if not self.can_view_profile and not self.can_view_prescriptions:
            raise ValueError("Grant at least one family access permission")
        return self


class PrescriptionResponse(PrescriptionBase):
    id: UUID
    resident_id: UUID
    doctor_id: UUID
    status: PrescriptionStatus
    prescribed_at: datetime
    discontinued_at: Optional[datetime] = None
    discontinued_by: Optional[UUID] = None
    discontinuation_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DoseOutcomeCreate(InputModel):
    status: str
    reason: Optional[str] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_outcome(self):
        allowed = {"administered", "refused", "withheld", "not_administered", "unable_to_confirm"}
        if self.status not in allowed:
            raise ValueError("Unsupported dose outcome")
        if self.status != "administered" and not (self.reason and self.reason.strip()):
            raise ValueError("A reason is required for this dose outcome")
        return self


class EscalationResolution(InputModel):
    notes: str = Field(min_length=1, max_length=2000)


class InventoryStockIn(InputModel):
    medicine_id: UUID
    lot_code: str = Field(min_length=1, max_length=120)
    expires_on: date
    quantity: int = Field(gt=0, le=1000000)
    reason: Optional[str] = Field(default=None, max_length=2000)


class InventoryStockOut(InputModel):
    quantity: int = Field(gt=0, le=1000000)
    reason: str = Field(min_length=1, max_length=2000)


class FamilyContactCreate(InputModel):
    resident_id: UUID
    message: str = Field(min_length=1, max_length=4000)


class FamilyContactUpdate(InputModel):
    status: str
    response: str = Field(min_length=1, max_length=4000)

    @model_validator(mode="after")
    def validate_status(self):
        if self.status not in {"received", "resolved"}:
            raise ValueError("status must be received or resolved")
        return self


class ShiftHandoverCreate(InputModel):
    resident_id: UUID
    incoming_caretaker_id: UUID
    shift_started_at: datetime
    shift_ended_at: datetime
    notes: str = Field(min_length=1, max_length=4000)

    @model_validator(mode="after")
    def validate_shift(self):
        if (
            self.shift_started_at.tzinfo is None
            or self.shift_started_at.utcoffset() is None
            or self.shift_ended_at.tzinfo is None
            or self.shift_ended_at.utcoffset() is None
        ):
            raise ValueError("shift timestamps must include a UTC offset")
        if self.shift_ended_at <= self.shift_started_at:
            raise ValueError("shift_ended_at must be after shift_started_at")
        return self
