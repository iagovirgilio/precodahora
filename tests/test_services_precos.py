import requests

import app.services.precos as precos_module
from app.services.precos import (
    PrecoDaHoraService,
    SearchParams,
    UpstreamChallengeError,
)


def test_to_iso_utc_deve_converter_data_do_site():
    service = PrecoDaHoraService()
    assert service._to_iso_utc("2026-03-20 13:15:48-00:00") == "2026-03-20T13:15:48Z"


def test_normalizar_cnpj_deve_preservar_14_digitos():
    service = PrecoDaHoraService()
    assert service._normalizar_cnpj(2212937004224) == "02212937004224"


def test_normalizar_item_deve_mapear_campos_esperados():
    service = PrecoDaHoraService()
    item_bruto = {
        "produto": {
            "gtin": 7896224802963,
            "descricao": "CAFE PREM SANTA CLARA 250G VACUO",
            "precoUnitario": 17.9,
            "precoLiquido": 16.9,
            "desconto": 1.0,
            "unidade": "PCT9",
            "data": "2026-03-20 10:33:42-00:00",
            "foto": "https://api.precodahora.ba.gov.br/v1/images/7896224802963",
        },
        "estabelecimento": {
            "nomeEstabelecimento": "ATACADAO",
            "endLogradouro": "AVENIDA EDUARDO FROES DA MOTA",
            "endNumero": "5500",
            "bairro": "SOBRADINHO",
            "municipio": "FEIRA DE SANTANA",
            "uf": "BA",
            "cep": "44021215",
            "cnpj": 93209765054985,
            "distancia": 6.2998,
            "latitude": -12.2322007,
            "longitude": -38.9736466,
        },
    }

    item = service._normalizar_item(item_bruto, "7896224802963")
    assert item["gtin"] == "7896224802963"
    assert item["preco"] == 16.9
    assert item["preco_original"] == 17.9
    assert item["desconto"] == 1.0
    assert item["foto"] == "https://api.precodahora.ba.gov.br/v1/images/7896224802963"
    assert item["registrado_em"] == "2026-03-20T10:33:42Z"
    assert item["loja"]["cnpj"] == "93209765054985"
    assert item["loja"]["distancia_km"] == 6.3


def test_buscar_retorna_vazio_quando_nao_encontra_gtin(monkeypatch):
    service = PrecoDaHoraService()

    def fake_busca(_params: SearchParams):
        return {"totalRegistros": 0, "resultado": []}

    monkeypatch.setattr(service, "_buscar", fake_busca)
    resultado = service.top5_mais_baratos("7896224802963", -12.0, -38.0, 15, 72)
    assert resultado == {"total_encontrado": 0, "top5": []}


def test_busca_deve_usar_cache(monkeypatch):
    service = PrecoDaHoraService()
    chamadas = {"count": 0}

    def fake_obter_csrf_token():
        return "token"

    def fake_post_with_retry(payload, headers):
        chamadas["count"] += 1

        class FakeResponse:
            status_code = 200

            @staticmethod
            def raise_for_status():
                return None

            @staticmethod
            def json():
                return {"totalRegistros": 0, "resultado": []}

        return FakeResponse()

    monkeypatch.setattr(service, "_obter_csrf_token", fake_obter_csrf_token)
    monkeypatch.setattr(service, "_post_with_retry", fake_post_with_retry)

    params = SearchParams(
        gtin="7896224802963",
        latitude=-12.0,
        longitude=-38.0,
        raio=15,
        horas=72,
    )
    service._buscar(params)
    service._buscar(params)
    assert chamadas["count"] == 1


def test_post_with_retry_deve_repetir_quando_status_transitorio(monkeypatch):
    service = PrecoDaHoraService()
    tentativas = {"count": 0}

    class FakeResponse:
        def __init__(self, status_code: int):
            self.status_code = status_code

    def fake_post(*args, **kwargs):
        tentativas["count"] += 1
        if tentativas["count"] < 3:
            return FakeResponse(503)
        return FakeResponse(200)

    monkeypatch.setattr(service.session, "post", fake_post)
    monkeypatch.setattr("app.services.precos.time.sleep", lambda *_: None)

    response = service._post_with_retry(payload={}, headers={})
    assert response.status_code == 200
    assert tentativas["count"] == 3


def test_post_with_retry_deve_levantar_erro_na_ultima_tentativa(monkeypatch):
    service = PrecoDaHoraService()

    def fake_post(*args, **kwargs):
        raise requests.RequestException("falha de rede")

    monkeypatch.setattr(service.session, "post", fake_post)
    monkeypatch.setattr("app.services.precos.time.sleep", lambda *_: None)

    try:
        service._post_with_retry(payload={}, headers={})
        assert False, "Era esperado RequestException"
    except requests.RequestException:
        assert True


def test_obter_csrf_token_por_input_quando_meta_nao_existe(monkeypatch):
    service = PrecoDaHoraService()

    class FakeResponse:
        status_code = 200
        text = '<input name="csrf-token" value="abc123">'

        @staticmethod
        def raise_for_status():
            return None

    monkeypatch.setattr(service.session, "get", lambda *args, **kwargs: FakeResponse())
    token = service._obter_csrf_token()
    assert token == "abc123"


def test_obter_csrf_token_deve_falhar_quando_token_inexistente(monkeypatch):
    service = PrecoDaHoraService()

    class FakeResponse:
        status_code = 200
        text = "<html></html>"

        @staticmethod
        def raise_for_status():
            return None

    monkeypatch.setattr(service.session, "get", lambda *args, **kwargs: FakeResponse())
    try:
        service._obter_csrf_token()
        assert False, "Era esperado RuntimeError"
    except RuntimeError:
        assert True


def test_obter_csrf_token_deve_ler_meta_validate(monkeypatch):
    service = PrecoDaHoraService()

    class FakeResponse:
        status_code = 200
        text = '<meta id="validate" data-id="tok_meta_123" />'

        @staticmethod
        def raise_for_status():
            return None

    monkeypatch.setattr(service.session, "get", lambda *args, **kwargs: FakeResponse())
    token = service._obter_csrf_token()
    assert token == "tok_meta_123"


def test_obter_csrf_token_com_retry_em_status_transitorio(monkeypatch):
    service = PrecoDaHoraService()
    chamadas = {"count": 0}

    class FakeResponse:
        def __init__(self, status_code: int, text: str):
            self.status_code = status_code
            self.text = text

        def raise_for_status(self):
            if self.status_code >= 400:
                raise requests.HTTPError(response=self)

    def fake_get(*args, **kwargs):
        chamadas["count"] += 1
        if chamadas["count"] == 1:
            return FakeResponse(503, "")
        return FakeResponse(200, '<meta id="validate" data-id="tok_retry_ok" />')

    monkeypatch.setattr(service.session, "get", fake_get)
    monkeypatch.setattr("app.services.precos.time.sleep", lambda *_: None)
    assert service._obter_csrf_token() == "tok_retry_ok"
    assert chamadas["count"] == 2


def test_buscar_deve_renovar_token_quando_401(monkeypatch):
    service = PrecoDaHoraService()
    service._csrf_token = "token_antigo"
    chamadas = {"count": 0}

    class FakeResponse:
        def __init__(self, status_code: int):
            self.status_code = status_code

        @staticmethod
        def raise_for_status():
            return None

        @staticmethod
        def json():
            return {"totalRegistros": 0, "resultado": []}

    def fake_post_with_retry(payload, headers):
        chamadas["count"] += 1
        if chamadas["count"] == 1:
            return FakeResponse(401)
        return FakeResponse(200)

    monkeypatch.setattr(service, "_post_with_retry", fake_post_with_retry)
    monkeypatch.setattr(
        service, "_renovar_token", lambda: setattr(service, "_csrf_token", "novo_token")
    )

    params = SearchParams(
        gtin="7896224802963", latitude=-12.0, longitude=-38.0, raio=15, horas=72
    )
    resultado = service._buscar(params)
    assert resultado == {"totalRegistros": 0, "resultado": []}
    assert service._csrf_token == "novo_token"
    assert chamadas["count"] == 2


def test_helpers_diversos():
    service = PrecoDaHoraService()
    assert service._to_iso_utc(None) is None
    assert service._to_iso_utc("invalida") == "invalida"
    assert service._to_float("12.3") == 12.3
    assert service._to_float("abc") is None
    assert service._to_str("  oi ") == "oi"
    assert service._to_str("   ") is None
    assert (
        service._montar_endereco({"endLogradouro": "Rua A", "endNumero": "10"})
        == "Rua A, 10"
    )
    assert service._montar_endereco({"endLogradouro": "Rua A"}) == "Rua A"
    assert service._first_not_empty(None, "", "abc", "zzz") == "abc"


def test_top5_usa_len_quando_total_registros_ausente(monkeypatch):
    service = PrecoDaHoraService()

    def fake_busca(_params):
        return {
            "resultado": [
                {"produto": {"gtin": 1, "precoUnitario": 1.0}, "estabelecimento": {}}
            ]
        }

    monkeypatch.setattr(service, "_buscar", fake_busca)
    resultado = service.top5_mais_baratos("1", -12.0, -38.0, 15, 72)
    assert resultado["total_encontrado"] == 1
    assert len(resultado["top5"]) == 1


def test_buscar_lista_retorna_contexto(monkeypatch):
    service = PrecoDaHoraService()
    monkeypatch.setattr(
        service,
        "top5_mais_baratos",
        lambda **kwargs: {"total_encontrado": 0, "top5": []},
    )
    resposta = service.buscar_lista(["1", "2"], -12.1, -38.1, 20, 48)
    assert resposta["localizacao"]["raio_km"] == 20
    assert set(resposta["resultados"].keys()) == {"1", "2"}


def test_get_preco_da_hora_service_retorna_singleton():
    precos_module._SERVICE_SINGLETON = None
    s1 = precos_module.get_preco_da_hora_service()
    s2 = precos_module.get_preco_da_hora_service()
    assert s1 is s2


def test_obter_csrf_token_deve_detectar_challenge(monkeypatch):
    service = PrecoDaHoraService()

    class FakeResponse:
        status_code = 200
        text = "<html>recaptcha challenge</html>"
        url = "https://precodahora.ba.gov.br/challenge/"

        @staticmethod
        def raise_for_status():
            return None

    monkeypatch.setattr(service.session, "get", lambda *args, **kwargs: FakeResponse())
    try:
        service._obter_csrf_token()
        assert False, "Era esperado UpstreamChallengeError"
    except UpstreamChallengeError:
        assert True


def test_buscar_deve_respeitar_cooldown_de_challenge():
    service = PrecoDaHoraService()
    service._challenge_blocked_until = precos_module.time.time() + 60
    try:
        service._raise_if_challenge_cooldown_active()
        assert False, "Era esperado UpstreamChallengeError"
    except UpstreamChallengeError:
        assert True


def test_obter_csrf_token_deve_resetar_sessao_uma_vez_apos_challenge(monkeypatch):
    service = PrecoDaHoraService()
    chamadas = {"count": 0}

    class FakeResponse:
        def __init__(self, text: str, url: str):
            self.status_code = 200
            self.text = text
            self.url = url

        @staticmethod
        def raise_for_status():
            return None

    def fake_get(*args, **kwargs):
        chamadas["count"] += 1
        if chamadas["count"] == 1:
            return FakeResponse(
                "<html>recaptcha challenge</html>",
                "https://precodahora.ba.gov.br/challenge/",
            )
        return FakeResponse(
            '<meta id="validate" data-id="token_ok" />',
            "https://precodahora.ba.gov.br/produtos/",
        )

    monkeypatch.setattr(service, "_reset_session", lambda: None)
    monkeypatch.setattr(service.session, "get", fake_get)
    token = service._obter_csrf_token()
    assert token == "token_ok"
    assert chamadas["count"] == 2


def test_buscar_deve_resetar_sessao_uma_vez_apos_challenge(monkeypatch):
    service = PrecoDaHoraService()

    class FakeResponse:
        def __init__(self, status_code: int, text: str, url: str):
            self.status_code = status_code
            self.text = text
            self.url = url

        @staticmethod
        def raise_for_status():
            return None

        @staticmethod
        def json():
            return {"totalRegistros": 0, "resultado": []}

    def fake_token():
        return "tok"

    chamadas_post = {"count": 0}

    def fake_post(payload, headers):
        chamadas_post["count"] += 1
        if chamadas_post["count"] == 1:
            return FakeResponse(
                200,
                "<html>recaptcha challenge</html>",
                "https://precodahora.ba.gov.br/challenge/",
            )
        return FakeResponse(
            200,
            "{}",
            "https://precodahora.ba.gov.br/produtos/",
        )

    monkeypatch.setattr(service, "_obter_csrf_token", fake_token)
    monkeypatch.setattr(service, "_post_with_retry", fake_post)

    params = SearchParams(
        gtin="7896224802963",
        latitude=-12.0,
        longitude=-38.0,
        raio=15,
        horas=72,
    )
    result = service._buscar(params)
    assert result == {"totalRegistros": 0, "resultado": []}
    assert chamadas_post["count"] == 2
