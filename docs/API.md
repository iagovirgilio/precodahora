# API Contract

## Autenticacao (servico a servico)

`POST /api/v1/precos/buscar` exige autenticacao quando `PRECODAHORA_API_AUTH_ENABLED=true` (veja `.env.example`).

Envie **uma** das opcoes:

- Cabecalho `Authorization: Bearer <sua-chave>`
- Cabecalho `X-API-Key: <sua-chave>`

Chaves validas vêm de `PRECODAHORA_API_KEYS` (lista separada por virgula). Com autenticacao ligada e lista vazia, a API responde `503` com corpo padronizado (misconfiguracao).

Rotas **sem** chave: `GET /health`, `GET /docs`, `GET /redoc`, `GET /openapi.json`.

## Correlacao de requisicao

- Opcional: envie `X-Request-Id` (1–128 caracteres, `A–Z`, `a–z`, `0–9` e `-`).
- Sempre na resposta: `X-Request-Id` (o valor enviado se valido, senao um UUID gerado pela API).

Use o mesmo id nos logs do cliente e da API para depurar integracao.

## Formato de erro

Respostas de erro seguem o envelope:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Payload invalido.",
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "details": []
  }
}
```

- `details` aparece em erros de validacao (`422`), com lista no estilo Pydantic/FastAPI (serializada para JSON).
- `request_id` pode ser omitido se indisponivel em casos extremos.

## Endpoint principal

### `POST /api/v1/precos/buscar`

Consulta os dados de precos para uma lista de GTINs e retorna:

- `consultado_em`
- `localizacao`
- `resultados` por GTIN

Cabecalhos de resposta (observabilidade do cache e do upstream):

| Cabecalho | Significado |
|-----------|-------------|
| `X-Cache` | `HIT` (todos os GTINs do cache), `MISS` (nenhum hit) ou `MIXED` |
| `X-Cache-Hits` | Quantidade de consultas atendidas pelo cache interno |
| `X-Cache-Misses` | Quantidade de consultas que foram ao portal |
| `X-Upstream-Posts` | POSTs HTTP ao portal na requisicao (401 com retry conta 2 no GTIN afetado) |

O mesmo resumo e registrado em log (`precos_buscar ... x_cache=...`) no logger `precodahora.api`, com `request_id`.

### Request body

```json
{
  "gtins": ["7894904015108"],
  "latitude": -12.2690245,
  "longitude": -38.9295865,
  "raio": 15,
  "horas": 72
}
```

Limite de tamanho de `gtins`: no maximo `PRECODAHORA_MAX_GTINS_PER_REQUEST` itens (padrao 50).

### Response body (resumido)

```json
{
  "consultado_em": "2026-03-20T13:21:28Z",
  "localizacao": {
    "latitude": -12.2690245,
    "longitude": -38.9295865,
    "raio_km": 15
  },
  "resultados": {
    "7894904015108": {
      "total_encontrado": 43,
      "top5": [
        {
          "descricao": "FILE PEITO FGO SEARA",
          "gtin": "7894904015108",
          "preco": 19.9,
          "preco_original": null,
          "desconto": null,
          "unidade": "BDJ9",
          "foto": "https://api.precodahora.ba.gov.br/v1/images/7894904015108",
          "registrado_em": "2026-03-20T13:02:25Z",
          "loja": {
            "nome": "ATACADAO",
            "cnpj": "93209765054985",
            "endereco": "AVENIDA EDUARDO FROES DA MOTA, 5500",
            "bairro": "SOBRADINHO",
            "cidade": "FEIRA DE SANTANA",
            "uf": "BA",
            "cep": "44021215",
            "telefone": null,
            "latitude": -12.2322007,
            "longitude": -38.9736466,
            "distancia_km": 2.8
          }
        }
      ]
    }
  }
}
```

## Endpoint de saude

### `GET /health`

Retorna status da API e alguns parametros operacionais (para conferencia de deploy), por exemplo:

- `cache_ttl_seconds`: tempo maximo para reutilizar resposta da fonte externa.
- `cache_max_entries`: tamanho maximo do cache em memoria (LRU); `0` significa sem limite de entradas.
- `rate_limit_window_seconds`: janela em segundos do rate limit (ver `429`).

Nao exige API key. **Nao** conta para o rate limit (assim como `/docs`, `/redoc`, `/openapi.json`).

Exemplo:

```json
{
  "status": "ok",
  "cache_ttl_seconds": 900,
  "cache_max_entries": 512,
  "rate_limit_window_seconds": 60
}
```

## Rate limit

- Janela e teto: `PRECODAHORA_RATE_LIMIT_WINDOW_SECONDS` e `PRECODAHORA_RATE_LIMIT_REQUESTS_PER_MINUTE`.
- Identidade do balde: se a requisicao traz Bearer ou `X-API-Key`, o limite e **por chave** (hash no servidor); caso contrario, **por IP**.
- Resposta `429` usa o envelope `error` com `code`: `rate_limit_exceeded`.

## Codigos de status

| HTTP | `error.code` tipico | Quando |
|------|---------------------|--------|
| `200` | — | Sucesso |
| `401` | `unauthorized` | Chave ausente ou invalida (auth ligada) |
| `422` | `validation_error` | Payload invalido (inclui excesso de GTINs) |
| `429` | `rate_limit_exceeded` | Limite na janela |
| `502` | `upstream_http_error` | Erro HTTP na fonte externa |
| `503` | `upstream_network_error` ou configuracao | Rede com a fonte, ou API keys nao configuradas com auth ligada |
| `500` | `internal_error` | Erro interno inesperado |
