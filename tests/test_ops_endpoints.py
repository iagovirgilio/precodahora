from fastapi.testclient import TestClient

from app.main import app


def test_ready_sem_redis_marca_skipped(monkeypatch):
    monkeypatch.setattr("app.config.settings.redis_url", "")
    with TestClient(app) as client:
        r = client.get("/ready")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ready"
    assert data["checks"]["redis"] == "skipped"


def test_metrics_expoem_contador_prometheus():
    with TestClient(app) as client:
        r = client.get("/metrics")
    assert r.status_code == 200
    assert "precodahora_http_requests_total" in r.text
