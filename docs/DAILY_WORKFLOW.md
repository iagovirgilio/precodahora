# Daily Workflow

Este guia descreve o fluxo diario recomendado para desenvolver com qualidade e previsibilidade.

## Setup inicial (uma vez)

```bash
uv sync --extra dev
uv run --extra dev pre-commit install
```

## Fluxo diario (passo a passo)

1. Formatar codigo:

```bash
uv run --extra dev black .
```

2. Rodar lint:

```bash
uv run --extra dev ruff check .
```

3. Rodar checagem de tipos:

```bash
uv run --extra dev mypy
```

4. Rodar testes e cobertura:

```bash
uv run --extra dev pytest -q
```

5. Commit:

```bash
git add .
git commit -m "feat: sua mensagem"
```

## Fluxo rapido (um comando)

```bash
uv run --extra dev black . && uv run --extra dev ruff check . && uv run --extra dev mypy && uv run --extra dev pytest -q
```

## Antes de abrir PR

```bash
uv run --extra dev pre-commit run --all-files
uv run --extra dev pytest -q
```

## Dicas praticas

- Se o commit falhar por hook, aplique os fixes e rode `git add` novamente.
- Para detalhar testes: `uv run --extra dev pytest -vv`.
- Para cobertura visual: abrir `htmlcov/index.html`.
