"""User accounts: validation shared by the API and the command line."""
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import ACTIVE, _msg, check_password_rules, hash_password, permissions_of
from app.core.config_files import app_config, catalog
from app.models import User
from app.schemas.auth import UserItem

MANAGE_USERS = "manage_users"


def user_item(user: User) -> UserItem:
    conf = app_config().auth
    sector = next((s.name for s in catalog().sectors if s.sector_code == user.sector_code), None)
    return UserItem(
        user_id=user.user_id, email=user.email, full_name=user.full_name, role=user.role,
        role_label=conf.roles[user.role].label if user.role in conf.roles else user.role,
        permissions=sorted(permissions_of(user.role)), sector_code=user.sector_code,
        sector_name=sector, countries=list(user.countries or []), status=user.status,
        status_label=conf.statuses.get(user.status, user.status), created_at=user.created_at,
        last_login_at=user.last_login_at)


def _bad(key: str, **kw) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, _msg(key, **kw))


def validate_profile(role: str | None, sector_code: str | None, countries: list[str] | None,
                     status_value: str | None = None) -> None:
    conf = app_config().auth
    if role is not None and role not in conf.roles:
        raise _bad("unknown_role", role=role)
    if sector_code and sector_code not in {s.sector_code for s in catalog().sectors}:
        raise _bad("unknown_sector", sector=sector_code)
    known = {c.iso3 for c in catalog().countries}
    for country in countries or []:
        if country.upper() not in known:
            raise _bad("unknown_country", country=country)
    if status_value is not None and status_value not in conf.statuses:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, status_value)


def create_user(session: Session, email: str, full_name: str, password: str, role: str | None = None,
                sector_code: str | None = None, countries: list[str] | None = None) -> User:
    role = role or app_config().auth.default_role
    validate_profile(role, sector_code, countries)
    check_password_rules(password)
    email = email.strip().lower()
    if session.scalar(select(User.user_id).where(func.lower(User.email) == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, _msg("email_taken"))
    user = User(email=email, full_name=full_name.strip(), password_hash=hash_password(password),
                role=role, sector_code=sector_code or None,
                countries=[c.upper() for c in countries or []], status=ACTIVE,
                created_at=datetime.now(UTC))
    session.add(user)
    session.flush()
    return user


def is_last_admin(session: Session, user: User) -> bool:
    """True when the user is the only active account that can manage users."""
    managers = [r for r, conf in app_config().auth.roles.items() if MANAGE_USERS in conf.permissions]
    others = session.scalar(select(func.count()).select_from(User).where(
        User.role.in_(managers), User.status == ACTIVE, User.user_id != user.user_id))
    return user.role in managers and user.status == ACTIVE and not others
