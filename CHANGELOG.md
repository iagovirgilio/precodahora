# Changelog

Todas as mudancas relevantes deste projeto serao documentadas neste arquivo.

Este projeto segue, de forma simplificada:

- [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
- [Semantic Versioning](https://semver.org/lang/pt-BR/)

## [Unreleased]

### Added

- Fase 2: `PRECODAHORA_REDIS_URL` opcional para rate limit distribuido (Lua + ZSET); fallback em memoria se URL vazia ou erro no Redis.
- `GET /ready` (readiness) e `GET /metrics` (Prometheus `precodahora_http_requests_total`).
- `GET /health` inclui `rate_limit_backend` (`memory` ou `redis`).
- `Dockerfile`, `docker-compose.yml` (API + Redis) e `.dockerignore`.
- Dependencias `redis` e `prometheus-client`; modulos `app/redis_client.py` e `app/rate_limiting.py`.
- Autenticacao opcional por API key (`PRECODAHORA_API_AUTH_ENABLED`, `PRECODAHORA_API_KEYS`) em `POST /api/v1/precos/buscar` via `Authorization: Bearer` ou `X-API-Key`.
- Middleware `X-Request-Id` (entrada opcional validada, resposta sempre com id) e inclusao em logs `http_request` e `precos_buscar`.
- Respostas de erro com envelope JSON `{"error": {"code", "message", "request_id?", "details?"}}` para `HTTPException` e `RequestValidationError`.
- Limite `PRECODAHORA_MAX_GTINS_PER_REQUEST` na lista `gtins`.
- Rate limit por identidade: hash da chave quando presente, senao IP; isencao para `/health`, `/docs`, `/redoc`, `/openapi.json`.
- Modulos `app/deps/auth.py`, `app/schemas/errors.py` e testes de integracao em `tests/test_api_integration.py`.
- Limite configuravel de entradas no cache upstream (`PRECODAHORA_CACHE_MAX_ENTRIES`) com eviction LRU.
- `PRECODAHORA_RATE_LIMIT_WINDOW_SECONDS` e campos extras em `GET /health`.
- Cabecalhos `X-Cache`, `X-Cache-Hits`, `X-Cache-Misses`, `X-Upstream-Posts` e log estruturado em `POST /api/v1/precos/buscar`.

### Changed

- Documentacao de contrato, cache (chave, TTL, LRU) e operacao (`docs/API.md`, `docs/ARCHITECTURE.md`, `docs/OPERATIONS.md`, `README.md`).
- `PrecoDaHoraService.buscar_lista` passa a retornar `(corpo, observabilidade)` para uso no router.

## [0.1.0] - 2026-03-20

### Added

- API FastAPI com endpoint `POST /api/v1/precos/buscar`.
- Healthcheck em `GET /health`.
- Camadas separadas em `routers`, `schemas`, `services` e `config`.
- Contrato de resposta limpo e normalizado para consumo externo.
- Rate limiting por IP.
- Cache em memoria com TTL.
- Retry com backoff exponencial e timeout configuravel para upstream.
- Logs estruturados em JSON.
- Validacao de GTIN (8, 12, 13 ou 14 digitos).
- Suite de testes automatizados com cobertura.
- Documentacao tecnica em `README.md` e `docs/`.

### Changed

- Evolucao de script unico para API com arquitetura em camadas.

### Fixed

- Correcoes de mapeamento de `foto` e `registrado_em`.
- Correcao de `cnpj` com preservacao de zeros a esquerda.
- Ajuste de `distancia_km` para 2 casas decimais.
