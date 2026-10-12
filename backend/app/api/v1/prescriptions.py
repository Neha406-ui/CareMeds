from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from datetime import datetime
import json
from app.db.base import get_db
from app.models.user import User, UserRole
from app.models.resident import Resident
from app.models.prescription import Medicine, Prescription, PrescriptionHistory, PrescriptionStatus
from app.api.deps import get_current_user, require_role
from app.schemas import MedicineCreate, MedicineResponse, PrescriptionCreate, PrescriptionResponse, PrescriptionUpdate

router = APIRouter()


@router.post("/medicines", response_model=MedicineResponse, dependencies=[Depends(require_role(UserRole.ADMIN.value, UserRole.DOCTOR.value))])
def create_medicine(med_in: MedicineCreate, db: Session = Depends(get_db)):
    med = Medicine(**med_in.model_dump())
    db.add(med)
    db.commit()
    db.refresh(med)
    return med


@router.get("/medicines", response_model=List[MedicineResponse])
def list_medicines(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Medicine).filter(Medicine.is_active == True).all()


@router.post("/prescriptions", response_model=PrescriptionResponse, dependencies=[Depends(require_role(UserRole.DOCTOR.value))])
def create_prescription(pres_in: PrescriptionCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    resident = db.query(Resident).get(pres_in.resident_id)
    if not resident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resident not found")
    if pres_in.end_date and pres_in.start_date and pres_in.end_date < pres_in.start_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end_date must be after start_date")
    med = db.query(Medicine).get(pres_in.medicine_id)
    if not med:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medicine not found")
    pres = Prescription(
        resident_id=pres_in.resident_id,
        medicine_id=pres_in.medicine_id,
        dosage=pres_in.dosage,
        route=pres_in.route,
        frequency=pres_in.frequency,
        instructions=pres_in.instructions,
        start_date=pres_in.start_date,
        end_date=pres_in.end_date,
        doctor_id=current_user.id,
        status=PrescriptionStatus.ACTIVE,
    )
    db.add(pres)
    db.commit()
    db.refresh(pres)
    hist = PrescriptionHistory(
        prescription_id=pres.id,
        changed_by=current_user.id,
        change_type="created",
        after_state=json.dumps(str(pres.id)),
        changed_at=datetime.utcnow(),
    )
    db.add(hist)
    db.commit()
    return pres


@router.get("/prescriptions", response_model=List[PrescriptionResponse])
def list_prescriptions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role == UserRole.DOCTOR:
        return db.query(Prescription).all()
    if current_user.role == UserRole.ADMIN:
        return db.query(Prescription).all()
    if current_user.role == UserRole.CARETAKER:
        return db.query(Prescription).join(Resident).join(CaretakerAssignment, CaretakerAssignment.resident_id == Resident.id).filter(CaretakerAssignment.caretaker_id == current_user.id, CaretakerAssignment.is_active == True).all()
    if current_user.role == UserRole.RESIDENT:
        if current_user.resident_profile:
            return db.query(Prescription).filter(Prescription.resident_id == current_user.resident_profile.id).all()
        return []
    if current_user.role == UserRole.FAMILY_MEMBER:
        from app.models.family import FamilyLink
        links = db.query(FamilyLink).filter(FamilyLink.family_member_id == current_user.id, FamilyLink.is_active == True, FamilyLink.consent_granted == True).all()
        res_ids = [l.resident_id for l in links]
        return db.query(Prescription).filter(Prescription.resident_id.in_(res_ids)).all() if res_ids else []
    return []


@router.put("/prescriptions/{prescription_id}", response_model=PrescriptionResponse, dependencies=[Depends(require_role(UserRole.DOCTOR.value))])
def update_prescription(prescription_id: UUID, pres_in: PrescriptionUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    pres = db.query(Prescription).get(prescription_id)
    if not pres:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found")
    for k, v in pres_in.model_dump(exclude_unset=True).items():
        setattr(pres, k, v)
    pres.history.append(PrescriptionHistory(prescription_id=pres.id, changed_by=current_user.id, change_type="updated", changed_at=datetime.utcnow()))
    db.commit()
    db.refresh(pres)
    return pres


@router.post("/prescriptions/{prescription_id}/discontinue", response_model=PrescriptionResponse, dependencies=[Depends(require_role(UserRole.DOCTOR.value))])
def discontinue_prescription(prescription_id: UUID, reason: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    pres = db.query(Prescription).get(prescription_id)
    if not pres:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found")
    pres.status = PrescriptionStatus.DISCONTINUED
    pres.discontinued_at = datetime.utcnow()
    pres.discontinued_by = current_user.id
    pres.discontinuation_reason = reason
    pres.history.append(PrescriptionHistory(prescription_id=pres.id, changed_by=current_user.id, change_type="discontinued", changed_at=datetime.utcnow()))
    db.commit()
    db.refresh(pres)
    return pres
