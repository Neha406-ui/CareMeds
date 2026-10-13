from datetime import date, datetime, timedelta, timezone
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import accessible_residents, get_current_user, require_role
from app.core.config import settings
from app.db.base import get_db
from app.models.assignment import CaretakerAssignment
from app.models.dose import DoseEvent, DoseOccurrence, EscalationEvent
from app.models.resident import Resident
from app.models.user import User, UserRole
from app.schemas import DoseOutcomeCreate
from app.services.audit import record_audit
from app.services.scheduling import generate_dose_occurrences

router = APIRouter()


def _timeliness(dose: DoseOccurrence, now: datetime) -> str:
    if dose.status != "scheduled":
        return dose.status
    if now < dose.scheduled_for - timedelta(minutes=30):
        return "scheduled"
    if now <= dose.scheduled_for + timedelta(minutes=settings.DOSE_OVERDUE_GRACE_MINUTES):
        return "due"
    return "overdue"


def _dose_response(dose: DoseOccurrence, now: datetime) -> dict:
    return {
        "id": str(dose.id),
        "prescription_id": str(dose.prescription_id),
        "resident_id": str(dose.resident_id),
        "scheduled_for": dose.scheduled_for,
        "scheduled_date": dose.scheduled_date,
        "scheduled_local_time": dose.scheduled_local_time,
        "timezone": dose.timezone,
        "medicine_name": dose.medicine_name,
        "dosage": dose.dosage,
        "route": dose.route,
        "instructions": dose.instructions,
        "status": dose.status,
        "timeliness": _timeliness(dose, now),
        "actual_at": dose.actual_at,
        "recorded_by": str(dose.recorded_by) if dose.recorded_by else None,
        "outcome_reason": dose.outcome_reason,
        "notes": dose.notes,
        "acknowledged_at": dose.acknowledged_at,
        "acknowledged_by": str(dose.acknowledged_by) if dose.acknowledged_by else None,
    }


def _accessible_dose_query(db: Session, user: User):
    resident_ids = accessible_residents(
        db,
        user,
        family_permission="can_view_prescriptions",
    ).with_entities(Resident.id)
    return db.query(DoseOccurrence).filter(DoseOccurrence.resident_id.in_(resident_ids))


@router.get("/doses")
def list_doses(
    start_date: date = Query(default_factory=lambda: datetime.now(timezone.utc).date()),
    end_date: date | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    end_date = end_date or start_date
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must be on or after start_date")
    if (end_date - start_date).days > 30:
        raise HTTPException(status_code=400, detail="Dose schedules may be requested for at most 31 days")
    authorized_residents = accessible_residents(
        db,
        current_user,
        family_permission="can_view_prescriptions",
    ).with_entities(Resident.id)
    try:
        generate_dose_occurrences(db, start_date, end_date, authorized_residents)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    rows = _accessible_dose_query(db, current_user).filter(
        DoseOccurrence.scheduled_date >= start_date,
        DoseOccurrence.scheduled_date <= end_date,
        DoseOccurrence.status != "cancelled",
    ).order_by(DoseOccurrence.scheduled_for).all()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return [_dose_response(dose, now) for dose in rows]


@router.post(
    "/doses/{dose_id}/outcome",
    dependencies=[Depends(require_role(UserRole.CARETAKER.value))],
)
def record_dose_outcome(
    dose_id: UUID,
    outcome: DoseOutcomeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dose = db.query(DoseOccurrence).join(
        Resident, Resident.id == DoseOccurrence.resident_id
    ).filter(
        DoseOccurrence.id == dose_id,
        Resident.is_active.is_(True),
    ).first()
    assignment = db.query(CaretakerAssignment.id).filter(
        CaretakerAssignment.caretaker_id == current_user.id,
        CaretakerAssignment.resident_id == (dose.resident_id if dose else None),
        CaretakerAssignment.is_active.is_(True),
    ).first()
    if dose is None or assignment is None:
        raise HTTPException(status_code=404, detail="Dose occurrence not found")
    if dose.status != "scheduled":
        raise HTTPException(status_code=409, detail="Dose outcome has already been recorded")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if dose.scheduled_for > now:
        raise HTTPException(status_code=409, detail="A future dose cannot be recorded")
    dose.status = outcome.status
    dose.actual_at = now if outcome.status == "administered" else None
    dose.recorded_by = current_user.id
    dose.outcome_reason = outcome.reason.strip() if outcome.reason else None
    dose.notes = outcome.notes.strip() if outcome.notes else None
    db.add(DoseEvent(
        dose_occurrence_id=dose.id,
        actor_id=current_user.id,
        event_type="outcome_recorded",
        previous_status="scheduled",
        new_status=outcome.status,
        details=json.dumps({"reason": dose.outcome_reason, "notes": dose.notes}),
        occurred_at=now,
    ))
    for escalation in db.query(EscalationEvent).filter(
        EscalationEvent.dose_occurrence_id == dose.id,
        EscalationEvent.status == "open",
    ).all():
        escalation.status = "resolved"
        escalation.resolved_at = now
        escalation.resolved_by = current_user.id
        escalation.resolution_notes = "Dose outcome recorded"
    record_audit(
        db,
        current_user.id,
        "dose_outcome_recorded",
        "dose_occurrence",
        dose.id,
        {"status": outcome.status},
    )
    db.commit()
    db.refresh(dose)
    return _dose_response(dose, now)


@router.post(
    "/doses/{dose_id}/acknowledge",
    dependencies=[Depends(require_role(UserRole.RESIDENT.value))],
)
def acknowledge_dose(
    dose_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dose = db.query(DoseOccurrence).join(
        Resident, Resident.id == DoseOccurrence.resident_id
    ).filter(
        DoseOccurrence.id == dose_id,
        Resident.user_id == current_user.id,
        Resident.is_active.is_(True),
    ).first()
    if dose is None:
        raise HTTPException(status_code=404, detail="Dose occurrence not found")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if dose.acknowledged_at is None:
        dose.acknowledged_at = now
        dose.acknowledged_by = current_user.id
        db.add(DoseEvent(
            dose_occurrence_id=dose.id,
            actor_id=current_user.id,
            event_type="reminder_acknowledged",
            occurred_at=now,
        ))
        record_audit(db, current_user.id, "dose_reminder_acknowledged", "dose_occurrence", dose.id)
        db.commit()
        db.refresh(dose)
    return _dose_response(dose, now)


@router.get("/doses/{dose_id}/history")
def dose_history(
    dose_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dose = _accessible_dose_query(db, current_user).filter(DoseOccurrence.id == dose_id).first()
    if dose is None:
        raise HTTPException(status_code=404, detail="Dose occurrence not found")
    return [
        {
            "event_type": event.event_type,
            "previous_status": event.previous_status,
            "new_status": event.new_status,
            "details": event.details,
            "occurred_at": event.occurred_at,
        }
        for event in db.query(DoseEvent).filter(
            DoseEvent.dose_occurrence_id == dose_id
        ).order_by(DoseEvent.occurred_at).all()
    ]
