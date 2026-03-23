# Preco da Hora API

API FastAPI para consulta de precos de produtos (GTIN/EAN) no portal Preco da Hora Bahia, com resposta padronizada para consumo por clientes internos/externos.

## Objetivo

- Consultar precos por GTIN com foco em top 5 menores valores.
- Expor contrato limpo e estavel (sem payload cru da fonte).
- Aplicar boas praticas de operacao: retry, timeout, cache e rate limit.

## Stack

- Python 3.12+
- FastAPI
- Requests
- Redis (cliente async; rate limit distribuido opcional)
- Prometheus client (metricas em `/metrics`)
- Pydantic / pydantic-settings
- Pytest + pytest-cov

## Estrutura do projeto

```text
app/
  config.py             # configuracoes da aplicacao
  main.py               # app FastAPI, middleware, health/ready/metrics, lifespan
  deps/
    auth.py             # API key e identidade para rate limit
  redis_client.py       # pool Redis async (opcional)
  rate_limiting.py      # rate limit memoria ou Redis (Lua)
  routers/
    precos.py           # endpoint HTTP
  schemas/
    precos.py           # request/response models
    errors.py           # envelope de erro JSON
  services/
    precos.py           # integracao e transformacao de dados
tests/
```

## Como executar

1. Instalar dependencias:

```bash
uv sync
```

2. Subir API local:

```bash
uv run uvicorn app.main:app --reload
```

3. Acessar documentacao interativa:

- Swagger: `http://127.0.0.1:8000/docs`
- OpenAPI: `http://127.0.0.1:8000/openapi.json`

## Docker (API + Redis)

Na raiz do repositorio:

```bash
docker compose up --build
```

A API sobe em `http://127.0.0.1:8000` com `PRECODAHORA_REDIS_URL=redis://redis:6379/0` (ver `docker-compose.yml`). Imagem de producao: `docker build -t precodahora-api .`

## Endpoints

- `GET /health` — liveness e parametros operacionais
- `GET /ready` — readiness (Redis quando `PRECODAHORA_REDIS_URL` definido)
- `GET /metrics` — Prometheus
- `POST /api/v1/precos/buscar`

Exemplo de request:

```json
{
  "gtins": ["7894904015108", "7896224802963"],
  "latitude": -12.2690245,
  "longitude": -38.9295865,
  "raio": 15,
  "horas": 72
}
```

Regras de validacao:

- `gtins`: somente digitos, com tamanhos permitidos 8, 12, 13 ou 14; quantidade maxima por request configuravel (`PRECODAHORA_MAX_GTINS_PER_REQUEST`, padrao 50).
- `raio`: 1 a 100.
- `horas`: 1 a 168.

## Integracao servico a servico

Para o produto consumir esta API com autenticacao:

1. Defina `PRECODAHORA_API_AUTH_ENABLED=true` e `PRECODAHORA_API_KEYS` (uma ou mais chaves separadas por virgula).
2. Envie `Authorization: Bearer <chave>` ou `X-API-Key: <chave>` em `POST /api/v1/precos/buscar`.
3. Opcional: envie `X-Request-Id` para correlacionar logs entre sistemas.

Exemplo com `curl`:

```bash
curl -sS -X POST "http://127.0.0.1:8000/api/v1/precos/buscar" \
  -H "Authorization: Bearer SUA_CHAVE" \
  -H "Content-Type: application/json" \
  -H "X-Request-Id: meu-rastreio-001" \
  -d "{\"gtins\":[\"7894904015108\"],\"latitude\":-12.2690245,\"longitude\":-38.9295865,\"raio\":15,\"horas\":72}"
```

Com `PRECODAHORA_API_AUTH_ENABLED=false` (padrao), o endpoint de precos permanece aberto para desenvolvimento local; em staging/producao recomenda-se ligar a autenticacao.

## Configuracao via ambiente

As variaveis usam prefixo `PRECODAHORA_`.

Principais:

- `PRECODAHORA_BASE_URL`
- `PRECODAHORA_REQUEST_TIMEOUT_SECONDS`
- `PRECODAHORA_REQUEST_RETRY_ATTEMPTS`
- `PRECODAHORA_REQUEST_BACKOFF_BASE_SECONDS`
- `PRECODAHORA_CACHE_TTL_SECONDS`
- `PRECODAHORA_CACHE_MAX_ENTRIES`
- `PRECODAHORA_RATE_LIMIT_WINDOW_SECONDS`
- `PRECODAHORA_RATE_LIMIT_REQUESTS_PER_MINUTE`
- `PRECODAHORA_API_KEYS` (lista separada por virgula)
- `PRECODAHORA_API_AUTH_ENABLED` (`true`/`false`)
- `PRECODAHORA_MAX_GTINS_PER_REQUEST`
- `PRECODAHORA_REDIS_URL` (ex.: `redis://localhost:6379/0`; vazio = rate limit so em memoria)

Veja um template em `.env.example`.

## Testes e cobertura

Executar testes:

```bash
uv run pytest -q
```

Executar com detalhes:

```bash
uv run pytest -vv
```

Cobertura:

- Relatorio de terminal com linhas faltantes.
- Relatorio HTML em `htmlcov/index.html`.

## Observabilidade e resiliencia

- Logs estruturados em JSON (inclui `request_id` por requisicao).
- Rate limiting por janela configuravel: por chave de API (hash) quando o cliente envia Bearer/`X-API-Key`, senao por IP; backend Redis opcional para varios workers.
- Metricas HTTP expostas em `/metrics` (Prometheus).
- Cache em memoria (TTL + LRU) por combinacao de parametros de busca na fonte externa.
- Retry com backoff exponencial para erros transitorios.
- Tratamento de erro upstream com respostas HTTP consistentes (502/503/500).

## Documentacao complementar

- `docs/API.md`
- `docs/ARCHITECTURE.md`
- `docs/OPERATIONS.md`
- `docs/DAILY_WORKFLOW.md`
- `docs/CODE_QUALITY.md`
- `CONTRIBUTING.md`
- `CHANGELOG.md`
