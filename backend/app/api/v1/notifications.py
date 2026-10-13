from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import accessible_residents, get_current_user, require_role
from app.db.base import get_db
from app.models.assignment import CaretakerAssignment, DoctorAssignment
from app.models.dose import DoseOccurrence, EscalationEvent, Notification
from app.models.resident import Resident
from app.models.user import User, UserRole
from app.schemas import EscalationResolution
from app.services.audit import record_audit

router = APIRouter()


def _accessible_dose_ids(db: Session, user: User):
    return accessible_residents(
        db,
        user,
        family_permission="can_view_prescriptions",
    ).with_entities(Resident.id)


@router.get("/notifications")
def list_notifications(
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Notification).join(
        DoseOccurrence, DoseOccurrence.id == Notification.dose_occurrence_id
    ).filter(
        Notification.recipient_id == current_user.id,
        DoseOccurrence.resident_id.in_(_accessible_dose_ids(db, current_user)),
    )
    if unread_only:
        query = query.filter(Notification.read_at.is_(None))
    return [
        {
            "id": str(item.id),
            "dose_occurrence_id": str(item.dose_occurrence_id),
            "notification_type": item.notification_type,
            "message": item.message,
            "created_at": item.created_at,
            "read_at": item.read_at,
        }
        for item in query.order_by(Notification.created_at.desc()).limit(100).all()
    ]


@router.post("/notifications/{notification_id}/acknowledge")
def acknowledge_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notification = db.query(Notification).join(
        DoseOccurrence, DoseOccurrence.id == Notification.dose_occurrence_id
    ).filter(
        Notification.id == notification_id,
        Notification.recipient_id == current_user.id,
        DoseOccurrence.resident_id.in_(_accessible_dose_ids(db, current_user)),
    ).first()
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notification.read_at is None:
        notification.read_at = datetime.utcnow()
        record_audit(
            db,
            current_user.id,
            "notification_acknowledged",
            "notification",
            notification.id,
        )
        db.commit()
    return {"id": str(notification.id), "read_at": notification.read_at}


@router.get(
    "/escalations",
    dependencies=[Depends(require_role(
        UserRole.ADMIN.value,
        UserRole.DOCTOR.value,
        UserRole.CARETAKER.value,
    ))],
)
def list_escalations(
    open_only: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(EscalationEvent)
    if current_user.role != UserRole.ADMIN:
        query = query.join(
            DoseOccurrence, DoseOccurrence.id == EscalationEvent.dose_occurrence_id
        ).filter(
            DoseOccurrence.resident_id.in_(_accessible_dose_ids(db, current_user))
        )
    if open_only:
        query = query.filter(EscalationEvent.status == "open")
    return [
        {
            "id": str(item.id),
            "dose_occurrence_id": str(item.dose_occurrence_id),
            "recipient_id": str(item.recipient_id),
            "status": item.status,
            "created_at": item.created_at,
            "resolved_at": item.resolved_at,
            "resolved_by": str(item.resolved_by) if item.resolved_by else None,
            "resolution_notes": item.resolution_notes,
        }
        for item in query.order_by(EscalationEvent.created_at.desc()).limit(200).all()
    ]


@router.post(
    "/escalations/{escalation_id}/resolve",
    dependencies=[Depends(require_role(
        UserRole.ADMIN.value,
        UserRole.DOCTOR.value,
        UserRole.CARETAKER.value,
    ))],
)
def resolve_escalation(
    escalation_id: UUID,
    resolution: EscalationResolution,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(EscalationEvent).join(
        DoseOccurrence, DoseOccurrence.id == EscalationEvent.dose_occurrence_id
    )
    if current_user.role != UserRole.ADMIN:
        resident_ids = _accessible_dose_ids(db, current_user)
        query = query.filter(DoseOccurrence.resident_id.in_(resident_ids))
    escalation = query.filter(EscalationEvent.id == escalation_id).first()
    if escalation is None:
        raise HTTPException(status_code=404, detail="Escalation not found")
    if current_user.role == UserRole.CARETAKER:
        resident_id = db.query(DoseOccurrence.resident_id).filter(
            DoseOccurrence.id == escalation.dose_occurrence_id
        ).scalar()
        assigned = db.query(CaretakerAssignment.id).filter(
            CaretakerAssignment.caretaker_id == current_user.id,
            CaretakerAssignment.resident_id == resident_id,
            CaretakerAssignment.is_active.is_(True),
        ).first()
        if assigned is None:
            raise HTTPException(status_code=404, detail="Escalation not found")
    if current_user.role == UserRole.DOCTOR:
        resident_id = db.query(DoseOccurrence.resident_id).filter(
            DoseOccurrence.id == escalation.dose_occurrence_id
        ).scalar()
        assigned = db.query(DoctorAssignment.id).filter(
            DoctorAssignment.doctor_id == current_user.id,
            DoctorAssignment.resident_id == resident_id,
            DoctorAssignment.is_active.is_(True),
        ).first()
        if assigned is None:
            raise HTTPException(status_code=404, detail="Escalation not found")
    if escalation.status == "resolved":
        raise HTTPException(status_code=409, detail="Escalation is already resolved")
    now = datetime.utcnow()
    for open_event in db.query(EscalationEvent).filter(
        EscalationEvent.dose_occurrence_id == escalation.dose_occurrence_id,
        EscalationEvent.status == "open",
    ).all():
        open_event.status = "resolved"
        open_event.resolved_at = now
        open_event.resolved_by = current_user.id
        open_event.resolution_notes = resolution.notes.strip()
    record_audit(
        db,
        current_user.id,
        "escalation_resolved",
        "escalation",
        escalation.id,
        {"dose_occurrence_id": str(escalation.dose_occurrence_id)},
    )
    db.commit()
    return {"id": str(escalation.id), "status": "resolved"}
