# Operations Runbook

## Executar localmente

```bash
uv sync
uv run uvicorn app.main:app --reload
```

## Docker Compose (API + Redis)

```bash
docker compose up --build
```

API em `http://127.0.0.1:8000`. Para so a imagem: `docker build -t precodahora-api .`

## Testes

```bash
uv run pytest -q
uv run pytest -vv
```

## Cobertura

```bash
uv run pytest -q
```

Relatorio HTML: `htmlcov/index.html`.

## Variaveis de ambiente

Prefixo: `PRECODAHORA_`

- `BASE_URL`
- `REQUEST_TIMEOUT_SECONDS`
- `REQUEST_RETRY_ATTEMPTS`
- `REQUEST_BACKOFF_BASE_SECONDS`
- `CACHE_TTL_SECONDS`
- `CACHE_MAX_ENTRIES` (LRU; `0` = sem limite de entradas)
- `RATE_LIMIT_WINDOW_SECONDS`
- `RATE_LIMIT_REQUESTS_PER_MINUTE`
- `API_AUTH_ENABLED` / `API_KEYS` / `MAX_GTINS_PER_REQUEST`
- `REDIS_URL` (opcional; rate limit compartilhado entre instancias)

## Checklist de deploy

- [ ] Variaveis de ambiente definidas
- [ ] Em producao: `API_AUTH_ENABLED=true` e `API_KEYS` nao vazio (se usar autenticacao)
- [ ] Testes passando
- [ ] Cobertura minima aceita pelo time
- [ ] `GET /health` respondendo `200` (liveness)
- [ ] `GET /ready` respondendo `200` quando Redis e obrigatorio no ambiente
- [ ] Logs JSON coletados no ambiente

## Troubleshooting rapido

- **`429` frequente**: aumentar limite por minuto ou reduzir carga do cliente.
- **`502`**: erro HTTP do provedor externo.
- **`503`**: erro de conectividade/rede no provedor, ou autenticacao ligada sem `API_KEYS` configuradas.
- **`500`**: erro interno; verificar logs estruturados para stacktrace.
