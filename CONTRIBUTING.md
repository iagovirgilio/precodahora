# Contributing

Obrigado por contribuir com o projeto `precodahora`.

Este guia define o fluxo recomendado para desenvolvimento, testes e envio de mudancas.

## Requisitos

- Python 3.12+
- `uv` instalado

## Setup local

```bash
uv sync
```

Para instalar dependencias de desenvolvimento:

```bash
uv sync --extra dev
```

## Executando a API

```bash
uv run uvicorn app.main:app --reload
```

Swagger: `http://127.0.0.1:8000/docs`

## Rodando testes

```bash
uv run pytest -q
```

Com detalhes:

```bash
uv run pytest -vv
```

## Cobertura

```bash
uv run pytest -q
```

Relatorio HTML: `htmlcov/index.html`

## Padroes de codigo

- Manter separacao por camadas:
  - `routers`: HTTP e traducao de erros
  - `schemas`: contratos Pydantic
  - `services`: regras de negocio e integracao externa
- Nao expor campos internos do upstream no contrato publico.
- Preferir nomes consistentes em portugues no payload da API.
- Garantir backward compatibility de contrato, quando possivel.

## Fluxo de contribuicao

1. Crie uma branch de feature/correcao.
2. Implemente a mudanca com testes.
3. Rode testes e cobertura localmente.
4. Atualize documentacao quando necessario.
5. Abra PR descrevendo:
   - contexto
   - mudancas
   - riscos
   - plano de teste

## Checklist minimo para PR

- [ ] Testes passando localmente
- [ ] Sem regressao de contrato da API
- [ ] Sem segredos no codigo
- [ ] Documentacao atualizada (README/docs) quando aplicavel

## Convencao de commits (recomendado)

Sugestao de prefixos:

- `feat:` nova funcionalidade
- `fix:` correcao de bug
- `refactor:` refatoracao sem alteracao funcional
- `test:` adicao/ajuste de testes
- `docs:` alteracoes de documentacao
- `chore:` tarefas de manutencao
