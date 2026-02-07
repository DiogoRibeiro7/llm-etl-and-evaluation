# Architecture

This project is a reference implementation of a reliable LLM data pipeline that treats model output as untrusted input and enforces a strict downstream contract.

## Core Flow

1. Ingest and clean messy CSV/JSONL inputs.
2. Join tickets with related events and normalize to LLM inputs.
3. Construct prompt payloads (system + user) that directly reflect the target schema.
4. Simulate or call a real LLM to produce outputs.
5. Transform LLM outputs into target‑system records with tolerant parsing and explicit error capture.
6. Evaluate output quality, then run monitoring checks to detect regressions.

## Reliability Mechanisms

- JSON Schema is the single source of truth for downstream format.
- Transform layer separates parse/coerce/map to avoid silent corruption.
- Evaluation + monitoring provide automated guardrails against regressions.

## Extensibility

- New schemas can be adopted by adding a new JSON Schema and reusing the transform/eval stack.
- Additional metrics can be added in `src/llm_etl_eval/eval/metrics.py`.
- Real LLM integrations can be wired into the simulator boundary and still produce JSONL outputs.

## Execution Surface

- ETL: `python -m llm_etl_eval.etl.run`
- Sim: `python -m llm_etl_eval.sim.run`
- Transform: `python -m llm_etl_eval.transform.run`
- Eval: `python -m llm_etl_eval.eval.run`
- Checks: `python -m llm_etl_eval.checks.run`
