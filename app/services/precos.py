import re
import time
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import requests

from app.config import settings

BROWSER_HEADERS = {
    "accept": "*/*",
    "accept-encoding": "gzip, deflate, br",
    "accept-language": "pt-BR,pt;q=0.9",
    "origin": "https://precodahora.ba.gov.br",
    "referer": settings.base_url,
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "x-requested-with": "XMLHttpRequest",
}

_SERVICE_SINGLETON: "PrecoDaHoraService | None" = None

_CacheKey = tuple[str, float, float, int, int]


@dataclass
class SearchParams:
    gtin: str
    latitude: float
    longitude: float
    raio: int
    horas: int
    pagina: int = 1
    ordenar: str = "preco.asc"


class PrecoDaHoraService:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(BROWSER_HEADERS)
        self._csrf_token: Optional[str] = None
        self._cache: OrderedDict[_CacheKey, tuple[float, dict]] = OrderedDict()

    def _post_with_retry(
        self,
        payload: dict[str, str],
        headers: dict[str, str],
    ) -> requests.Response:
        ultima_excecao: Exception | None = None
        for tentativa in range(1, settings.request_retry_attempts + 1):
            try:
                resposta = self.session.post(
                    settings.base_url,
                    data=payload,
                    headers=headers,
                    timeout=settings.request_timeout_seconds,
                )
                if resposta.status_code in {429, 500, 502, 503, 504}:
                    if tentativa < settings.request_retry_attempts:
                        espera = settings.request_backoff_base_seconds * (
                            2 ** (tentativa - 1)
                        )
                        time.sleep(espera)
                        continue
                return resposta
            except requests.RequestException as exc:
                ultima_excecao = exc
                if tentativa < settings.request_retry_attempts:
                    espera = settings.request_backoff_base_seconds * (
                        2 ** (tentativa - 1)
                    )
                    time.sleep(espera)
                    continue
                raise
        if ultima_excecao:
            raise ultima_excecao
        raise RuntimeError("Falha inesperada ao executar requisicao externa.")

    def _obter_csrf_token(self) -> str:
        ultima_excecao: Exception | None = None
        response: requests.Response | None = None
        for tentativa in range(1, settings.request_retry_attempts + 1):
            try:
                response = self.session.get(
                    settings.base_url, timeout=settings.request_timeout_seconds
                )
                if response.status_code in {429, 500, 502, 503, 504}:
                    if tentativa < settings.request_retry_attempts:
                        espera = settings.request_backoff_base_seconds * (
                            2 ** (tentativa - 1)
                        )
                        time.sleep(espera)
                        continue
                response.raise_for_status()
                break
            except requests.RequestException as exc:
                ultima_excecao = exc
                if tentativa < settings.request_retry_attempts:
                    espera = settings.request_backoff_base_seconds * (
                        2 ** (tentativa - 1)
                    )
                    time.sleep(espera)
                    continue
                raise
        if response is None:
            if ultima_excecao:
                raise ultima_excecao
            raise RuntimeError("Falha ao obter sessao inicial.")

        match = re.search(
            r'<meta\s+id=["\']validate["\'][^>]+data-id=["\']([^"\']+)["\']',
            response.text,
        )
        if not match:
            match = re.search(
                r'<input[^>]+name=["\']csrf[_-]?token["\'][^>]+value=["\']([^"\']+)["\']',
                response.text,
            )

        if not match:
            raise RuntimeError(
                "CSRF token nao encontrado no HTML. O site pode ter mudado a estrutura."
            )

        return match.group(1)

    def _renovar_token(self) -> None:
        self._csrf_token = self._obter_csrf_token()

    def _cache_obter(self, key: _CacheKey) -> dict | None:
        item = self._cache.get(key)
        if not item:
            return None
        gravado_em, payload = item
        if time.time() - gravado_em >= settings.cache_ttl_seconds:
            del self._cache[key]
            return None
        self._cache.move_to_end(key)
        return payload

    def _cache_gravar(self, key: _CacheKey, payload: dict) -> None:
        agora = time.time()
        if key in self._cache:
            self._cache[key] = (agora, payload)
            self._cache.move_to_end(key)
            return
        maximo = settings.cache_max_entries
        if maximo > 0:
            while len(self._cache) >= maximo:
                self._cache.popitem(last=False)
        self._cache[key] = (agora, payload)

    def _buscar(self, params: SearchParams) -> dict:
        cache_key: _CacheKey = (
            params.gtin,
            params.latitude,
            params.longitude,
            params.raio,
            params.horas,
        )
        em_cache = self._cache_obter(cache_key)
        if em_cache is not None:
            return em_cache

        if not self._csrf_token:
            self._csrf_token = self._obter_csrf_token()

        payload = {
            "termo": params.gtin,
            "horas": str(params.horas),
            "latitude": str(params.latitude),
            "longitude": str(params.longitude),
            "raio": str(params.raio),
            "pagina": str(params.pagina),
            "ordenar": params.ordenar,
        }
        headers = {
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-csrftoken": self._csrf_token,
        }

        response = self._post_with_retry(payload=payload, headers=headers)

        if response.status_code == 401:
            self._renovar_token()
            headers["x-csrftoken"] = self._csrf_token
            response = self._post_with_retry(payload=payload, headers=headers)

        response.raise_for_status()
        json_data = response.json()
        self._cache_gravar(cache_key, json_data)
        return json_data

    @staticmethod
    def _to_iso_utc(value: str | None) -> str | None:
        if not value:
            return None
        normalizado = value.strip().replace(" ", "T")
        try:
            if normalizado.endswith("Z"):
                dt = datetime.fromisoformat(normalizado.replace("Z", "+00:00"))
            else:
                dt = datetime.fromisoformat(normalizado)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        except ValueError:
            return value

    @staticmethod
    def _to_float(value: object) -> float | None:
        if value is None:
            return None
        try:
            if isinstance(value, (str, int, float)):
                return float(value)
            return None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_str(value: object) -> str | None:
        if value is None:
            return None
        texto = str(value).strip()
        return texto or None

    @staticmethod
    def _normalizar_cnpj(value: object) -> str | None:
        texto = PrecoDaHoraService._to_str(value)
        if not texto:
            return None
        apenas_digitos = "".join(ch for ch in texto if ch.isdigit())
        if not apenas_digitos:
            return texto
        return apenas_digitos.zfill(14)

    @staticmethod
    def _montar_endereco(loja: dict) -> str | None:
        logradouro = loja.get("endLogradouro")
        numero = loja.get("endNumero")
        if logradouro and numero:
            return f"{logradouro}, {numero}"
        return logradouro or None

    @staticmethod
    def _first_not_empty(*values: object) -> str | None:
        for value in values:
            texto = PrecoDaHoraService._to_str(value)
            if texto:
                return texto
        return None

    def _normalizar_item(self, item: dict, gtin: str) -> dict:
        produto = item.get("produto", {})
        estabelecimento = item.get("estabelecimento", {})
        distancia = self._to_float(estabelecimento.get("distancia"))

        preco_final = self._to_float(produto.get("precoLiquido"))
        if preco_final is None:
            preco_final = self._to_float(produto.get("precoUnitario")) or 0.0

        desconto = self._to_float(produto.get("desconto"))
        preco_original = None
        if desconto is not None:
            preco_original = round(preco_final + desconto, 2)

        return {
            "descricao": produto.get("descricao"),
            "gtin": str(produto.get("gtin") or gtin),
            "preco": round(preco_final, 2),
            "preco_original": preco_original,
            "desconto": desconto,
            "unidade": produto.get("unidade"),
            "foto": self._first_not_empty(
                produto.get("urlFoto"),
                produto.get("foto"),
                produto.get("imagem"),
                produto.get("urlImagem"),
                item.get("urlFoto"),
                item.get("foto"),
                item.get("imagem"),
                item.get("urlImagem"),
            ),
            "registrado_em": self._to_iso_utc(
                self._first_not_empty(
                    produto.get("data"),
                    produto.get("dataHora"),
                    produto.get("dataRegistro"),
                    produto.get("hora"),
                    item.get("dataHora"),
                    item.get("dataRegistro"),
                    item.get("hora"),
                    item.get("intervalo"),
                )
            ),
            "loja": {
                "nome": estabelecimento.get("nomeEstabelecimento"),
                "cnpj": self._normalizar_cnpj(estabelecimento.get("cnpj")),
                "endereco": self._montar_endereco(estabelecimento),
                "bairro": estabelecimento.get("bairro"),
                "cidade": estabelecimento.get("municipio"),
                "uf": estabelecimento.get("uf"),
                "cep": self._to_str(estabelecimento.get("cep")),
                "telefone": self._to_str(estabelecimento.get("telefone")),
                "latitude": self._to_float(estabelecimento.get("latitude")),
                "longitude": self._to_float(estabelecimento.get("longitude")),
                "distancia_km": round(distancia, 2) if distancia is not None else None,
            },
        }

    def top5_mais_baratos(
        self,
        gtin: str,
        latitude: float,
        longitude: float,
        raio: int,
        horas: int,
    ) -> dict:
        dados = self._buscar(
            SearchParams(
                gtin=gtin,
                latitude=latitude,
                longitude=longitude,
                raio=raio,
                horas=horas,
            )
        )
        resultados = dados.get("resultado", [])
        return {
            "total_encontrado": int(dados.get("totalRegistros") or len(resultados)),
            "top5": [self._normalizar_item(item, gtin) for item in resultados[:5]],
        }

    def buscar_lista(
        self,
        gtins: list[str],
        latitude: float,
        longitude: float,
        raio: int,
        horas: int,
    ) -> dict:
        consultado_em = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        resultados = {
            gtin: self.top5_mais_baratos(
                gtin=gtin,
                latitude=latitude,
                longitude=longitude,
                raio=raio,
                horas=horas,
            )
            for gtin in gtins
        }
        return {
            "consultado_em": consultado_em,
            "localizacao": {
                "latitude": latitude,
                "longitude": longitude,
                "raio_km": raio,
            },
            "resultados": resultados,
        }


def get_preco_da_hora_service() -> PrecoDaHoraService:
    global _SERVICE_SINGLETON
    if _SERVICE_SINGLETON is None:
        _SERVICE_SINGLETON = PrecoDaHoraService()
    return _SERVICE_SINGLETON
