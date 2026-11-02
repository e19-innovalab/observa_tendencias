from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

# Basic shape only (something@domain.tld); stored lowercased.
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
Email = Annotated[str, Field(pattern=EMAIL_PATTERN, max_length=320), AfterValidator(str.lower)]


class UserItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    email: str
    full_name: str
    role: str
    role_label: str
    permissions: list[str]
    sector_code: str | None
    sector_name: str | None
    countries: list[str]  # empty = the whole region
    status: str
    status_label: str
    created_at: datetime
    last_login_at: datetime | None


class LoginRequest(BaseModel):
    email: Email
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserItem


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class UserCreate(BaseModel):
    email: Email
    full_name: str = Field(min_length=1)
    password: str
    role: str | None = None  # default: app.yaml -> auth.default_role
    sector_code: str | None = None
    countries: list[str] = []


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1)
    role: str | None = None
    sector_code: str | None = None
    countries: list[str] | None = None
    status: str | None = None
    password: str | None = None  # set a new password (administrators)


class UsersPage(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[UserItem]


class RoleItem(BaseModel):
    role: str
    label: str
    permissions: list[str]


class AuthOptions(BaseModel):
    """What a user form can offer: roles, statuses and the password rule."""
    roles: list[RoleItem]
    statuses: dict[str, str]
    password_min_length: int
    default_role: str
