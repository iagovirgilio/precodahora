# Operations Runbook

## Executar localmente

```bash
uv sync
uv run uvicorn app.main:app --reload
```

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

## Checklist de deploy

- [ ] Variaveis de ambiente definidas
- [ ] Testes passando
- [ ] Cobertura minima aceita pelo time
- [ ] Healthcheck respondendo `200`
- [ ] Logs JSON coletados no ambiente

## Troubleshooting rapido

- **`429` frequente**: aumentar limite por minuto ou reduzir carga do cliente.
- **`502`**: erro HTTP do provedor externo.
- **`503`**: erro de conectividade/rede no provedor.
- **`500`**: erro interno; verificar logs estruturados para stacktrace.
