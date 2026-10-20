from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_explorer_served_when_enabled():
    from app.core.config_files import app_config

    r = client.get("/explorer")
    if app_config().dev_tools.explorer:
        assert r.status_code == 200 and "Explorer" in r.text
    else:
        assert r.status_code == 404
