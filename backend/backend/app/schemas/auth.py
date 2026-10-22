from pydantic import BaseModel, Field, field_validator


class SignUpRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, username: str) -> str:
        username = username.strip()
        if not username:
            raise ValueError("El nombre de usuario no puede estar vacío.")
        return username


class SignInRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)


class ResendConfirmationRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class AuthUser(BaseModel):
    id: str
    email: str | None = None
    username: str | None = None


class AuthResult(BaseModel):
    user: AuthUser
    authenticated: bool


class GoogleAuthUrl(BaseModel):
    auth_url: str
