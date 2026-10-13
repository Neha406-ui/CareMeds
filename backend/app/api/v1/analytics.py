from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import accessible_residents, get_current_user
from app.db.base import get_db
from app.models.dose import DoseOccurrence
from app.models.resident import Resident
from app.models.user import User

router = APIRouter()
OUTCOMES = (
    "administered",
    "refused",
    "withheld",
    "not_administered",
    "unable_to_confirm",
)


def _new_counts() -> dict[str, int]:
    return {
        "administered": 0,
        "refused": 0,
        "withheld": 0,
        "not_administered": 0,
        "unable_to_confirm": 0,
        "unresolved": 0,
    }


def _report(counts: dict[str, int], cancelled: int) -> dict:
    total = sum(counts.values())
    recorded = sum(counts[outcome] for outcome in OUTCOMES)
    return {
        "total_doses": total,
        "recorded_doses": recorded,
        "cancelled_doses": cancelled,
        "adherence_rate_percent": round(counts["administered"] / total * 100, 2) if total else None,
        "counts": counts,
    }


@router.get("/analytics/adherence")
def adherence_report(
    start_date: date = Query(default_factory=lambda: datetime.now(timezone.utc).date() - timedelta(days=29)),
    end_date: date = Query(default_factory=lambda: datetime.now(timezone.utc).date()),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must be on or before end_date")
    if (end_date - start_date).days > 365:
        raise HTTPException(status_code=400, detail="Adherence reports are limited to 366 days")

    resident_query = accessible_residents(
        db,
        current_user,
        family_permission="can_view_prescriptions",
    )
    residents = resident_query.all()
    if current_user.role.value == "family_member":
        profile_ids = accessible_residents(
            db,
            current_user,
            family_permission="can_view_profile",
        ).with_entities(Resident.id)
        resident_names = {
            str(resident.id): resident.full_name
            for resident in db.query(Resident).filter(Resident.id.in_(profile_ids)).all()
        }
    else:
        resident_names = {str(resident.id): resident.full_name for resident in residents}
    resident_ids = resident_query.with_entities(Resident.id)
    occurrences = db.query(DoseOccurrence).filter(
        DoseOccurrence.resident_id.in_(resident_ids),
        DoseOccurrence.scheduled_date >= start_date,
        DoseOccurrence.scheduled_date <= end_date,
    ).all()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    all_counts = _new_counts()
    cancelled_count = 0
    per_resident: dict[str, dict] = defaultdict(lambda: {
        "resident_name": "",
        "counts": _new_counts(),
        "cancelled_doses": 0,
    })
    for occurrence in occurrences:
        resident_key = str(occurrence.resident_id)
        detail = per_resident[resident_key]
        detail["resident_name"] = resident_names.get(resident_key)
        if occurrence.status == "cancelled":
            cancelled_count += 1
            detail["cancelled_doses"] += 1
            continue
        if occurrence.scheduled_for > now:
            continue
        count_key = occurrence.status if occurrence.status in OUTCOMES else "unresolved"
        all_counts[count_key] += 1
        detail["counts"][count_key] += 1

    report = _report(all_counts, cancelled_count)
    report.update({
        "start_date": start_date,
        "end_date": end_date,
        "per_resident": {
            resident_id: {
                "resident_name": item["resident_name"],
                **_report(item["counts"], item["cancelled_doses"]),
            }
            for resident_id, item in per_resident.items()
        },
        "formula": "administered / all occurred, non-cancelled scheduled doses; unresolved outcomes remain in the denominator",
    })
    return report
