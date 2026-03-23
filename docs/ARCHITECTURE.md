# Architecture

## Visao geral

A aplicacao segue arquitetura em camadas:

- `routers`: transporte HTTP e traducao de excecoes para status code.
- `schemas`: contratos de entrada e saida (Pydantic).
- `services`: regras de integracao com a fonte externa e normalizacao de dados.
- `config`: configuracoes via ambiente.

## Fluxo principal

1. Cliente chama `POST /api/v1/precos/buscar`.
2. Router valida payload com schema.
3. Service consulta fonte externa com:
   - retry com backoff
   - timeout configuravel
   - token CSRF
   - cache TTL
4. Service transforma payload bruto em contrato da API.
5. Router retorna response tipada.

## Decisoes de design

- **Contrato estavel**: nao expor campos internos da fonte.
- **Resiliencia**: retry em erros transitorios e tratamento explicito de upstream.
- **Protecao da fonte**: cache e rate limiting para reduzir carga.
- **Observabilidade**: logs JSON no nivel de request e erro.

## Cache da fonte externa (upstream)

O servico mantem em memoria a **resposta JSON bruta** do POST ao portal, para nao repetir a mesma consulta dentro do TTL.

- **Chave**: tupla `(gtin, latitude, longitude, raio, horas)` — os mesmos campos enviados ao site (pagina e ordenacao fixos no fluxo atual).
- **TTL**: `PRECODAHORA_CACHE_TTL_SECONDS` — aplica-se apenas a **reutilizar** o resultado da fonte; nao ha endpoint de invalidacao manual.
- **Limite de entradas**: `PRECODAHORA_CACHE_MAX_ENTRIES` — politica LRU; ao encher, remove a entrada **menos usada recentemente**. Valor `0` desativa o teto (comportamento anterior, so limitado pelo TTL).
- **Escopo**: um processo Python; com varios workers, cada um tem cache proprio.

Em `POST /api/v1/precos/buscar`, o router acrescenta cabecalhos `X-Cache` / `X-Cache-Hits` / `X-Cache-Misses` / `X-Upstream-Posts` e um log `precos_buscar` com o mesmo resumo.

## Integracao (Fase 1)

- **API key** em `POST /api/v1/precos/buscar` quando `PRECODAHORA_API_AUTH_ENABLED=true` (`app/deps/auth.py`). Aceita `Authorization: Bearer` ou `X-API-Key`.
- **`X-Request-Id`**: middleware gera ou valida e devolve no response; logs `http_request` e `precos_buscar` incluem `request_id`.
- **Erros HTTP**: envelope comum `{"error": {"code", "message", "request_id?", "details?"}}` via handlers em `app/main.py`.
- **Rate limit**: em memoria, por identidade (`key:<hash>` se houver token, senao `ip:<host>`). Rotas isentas: `/health`, `/docs`, `/redoc`, `/openapi.json`.
- **Teto de GTINs**: `PRECODAHORA_MAX_GTINS_PER_REQUEST` validado no schema de entrada.

## Limites atuais

- Cache e rate limit em memoria local (processo unico).
- Em ambiente distribuido, mover para Redis (ou equivalente).
