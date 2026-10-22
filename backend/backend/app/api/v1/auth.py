import logging

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from supabase_auth.errors import AuthApiError
from supabase_auth.types import Session, User

from app.core.config import settings
from app.schemas.auth import (
    AuthResult,
    AuthSessionRequest,
    AuthUser,
    GoogleAuthUrl,
    ResendConfirmationRequest,
    SignInRequest,
    SignUpRequest,
)
from app.services.supabase_auth import auth_error, auth_result, get_supabase_client

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)
ACCESS_COOKIE = "observa_access_token"
REFRESH_COOKIE = "observa_refresh_token"
COOKIE_OPTIONS = {
    "httponly": True,
    "secure": settings.auth_cookie_secure,
    "samesite": "lax",
    "path": "/",
}


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(ACCESS_COOKIE, access_token, **COOKIE_OPTIONS)
    response.set_cookie(REFRESH_COOKIE, refresh_token, **COOKIE_OPTIONS)


def set_session_cookies(response: Response, session: Session) -> None:
    set_auth_cookies(response, session.access_token, session.refresh_token)


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, **COOKIE_OPTIONS)
    response.delete_cookie(REFRESH_COOKIE, **COOKIE_OPTIONS)


def expired_session_response() -> JSONResponse:
    response = JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "La sesión venció. Inicia sesión nuevamente."},
    )
    clear_session_cookies(response)
    return response


def user_result(user: User) -> AuthResult:
    metadata = user.user_metadata or {}
    return AuthResult(
        user=AuthUser(
            id=user.id,
            email=user.email,
            username=metadata.get("username") or metadata.get("name"),
        ),
        authenticated=True,
    )


@router.post("/signup", response_model=AuthResult, status_code=status.HTTP_201_CREATED)
def sign_up(payload: SignUpRequest):
    client = get_supabase_client()
    options = {"data": {"username": payload.username}}
    if settings.supabase_redirect_url:
        options["email_redirect_to"] = settings.supabase_redirect_url
    try:
        response = client.auth.sign_up(
            {
                "email": payload.email,
                "password": payload.password,
                "options": options,
            }
        )
    except AuthApiError as exc:
        raise auth_error(exc, status.HTTP_400_BAD_REQUEST) from exc
    return auth_result(response)


@router.post("/login", response_model=AuthResult)
def sign_in(payload: SignInRequest, response: Response):
    client = get_supabase_client()
    try:
        auth_response = client.auth.sign_in_with_password(
            {"email": payload.email, "password": payload.password}
        )
    except AuthApiError as exc:
        raise auth_error(exc, status.HTTP_401_UNAUTHORIZED) from exc
    result = auth_result(auth_response)
    session = auth_response.session
    if session is None:
        raise auth_error(
            AuthApiError(
                "Supabase no devolvió una sesión para el inicio de sesión.",
                status.HTTP_502_BAD_GATEWAY,
                None,
            ),
            status.HTTP_502_BAD_GATEWAY,
        )
    set_session_cookies(response, session)
    logger.info(
        "Supabase login successful: user_id=%s email=%s token_received=%s "
        "token_type=%s expires_in=%s",
        result.user.id,
        result.user.email,
        bool(session.access_token),
        session.token_type,
        session.expires_in,
    )
    return result


@router.post("/session", response_model=AuthResult)
def establish_session(payload: AuthSessionRequest, response: Response):
    client = get_supabase_client()
    try:
        user_response = client.auth.get_user(payload.access_token)
    except AuthApiError as exc:
        raise auth_error(exc, status.HTTP_401_UNAUTHORIZED) from exc
    if user_response is None or user_response.user is None:
        raise auth_error(
            AuthApiError(
                "Supabase no pudo validar el usuario recibido.",
                status.HTTP_401_UNAUTHORIZED,
                None,
            ),
            status.HTTP_401_UNAUTHORIZED,
        )
    set_auth_cookies(response, payload.access_token, payload.refresh_token)
    return user_result(user_response.user)


@router.get("/me", response_model=AuthResult)
def current_user(request: Request, response: Response):
    access_token = request.cookies.get(ACCESS_COOKIE)
    refresh_token = request.cookies.get(REFRESH_COOKIE)
    if not access_token and not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No hay una sesión iniciada.",
        )

    client = get_supabase_client()
    user = None
    if access_token:
        try:
            user_response = client.auth.get_user(access_token)
        except AuthApiError:
            user_response = None
        if user_response is not None:
            user = user_response.user

    if user is None and refresh_token:
        try:
            refreshed = client.auth.refresh_session(refresh_token)
        except AuthApiError as exc:
            logger.warning("Supabase session refresh failed: %s", exc)
            return expired_session_response()
        if refreshed.session is None or refreshed.user is None:
            return expired_session_response()
        set_session_cookies(response, refreshed.session)
        user = refreshed.user

    if user is None:
        return expired_session_response()
    return user_result(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def sign_out(request: Request, response: Response):
    access_token = request.cookies.get(ACCESS_COOKIE)
    refresh_token = request.cookies.get(REFRESH_COOKIE)
    clear_session_cookies(response)

    if access_token and refresh_token:
        client = get_supabase_client()
        try:
            client.auth.set_session(access_token, refresh_token)
            client.auth.sign_out({"scope": "local"})
        except AuthApiError as exc:
            logger.warning("Supabase session revocation failed: %s", exc)
            error_response = JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content={"detail": "No se pudo revocar la sesión en Supabase."},
            )
            clear_session_cookies(error_response)
            return error_response


@router.post("/resend-confirmation", status_code=status.HTTP_202_ACCEPTED)
def resend_confirmation(payload: ResendConfirmationRequest):
    client = get_supabase_client()
    options = {}
    if settings.supabase_redirect_url:
        options["email_redirect_to"] = settings.supabase_redirect_url
    try:
        client.auth.resend(
            {
                "type": "signup",
                "email": payload.email,
                "options": options,
            }
        )
    except AuthApiError as exc:
        raise auth_error(exc, status.HTTP_400_BAD_REQUEST) from exc
    return {"message": "Si la cuenta necesita confirmación, se envió un nuevo correo."}


@router.get("/google", response_model=GoogleAuthUrl)
def google_sign_in():
    client = get_supabase_client()
    options = {}
    if settings.supabase_redirect_url:
        options["redirect_to"] = settings.supabase_redirect_url
    try:
        response = client.auth.sign_in_with_oauth(
            {"provider": "google", "options": options}
        )
    except AuthApiError as exc:
        raise auth_error(exc, status.HTTP_400_BAD_REQUEST) from exc
    return {"auth_url": response.url}
