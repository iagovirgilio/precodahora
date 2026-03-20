from fastapi.testclient import TestClient
import requests

from app.config import settings
from app.main import _rate_limit_bucket, app
from app.services.precos import get_preco_da_hora_service


class FakeServiceSuccess:
    def buscar_lista(self, gtins, latitude, longitude, raio, horas):
        return {
            "consultado_em": "2026-03-20T13:21:28Z",
            "localizacao": {
                "latitude": latitude,
                "longitude": longitude,
                "raio_km": raio,
            },
            "resultados": {
                gtin: {"total_encontrado": 0, "top5": []}
                for gtin in gtins
            },
        }


class FakeServiceHttpError:
    def buscar_lista(self, gtins, latitude, longitude, raio, horas):
        response = requests.Response()
        response.status_code = 503
        raise requests.HTTPError(response=response)


class FakeServiceNetworkError:
    def buscar_lista(self, gtins, latitude, longitude, raio, horas):
        raise requests.RequestException("rede indisponivel")


class FakeServiceRuntimeError:
    def buscar_lista(self, gtins, latitude, longitude, raio, horas):
        raise RuntimeError("erro interno")


def test_healthcheck_deve_retornar_ok():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "cache_ttl_seconds" in body


def test_post_buscar_deve_retornar_contrato_esperado():
    app.dependency_overrides[get_preco_da_hora_service] = lambda: FakeServiceSuccess()
    client = TestClient(app)

    payload = {
        "gtins": ["7894904015108"],
        "latitude": -12.2690245,
        "longitude": -38.9295865,
        "raio": 15,
        "horas": 72,
    }
    response = client.post("/api/v1/precos/buscar", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["resultados"]["7894904015108"]["total_encontrado"] == 0
    assert body["resultados"]["7894904015108"]["top5"] == []
    app.dependency_overrides.clear()


def test_post_buscar_deve_retornar_422_para_gtin_invalido():
    app.dependency_overrides[get_preco_da_hora_service] = lambda: FakeServiceSuccess()
    client = TestClient(app)
    response = client.post("/api/v1/precos/buscar", json={"gtins": ["123"]})
    assert response.status_code == 422
    app.dependency_overrides.clear()


def test_rate_limit_deve_retornar_429_quando_excedido():
    app.dependency_overrides[get_preco_da_hora_service] = lambda: FakeServiceSuccess()
    client = TestClient(app)
    _rate_limit_bucket.clear()

    limite_original = settings.rate_limit_requests_per_minute
    settings.rate_limit_requests_per_minute = 2
    try:
        payload = {"gtins": ["7894904015108"]}
        assert client.post("/api/v1/precos/buscar", json=payload).status_code == 200
        assert client.post("/api/v1/precos/buscar", json=payload).status_code == 200
        assert client.post("/api/v1/precos/buscar", json=payload).status_code == 429
    finally:
        settings.rate_limit_requests_per_minute = limite_original
        _rate_limit_bucket.clear()
        app.dependency_overrides.clear()


def test_post_buscar_deve_retornar_502_para_erro_http_upstream():
    app.dependency_overrides[get_preco_da_hora_service] = lambda: FakeServiceHttpError()
    client = TestClient(app)
    response = client.post("/api/v1/precos/buscar", json={"gtins": ["7894904015108"]})
    assert response.status_code == 502
    app.dependency_overrides.clear()


def test_post_buscar_deve_retornar_503_para_erro_rede():
    app.dependency_overrides[get_preco_da_hora_service] = lambda: FakeServiceNetworkError()
    client = TestClient(app)
    response = client.post("/api/v1/precos/buscar", json={"gtins": ["7894904015108"]})
    assert response.status_code == 503
    app.dependency_overrides.clear()


def test_post_buscar_deve_retornar_500_para_runtime_error():
    app.dependency_overrides[get_preco_da_hora_service] = lambda: FakeServiceRuntimeError()
    client = TestClient(app)
    response = client.post("/api/v1/precos/buscar", json={"gtins": ["7894904015108"]})
    assert response.status_code == 500
    app.dependency_overrides.clear()
