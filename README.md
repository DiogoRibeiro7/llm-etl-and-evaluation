# llm-etl-and-evaluation

Professional, typed Python tooling for LLM ETL and evaluation workflows.

**Scenario**
Messy support tickets and incident events arrive in CSV + JSONL with inconsistent categories, missing fields, and mixed timestamp formats. The pipeline normalizes the data, builds an LLM prompt payload, then validates and evaluates model outputs against a strict target JSON schema for downstream systems.

**Demo Data**
- Raw tickets: `data/raw/tickets.csv`
- Raw events: `data/raw/events.jsonl`
- Expected schema: `data/expected/target_schema.json`
- Generator: `scripts/generate_demo_data.py` (deterministic seed)
- Validator: `scripts/validate_demo_data.py` (validates normalized LLM outputs)
  - Expects `data/raw/llm_outputs.jsonl` containing one normalized JSON object per line.

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

**ETL Run**
```bash
poetry run python -m llm_etl_eval.etl.run --input-dir data/raw --output-dir data/processed
```

**LLM Simulator**
```bash
poetry run python -m llm_etl_eval.sim.run --inputs data/processed/llm_inputs.jsonl --outputs data/llm/outputs.jsonl --error-rate 0.2
```

**Transform to Target System**
```bash
poetry run python -m llm_etl_eval.transform.run --schema data/expected/target_schema.json --llm-outputs data/llm/outputs.jsonl --out-dir data/final
```

**Common Commands**
```bash
make lint
make format
make typecheck
make test
make ci
make demo-data
make validate-demo
```

**CI**
GitHub Actions runs Ruff, mypy, and pytest with coverage on push and pull requests.
