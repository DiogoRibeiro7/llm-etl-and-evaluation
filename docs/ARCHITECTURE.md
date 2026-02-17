# Architecture

This project is a reference implementation of a reliable LLM data pipeline that treats model output as untrusted input and enforces a strict downstream contract.

## Core Flow

1. Ingest and clean messy CSV/JSONL inputs.
2. Join tickets with related events and normalize to LLM inputs.
3. Construct prompt payloads (system + user) that directly reflect the target schema.
4. Simulate or call a real LLM to produce outputs.
5. Transform LLM outputs into target‑system records with tolerant parsing and explicit error capture.
6. Evaluate output quality, then run monitoring checks to detect regressions.

## Default Interview Flow

Use the interview demo scripts as the canonical, stable run path.

- Windows: `powershell -ExecutionPolicy Bypass -File .\scripts\demo_interview.ps1`
- macOS/Linux: `bash scripts/demo_interview.sh`
- Legacy entry points forward to the interview scripts:
- `scripts/demo.ps1`
- `scripts/demo.sh`

## Reliability Mechanisms

- JSON Schema is the single source of truth for downstream format.
- Transform layer separates parse/coerce/map to avoid silent corruption.
- Typed contracts (`src/llm_etl_eval/contracts/`) validate ETL and transform boundaries.
- Evaluation + monitoring provide automated guardrails against regressions.
- Round-trip checks validate `accepted.jsonl` and emit mock API payloads.

## Configurable Improvement Knobs

- Parsing strictness: strict mode requires clean JSON only; lenient mode can handle fences, extra text, and trailing commas.
- Coercion rules: disabled in baseline to surface real errors; enabled in improved to recover valid shapes.
- Prompt strictness: minimal vs. strict templates with optional schema reminders embedded in the prompt.
- Config files live under `configs/` and are consumed by `transform` and `prompting` CLIs.

## Parsing Rules (LLM Output)

- Accepts JSON wrapped in ```json fences.
- Trims leading/trailing text to the first JSON object.
- Removes trailing commas before `}` or `]` as a best-effort fix.
- Supports Python-style single-quoted dicts only when they map cleanly to JSON (string keys + JSON-compatible values).
- Never guesses values: if parsing fails, returns a structured error.

## Extensibility

- New schemas can be adopted by adding a new JSON Schema and reusing the transform/eval stack.
- Additional metrics can be added in `src/llm_etl_eval/eval/metrics.py`.
- Real LLM integrations can be wired into the simulator boundary and still produce JSONL outputs.

## Execution Surface

- ETL: `python -m llm_etl_eval.etl.run`
- Prompting: `python -m llm_etl_eval.prompting.run`
- Sim: `python -m llm_etl_eval.sim.run`
- Transform: `python -m llm_etl_eval.transform.run`
- Eval: `python -m llm_etl_eval.eval.run`
- Checks: `python -m llm_etl_eval.checks.run`
- Round-trip: `python -m llm_etl_eval.checks.roundtrip`
