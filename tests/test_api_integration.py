import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.precos import BuscarPrecosObservabilidade, get_preco_da_hora_service


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("app.config.settings.api_auth_enabled", True)
    monkeypatch.setattr("app.config.settings.api_keys", "integration-test-key")
    monkeypatch.setattr("app.config.settings.rate_limit_requests_per_minute", 5)
    monkeypatch.setattr("app.config.settings.max_gtins_per_request", 3)
    import app.main as main_mod

    main_mod._rate_limit_bucket.clear()

    class FakePrecoService:
        def buscar_lista(self, **_kwargs):
            return (
                {
                    "consultado_em": "2026-03-22T12:00:00Z",
                    "localizacao": {
                        "latitude": -12.0,
                        "longitude": -38.0,
                        "raio_km": 15,
                    },
                    "resultados": {},
                },
                BuscarPrecosObservabilidade(),
            )

    app.dependency_overrides[get_preco_da_hora_service] = lambda: FakePrecoService()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    main_mod._rate_limit_bucket.clear()


def test_health_sem_api_key(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_buscar_sem_api_key_retorna_401(client):
    r = client.post("/api/v1/precos/buscar", json={"gtins": ["7894904015108"]})
    assert r.status_code == 401
    body = r.json()
    assert body["error"]["code"] == "unauthorized"
    assert "request_id" in body["error"]


def test_buscar_com_bearer_ok(client):
    r = client.post(
        "/api/v1/precos/buscar",
        headers={"Authorization": "Bearer integration-test-key"},
        json={"gtins": ["7894904015108"]},
    )
    assert r.status_code == 200
    assert r.headers.get("X-Request-Id")


def test_buscar_com_x_api_key_ok(client):
    r = client.post(
        "/api/v1/precos/buscar",
        headers={"X-API-Key": "integration-test-key"},
        json={"gtins": ["7894904015108"]},
    )
    assert r.status_code == 200


def test_request_id_ecoado_no_header(client):
    rid = "abc-def-0123456789"
    r = client.post(
        "/api/v1/precos/buscar",
        headers={
            "Authorization": "Bearer integration-test-key",
            "X-Request-Id": rid,
        },
        json={"gtins": ["7894904015108"]},
    )
    assert r.status_code == 200
    assert r.headers["X-Request-Id"] == rid


def test_validation_gtins_demais_retorna_422_envelope(client):
    r = client.post(
        "/api/v1/precos/buscar",
        headers={"Authorization": "Bearer integration-test-key"},
        json={"gtins": ["7894904015108", "7896224802963", "12345670", "123456789012"]},
    )
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["code"] == "validation_error"
    assert "details" in body["error"]


def test_rate_limit_429_envelope(client):
    h = {"Authorization": "Bearer integration-test-key"}
    body = {"gtins": ["7894904015108"]}
    for _ in range(5):
        r = client.post("/api/v1/precos/buscar", headers=h, json=body)
        assert r.status_code == 200
    r = client.post("/api/v1/precos/buscar", headers=h, json=body)
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "rate_limit_exceeded"
