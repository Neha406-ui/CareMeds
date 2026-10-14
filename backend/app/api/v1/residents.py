from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from app.db.base import get_db
from app.models.user import User, UserRole
from app.models.resident import Resident
from app.models.family import FamilyLink
from app.models.assignment import CaretakerAssignment
from app.api.deps import get_current_user, require_role
from app.schemas import ResidentCreate, ResidentResponse, ResidentUpdate

router = APIRouter()


@router.post("/residents", response_model=ResidentResponse, dependencies=[Depends(require_role(UserRole.ADMIN.value))])
def create_resident(resident_in: ResidentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    resident = Resident(**resident_in.model_dump())
    db.add(resident)
    db.commit()
    db.refresh(resident)
    return resident


@router.get("/residents", response_model=List[ResidentResponse])
def list_residents(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role == UserRole.ADMIN:
        return db.query(Resident).all()
    elif current_user.role == UserRole.CARETAKER:
        assignments = db.query(CaretakerAssignment).filter(CaretakerAssignment.caretaker_id == current_user.id, CaretakerAssignment.is_active == True).all()
        res_ids = [a.resident_id for a in assignments]
        return db.query(Resident).filter(Resident.id.in_(res_ids)).all() if res_ids else []
    elif current_user.role == UserRole.RESIDENT:
        if current_user.resident_profile:
            return [current_user.resident_profile]
        return []
    elif current_user.role == UserRole.FAMILY_MEMBER:
        links = db.query(FamilyLink).filter(FamilyLink.family_member_id == current_user.id, FamilyLink.is_active == True, FamilyLink.consent_granted == True).all()
        res_ids = [l.resident_id for l in links]
        return db.query(Resident).filter(Resident.id.in_(res_ids)).all() if res_ids else []
    else:
        return []


@router.get("/residents/{resident_id}", response_model=ResidentResponse)
def get_resident(resident_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    resident = db.query(Resident).get(resident_id)
    if not resident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resident not found")
    if current_user.role == UserRole.ADMIN:
        return resident
    elif current_user.role == UserRole.CARETAKER:
        if db.query(CaretakerAssignment).filter(CaretakerAssignment.caretaker_id == current_user.id, CaretakerAssignment.resident_id == resident_id, CaretakerAssignment.is_active == True).first():
            return resident
    elif current_user.role == UserRole.RESIDENT:
        if current_user.resident_profile and current_user.resident_profile.id == resident_id:
            return resident
    elif current_user.role == UserRole.FAMILY_MEMBER:
        if db.query(FamilyLink).filter(FamilyLink.family_member_id == current_user.id, FamilyLink.resident_id == resident_id, FamilyLink.is_active == True, FamilyLink.consent_granted == True).first():
            return resident
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.put("/residents/{resident_id}", response_model=ResidentResponse, dependencies=[Depends(require_role(UserRole.ADMIN.value))])
def update_resident(resident_id: UUID, resident_in: ResidentUpdate, db: Session = Depends(get_db)):
    resident = db.query(Resident).get(resident_id)
    if not resident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resident not found")
    for k, v in resident_in.model_dump(exclude_unset=True).items():
        setattr(resident, k, v)
    from datetime import datetime
    resident.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(resident)
    return resident


@router.delete("/residents/{resident_id}", response_model=ResidentResponse, dependencies=[Depends(require_role(UserRole.ADMIN.value))])
def deactivate_resident(resident_id: UUID, db: Session = Depends(get_db)):
    resident = db.query(Resident).get(resident_id)
    if not resident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resident not found")
    resident.is_active = False
    from datetime import datetime
    resident.deactivated_at = datetime.utcnow()
    resident.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(resident)
    return resident
