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
    verify_google_credential,
    verify_password,
)
from app.core.config_files import app_config
from app.core.database import get_session
from app.models import User
from app.schemas.auth import (
    GoogleLoginRequest,
    LoginRequest,
    LoginResponse,
    PasswordChange,
    UserItem,
)
from app.services.users import user_item

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, session: Session = Depends(get_session)):
    """Email and password -> session token (send it as `Authorization: Bearer <token>`)."""
    user = session.scalar(select(User).where(func.lower(User.email) == body.email))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, _msg("bad_credentials"))
    return _session_for(user, session)


@router.post("/google", response_model=LoginResponse)
def login_with_google(body: GoogleLoginRequest, session: Session = Depends(get_session)):
    """The token of the Google button -> session token. A known Google account or email signs in
    with its role; a new one gets an account with app.yaml -> auth.google.signup_role."""
    claims = verify_google_credential(body.credential)
    email = claims["email"].strip().lower()
    user = session.scalar(select(User).where(User.google_sub == claims["sub"])) \
        or session.scalar(select(User).where(func.lower(User.email) == email))
    if user is None:
        user = User(email=email, full_name=(claims.get("name") or email).strip(), password_hash=None,
                    google_sub=claims["sub"], role=app_config().auth.google.signup_role, countries=[],
                    status=ACTIVE, created_at=datetime.now(UTC))
        session.add(user)
        session.flush()
    elif user.google_sub is None:  # an account created by an administrator, first time with Google
        user.google_sub = claims["sub"]
    elif user.google_sub != claims["sub"]:  # the email now belongs to another Google account
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, _msg("google_invalid"))
    return _session_for(user, session)


def _session_for(user: User, session: Session) -> LoginResponse:
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
