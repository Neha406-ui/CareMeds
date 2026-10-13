from datetime import datetime
import uuid

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class DoseOccurrence(Base):
    __tablename__ = "dose_occurrences"
    __table_args__ = (
        UniqueConstraint(
            "prescription_id",
            "schedule_revision",
            "scheduled_for",
            name="uq_dose_prescription_revision_time",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prescription_id = Column(UUID(as_uuid=True), ForeignKey("prescriptions.id"), nullable=False)
    schedule_revision = Column(Integer, nullable=False)
    resident_id = Column(UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False)
    scheduled_for = Column(DateTime, nullable=False)
    scheduled_date = Column(Date, nullable=False)
    scheduled_local_time = Column(String(5), nullable=False)
    timezone = Column(String(64), nullable=False)
    medicine_name = Column(String(255), nullable=False)
    dosage = Column(String(100), nullable=False)
    route = Column(String(100), nullable=True)
    instructions = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="scheduled", server_default="scheduled")
    actual_at = Column(DateTime, nullable=True)
    recorded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    outcome_reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class DoseEvent(Base):
    __tablename__ = "dose_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dose_occurrence_id = Column(UUID(as_uuid=True), ForeignKey("dose_occurrences.id"), nullable=False)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    event_type = Column(String(32), nullable=False)
    previous_status = Column(String(32), nullable=True)
    new_status = Column(String(32), nullable=True)
    details = Column(Text, nullable=True)
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint(
            "dose_occurrence_id",
            "recipient_id",
            "notification_type",
            name="uq_notification_dose_recipient_type",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dose_occurrence_id = Column(UUID(as_uuid=True), ForeignKey("dose_occurrences.id"), nullable=False)
    recipient_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    notification_type = Column(String(32), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)


class EscalationEvent(Base):
    __tablename__ = "escalation_events"
    __table_args__ = (
        UniqueConstraint(
            "dose_occurrence_id",
            "recipient_id",
            name="uq_escalation_dose_recipient",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dose_occurrence_id = Column(UUID(as_uuid=True), ForeignKey("dose_occurrences.id"), nullable=False)
    recipient_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status = Column(String(16), nullable=False, default="open", server_default="open")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resolution_notes = Column(Text, nullable=True)
