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
    cors_origins: list[str] = []
    admin_api_key: str = ""  # X-API-Key for upload / refresh / alert endpoints (scripts)
    auth_secret: str = ""  # signs login tokens; empty = login disabled
    config_dir: Path = BACKEND_DIR / "config"
    bcentral_user: str = ""
    bcentral_password: str = ""
    anthropic_api_key: str = ""  # assistant with provider anthropic
    # key of the OpenAI-compatible server (provider local): empty for Ollama on this computer, the
    # API key for a hosted service (Groq, Together, OpenRouter…)
    assistant_local_api_key: str = ""
    # Per environment, instead of app.yaml -> assistant (empty = use app.yaml). In the cloud there is
    # no Ollama: point provider local to a hosted OpenAI-compatible API with these.
    assistant_provider: str = ""  # local | anthropic
    assistant_base_url: str = ""  # URL of the OpenAI-compatible API (provider local)
    assistant_model: str = ""  # model name for the active provider


settings = Settings()
