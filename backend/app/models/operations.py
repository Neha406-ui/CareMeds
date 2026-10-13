from datetime import datetime
import uuid

from sqlalchemy import (
    CheckConstraint,
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


class InventoryBatch(Base):
    __tablename__ = "inventory_batches"
    __table_args__ = (
        UniqueConstraint("medicine_id", "lot_code", name="uq_inventory_medicine_lot"),
        CheckConstraint("quantity_remaining >= 0", name="ck_inventory_nonnegative"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    medicine_id = Column(UUID(as_uuid=True), ForeignKey("medicines.id"), nullable=False)
    lot_code = Column(String(120), nullable=False)
    expires_on = Column(Date, nullable=False)
    quantity_remaining = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("inventory_batches.id"), nullable=False)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    transaction_type = Column(String(16), nullable=False)
    quantity = Column(Integer, nullable=False)
    quantity_after = Column(Integer, nullable=False)
    reason = Column(Text, nullable=True)
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class FamilyContactRequest(Base):
    __tablename__ = "family_contact_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resident_id = Column(UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False)
    family_member_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(16), nullable=False, default="pending", server_default="pending")
    response = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    responded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)


class ShiftHandover(Base):
    __tablename__ = "shift_handovers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resident_id = Column(UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False)
    outgoing_caretaker_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    incoming_caretaker_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    shift_started_at = Column(DateTime, nullable=False)
    shift_ended_at = Column(DateTime, nullable=False)
    notes = Column(Text, nullable=False)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String(64), nullable=False)
    resource_type = Column(String(64), nullable=False)
    resource_id = Column(String(64), nullable=True)
    details = Column(Text, nullable=True)
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow)
