from fastapi import Header, HTTPException, status

from app.core.config import settings
from app.core.config_files import app_config


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Admin endpoints (upload, refresh, alert marking). Disabled when ADMIN_API_KEY is empty."""
    if not settings.admin_api_key or x_api_key != settings.admin_api_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, app_config().messages["invalid_api_key"])
