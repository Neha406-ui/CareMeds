from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from .base import Base


class CaretakerAssignment(Base):
    __tablename__ = "caretaker_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    caretaker_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    resident_id = Column(UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    unassigned_at = Column(DateTime, nullable=True)

    caretaker = relationship("User", foreign_keys=[caretaker_id])
    assigner = relationship("User", foreign_keys=[assigned_by])
    resident = relationship("Resident", back_populates="caretaker_assignments")


class DoctorAssignment(Base):
    __tablename__ = "doctor_assignments"
    __table_args__ = (UniqueConstraint("doctor_id", "resident_id", name="uq_doctor_resident"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    resident_id = Column(UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    unassigned_at = Column(DateTime, nullable=True)

    doctor = relationship("User", foreign_keys=[doctor_id])
    assigner = relationship("User", foreign_keys=[assigned_by])
    resident = relationship("Resident")
