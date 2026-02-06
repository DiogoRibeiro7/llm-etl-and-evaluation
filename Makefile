POETRY ?= poetry

.PHONY: lint format typecheck test ci

lint:
	$(POETRY) run ruff check .

format:
	$(POETRY) run ruff format .

typecheck:
	$(POETRY) run mypy .

test:
	$(POETRY) run pytest --cov=llm_etl_eval --cov-report=term-missing

ci: lint typecheck test
