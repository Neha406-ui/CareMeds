from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import accessible_residents, get_current_user, require_role
from app.db.base import get_db
from app.models.assignment import CaretakerAssignment, DoctorAssignment
from app.models.operations import FamilyContactRequest, ShiftHandover
from app.models.resident import Resident
from app.models.user import User, UserRole
from app.schemas import FamilyContactCreate, FamilyContactUpdate, ShiftHandoverCreate
from app.services.audit import record_audit

router = APIRouter()
STAFF_ROLES = (UserRole.ADMIN.value, UserRole.DOCTOR.value, UserRole.CARETAKER.value)


def _now_utc_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _contact_accessible_query(db: Session, user: User):
    if user.role == UserRole.ADMIN:
        return db.query(Resident.id)
    return accessible_residents(
        db,
        user,
        family_permission=None if user.role == UserRole.FAMILY_MEMBER else "can_view_profile",
    ).with_entities(Resident.id)


def _handover_payload(item: ShiftHandover) -> dict:
    return {
        "id": str(item.id),
        "resident_id": str(item.resident_id),
        "outgoing_caretaker_id": str(item.outgoing_caretaker_id),
        "incoming_caretaker_id": str(item.incoming_caretaker_id),
        "shift_started_at": item.shift_started_at,
        "shift_ended_at": item.shift_ended_at,
        "notes": item.notes,
        "acknowledged_at": item.acknowledged_at,
        "acknowledged_by": str(item.acknowledged_by) if item.acknowledged_by else None,
        "created_at": item.created_at,
    }


@router.get("/family-contact-requests")
def list_family_contact_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(FamilyContactRequest).filter(
        FamilyContactRequest.resident_id.in_(_contact_accessible_query(db, current_user))
    )
    if current_user.role == UserRole.FAMILY_MEMBER:
        query = query.filter(FamilyContactRequest.family_member_id == current_user.id)
    elif current_user.role not in {
        UserRole.ADMIN,
        UserRole.DOCTOR,
        UserRole.CARETAKER,
    }:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return [
        {
            "id": str(item.id),
            "resident_id": str(item.resident_id),
            "family_member_id": str(item.family_member_id),
            "message": item.message,
            "status": item.status,
            "response": item.response,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "responded_by": str(item.responded_by) if item.responded_by else None,
        }
        for item in query.order_by(FamilyContactRequest.created_at.desc()).limit(200).all()
    ]


@router.post(
    "/family-contact-requests",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.FAMILY_MEMBER.value))],
)
def create_family_contact_request(
    item: FamilyContactCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resident = db.query(Resident).filter(
        Resident.id == item.resident_id,
        Resident.id.in_(_contact_accessible_query(db, current_user)),
    ).first()
    if resident is None:
        raise HTTPException(status_code=404, detail="Linked resident not found")
    request_item = FamilyContactRequest(
        resident_id=resident.id,
        family_member_id=current_user.id,
        message=item.message.strip(),
    )
    db.add(request_item)
    db.flush()
    record_audit(
        db,
        current_user.id,
        "family_contact_requested",
        "family_contact_request",
        request_item.id,
        {"resident_id": str(resident.id)},
    )
    db.commit()
    db.refresh(request_item)
    return {
        "id": str(request_item.id),
        "resident_id": str(request_item.resident_id),
        "family_member_id": str(request_item.family_member_id),
        "message": request_item.message,
        "status": request_item.status,
        "created_at": request_item.created_at,
    }


@router.patch(
    "/family-contact-requests/{request_id}",
    dependencies=[Depends(require_role(*STAFF_ROLES))],
)
def respond_to_family_contact_request(
    request_id: UUID,
    item: FamilyContactUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(FamilyContactRequest).filter(
        FamilyContactRequest.id == request_id,
        FamilyContactRequest.resident_id.in_(_contact_accessible_query(db, current_user)),
    )
    request_item = query.first()
    if request_item is None:
        raise HTTPException(status_code=404, detail="Contact request not found")
    if request_item.status == "resolved":
        raise HTTPException(status_code=409, detail="Contact request is already resolved")
    request_item.status = item.status
    request_item.response = item.response.strip()
    request_item.responded_by = current_user.id
    request_item.updated_at = _now_utc_naive()
    record_audit(
        db,
        current_user.id,
        "family_contact_responded",
        "family_contact_request",
        request_item.id,
        {"status": item.status},
    )
    db.commit()
    return {
        "id": str(request_item.id),
        "status": request_item.status,
        "response": request_item.response,
        "responded_by": str(request_item.responded_by),
        "updated_at": request_item.updated_at,
    }


@router.get(
    "/handovers",
    dependencies=[Depends(require_role(UserRole.ADMIN.value, UserRole.CARETAKER.value))],
)
def list_handovers(
    resident_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ShiftHandover)
    if current_user.role == UserRole.CARETAKER:
        query = query.filter(
            ShiftHandover.resident_id.in_(
                accessible_residents(db, current_user).with_entities(Resident.id)
            )
        )
    if resident_id is not None:
        query = query.filter(ShiftHandover.resident_id == resident_id)
    return [
        _handover_payload(item)
        for item in query.order_by(ShiftHandover.created_at.desc()).limit(limit).all()
    ]


@router.post(
    "/handovers",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.CARETAKER.value))],
)
def create_handover(
    item: ShiftHandoverCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if item.incoming_caretaker_id == current_user.id:
        raise HTTPException(status_code=400, detail="Incoming caretaker must be another user")
    assignments = db.query(CaretakerAssignment).filter(
        CaretakerAssignment.resident_id == item.resident_id,
        CaretakerAssignment.is_active.is_(True),
        CaretakerAssignment.caretaker_id.in_(
            (current_user.id, item.incoming_caretaker_id)
        ),
    ).all()
    assigned_ids = {assignment.caretaker_id for assignment in assignments}
    active_resident = accessible_residents(db, current_user).filter(
        Resident.id == item.resident_id
    ).first()
    if active_resident is None:
        raise HTTPException(status_code=404, detail="Assigned resident not found")
    if current_user.id not in assigned_ids:
        raise HTTPException(status_code=404, detail="Assigned resident not found")
    if item.incoming_caretaker_id not in assigned_ids:
        raise HTTPException(status_code=409, detail="Incoming caretaker is not assigned to this resident")
    incoming = db.query(User).filter(
        User.id == item.incoming_caretaker_id,
        User.role == UserRole.CARETAKER,
        User.is_active.is_(True),
    ).first()
    if incoming is None:
        raise HTTPException(status_code=409, detail="Incoming caretaker account is not active")
    handover = ShiftHandover(
        resident_id=item.resident_id,
        outgoing_caretaker_id=current_user.id,
        incoming_caretaker_id=incoming.id,
        shift_started_at=item.shift_started_at.astimezone(timezone.utc).replace(tzinfo=None),
        shift_ended_at=item.shift_ended_at.astimezone(timezone.utc).replace(tzinfo=None),
        notes=item.notes.strip(),
    )
    db.add(handover)
    db.flush()
    record_audit(
        db,
        current_user.id,
        "shift_handover_created",
        "shift_handover",
        handover.id,
        {"resident_id": str(item.resident_id), "incoming_caretaker_id": str(incoming.id)},
    )
    db.commit()
    db.refresh(handover)
    return _handover_payload(handover)


@router.get(
    "/handovers/eligible-caretakers",
    dependencies=[Depends(require_role(UserRole.ADMIN.value, UserRole.CARETAKER.value))],
)
def eligible_handover_caretakers(
    resident_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role == UserRole.CARETAKER and not accessible_residents(db, current_user).filter(
        Resident.id == resident_id
    ).first():
        raise HTTPException(status_code=404, detail="Assigned resident not found")
    return [
        {
            "id": str(user.id),
            "full_name": user.full_name,
            "username": user.username,
        }
        for user in db.query(User).join(
            CaretakerAssignment,
            CaretakerAssignment.caretaker_id == User.id,
        ).filter(
            CaretakerAssignment.resident_id == resident_id,
            CaretakerAssignment.is_active.is_(True),
            User.role == UserRole.CARETAKER,
            User.is_active.is_(True),
        ).order_by(User.full_name, User.username).all()
    ]


@router.post(
    "/handovers/{handover_id}/acknowledge",
    dependencies=[Depends(require_role(UserRole.CARETAKER.value))],
)
def acknowledge_handover(
    handover_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    handover = db.query(ShiftHandover).filter(
        ShiftHandover.id == handover_id,
        ShiftHandover.incoming_caretaker_id == current_user.id,
        ShiftHandover.resident_id.in_(
            accessible_residents(db, current_user).with_entities(Resident.id)
        ),
    ).first()
    if handover is None:
        raise HTTPException(status_code=404, detail="Handover not found")
    if handover.acknowledged_at is not None:
        raise HTTPException(status_code=409, detail="Handover is already acknowledged")
    handover.acknowledged_at = _now_utc_naive()
    handover.acknowledged_by = current_user.id
    record_audit(
        db,
        current_user.id,
        "shift_handover_acknowledged",
        "shift_handover",
        handover.id,
        {"resident_id": str(handover.resident_id)},
    )
    db.commit()
    return _handover_payload(handover)
