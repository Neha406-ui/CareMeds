from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from uuid import UUID
from app.core.config import settings
from app.core.security import verify_password, get_password_hash, create_access_token
from app.db.base import get_db
from app.models.user import User, UserRole
from app.api.deps import get_current_user, require_role
from app.schemas import Token, UserCreate, UserResponse, UserStatusUpdate
from app.services.audit import record_audit

router = APIRouter()


@router.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if len(form_data.password) > 72 or not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "ver": user.token_version},
        expires_delta=access_token_expires,
    )
    user.last_login_at = datetime.utcnow()
    record_audit(db, user.id, "auth_login", "user", user.id)
    db.commit()
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/users", response_model=UserResponse, dependencies=[Depends(require_role(UserRole.ADMIN.value))])
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_user),
):
    username = user_in.username.strip()
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already registered")
    user = User(
        username=username,
        password_hash=get_password_hash(user_in.password),
        role=user_in.role,
        full_name=user_in.full_name,
        phone=user_in.phone,
    )
    db.add(user)
    try:
        db.flush()
        record_audit(
            db,
            admin.id,
            "user_created",
            "user",
            user.id,
            {"role": user.role.value},
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if db.query(User).filter(User.username == username).first():
            raise HTTPException(status_code=409, detail="Username already registered") from exc
        raise
    db.refresh(user)
    return user


@router.get("/users", response_model=list[UserResponse], dependencies=[Depends(require_role(UserRole.ADMIN.value))])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.patch(
    "/users/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN.value))],
)
def update_user_status(
    user_id: UUID,
    status_in: UserStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_user),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == admin.id and not status_in.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Administrators cannot deactivate their own account")
    if user.is_active != status_in.is_active:
        user.is_active = status_in.is_active
        user.token_version += 1
        record_audit(
            db,
            admin.id,
            "user_status_changed",
            "user",
            user.id,
            {"is_active": user.is_active},
        )
        db.commit()
        db.refresh(user)
    return user


@router.get("/me", response_model=UserResponse)
def read_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.token_version += 1
    record_audit(db, current_user.id, "auth_logout", "user", current_user.id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
