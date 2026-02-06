POETRY ?= poetry

.PHONY: lint format typecheck test ci demo-data validate-demo transform

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
	$(POETRY) run python -m llm_etl_eval.etl.run --input-dir data/raw --output-dir data/processed
	$(POETRY) run python scripts/validate_demo_data.py

transform:
	$(POETRY) run python -m llm_etl_eval.transform.run --schema data/expected/target_schema.json --llm-outputs data/llm/outputs.jsonl --out-dir data/final
