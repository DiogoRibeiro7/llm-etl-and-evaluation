# LLM ETL & Evaluation — Candidate Artifact

This repo demonstrates a production‑minded pipeline for normalizing messy operational data, producing LLM‑ready inputs, simulating and validating LLM outputs, and integrating them into a strict downstream system with evaluation and monitoring. It is designed to show how I build reliable data/LLM systems: typed contracts, deterministic ETL, robust parsing, and measurable quality.

## System Flow

```
Raw Data (CSV/JSONL)
        |
        v
      ETL
        |
        v
   LLM Inputs  ---> (simulate / real) --->  LLM Outputs
        |                                      |
        v                                      v
   Transform -----------------------------> Target System
        ^                                      |
        |                                      v
        +-------------- Eval / Monitoring <----+
```

## Quickstart

```bash
poetry install
poetry run python -m llm_etl_eval.etl.run --input-dir data/raw --output-dir data/processed
poetry run python -m llm_etl_eval.sim.run --inputs data/processed/llm_inputs.jsonl --outputs data/llm/outputs.jsonl --error-rate 0.2
poetry run python -m llm_etl_eval.transform.run --schema data/expected/target_schema.json --llm-outputs data/llm/outputs.jsonl --out-dir data/final
poetry run python -m llm_etl_eval.eval.run --inputs data/processed/llm_inputs.jsonl --outputs data/llm/outputs.jsonl --gold data/gold/labels.jsonl --schema data/expected/target_schema.json --out reports/
poetry run python -m llm_etl_eval.checks.run --baseline reports/example/report.json --current reports/latest/report.json
```

## Design Choices

**Schemas / Contracts**
- JSON Schema defines the downstream contract and gates both transform and evaluation.
- Typed dataclasses for ETL and LLM outputs enforce predictable structure throughout the pipeline.

**Parsing / Guardrails**
- Tolerant JSON parsing handles markdown fences and trailing text.
- Coercion rules convert common model mistakes (e.g., item → list) while tracking structured errors.
- Transform rejects invalid records with explicit, machine‑readable failure reasons.

**Evaluation Strategy**
- Schema validity: hard correctness for downstream systems.
- Field‑level accuracy vs. gold: correctness on critical fields.
- Completeness: coverage of required fields.
- Constraint violations: enum/range guardrail adherence.
- Consistency: stability across repeated runs.
- Error taxonomy: actionable error clustering.

## How to Extend

- Plug real LLM calls: replace the simulator by wiring `prompting/*` into an API client; keep output JSONL for compatibility.
- Add new schemas: update `data/expected/*.json`, then re‑use transform + eval by passing a new schema path.
- Add new metrics: implement in `src/llm_etl_eval/eval/metrics.py` and extend `report.py`.

## Repo Map

- `src/llm_etl_eval/etl/` — ingest, clean, join, normalize
- `src/llm_etl_eval/prompting/` — prompt templates and contracts
- `src/llm_etl_eval/sim/` — deterministic output simulator
- `src/llm_etl_eval/transform/` — tolerant parse, coercion, mapping, rejection handling
- `src/llm_etl_eval/eval/` — schema validation, metrics, reporting
- `src/llm_etl_eval/checks/` — monitoring‑style checks

