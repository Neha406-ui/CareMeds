from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import or_
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from app.core.config import settings
from app.db.base import get_db
from app.models.assignment import CaretakerAssignment, DoctorAssignment
from app.models.family import FamilyLink
from app.models.resident import Resident
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/token")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
        token_version = payload.get("ver", 0)
        if (
            not isinstance(username, str)
            or not isinstance(token_version, int)
            or isinstance(token_version, bool)
        ):
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None or user.token_version != token_version:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return user


def require_role(*roles: str):
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role.value not in {role.value if hasattr(role, "value") else role for role in roles}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user
    return role_checker


def accessible_residents(db: Session, user: User, family_permission: str | None = "can_view_profile"):
    query = db.query(Resident)
    if user.role == UserRole.ADMIN:
        return query
    query = query.filter(Resident.is_active.is_(True))
    if user.role == UserRole.DOCTOR:
        return query.join(DoctorAssignment).filter(
            DoctorAssignment.doctor_id == user.id,
            DoctorAssignment.is_active.is_(True),
        ).distinct()
    if user.role == UserRole.CARETAKER:
        return query.join(CaretakerAssignment).filter(
            CaretakerAssignment.caretaker_id == user.id,
            CaretakerAssignment.is_active.is_(True),
        ).distinct()
    if user.role == UserRole.RESIDENT:
        return query.filter(Resident.user_id == user.id)
    if user.role == UserRole.FAMILY_MEMBER:
        query = query.join(FamilyLink).filter(
            FamilyLink.family_member_id == user.id,
            FamilyLink.is_active.is_(True),
            FamilyLink.consent_granted.is_(True),
            FamilyLink.consent_granted_at.is_not(None),
            FamilyLink.consent_granted_by.is_not(None),
            FamilyLink.consent_revoked_at.is_(None),
        )
        if family_permission is None:
            query = query.filter(or_(
                FamilyLink.can_view_profile.is_(True),
                FamilyLink.can_view_prescriptions.is_(True),
            ))
        elif family_permission == "can_view_profile":
            query = query.filter(FamilyLink.can_view_profile.is_(True))
        elif family_permission == "can_view_prescriptions":
            query = query.filter(FamilyLink.can_view_prescriptions.is_(True))
        else:
            raise ValueError("Unsupported family access permission")
        return query.distinct()
    return query.filter(False)


def is_doctor_assigned(db: Session, doctor_id, resident_id) -> bool:
    return db.query(DoctorAssignment.id).filter(
        DoctorAssignment.doctor_id == doctor_id,
        DoctorAssignment.resident_id == resident_id,
        DoctorAssignment.is_active.is_(True),
    ).first() is not None
