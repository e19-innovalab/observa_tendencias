from fastapi import HTTPException, status
from supabase import Client, create_client
from supabase_auth.errors import AuthApiError
from supabase_auth.types import AuthResponse

from app.core.config import settings
from app.schemas.auth import AuthResult, AuthSession, AuthUser


def get_supabase_client() -> Client:
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La autenticación de Supabase no está configurada.",
        )
    return create_client(settings.supabase_url, settings.supabase_anon_key)


def auth_result(response: AuthResponse) -> AuthResult:
    user = response.user
    session = response.session
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Supabase no devolvió los datos del usuario.",
        )

    return AuthResult(
        user=AuthUser(
            id=user.id,
            email=user.email,
            username=user.user_metadata.get("username") or user.user_metadata.get("name"),
        ),
        session=(
            AuthSession(
                access_token=session.access_token,
                refresh_token=session.refresh_token,
                token_type=session.token_type,
                expires_in=session.expires_in,
                expires_at=session.expires_at,
            )
            if session
            else None
        ),
    )


def auth_error(exc: AuthApiError, code: int) -> HTTPException:
    return HTTPException(status_code=code, detail=str(exc))
