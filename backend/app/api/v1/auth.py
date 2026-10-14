from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import List
from app.core.config import settings
from app.core.security import verify_password, get_password_hash, create_access_token
from app.db.base import get_db
from app.models.user import User, UserRole
from app.api.deps import get_current_user, require_role
from app.schemas import Token, UserCreate, UserResponse

router = APIRouter()


@router.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    user.last_login_at = __import__('datetime').datetime.utcnow()
    db.commit()
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def read_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(body: UserCreate, db: Session = Depends(get_db)):
    """Public self-registration — only the family_member role is permitted."""
    if body.role not in (UserRole.FAMILY_MEMBER,):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public registration is only available for the Family Member role. "
                   "Contact an administrator to create doctor, caretaker, or resident accounts.",
        )
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")
    user = User(
        username=body.username,
        password_hash=get_password_hash(body.password),
        role=body.role,
        full_name=body.full_name,
        phone=body.phone,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN.value)),
):
    """Admin-only: create a user with any role."""
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")
    user = User(
        username=body.username,
        password_hash=get_password_hash(body.password),
        role=body.role,
        full_name=body.full_name,
        phone=body.phone,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/users", response_model=List[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN.value)),
):
    return db.query(User).all()


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user_status(
    user_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN.value)),
):
    from app.schemas import UserStatusUpdate
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

