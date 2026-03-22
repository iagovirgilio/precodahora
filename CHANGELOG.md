# Changelog

Todas as mudancas relevantes deste projeto serao documentadas neste arquivo.

Este projeto segue, de forma simplificada:

- [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
- [Semantic Versioning](https://semver.org/lang/pt-BR/)

## [Unreleased]

### Added

- Limite configuravel de entradas no cache upstream (`PRECODAHORA_CACHE_MAX_ENTRIES`) com eviction LRU.
- `PRECODAHORA_RATE_LIMIT_WINDOW_SECONDS` e campos extras em `GET /health`.

### Changed

- Documentacao do cache (chave, TTL, LRU) em `docs/ARCHITECTURE.md` e `docs/API.md`.

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
