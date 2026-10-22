import logging

from fastapi import APIRouter, status
from supabase_auth.errors import AuthApiError

from app.core.config import settings
from app.schemas.auth import (
    AuthResult,
    GoogleAuthUrl,
    ResendConfirmationRequest,
    SignInRequest,
    SignUpRequest,
)
from app.services.supabase_auth import auth_error, auth_result, get_supabase_client

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


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
def sign_in(payload: SignInRequest):
    client = get_supabase_client()
    try:
        response = client.auth.sign_in_with_password(
            {"email": payload.email, "password": payload.password}
        )
    except AuthApiError as exc:
        raise auth_error(exc, status.HTTP_401_UNAUTHORIZED) from exc
    result = auth_result(response)
    session = response.session
    if session is None:
        raise auth_error(
            AuthApiError("Supabase no devolvió una sesión para el inicio de sesión.", None),
            status.HTTP_502_BAD_GATEWAY,
        )
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
