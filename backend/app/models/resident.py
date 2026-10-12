from sqlalchemy import Column, String, DateTime, Boolean, Date, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from .base import Base


class Resident(Base):
    __tablename__ = "residents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, unique=True)
    full_name = Column(String(255), nullable=False)
    dob = Column(Date, nullable=True)
    room_number = Column(String(50), nullable=True)
    emergency_contact = Column(Text, nullable=True)
    allergies = Column(Text, nullable=True)
    care_notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    deactivated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="resident_profile")
    prescriptions = relationship("Prescription", back_populates="resident")
    family_links = relationship("FamilyLink", back_populates="resident")
    caretaker_assignments = relationship("CaretakerAssignment", back_populates="resident")
