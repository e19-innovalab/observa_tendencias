"""Login: password hashing, signed session tokens and the dependencies that check them.

Passwords are hashed with scrypt (standard library). A token is
"v1.<payload>.<signature>": the payload (user id, issue and expiry times) in base64url, signed
with HMAC-SHA256 and AUTH_SECRET. The user is read from the database on every request, so a
suspended account or a changed role takes effect at once. Roles and their permissions come from
app.yaml -> auth.
"""
import base64
import hashlib
import hmac
import json
import secrets
import time

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.config_files import app_config
from app.core.database import get_session
from app.models import User

TOKEN_VERSION = "v1"
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**14, 8, 1
BEARER = "bearer"
ACTIVE = "active"


def _msg(key: str, **kw) -> str:
    return app_config().auth.messages[key].format(**kw)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


# --- passwords ---------------------------------------------------------------------------------
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
    except ValueError:
        return False
    if scheme != "scrypt":
        return False
    found = hashlib.scrypt(password.encode(), salt=_unb64(salt), n=int(n), r=int(r), p=int(p))
    return hmac.compare_digest(found, _unb64(digest))


def check_password_rules(password: str) -> None:
    minimum = app_config().auth.password_min_length
    if len(password) < minimum:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, _msg("short_password", min=minimum))


# --- tokens ------------------------------------------------------------------------------------
def _secret() -> bytes:
    if not settings.auth_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, _msg("no_secret"))
    return settings.auth_secret.encode()


def _sign(body: str) -> str:
    return _b64(hmac.new(_secret(), body.encode(), hashlib.sha256).digest())


def create_token(user_id: int, now: float | None = None) -> tuple[str, int]:
    """(token, expiry as unix time)."""
    issued = int(now or time.time())
    expires = issued + int(app_config().auth.token_ttl_hours * 3600)
    body = f"{TOKEN_VERSION}.{_b64(json.dumps({'sub': user_id, 'iat': issued, 'exp': expires}).encode())}"
    return f"{body}.{_sign(body)}", expires


def decode_token(token: str, now: float | None = None) -> int:
    """The user id of a valid, unexpired token; 401 otherwise."""
    invalid = HTTPException(status.HTTP_401_UNAUTHORIZED, _msg("invalid_token"))
    try:
        version, payload, signature = token.split(".")
    except ValueError:
        raise invalid from None
    if version != TOKEN_VERSION or not hmac.compare_digest(_sign(f"{version}.{payload}"), signature):
        raise invalid
    try:
        data = json.loads(_unb64(payload))
    except ValueError:
        raise invalid from None
    if data.get("exp", 0) < (now or time.time()):
        raise invalid
    return int(data["sub"])


# --- dependencies ------------------------------------------------------------------------------
def permissions_of(role: str) -> set[str]:
    conf = app_config().auth.roles.get(role)
    return set(conf.permissions) if conf else set()


def _bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    return token.strip() if scheme.lower() == BEARER and token.strip() else None


def optional_user(authorization: str | None = Header(default=None),
                  session: Session = Depends(get_session)) -> User | None:
    """The logged-in user, or None without a token. A bad or expired token is an error."""
    token = _bearer(authorization)
    if token is None:
        return None
    user = session.get(User, decode_token(token))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, _msg("invalid_token"))
    if user.status != ACTIVE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, _msg("suspended"))
    return user


def current_user(user: User | None = Depends(optional_user)) -> User:
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, _msg("not_authenticated"))
    return user


def require_permission(permission: str):
    """A logged-in user whose role has the permission, or (for scripts) the X-API-Key."""

    def check(x_api_key: str | None = Header(default=None),
              user: User | None = Depends(optional_user)) -> User | None:
        if settings.admin_api_key and x_api_key == settings.admin_api_key:
            return user
        if user is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, _msg("not_authenticated"))
        if permission not in permissions_of(user.role):
            raise HTTPException(status.HTTP_403_FORBIDDEN, _msg("forbidden"))
        return user

    return check
