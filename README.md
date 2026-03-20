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
- Pydantic / pydantic-settings
- Pytest + pytest-cov

## Estrutura do projeto

```text
app/
  config.py             # configuracoes da aplicacao
  main.py               # app FastAPI, middleware e healthcheck
  routers/
    precos.py           # endpoint HTTP
  schemas/
    precos.py           # request/response models
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

## Endpoints

- `GET /health`
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

- `gtins`: somente digitos, com tamanhos permitidos 8, 12, 13 ou 14.
- `raio`: 1 a 100.
- `horas`: 1 a 168.

## Configuracao via ambiente

As variaveis usam prefixo `PRECODAHORA_`.

Principais:

- `PRECODAHORA_BASE_URL`
- `PRECODAHORA_REQUEST_TIMEOUT_SECONDS`
- `PRECODAHORA_REQUEST_RETRY_ATTEMPTS`
- `PRECODAHORA_REQUEST_BACKOFF_BASE_SECONDS`
- `PRECODAHORA_CACHE_TTL_SECONDS`
- `PRECODAHORA_RATE_LIMIT_REQUESTS_PER_MINUTE`

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

- Logs estruturados em JSON.
- Rate limiting por IP (janela de 60s).
- Cache em memoria por combinacao de parametros de busca.
- Retry com backoff exponencial para erros transitorios.
- Tratamento de erro upstream com respostas HTTP consistentes (502/503/500).

## Documentacao complementar

- `docs/API.md`
- `docs/ARCHITECTURE.md`
- `docs/OPERATIONS.md`
- `CONTRIBUTING.md`
- `CHANGELOG.md`
