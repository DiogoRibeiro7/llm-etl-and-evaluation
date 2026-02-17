# LLM ETL & Evaluation — Interview Pitch

This repo is a compact, production-minded LLM data pipeline that treats model output as untrusted input and proves downstream compatibility. It showcases how I design data semantics, enforce contracts, transform messy LLM output into safe records, and measure quality with meaningful success metrics.

**Pipeline Diagram**

```
Raw Data (CSV/JSONL)
        |
        v
  Ingest + Clean
        |
        v
 Canonical Inputs  --->  Prompting (strictness knobs)
        |                               |
        v                               v
     Simulator / LLM  ----------------> LLM Outputs
        |                               |
        v                               v
 Parse + Coerce + Map  --->  Accepted / Rejected
        |                               |
        v                               v
  Round-trip Check  ----------------> Target API Payloads
        |
        v
 Evaluation + Monitoring
```

**What This Demonstrates**

- Data semantics: stable canonical input record with deterministic normalization rules and explicit fallbacks.
- Schemas/contracts: JSON Schema gates downstream shape, plus typed contracts at ETL and transform boundaries.
- Transformation logic: tolerant parsing, explicit coercion rules, and structured error taxonomy (no silent guessing).
- Evaluation strategy + success metrics: schema validity rate, completeness, field accuracy vs. gold, constraints per record, and consistency.

**Run the Interview Demo on Windows (3 commands max)**

```powershell
poetry install
powershell -ExecutionPolicy Bypass -File .\scripts\demo_interview.ps1
```

**Run the Interview Demo on macOS/Linux**

```bash
poetry install
bash scripts/demo_interview.sh
```

**Screenshot-Friendly Report Snippet**

```markdown
# Evaluation Report

## Summary
- Records: 200
- Gold records: 200
- Schema validity rate: 92.50%
- Completeness rate: 98.00%
- Field accuracy (overall): 94.10%
- Constraint violations per record: 0.08
- Consistency rate: 99.50%

## Error Taxonomy
- missing_required: 6
- enum_mismatch: 4
```

**Why This Is Credible**

- Improvements are config-driven knobs, not just a lower simulator error rate.
- Baseline vs. improved runs keep the simulator settings fixed.
- Round-trip checks prove that `accepted.jsonl` is safe to ingest as a target-system payload.

**Repo Map**

- `src/llm_etl_eval/contracts/` — typed data contracts + validation
- `src/llm_etl_eval/etl/` — ingest, clean, join, normalize
- `src/llm_etl_eval/prompting/` — prompt templates + strictness controls
- `src/llm_etl_eval/sim/` — deterministic output simulator
- `src/llm_etl_eval/transform/` — tolerant parse, coercion, mapping, rejection handling
- `src/llm_etl_eval/eval/` — schema validation, metrics, reporting
- `src/llm_etl_eval/checks/` — monitoring + round-trip verification
