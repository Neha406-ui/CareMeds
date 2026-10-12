from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from .base import Base


class FamilyLink(Base):
    __tablename__ = "family_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resident_id = Column(UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False)
    family_member_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    consent_granted = Column(Boolean, default=True)
    consent_granted_at = Column(DateTime, default=datetime.utcnow)
    consent_revoked_at = Column(DateTime, nullable=True)
    consent_revoked_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    relationship_type = Column(String(100), nullable=True)

    resident = relationship("Resident", back_populates="family_links")
    family_member = relationship("User", back_populates="family_links")
