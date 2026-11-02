from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.auth import _msg, check_password_rules, hash_password, require_permission
from app.core.config_files import app_config
from app.core.database import get_session
from app.models import User
from app.schemas.auth import AuthOptions, RoleItem, UserCreate, UserItem, UsersPage, UserUpdate
from app.services.users import MANAGE_USERS, create_user, is_last_admin, user_item, validate_profile

router = APIRouter(prefix="/users", tags=["users"],
                   dependencies=[Depends(require_permission(MANAGE_USERS))])
_pagination = app_config().pagination


@router.get("/options", response_model=AuthOptions)
def user_options():
    """Roles (with their permissions), statuses and the password rule, for user forms."""
    conf = app_config().auth
    return AuthOptions(
        roles=[RoleItem(role=k, label=v.label, permissions=v.permissions) for k, v in conf.roles.items()],
        statuses=conf.statuses, password_min_length=conf.password_min_length,
        default_role=conf.default_role)


@router.get("", response_model=UsersPage)
def list_users(
    q: str | None = Query(None, description="Nombre o correo"),
    role: str | None = None,
    sector: str | None = None,
    status_value: str | None = Query(None, alias="status"),
    limit: int = Query(_pagination.default_limit, ge=1, le=_pagination.max_limit),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    conds = []
    if q:
        like = f"%{q.strip().lower()}%"
        conds.append(or_(func.lower(User.full_name).like(like), func.lower(User.email).like(like)))
    if role:
        conds.append(User.role == role)
    if sector:
        conds.append(User.sector_code == sector)
    if status_value:
        conds.append(User.status == status_value)
    total = session.scalar(select(func.count()).select_from(User).where(*conds))
    rows = session.scalars(select(User).where(*conds).order_by(User.full_name, User.user_id)
                           .limit(limit).offset(offset)).all()
    return UsersPage(total=total, limit=limit, offset=offset, items=[user_item(u) for u in rows])


@router.post("", response_model=UserItem, status_code=status.HTTP_201_CREATED)
def add_user(body: UserCreate, session: Session = Depends(get_session)):
    user = create_user(session, body.email, body.full_name, body.password, body.role,
                       body.sector_code, body.countries)
    session.commit()
    return user_item(user)


@router.patch("/{user_id}", response_model=UserItem)
def update_user(user_id: int, body: UserUpdate, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _msg("user_not_found"))
    # null means "unchanged" for everything except the sector (null or "" clears it)
    fields = {k: v for k, v in body.model_dump(exclude_unset=True).items()
              if v is not None or k == "sector_code"}
    validate_profile(fields.get("role"), fields.get("sector_code"), fields.get("countries"),
                     fields.get("status"))
    losing_admin = ("role" in fields and MANAGE_USERS not in app_config().auth.roles[fields["role"]].permissions) \
        or fields.get("status") not in (None, user.status, "active")
    if losing_admin and is_last_admin(session, user):
        raise HTTPException(status.HTTP_409_CONFLICT, _msg("last_admin"))
    if "password" in fields:
        check_password_rules(fields.pop("password"))
        user.password_hash = hash_password(body.password)
    if "countries" in fields:
        fields["countries"] = [c.upper() for c in fields["countries"] or []]
    if "sector_code" in fields:
        fields["sector_code"] = fields["sector_code"] or None
    for key, value in fields.items():
        setattr(user, key, value)
    session.commit()
    return user_item(user)
