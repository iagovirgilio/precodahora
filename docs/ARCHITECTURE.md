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

## Limites atuais

- Cache e rate limit em memoria local (processo unico).
- Em ambiente distribuido, mover para Redis (ou equivalente).
