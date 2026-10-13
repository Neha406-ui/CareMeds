from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import accessible_residents, get_current_user, require_role
from app.db.base import get_db
from app.models.assignment import CaretakerAssignment, DoctorAssignment
from app.models.family import FamilyLink
from app.models.resident import Resident
from app.models.user import User, UserRole
from app.schemas import (
    AssignmentCreate,
    FamilyConsentCreate,
    FamilyConsentUpdate,
    ResidentCreate,
    ResidentResponse,
    ResidentUpdate,
)
from app.services.audit import record_audit

router = APIRouter()


def _has_valid_consent(link: FamilyLink) -> bool:
    return bool(
        link.is_active
        and link.resident.is_active
        and link.consent_granted
        and (link.can_view_profile or link.can_view_prescriptions)
        and link.consent_granted_at is not None
        and link.consent_granted_by is not None
        and link.consent_revoked_at is None
    )


def _get_resident(db: Session, resident_id: UUID) -> Resident:
    resident = db.get(Resident, resident_id)
    if resident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resident not found")
    return resident


def _ensure_active_resident(db: Session, resident_id: UUID) -> Resident:
    resident = _get_resident(db, resident_id)
    if not resident.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resident not found")
    return resident


def _ensure_role_user(db: Session, user_id: UUID, role: UserRole) -> User:
    user = db.get(User, user_id)
    if user is None or not user.is_active or user.role != role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Active {role.value} account not found")
    return user


def _assignment_response(assignment: Any, user_id: UUID) -> dict[str, Any]:
    return {
        "resident_id": str(assignment.resident_id),
        "user_id": str(user_id),
        "is_active": assignment.is_active,
        "assigned_at": assignment.assigned_at,
        "unassigned_at": assignment.unassigned_at,
    }


@router.post(
    "/residents",
    response_model=ResidentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADMIN.value))],
)
def create_resident(
    resident_in: ResidentCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_user),
):
    if resident_in.user_id is not None:
        resident_user = _ensure_role_user(db, resident_in.user_id, UserRole.RESIDENT)
        if resident_user.resident_profile is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Resident account is already linked")
    resident = Resident(**resident_in.model_dump())
    db.add(resident)
    db.flush()
    record_audit(db, admin.id, "resident_created", "resident", resident.id)
    db.commit()
    db.refresh(resident)
    return resident


@router.get("/residents", response_model=list[ResidentResponse])
def list_residents(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return accessible_residents(db, current_user).all()


@router.get("/residents/{resident_id}", response_model=ResidentResponse)
def get_resident(resident_id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resident = accessible_residents(db, current_user).filter(Resident.id == resident_id).first()
    if resident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resident not found")
    return resident


@router.put(
    "/residents/{resident_id}",
    response_model=ResidentResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN.value))],
)
def update_resident(
    resident_id: UUID,
    resident_in: ResidentUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_user),
):
    resident = _get_resident(db, resident_id)
    updates = resident_in.model_dump(exclude_unset=True)
    if updates.get("is_active") is False and resident.is_active:
        resident.deactivated_at = datetime.utcnow()
    elif updates.get("is_active") is True:
        resident.deactivated_at = None
    for key, value in updates.items():
        setattr(resident, key, value)
    record_audit(db, admin.id, "resident_updated", "resident", resident.id, {"fields": sorted(updates)})
    db.commit()
    db.refresh(resident)
    return resident


@router.delete(
    "/residents/{resident_id}",
    response_model=ResidentResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN.value))],
)
def deactivate_resident(
    resident_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_user),
):
    resident = _get_resident(db, resident_id)
    resident.is_active = False
    resident.deactivated_at = datetime.utcnow()
    record_audit(db, admin.id, "resident_deactivated", "resident", resident.id)
    db.commit()
    db.refresh(resident)
    return resident


@router.get(
    "/users",
    dependencies=[Depends(require_role(UserRole.ADMIN.value))],
)
def list_resident_assignment_users(db: Session = Depends(get_db)):
    users = db.query(User).filter(User.is_active.is_(True)).all()
    return [
        {"id": user.id, "username": user.username, "full_name": user.full_name, "role": user.role.value}
        for user in users
        if user.role in {UserRole.DOCTOR, UserRole.CARETAKER}
    ]


@router.get("/assignments", dependencies=[Depends(require_role(UserRole.ADMIN.value))])
def list_assignments(db: Session = Depends(get_db)):
    caretaker_assignments = db.query(CaretakerAssignment).all()
    doctor_assignments = db.query(DoctorAssignment).all()
    return [
        {
            **_assignment_response(assignment, assignment.caretaker_id),
            "role": UserRole.CARETAKER.value,
        }
        for assignment in caretaker_assignments
    ] + [
        {
            **_assignment_response(assignment, assignment.doctor_id),
            "role": UserRole.DOCTOR.value,
        }
        for assignment in doctor_assignments
    ]


@router.post(
    "/residents/{resident_id}/assignments/caretakers",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADMIN.value))],
)
def assign_caretaker(
    resident_id: UUID,
    assignment_in: AssignmentCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_user),
):
    _ensure_active_resident(db, resident_id)
    caretaker = _ensure_role_user(db, assignment_in.user_id, UserRole.CARETAKER)
    assignment = db.query(CaretakerAssignment).filter_by(
        resident_id=resident_id, caretaker_id=caretaker.id
    ).first()
    if assignment and assignment.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Caretaker is already assigned")
    now = datetime.utcnow()
    if assignment:
        assignment.is_active = True
        assignment.assigned_by = admin.id
        assignment.assigned_at = now
        assignment.unassigned_at = None
    else:
        assignment = CaretakerAssignment(
            resident_id=resident_id,
            caretaker_id=caretaker.id,
            assigned_by=admin.id,
            assigned_at=now,
            is_active=True,
        )
        db.add(assignment)
    db.flush()
    record_audit(
        db,
        admin.id,
        "caretaker_assigned",
        "resident",
        resident_id,
        {"caretaker_id": str(caretaker.id)},
    )
    db.commit()
    db.refresh(assignment)
    return _assignment_response(assignment, caretaker.id)


@router.delete(
    "/residents/{resident_id}/assignments/caretakers/{caretaker_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADMIN.value))],
)
def unassign_caretaker(
    resident_id: UUID,
    caretaker_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_user),
):
    assignment = db.query(CaretakerAssignment).filter_by(
        resident_id=resident_id, caretaker_id=caretaker_id, is_active=True
    ).first()
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active caretaker assignment not found")
    assignment.is_active = False
    assignment.unassigned_at = datetime.utcnow()
    db.flush()
    record_audit(
        db,
        admin.id,
        "caretaker_unassigned",
        "resident",
        resident_id,
        {"caretaker_id": str(caretaker_id)},
    )
    db.commit()


@router.post(
    "/residents/{resident_id}/assignments/doctors",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADMIN.value))],
)
def assign_doctor(
    resident_id: UUID,
    assignment_in: AssignmentCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_user),
):
    _ensure_active_resident(db, resident_id)
    doctor = _ensure_role_user(db, assignment_in.user_id, UserRole.DOCTOR)
    assignment = db.query(DoctorAssignment).filter_by(
        resident_id=resident_id, doctor_id=doctor.id
    ).first()
    if assignment and assignment.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Doctor is already assigned")
    now = datetime.utcnow()
    if assignment:
        assignment.is_active = True
        assignment.assigned_by = admin.id
        assignment.assigned_at = now
        assignment.unassigned_at = None
    else:
        assignment = DoctorAssignment(
            resident_id=resident_id,
            doctor_id=doctor.id,
            assigned_by=admin.id,
            assigned_at=now,
            is_active=True,
        )
        db.add(assignment)
    record_audit(
        db,
        admin.id,
        "doctor_assigned",
        "resident",
        resident_id,
        {"doctor_id": str(doctor.id)},
    )
    db.commit()
    db.refresh(assignment)
    return _assignment_response(assignment, doctor.id)


@router.delete(
    "/residents/{resident_id}/assignments/doctors/{doctor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADMIN.value))],
)
def unassign_doctor(
    resident_id: UUID,
    doctor_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_user),
):
    assignment = db.query(DoctorAssignment).filter_by(
        resident_id=resident_id, doctor_id=doctor_id, is_active=True
    ).first()
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active doctor assignment not found")
    assignment.is_active = False
    assignment.unassigned_at = datetime.utcnow()
    record_audit(
        db,
        admin.id,
        "doctor_unassigned",
        "resident",
        resident_id,
        {"doctor_id": str(doctor_id)},
    )
    db.commit()


@router.post(
    "/residents/{resident_id}/family-consent",
    status_code=status.HTTP_201_CREATED,
)
def grant_family_consent(
    resident_id: UUID,
    consent_in: FamilyConsentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != UserRole.RESIDENT or current_user.resident_profile is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the resident may grant family consent")
    if current_user.resident_profile.id != resident_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resident not found")
    _ensure_active_resident(db, resident_id)
    family_member = _ensure_role_user(db, consent_in.family_member_id, UserRole.FAMILY_MEMBER)
    link = db.query(FamilyLink).filter_by(
        resident_id=resident_id, family_member_id=family_member.id
    ).first()
    if link and _has_valid_consent(link):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Consent is already active")
    now = datetime.utcnow()
    if link:
        link.is_active = True
        link.consent_granted = True
        link.consent_granted_at = now
        link.consent_granted_by = current_user.id
        link.can_view_profile = consent_in.can_view_profile
        link.can_view_prescriptions = consent_in.can_view_prescriptions
        link.relationship_type = consent_in.relationship_type
        link.consent_revoked_at = None
        link.consent_revoked_by = None
    else:
        link = FamilyLink(
            resident_id=resident_id,
            family_member_id=family_member.id,
            relationship_type=consent_in.relationship_type,
            consent_granted=True,
            can_view_profile=consent_in.can_view_profile,
            can_view_prescriptions=consent_in.can_view_prescriptions,
            consent_granted_at=now,
            consent_granted_by=current_user.id,
            is_active=True,
        )
        db.add(link)
    db.flush()
    record_audit(
        db,
        current_user.id,
        "family_consent_granted",
        "family_link",
        link.id,
        {
            "resident_id": str(resident_id),
            "family_member_id": str(family_member.id),
            "can_view_profile": link.can_view_profile,
            "can_view_prescriptions": link.can_view_prescriptions,
        },
    )
    db.commit()
    return {
        "resident_id": str(resident_id),
        "family_member_id": str(family_member.id),
        "consent_granted": True,
        "can_view_profile": link.can_view_profile,
        "can_view_prescriptions": link.can_view_prescriptions,
    }


@router.patch("/residents/{resident_id}/family-consent/{family_member_id}")
def update_family_consent_permissions(
    resident_id: UUID,
    family_member_id: UUID,
    permissions: FamilyConsentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if (
        current_user.role != UserRole.RESIDENT
        or current_user.resident_profile is None
        or current_user.resident_profile.id != resident_id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resident not found")
    link = db.query(FamilyLink).filter_by(
        resident_id=resident_id,
        family_member_id=family_member_id,
        is_active=True,
    ).first()
    if link is None or not _has_valid_consent(link):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active family consent not found")
    link.can_view_profile = permissions.can_view_profile
    link.can_view_prescriptions = permissions.can_view_prescriptions
    link.consent_granted_at = datetime.utcnow()
    link.consent_granted_by = current_user.id
    record_audit(
        db,
        current_user.id,
        "family_consent_updated",
        "family_link",
        link.id,
        {
            "resident_id": str(resident_id),
            "family_member_id": str(family_member_id),
            "can_view_profile": link.can_view_profile,
            "can_view_prescriptions": link.can_view_prescriptions,
        },
    )
    db.commit()
    return {
        "resident_id": str(resident_id),
        "family_member_id": str(family_member_id),
        "consent_granted": True,
        "can_view_profile": link.can_view_profile,
        "can_view_prescriptions": link.can_view_prescriptions,
    }


@router.post(
    "/family-links/{resident_id}",
    status_code=status.HTTP_201_CREATED,
)
def request_family_link(
    resident_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != UserRole.FAMILY_MEMBER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only family members may request access")
    _ensure_active_resident(db, resident_id)
    link = db.query(FamilyLink).filter_by(
        resident_id=resident_id, family_member_id=current_user.id
    ).first()
    if link:
        if _has_valid_consent(link):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Family access is already active")
        if link.is_active:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Family access request is already pending")
        link.consent_granted = False
        link.can_view_profile = False
        link.can_view_prescriptions = False
        link.is_active = True
        link.requested_at = datetime.utcnow()
    else:
        link = FamilyLink(
            resident_id=resident_id,
            family_member_id=current_user.id,
            consent_granted=False,
            can_view_profile=False,
            can_view_prescriptions=False,
            consent_granted_at=None,
            is_active=True,
        )
        db.add(link)
    db.flush()
    record_audit(
        db,
        current_user.id,
        "family_access_requested",
        "family_link",
        link.id,
        {"resident_id": str(resident_id)},
    )
    db.commit()
    return {"resident_id": str(resident_id), "status": "pending_resident_consent"}


@router.get("/family-links")
def list_family_links(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(FamilyLink).join(Resident)
    if current_user.role == UserRole.FAMILY_MEMBER:
        links = query.filter(
            FamilyLink.family_member_id == current_user.id,
            FamilyLink.is_active.is_(True),
            Resident.is_active.is_(True),
        ).all()
        return [
            {
                "resident_id": str(link.resident_id),
                "resident_name": link.resident.full_name if (
                    _has_valid_consent(link) and link.can_view_profile
                ) else None,
                "is_active": link.is_active,
                "consent_granted": _has_valid_consent(link),
                "can_view_profile": link.can_view_profile,
                "can_view_prescriptions": link.can_view_prescriptions,
                "consent_revoked_at": link.consent_revoked_at,
            }
            for link in links
        ]
    if current_user.role == UserRole.ADMIN:
        links = query.all()
        return [
            {
                "resident_id": str(link.resident_id),
                "resident_name": link.resident.full_name,
                "family_member_id": str(link.family_member_id),
                "family_member_name": link.family_member.full_name or link.family_member.username,
                "is_active": link.is_active,
                "consent_granted": _has_valid_consent(link),
                "can_view_profile": link.can_view_profile,
                "can_view_prescriptions": link.can_view_prescriptions,
                "consent_granted_at": link.consent_granted_at,
                "consent_revoked_at": link.consent_revoked_at,
            }
            for link in links
        ]
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Family link access is not permitted")


@router.delete("/family-links/{resident_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_family_link_request(
    resident_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != UserRole.FAMILY_MEMBER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only family members may cancel requests")
    link = db.query(FamilyLink).filter_by(
        resident_id=resident_id,
        family_member_id=current_user.id,
        is_active=True,
    ).first()
    if link is None or link.consent_granted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pending family request not found")
    link.is_active = False
    record_audit(
        db,
        current_user.id,
        "family_access_request_cancelled",
        "family_link",
        link.id,
        {"resident_id": str(resident_id)},
    )
    db.commit()


@router.get("/residents/{resident_id}/family-consents")
def list_family_consent_requests(
    resident_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if (
        current_user.role != UserRole.RESIDENT
        or current_user.resident_profile is None
        or current_user.resident_profile.id != resident_id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resident not found")
    links = db.query(FamilyLink).join(User, User.id == FamilyLink.family_member_id).filter(
        FamilyLink.resident_id == resident_id,
        FamilyLink.is_active.is_(True),
        User.is_active.is_(True),
    ).all()
    return [
        {
            "family_member_id": str(link.family_member_id),
            "username": link.family_member.username,
            "full_name": link.family_member.full_name,
            "requested_at": link.requested_at,
            "consent_granted": _has_valid_consent(link),
            "can_view_profile": link.can_view_profile,
            "can_view_prescriptions": link.can_view_prescriptions,
        }
        for link in links
    ]


@router.delete(
    "/residents/{resident_id}/family-consent/{family_member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def revoke_family_consent(
    resident_id: UUID,
    family_member_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    is_owner = (
        current_user.role == UserRole.RESIDENT
        and current_user.resident_profile is not None
        and current_user.resident_profile.id == resident_id
    )
    if not is_owner and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Family link not found")
    link = db.query(FamilyLink).filter_by(
        resident_id=resident_id, family_member_id=family_member_id, is_active=True
    ).first()
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Family link not found")
    link.is_active = False
    link.can_view_profile = False
    link.can_view_prescriptions = False
    link.consent_granted = False
    link.consent_revoked_at = datetime.utcnow()
    link.consent_revoked_by = current_user.id
    record_audit(
        db,
        current_user.id,
        "family_consent_revoked",
        "family_link",
        link.id,
        {"resident_id": str(resident_id), "family_member_id": str(family_member_id)},
    )
    db.commit()
