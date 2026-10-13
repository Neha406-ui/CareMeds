from datetime import date, datetime, time, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Query, Session

from app.models.dose import DoseOccurrence
from app.models.prescription import Prescription, PrescriptionStatus
from app.models.resident import Resident


def generate_dose_occurrences(
    db: Session,
    start_date: date,
    end_date: date,
    resident_ids: Query | None = None,
) -> int:
    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")

    query = db.query(Prescription).join(Resident).filter(
        Prescription.status == PrescriptionStatus.ACTIVE,
        Prescription.start_date <= end_date,
        (Prescription.end_date.is_(None) | (Prescription.end_date >= start_date)),
        Resident.is_active.is_(True),
    )
    if resident_ids is not None:
        query = query.filter(Resident.id.in_(resident_ids))
    prescriptions = query.all()

    records = []
    for prescription in prescriptions:
        zone = ZoneInfo(prescription.timezone)
        first_day = max(start_date, prescription.start_date)
        last_day = min(end_date, prescription.end_date or end_date)
        current_day = first_day
        while current_day <= last_day:
            for local_time in prescription.scheduled_times:
                scheduled_local = datetime.combine(
                    current_day,
                    time.fromisoformat(local_time),
                    tzinfo=zone,
                )
                scheduled_utc = scheduled_local.astimezone(timezone.utc)
                if scheduled_utc.astimezone(zone).replace(tzinfo=None) != scheduled_local.replace(tzinfo=None):
                    raise ValueError(
                        f"Scheduled time {local_time} does not exist on {current_day} in {prescription.timezone}"
                    )
                records.append({
                    "id": uuid4(),
                    "prescription_id": prescription.id,
                    "schedule_revision": prescription.schedule_revision,
                    "resident_id": prescription.resident_id,
                    "scheduled_for": scheduled_utc.replace(tzinfo=None),
                    "scheduled_date": current_day,
                    "scheduled_local_time": local_time,
                    "timezone": prescription.timezone,
                    "medicine_name": prescription.medicine.name,
                    "dosage": prescription.dosage,
                    "route": prescription.route,
                    "instructions": prescription.instructions,
                    "status": "scheduled",
                    "created_at": datetime.now(timezone.utc).replace(tzinfo=None),
                })
            current_day = date.fromordinal(current_day.toordinal() + 1)

    if not records:
        return 0
    dialect = db.bind.dialect.name if db.bind is not None else None
    table = DoseOccurrence.__table__
    if dialect == "postgresql":
        statement = pg_insert(table).values(records).on_conflict_do_nothing(
            index_elements=["prescription_id", "schedule_revision", "scheduled_for"]
        )
    elif dialect == "sqlite":
        statement = sqlite_insert(table).values(records).on_conflict_do_nothing(
            index_elements=["prescription_id", "schedule_revision", "scheduled_for"]
        )
    else:
        raise RuntimeError(f"Dose generation is unsupported for database dialect {dialect!r}")
    result = db.execute(statement)
    db.commit()
    return result.rowcount or 0
