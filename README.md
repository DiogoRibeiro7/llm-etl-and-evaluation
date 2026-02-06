# llm-etl-and-evaluation

Professional, typed Python tooling for LLM ETL and evaluation workflows.

**Requirements**
- Python 3.11+
- Poetry

**Setup**
```bash
poetry install
poetry run pre-commit install
```

**Quickstart**
```bash
poetry run python -m llm_etl_eval --help
```

**Common Commands**
```bash
make lint
make format
make typecheck
make test
make ci
```

**CI**
GitHub Actions runs Ruff, mypy, and pytest with coverage on push and pull requests.
