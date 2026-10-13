from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.assignment import CaretakerAssignment, DoctorAssignment
from app.models.dose import DoseOccurrence, EscalationEvent, Notification
from app.models.family import FamilyLink
from app.models.resident import Resident
from app.models.user import User, UserRole
from app.services.scheduling import generate_dose_occurrences


def _insert_idempotently(db: Session, model, records: list[dict], conflict_columns: list[str]) -> int:
    if not records:
        return 0
    dialect = db.bind.dialect.name if db.bind is not None else None
    if dialect == "postgresql":
        statement = pg_insert(model.__table__).values(records).on_conflict_do_nothing(
            index_elements=conflict_columns
        )
    elif dialect == "sqlite":
        statement = sqlite_insert(model.__table__).values(records).on_conflict_do_nothing(
            index_elements=conflict_columns
        )
    else:
        raise RuntimeError(f"Reminder processing is unsupported for database dialect {dialect!r}")
    return db.execute(statement).rowcount or 0


def run_reminder_cycle(db: Session, now: datetime | None = None) -> dict[str, int]:
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    if now.tzinfo is not None:
        now = now.astimezone(timezone.utc).replace(tzinfo=None)
    first_day = now.date() - timedelta(days=1)
    last_day = now.date() + timedelta(days=7)
    generated = generate_dose_occurrences(db, first_day, last_day)
    reminder_cutoff = now + timedelta(minutes=settings.DOSE_REMINDER_LEAD_MINUTES)
    doses = db.query(DoseOccurrence).join(
        Resident, Resident.id == DoseOccurrence.resident_id
    ).filter(
        Resident.is_active.is_(True),
        DoseOccurrence.status == "scheduled",
        DoseOccurrence.scheduled_for <= reminder_cutoff,
    ).all()

    notifications = []
    escalations = []
    for dose in doses:
        if dose.scheduled_for > now:
            notification_type = "dose_upcoming"
            recipient_ids = set()
        elif dose.scheduled_for + timedelta(minutes=settings.DOSE_OVERDUE_GRACE_MINUTES) < now:
            notification_type = "dose_overdue"
            recipient_ids = set()
        else:
            notification_type = "dose_due"
            recipient_ids = set()

        resident = db.get(Resident, dose.resident_id)
        if resident is None:
            continue
        if notification_type != "dose_overdue" and resident.user_id is not None:
            resident_user = db.get(User, resident.user_id)
            if resident_user is not None and resident_user.is_active:
                recipient_ids.add(resident_user.id)

        assignments = db.query(CaretakerAssignment.caretaker_id).filter(
            CaretakerAssignment.resident_id == dose.resident_id,
            CaretakerAssignment.is_active.is_(True),
        ).all()
        doctor_assignments = db.query(DoctorAssignment.doctor_id).filter(
            DoctorAssignment.resident_id == dose.resident_id,
            DoctorAssignment.is_active.is_(True),
        ).all()
        for (user_id,) in assignments + doctor_assignments:
            recipient = db.get(User, user_id)
            if recipient is not None and recipient.is_active:
                recipient_ids.add(user_id)

        links = db.query(FamilyLink).join(
            User, User.id == FamilyLink.family_member_id
        ).filter(
            FamilyLink.resident_id == dose.resident_id,
            FamilyLink.is_active.is_(True),
            FamilyLink.consent_granted.is_(True),
            FamilyLink.can_view_prescriptions.is_(True),
            FamilyLink.consent_granted_at.is_not(None),
            FamilyLink.consent_granted_by.is_not(None),
            FamilyLink.consent_revoked_at.is_(None),
            User.is_active.is_(True),
        ).all()
        recipient_ids.update(link.family_member_id for link in links)

        if not recipient_ids and notification_type == "dose_overdue":
            recipient_ids.update(
                user.id for user in db.query(User).filter(
                    User.role == UserRole.ADMIN,
                    User.is_active.is_(True),
                ).all()
            )

        message = (
            "A scheduled dose is approaching."
            if notification_type == "dose_upcoming"
            else "A scheduled dose is due; record the outcome when known."
            if notification_type == "dose_due"
            else "A dose remains unresolved after its grace period. Review it; it has not been classified as missed."
        )
        for recipient_id in recipient_ids:
            notifications.append({
                "id": uuid4(),
                "dose_occurrence_id": dose.id,
                "recipient_id": recipient_id,
                "notification_type": notification_type,
                "message": message,
                "created_at": now,
            })
            if notification_type == "dose_overdue":
                escalations.append({
                    "id": uuid4(),
                    "dose_occurrence_id": dose.id,
                    "recipient_id": recipient_id,
                    "status": "open",
                    "created_at": now,
                })

    notification_count = _insert_idempotently(
        db,
        Notification,
        notifications,
        ["dose_occurrence_id", "recipient_id", "notification_type"],
    )
    escalation_count = _insert_idempotently(
        db,
        EscalationEvent,
        escalations,
        ["dose_occurrence_id", "recipient_id"],
    )
    db.commit()
    return {
        "occurrences_created": generated,
        "notifications_created": notification_count,
        "escalations_created": escalation_count,
    }
