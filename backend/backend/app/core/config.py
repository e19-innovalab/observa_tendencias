from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Rumbo"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/rumbo"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3010"]
    admin_api_key: str = ""  # X-API-Key for upload / refresh / alert endpoints
    bcentral_user: str = ""
    bcentral_password: str = ""


settings = Settings()
