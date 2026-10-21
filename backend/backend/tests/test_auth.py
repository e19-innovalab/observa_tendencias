import logging
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

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
    assert response.json()["session"] is None


def test_login_returns_supabase_session_and_logs_redacted_token_metadata(
    client, monkeypatch, caplog
):
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
    assert response.json()["session"]["access_token"] == "sensitive-access-jwt"
    assert response.json()["session"]["refresh_token"] == "refresh"
    assert "Supabase login successful" in caplog.text
    assert "user-id" in caplog.text
    assert "person@example.com" in caplog.text
    assert "token_received=True" in caplog.text
    assert "token_type=bearer" in caplog.text
    assert "expires_in=3600" in caplog.text
    assert "sensitive-access-jwt" not in caplog.text
    assert "refresh" not in caplog.text


def test_google_sign_in_returns_oauth_url(client, monkeypatch):
    class FakeAuth:
        def sign_in_with_oauth(self, credentials):
            assert credentials == {
                "provider": "google",
                "options": {"redirect_to": "http://localhost:3010/auth/callback"},
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
