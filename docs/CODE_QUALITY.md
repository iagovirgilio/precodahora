# Code Quality Guide

Este documento explica as ferramentas de qualidade de codigo adotadas no projeto e como usa-las.

## Ferramentas

### Ruff (lint)

Identifica problemas estaticos de codigo:

- imports desorganizados
- codigo potencialmente incorreto
- padroes de estilo definidos no projeto

Comando:

```bash
uv run --extra dev ruff check .
```

Autofix quando possivel:

```bash
uv run --extra dev ruff check . --fix
```

### Black (formatter)

Padroniza formatacao automaticamente para evitar discussoes de estilo e reduzir ruido em PR.

Comando:

```bash
uv run --extra dev black .
```

### Mypy (type checker)

Valida tipos estaticos para reduzir bugs de contrato e inconsistencias entre camadas.

Comando:

```bash
uv run --extra dev mypy
```

### Pytest + Coverage

Executa testes automatizados e gera cobertura de codigo.

Comando:

```bash
uv run --extra dev pytest -q
```

Relatorio HTML:

- `htmlcov/index.html`

### Pre-commit

Roda os checks automaticamente antes de cada commit.

Instalar hooks:

```bash
uv run --extra dev pre-commit install
```

Executar manualmente em todos os arquivos:

```bash
uv run --extra dev pre-commit run --all-files
```

## Ordem recomendada de uso

1. `black`
2. `ruff`
3. `mypy`
4. `pytest`

## Troubleshooting rapido

- **Erro de lint**: rode `ruff --fix` e depois `black`.
- **Erro de mypy**: ajuste tipos/assinaturas e execute novamente.
- **Erro de teste**: rode `pytest -vv` para mais contexto.
- **Falha no pre-commit**: aplique correcoes, `git add` e tente commit novamente.
