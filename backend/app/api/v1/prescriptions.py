import json
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import accessible_residents, get_current_user, is_doctor_assigned, require_role
from app.db.base import get_db
from app.models.dose import DoseEvent, DoseOccurrence
from app.models.prescription import (
    Medicine,
    Prescription,
    PrescriptionHistory,
    PrescriptionStatus,
)
from app.models.resident import Resident
from app.models.user import User, UserRole
from app.schemas import (
    MedicineCreate,
    MedicineResponse,
    PrescriptionCreate,
    PrescriptionDiscontinue,
    PrescriptionResponse,
    PrescriptionUpdate,
)
from app.services.audit import record_audit

router = APIRouter()


def _prescription_snapshot(prescription: Prescription) -> str:
    return json.dumps({
        "dosage": prescription.dosage,
        "route": prescription.route,
        "frequency": prescription.frequency,
        "scheduled_times": prescription.scheduled_times,
        "timezone": prescription.timezone,
        "schedule_revision": prescription.schedule_revision,
        "instructions": prescription.instructions,
        "start_date": prescription.start_date,
        "end_date": prescription.end_date,
        "status": prescription.status.value,
        "discontinuation_reason": prescription.discontinuation_reason,
    }, default=str)


def _require_prescription_doctor(
    prescription_id: UUID,
    db: Session,
    current_user: User,
) -> Prescription:
    prescription = db.get(Prescription, prescription_id)
    active_resident = (
        db.query(Resident.id)
        .filter(Resident.id == prescription.resident_id, Resident.is_active.is_(True))
        .first()
        if prescription is not None
        else None
    )
    if (
        prescription is None
        or prescription.doctor_id != current_user.id
        or active_resident is None
        or not is_doctor_assigned(db, current_user.id, prescription.resident_id)
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found")
    return prescription


@router.post(
    "/medicines",
    response_model=MedicineResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADMIN.value, UserRole.DOCTOR.value))],
)
def create_medicine(
    med_in: MedicineCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    med = Medicine(**med_in.model_dump())
    db.add(med)
    db.flush()
    record_audit(db, current_user.id, "medicine_created", "medicine", med.id)
    db.commit()
    db.refresh(med)
    return med


@router.get("/medicines", response_model=list[MedicineResponse])
def list_medicines(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Medicine).filter(Medicine.is_active.is_(True)).all()


@router.post(
    "/prescriptions",
    response_model=PrescriptionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.DOCTOR.value))],
)
def create_prescription(
    pres_in: PrescriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resident = db.query(Resident).filter(
        Resident.id == pres_in.resident_id,
        Resident.is_active.is_(True),
    ).first()
    if resident is None or not is_doctor_assigned(db, current_user.id, pres_in.resident_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Authorized resident not found")
    if pres_in.end_date and pres_in.end_date < pres_in.start_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end_date must be after start_date")
    medicine = db.get(Medicine, pres_in.medicine_id)
    if medicine is None or not medicine.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active medicine not found")

    prescription = Prescription(
        **pres_in.model_dump(),
        doctor_id=current_user.id,
        status=PrescriptionStatus.ACTIVE,
    )
    db.add(prescription)
    db.flush()
    db.add(PrescriptionHistory(
        prescription_id=prescription.id,
        changed_by=current_user.id,
        change_type="created",
        after_state=_prescription_snapshot(prescription),
        changed_at=datetime.utcnow(),
    ))
    record_audit(
        db,
        current_user.id,
        "prescription_created",
        "prescription",
        prescription.id,
        {"resident_id": str(resident.id)},
    )
    db.commit()
    db.refresh(prescription)
    return prescription


@router.get("/prescriptions", response_model=list[PrescriptionResponse])
def list_prescriptions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role == UserRole.ADMIN:
        return db.query(Prescription).all()
    resident_ids = accessible_residents(
        db,
        current_user,
        family_permission="can_view_prescriptions",
    ).with_entities(Resident.id)
    return db.query(Prescription).filter(Prescription.resident_id.in_(resident_ids)).all()


@router.put(
    "/prescriptions/{prescription_id}",
    response_model=PrescriptionResponse,
    dependencies=[Depends(require_role(UserRole.DOCTOR.value))],
)
def update_prescription(
    prescription_id: UUID,
    pres_in: PrescriptionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prescription = _require_prescription_doctor(prescription_id, db, current_user)
    if prescription.status == PrescriptionStatus.DISCONTINUED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Discontinued prescriptions cannot be edited")
    updates = pres_in.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No prescription changes provided")
    end_date = updates.get("end_date", prescription.end_date)
    start_date = updates.get("start_date", prescription.start_date)
    if end_date and start_date and end_date < start_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end_date must be after start_date")

    before_state = _prescription_snapshot(prescription)
    prescription.schedule_revision += 1
    for key, value in updates.items():
        setattr(prescription, key, value)
    _cancel_future_doses(db, prescription, current_user, "Prescription updated")
    db.add(PrescriptionHistory(
        prescription_id=prescription.id,
        changed_by=current_user.id,
        change_type="updated",
        before_state=before_state,
        after_state=_prescription_snapshot(prescription),
        changed_at=datetime.utcnow(),
    ))
    record_audit(
        db,
        current_user.id,
        "prescription_updated",
        "prescription",
        prescription.id,
        {"fields": sorted(updates)},
    )
    db.commit()
    db.refresh(prescription)
    return prescription


@router.post(
    "/prescriptions/{prescription_id}/discontinue",
    response_model=PrescriptionResponse,
    dependencies=[Depends(require_role(UserRole.DOCTOR.value))],
)
def discontinue_prescription(
    prescription_id: UUID,
    discontinuation: PrescriptionDiscontinue,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reason = discontinuation.reason.strip()
    if not reason:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A discontinuation reason is required")
    prescription = _require_prescription_doctor(prescription_id, db, current_user)
    if prescription.status == PrescriptionStatus.DISCONTINUED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Prescription is already discontinued")
    before_state = _prescription_snapshot(prescription)
    prescription.status = PrescriptionStatus.DISCONTINUED
    prescription.discontinued_at = datetime.utcnow()
    prescription.discontinued_by = current_user.id
    prescription.discontinuation_reason = reason
    _cancel_future_doses(db, prescription, current_user, "Prescription discontinued")
    db.add(PrescriptionHistory(
        prescription_id=prescription.id,
        changed_by=current_user.id,
        change_type="discontinued",
        before_state=before_state,
        after_state=_prescription_snapshot(prescription),
        changed_at=datetime.utcnow(),
    ))
    record_audit(
        db,
        current_user.id,
        "prescription_discontinued",
        "prescription",
        prescription.id,
        {"reason_provided": True},
    )
    db.commit()
    db.refresh(prescription)
    return prescription


def _cancel_future_doses(db: Session, prescription: Prescription, actor: User, reason: str) -> None:
    now = datetime.utcnow()
    pending = db.query(DoseOccurrence).filter(
        DoseOccurrence.prescription_id == prescription.id,
        DoseOccurrence.status == "scheduled",
        DoseOccurrence.scheduled_for > now,
    ).all()
    for dose in pending:
        dose.status = "cancelled"
        db.add(DoseEvent(
            dose_occurrence_id=dose.id,
            actor_id=actor.id,
            event_type="schedule_cancelled",
            previous_status="scheduled",
            new_status="cancelled",
            details=reason,
            occurred_at=now,
        ))
