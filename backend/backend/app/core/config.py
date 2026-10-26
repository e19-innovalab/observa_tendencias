"""Environment settings: secrets and values that change between environments (backend/.env).

Everything else lives in backend/config/*.yaml and is read through app.core.config_files.
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    database_connect_timeout: int = 5
    cors_origins: list[str] = ["http://localhost:3010"]
    admin_api_key: str = ""  # X-API-Key for upload / refresh / alert endpoints
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_redirect_url: str = "http://localhost:3010/auth/callback"
    auth_cookie_secure: bool = False
    config_dir: Path = BACKEND_DIR / "config"
    bcentral_user: str = ""
    bcentral_password: str = ""


settings = Settings()
