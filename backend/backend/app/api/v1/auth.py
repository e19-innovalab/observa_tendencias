from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import (
    ACTIVE,
    _msg,
    check_password_rules,
    create_token,
    current_user,
    hash_password,
    verify_password,
)
from app.core.database import get_session
from app.models import User
from app.schemas.auth import LoginRequest, LoginResponse, PasswordChange, UserItem
from app.services.users import user_item

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, session: Session = Depends(get_session)):
    """Email and password -> session token (send it as `Authorization: Bearer <token>`)."""
    user = session.scalar(select(User).where(func.lower(User.email) == body.email))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, _msg("bad_credentials"))
    if user.status != ACTIVE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, _msg("suspended"))
    token, expires = create_token(user.user_id)
    user.last_login_at = datetime.now(UTC)
    session.commit()
    return LoginResponse(access_token=token, expires_at=datetime.fromtimestamp(expires, UTC),
                         user=user_item(user))


@router.get("/me", response_model=UserItem)
def me(user: User = Depends(current_user)):
    return user_item(user)


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(body: PasswordChange, user: User = Depends(current_user),
                    session: Session = Depends(get_session)):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, _msg("wrong_password"))
    check_password_rules(body.new_password)
    user.password_hash = hash_password(body.new_password)
    session.commit()
