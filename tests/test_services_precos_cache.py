from unittest.mock import MagicMock

import pytest

from app.config import settings
from app.services.precos import PrecoDaHoraService, SearchParams


@pytest.fixture
def params_base() -> dict:
    return {"latitude": -1.0, "longitude": -2.0, "raio": 15, "horas": 72}


def test_cache_evita_segundo_post_upstream(monkeypatch, params_base):
    monkeypatch.setattr(settings, "cache_ttl_seconds", 3600)
    monkeypatch.setattr(settings, "cache_max_entries", 16)
    svc = PrecoDaHoraService()
    svc._csrf_token = "fake"
    calls = {"n": 0}

    def fake_post(*_a, **_k):
        calls["n"] += 1
        r = MagicMock()
        r.status_code = 200
        r.json.return_value = {"resultado": [], "totalRegistros": 0}
        return r

    monkeypatch.setattr(svc, "_post_with_retry", fake_post)
    p = SearchParams(gtin="7896224802963", **params_base)
    svc._buscar(p)
    svc._buscar(p)
    assert calls["n"] == 1


def test_cache_respeita_ttl(monkeypatch, params_base):
    monkeypatch.setattr(settings, "cache_ttl_seconds", 10)
    monkeypatch.setattr(settings, "cache_max_entries", 16)
    svc = PrecoDaHoraService()
    svc._csrf_token = "fake"
    calls = {"n": 0}
    clock = {"t": 1_000_000.0}

    def fake_time():
        return clock["t"]

    def fake_post(*_a, **_k):
        calls["n"] += 1
        r = MagicMock()
        r.status_code = 200
        r.json.return_value = {"resultado": [], "totalRegistros": 0}
        return r

    monkeypatch.setattr("app.services.precos.time.time", fake_time)
    monkeypatch.setattr(svc, "_post_with_retry", fake_post)
    p = SearchParams(gtin="7896224802963", **params_base)
    svc._buscar(p)
    clock["t"] += 11.0
    svc._buscar(p)
    assert calls["n"] == 2


def test_cache_lru_evict_menos_recente(monkeypatch, params_base):
    monkeypatch.setattr(settings, "cache_ttl_seconds", 3600)
    monkeypatch.setattr(settings, "cache_max_entries", 2)
    svc = PrecoDaHoraService()
    svc._csrf_token = "fake"
    calls = {"n": 0}

    def fake_post(*_a, **_k):
        calls["n"] += 1
        r = MagicMock()
        r.status_code = 200
        r.json.return_value = {"resultado": [], "totalRegistros": 0}
        return r

    monkeypatch.setattr(svc, "_post_with_retry", fake_post)
    svc._buscar(SearchParams(gtin="111", **params_base))
    svc._buscar(SearchParams(gtin="222", **params_base))
    svc._buscar(SearchParams(gtin="333", **params_base))
    svc._buscar(SearchParams(gtin="111", **params_base))
    assert calls["n"] == 4


def test_cache_hit_atualiza_ordem_lru(monkeypatch, params_base):
    monkeypatch.setattr(settings, "cache_ttl_seconds", 3600)
    monkeypatch.setattr(settings, "cache_max_entries", 2)
    svc = PrecoDaHoraService()
    svc._csrf_token = "fake"
    calls = {"n": 0}

    def fake_post(*_a, **_k):
        calls["n"] += 1
        r = MagicMock()
        r.status_code = 200
        r.json.return_value = {"resultado": [], "totalRegistros": 0}
        return r

    monkeypatch.setattr(svc, "_post_with_retry", fake_post)
    svc._buscar(SearchParams(gtin="111", **params_base))
    svc._buscar(SearchParams(gtin="222", **params_base))
    svc._buscar(SearchParams(gtin="222", **params_base))
    svc._buscar(SearchParams(gtin="333", **params_base))
    svc._buscar(SearchParams(gtin="222", **params_base))
    assert calls["n"] == 3
