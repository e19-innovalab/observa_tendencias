import logging
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from supabase_auth.errors import AuthApiError

from app.api.v1 import auth
from app.main import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(auth.settings, "supabase_url", "https://example.supabase.co")
    monkeypatch.setattr(auth.settings, "supabase_anon_key", "test-key")
    monkeypatch.setattr(
        auth.settings, "supabase_redirect_url", "http://localhost:3010/auth/callback"
    )
    return TestClient(app)


def test_signup_sends_email_password_and_username(client, monkeypatch):
    calls = {}

    class FakeAuth:
        def sign_up(self, credentials):
            calls["credentials"] = credentials
            return SimpleNamespace(
                user=SimpleNamespace(
                    id="user-id",
                    email="person@example.com",
                    user_metadata={"username": "person"},
                ),
                session=None,
            )

    monkeypatch.setattr(auth, "get_supabase_client", lambda: SimpleNamespace(auth=FakeAuth()))

    response = client.post(
        "/api/v1/auth/signup",
        json={"username": " person ", "email": "person@example.com", "password": " secret "},
    )

    assert response.status_code == 201
    assert calls["credentials"]["options"]["data"]["username"] == "person"
    assert calls["credentials"]["options"]["email_redirect_to"] == (
        "http://localhost:3010/auth/callback"
    )
    assert calls["credentials"]["password"] == " secret "
    assert response.json()["user"] == {
        "id": "user-id",
        "email": "person@example.com",
        "username": "person",
    }
    assert response.json()["authenticated"] is False
    assert "session" not in response.json()


def test_login_returns_no_tokens_to_frontend(client, monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger=auth.__name__)

    class FakeAuth:
        def sign_in_with_password(self, credentials):
            assert credentials == {"email": "person@example.com", "password": "secret"}
            return SimpleNamespace(
                user=SimpleNamespace(
                    id="user-id", email="person@example.com", user_metadata={}
                ),
                session=SimpleNamespace(
                    access_token="sensitive-access-jwt",
                    refresh_token="refresh",
                    token_type="bearer",
                    expires_in=3600,
                    expires_at=123456,
                ),
            )

    monkeypatch.setattr(auth, "get_supabase_client", lambda: SimpleNamespace(auth=FakeAuth()))

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "person@example.com", "password": "secret"},
    )

    assert response.status_code == 200
    assert response.json()["authenticated"] is True
    assert response.cookies.get(auth.ACCESS_COOKIE) == "sensitive-access-jwt"
    assert response.cookies.get(auth.REFRESH_COOKIE) == "refresh"
    assert all("HttpOnly" in cookie for cookie in response.headers.get_list("set-cookie"))
    assert "session" not in response.json()
    assert "sensitive-access-jwt" not in response.text
    assert "Supabase login successful" in caplog.text
    assert "user-id" in caplog.text
    assert "person@example.com" in caplog.text
    assert "token_received=True" in caplog.text
    assert "token_type=bearer" in caplog.text
    assert "expires_in=3600" in caplog.text
    assert "sensitive-access-jwt" not in caplog.text
    assert "refresh" not in caplog.text


def test_login_cookies_persist_for_current_user_request(client, monkeypatch):
    user = SimpleNamespace(
        id="user-id",
        email="person@example.com",
        user_metadata={"username": "person"},
    )
    session = SimpleNamespace(
        access_token="session-access",
        refresh_token="session-refresh",
        token_type="bearer",
        expires_in=3600,
        expires_at=123456,
    )

    class FakeAuth:
        def sign_in_with_password(self, credentials):
            return SimpleNamespace(user=user, session=session)

        def get_user(self, access_token):
            assert access_token == "session-access"
            return SimpleNamespace(user=user)

    monkeypatch.setattr(auth, "get_supabase_client", lambda: SimpleNamespace(auth=FakeAuth()))

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "person@example.com", "password": "secret"},
    )
    current_user_response = client.get("/api/v1/auth/me")

    assert login_response.status_code == 200
    assert current_user_response.status_code == 200
    assert current_user_response.json()["user"]["email"] == "person@example.com"
    assert current_user_response.json()["authenticated"] is True


def test_google_session_exchange_validates_tokens_and_sets_http_only_cookies(
    client, monkeypatch
):
    user = SimpleNamespace(
        id="google-user-id",
        email="person@example.com",
        user_metadata={"name": "Person"},
    )
    class FakeAuth:
        def get_user(self, access_token):
            assert access_token == "google-access"
            return SimpleNamespace(user=user)

    monkeypatch.setattr(auth, "get_supabase_client", lambda: SimpleNamespace(auth=FakeAuth()))

    response = client.post(
        "/api/v1/auth/session",
        json={"access_token": "google-access", "refresh_token": "google-refresh"},
        headers={"Origin": "http://localhost:3010"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3010"
    assert response.headers["access-control-allow-credentials"] == "true"
    assert response.json() == {
        "user": {
            "id": "google-user-id",
            "email": "person@example.com",
            "username": "Person",
        },
        "authenticated": True,
    }
    assert response.cookies.get(auth.ACCESS_COOKIE) == "google-access"
    assert response.cookies.get(auth.REFRESH_COOKIE) == "google-refresh"
    assert all("HttpOnly" in cookie for cookie in response.headers.get_list("set-cookie"))
    assert "google-access" not in response.text
    assert "google-refresh" not in response.text

    explorer_response = client.get("/explorer")
    current_user_response = client.get(
        "/api/v1/auth/me",
        headers={"Origin": "http://localhost:3010"},
    )

    assert explorer_response.status_code == 200
    assert current_user_response.status_code == 200
    assert current_user_response.headers["access-control-allow-origin"] == (
        "http://localhost:3010"
    )
    assert current_user_response.json()["user"]["email"] == "person@example.com"


def test_current_user_uses_cookie_session(client, monkeypatch):
    user = SimpleNamespace(
        id="user-id", email="person@example.com", user_metadata={"username": "person"}
    )

    class FakeAuth:
        def get_user(self, access_token):
            assert access_token == "valid-access"
            return SimpleNamespace(user=user)

    monkeypatch.setattr(auth, "get_supabase_client", lambda: SimpleNamespace(auth=FakeAuth()))
    client.cookies.set(auth.ACCESS_COOKIE, "valid-access")
    client.cookies.set(auth.REFRESH_COOKIE, "valid-refresh")

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["user"]["id"] == "user-id"
    assert response.json()["authenticated"] is True


def test_current_user_refreshes_expired_access_token(client, monkeypatch):
    user = SimpleNamespace(
        id="user-id", email="person@example.com", user_metadata={"username": "person"}
    )
    session = SimpleNamespace(
        access_token="renewed-access", refresh_token="renewed-refresh", expires_in=3600
    )

    class FakeAuth:
        def get_user(self, access_token):
            assert access_token == "expired-access"
            raise AuthApiError("Token expired", 401, "invalid_jwt")

        def refresh_session(self, refresh_token):
            assert refresh_token == "valid-refresh"
            return SimpleNamespace(session=session, user=user)

    monkeypatch.setattr(auth, "get_supabase_client", lambda: SimpleNamespace(auth=FakeAuth()))
    client.cookies.set(auth.ACCESS_COOKIE, "expired-access")
    client.cookies.set(auth.REFRESH_COOKIE, "valid-refresh")

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["user"]["id"] == "user-id"
    assert response.cookies.get(auth.ACCESS_COOKIE) == "renewed-access"
    assert response.cookies.get(auth.REFRESH_COOKIE) == "renewed-refresh"


def test_current_user_clears_expired_session_cookies(client, monkeypatch):
    class FakeAuth:
        def get_user(self, access_token):
            raise AuthApiError("Token expired", 401, "invalid_jwt")

        def refresh_session(self, refresh_token):
            raise AuthApiError("Refresh token expired", 401, "invalid_grant")

    monkeypatch.setattr(auth, "get_supabase_client", lambda: SimpleNamespace(auth=FakeAuth()))
    client.cookies.set(auth.ACCESS_COOKIE, "expired-access")
    client.cookies.set(auth.REFRESH_COOKIE, "expired-refresh")

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "La sesión venció. Inicia sesión nuevamente."
    assert all("Max-Age=0" in cookie for cookie in response.headers.get_list("set-cookie"))


def test_logout_revokes_and_clears_cookie_session(client, monkeypatch):
    calls = {}

    class FakeAuth:
        def set_session(self, access_token, refresh_token):
            calls["session"] = (access_token, refresh_token)

        def sign_out(self, options):
            calls["sign_out"] = options

    monkeypatch.setattr(auth, "get_supabase_client", lambda: SimpleNamespace(auth=FakeAuth()))
    client.cookies.set(auth.ACCESS_COOKIE, "valid-access")
    client.cookies.set(auth.REFRESH_COOKIE, "valid-refresh")

    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 204
    assert calls["session"] == ("valid-access", "valid-refresh")
    assert calls["sign_out"] == {"scope": "local"}
    assert all("Max-Age=0" in cookie for cookie in response.headers.get_list("set-cookie"))


def test_google_sign_in_returns_oauth_url(client, monkeypatch):
    class FakeAuth:
        def sign_in_with_oauth(self, credentials):
            assert credentials == {
                "provider": "google",
                "options": {
                    "redirect_to": "http://localhost:3010/auth/callback",
                    "query_params": {"prompt": "select_account"},
                },
            }
            return SimpleNamespace(url="https://accounts.google.com/oauth")

    monkeypatch.setattr(auth, "get_supabase_client", lambda: SimpleNamespace(auth=FakeAuth()))

    response = client.get("/api/v1/auth/google")

    assert response.status_code == 200
    assert response.json() == {"auth_url": "https://accounts.google.com/oauth"}


def test_resend_confirmation_uses_signup_type_and_callback(client, monkeypatch):
    calls = {}

    class FakeAuth:
        def resend(self, credentials):
            calls["credentials"] = credentials

    monkeypatch.setattr(auth, "get_supabase_client", lambda: SimpleNamespace(auth=FakeAuth()))

    response = client.post(
        "/api/v1/auth/resend-confirmation",
        json={"email": "person@example.com"},
    )

    assert response.status_code == 202
    assert calls["credentials"] == {
        "type": "signup",
        "email": "person@example.com",
        "options": {"email_redirect_to": "http://localhost:3010/auth/callback"},
    }


def test_auth_requires_supabase_environment(client, monkeypatch):
    monkeypatch.setattr(auth.settings, "supabase_anon_key", "")

    response = client.get("/api/v1/auth/google")

    assert response.status_code == 503


def test_auth_cors_allows_credentialed_frontend_requests(client):
    response = client.options(
        "/api/v1/auth/me",
        headers={
            "Origin": "http://localhost:3010",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3010"
    assert response.headers["access-control-allow-credentials"] == "true"
