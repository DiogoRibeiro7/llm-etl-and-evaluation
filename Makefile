POETRY ?= poetry

.PHONY: lint format typecheck test ci demo-data validate-demo

lint:
	$(POETRY) run ruff check .

format:
	$(POETRY) run ruff format .

typecheck:
	$(POETRY) run mypy .

test:
	$(POETRY) run pytest --cov=llm_etl_eval --cov-report=term-missing

ci: lint typecheck test

demo-data:
	$(POETRY) run python scripts/generate_demo_data.py

validate-demo:
	$(POETRY) run python scripts/validate_demo_data.py
