from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from app.core.config import settings
from app.core.security import verify_password, get_password_hash, create_access_token
from app.db.base import get_db
from app.models.user import User, UserRole
from app.api.deps import get_current_user, require_role
from app.schemas import Token

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


@router.get("/me", response_model=Token)
def read_me(current_user: User = Depends(get_current_user)):
    return current_user
