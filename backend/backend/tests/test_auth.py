"""Login, roles and user management."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core import auth as auth_module
from app.core.config import settings
from app.core.config_files import app_config, catalog
from app.core.database import get_session
from app.main import app
from app.models import Base, Country
from app.services.users import create_user
from tests.conftest import sqlite_tables

PASSWORD = "clave-segura-123"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "test-secret")
    monkeypatch.setattr(settings, "admin_api_key", "")
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine, tables=sqlite_tables())
    with Session(engine) as s:
        s.add_all([Country(iso3=c.iso3, name_es=c.name_es, name_en=c.name_en) for c in catalog().countries])
        create_user(s, "admin@obs.org", "Ana Admin", PASSWORD, "admin")
        create_user(s, "editor@obs.org", "Eva Editora", PASSWORD, "editor", "health", ["arg"])
        create_user(s, "viewer@obs.org", "Vera Consulta", PASSWORD, "viewer")
        s.commit()

    def override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def _login(c, email):
    r = c.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_password_hash_and_token_round_trip(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "s")
    stored = auth_module.hash_password("abc")
    assert stored.startswith("scrypt$") and auth_module.verify_password("abc", stored)
    assert not auth_module.verify_password("abd", stored)
    token, expires = auth_module.create_token(7, now=1_000)
    assert auth_module.decode_token(token, now=1_001) == 7
    with pytest.raises(Exception):  # expired
        auth_module.decode_token(token, now=expires + 1)
    with pytest.raises(Exception):  # tampered
        auth_module.decode_token(token[:-2] + "xx", now=1_001)


def test_login_and_me(client):
    r = client.post("/api/v1/auth/login", json={"email": "EDITOR@obs.org", "password": PASSWORD})
    body = r.json()
    assert r.status_code == 200 and body["token_type"] == "bearer"
    assert body["user"]["role_label"] == app_config().auth.roles["editor"].label
    assert body["user"]["sector_name"] == "Salud" and body["user"]["countries"] == ["ARG"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}).json()
    assert me["email"] == "editor@obs.org" and me["last_login_at"]
    assert "manage_data" in me["permissions"] and "manage_users" not in me["permissions"]
    assert client.post("/api/v1/auth/login", json={"email": "editor@obs.org", "password": "nope-nope-1"}).status_code == 401
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer v1.bad.sig"}).status_code == 401


def test_roles_gate_user_management_and_data_actions(client):
    admin, editor, viewer = (_login(client, e) for e in ("admin@obs.org", "editor@obs.org", "viewer@obs.org"))
    assert client.get("/api/v1/users", headers=admin).json()["total"] == 3
    assert client.get("/api/v1/users", headers=editor).status_code == 403
    assert client.get("/api/v1/users").status_code == 401
    # data actions: editors yes, viewers no (refresh of an unknown source: 404 means it got through)
    assert client.post("/api/v1/sources/nope/refresh", headers=editor).status_code == 404
    assert client.post("/api/v1/sources/nope/refresh", headers=viewer).status_code == 403


def test_admin_creates_updates_and_suspends_users(client):
    admin = _login(client, "admin@obs.org")
    new = {"email": "nuevo@obs.org", "full_name": "Nico Nuevo", "password": PASSWORD,
           "role": "viewer", "sector_code": "energy", "countries": ["chl", "ury"]}
    r = client.post("/api/v1/users", json=new, headers=admin)
    assert r.status_code == 201 and r.json()["countries"] == ["CHL", "URY"]
    assert client.post("/api/v1/users", json=new, headers=admin).status_code == 409  # same email
    bad = client.post("/api/v1/users", json={**new, "email": "x@obs.org", "password": "corta"}, headers=admin)
    assert bad.status_code == 422
    uid = r.json()["user_id"]
    up = client.patch(f"/api/v1/users/{uid}", json={"role": "editor", "status": "suspended"}, headers=admin)
    assert up.status_code == 200 and up.json()["status"] == "suspended"
    # null fields are left as they are; the sector is cleared with null or ""
    up = client.patch(f"/api/v1/users/{uid}", json={"role": None, "full_name": None, "sector_code": ""},
                      headers=admin)
    assert up.status_code == 200 and (up.json()["role"], up.json()["full_name"]) == ("editor", "Nico Nuevo")
    assert up.json()["sector_code"] is None
    # a suspended user can no longer log in
    assert client.post("/api/v1/auth/login", json={"email": "nuevo@obs.org", "password": PASSWORD}).status_code == 403
    found = client.get("/api/v1/users", params={"q": "nico", "status": "suspended"}, headers=admin).json()
    assert [u["email"] for u in found["items"]] == ["nuevo@obs.org"]
    assert client.get("/api/v1/users/options", headers=admin).json()["password_min_length"] == \
        app_config().auth.password_min_length


def test_last_admin_cannot_lose_the_role(client):
    admin = _login(client, "admin@obs.org")
    me = client.get("/api/v1/auth/me", headers=admin).json()
    r = client.patch(f"/api/v1/users/{me['user_id']}", json={"role": "viewer"}, headers=admin)
    assert r.status_code == 409


def test_change_own_password(client):
    viewer = _login(client, "viewer@obs.org")
    assert client.post("/api/v1/auth/password", headers=viewer,
                       json={"current_password": "mal", "new_password": "otra-clave-456"}).status_code == 400
    assert client.post("/api/v1/auth/password", headers=viewer,
                       json={"current_password": PASSWORD, "new_password": "otra-clave-456"}).status_code == 204
    assert client.post("/api/v1/auth/login",
                       json={"email": "viewer@obs.org", "password": "otra-clave-456"}).status_code == 200


def test_login_disabled_without_secret(client, monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "")
    r = client.post("/api/v1/auth/login", json={"email": "admin@obs.org", "password": PASSWORD})
    assert r.status_code == 503
