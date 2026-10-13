from sqlalchemy import Column, String, DateTime, Boolean, Date, Text, ForeignKey, Integer, Enum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
import enum

from .base import Base


class PrescriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    DISCONTINUED = "discontinued"
    EXPIRED = "expired"
    ON_HOLD = "on_hold"


class Medicine(Base):
    __tablename__ = "medicines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    strength = Column(String(100), nullable=True)
    form = Column(String(100), nullable=True)
    manufacturer = Column(String(255), nullable=True)
    reorder_level = Column(Integer, nullable=False, default=0, server_default="0")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    prescriptions = relationship("Prescription", back_populates="medicine")


class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resident_id = Column(UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    medicine_id = Column(UUID(as_uuid=True), ForeignKey("medicines.id"), nullable=False)
    dosage = Column(String(100), nullable=False)
    route = Column(String(100), nullable=True)
    frequency = Column(String(100), nullable=False)
    scheduled_times = Column(JSON, nullable=False, default=list, server_default="[]")
    timezone = Column(String(64), nullable=False, default="UTC", server_default="UTC")
    schedule_revision = Column(Integer, nullable=False, default=1, server_default="1")
    instructions = Column(Text, nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    status = Column(Enum(PrescriptionStatus), default=PrescriptionStatus.ACTIVE, nullable=False)
    prescribed_at = Column(DateTime, default=datetime.utcnow)
    discontinued_at = Column(DateTime, nullable=True)
    discontinued_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    discontinuation_reason = Column(Text, nullable=True)

    resident = relationship("Resident", back_populates="prescriptions")
    doctor = relationship("User", foreign_keys=[doctor_id])
    discontinuer = relationship("User", foreign_keys=[discontinued_by])
    medicine = relationship("Medicine", back_populates="prescriptions")
    history = relationship("PrescriptionHistory", back_populates="prescription", order_by="PrescriptionHistory.changed_at.desc()")


class PrescriptionHistory(Base):
    __tablename__ = "prescription_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prescription_id = Column(UUID(as_uuid=True), ForeignKey("prescriptions.id"), nullable=False)
    changed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    change_type = Column(String(100), nullable=False)
    before_state = Column(Text, nullable=True)
    after_state = Column(Text, nullable=True)
    changed_at = Column(DateTime, default=datetime.utcnow)

    prescription = relationship("Prescription", back_populates="history")
    actor = relationship("User", foreign_keys=[changed_by])
