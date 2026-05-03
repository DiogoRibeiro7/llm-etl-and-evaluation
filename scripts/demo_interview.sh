#!/usr/bin/env bash
set -euo pipefail

# Demo: ETL -> LLM outputs (simulated) -> Transform/Validate -> Evaluate -> Improve
# Usage:
#   bash scripts/demo_interview.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ERROR_RATE="0.35"
BASELINE_CONFIG="configs/baseline.yaml"
IMPROVED_CONFIG="configs/improved.yaml"
SCHEMA_PATH="data/expected/target_schema.json"

echo ""
echo "=============================================="
echo "Demo: llm-etl-and-evaluation (interview run)"
echo "=============================================="
echo ""

cd "$ROOT_DIR"

echo ">> [0/9] Installing dependencies"
poetry install --no-interaction

echo ""
echo ">> [1/9] Running ETL (raw -> processed)"
poetry run python -m llm_etl_eval.etl.run \
  --input-dir data/raw \
  --output-dir data/processed

echo ""
echo ">> [2/9] Generating BASELINE prompts (config-driven)"
poetry run python -m llm_etl_eval.prompting.run \
  --inputs data/processed/llm_inputs.jsonl \
  --schema "$SCHEMA_PATH" \
  --config "$BASELINE_CONFIG" \
  --out data/llm/prompts_baseline.jsonl

echo ""
echo ">> [3/9] Generating BASELINE LLM outputs (simulated errors)"
poetry run python -m llm_etl_eval.sim.run \
  --inputs data/processed/llm_inputs.jsonl \
  --outputs data/llm/outputs_baseline.jsonl \
  --error-rate "$ERROR_RATE" \
  --seed 7

echo ""
echo ">> [4/9] Transform + validate BASELINE outputs"
poetry run python -m llm_etl_eval.transform.run \
  --schema "$SCHEMA_PATH" \
  --llm-outputs data/llm/outputs_baseline.jsonl \
  --config "$BASELINE_CONFIG" \
  --out-dir data/final/baseline

echo ""
echo ">> [5/9] Round-trip BASELINE accepted outputs"
poetry run python -m llm_etl_eval.checks.roundtrip \
  --accepted data/final/baseline/accepted.jsonl \
  --schema "$SCHEMA_PATH" \
  --out data/final/baseline/api_payloads.jsonl

echo ""
echo ">> [6/9] Evaluate BASELINE (metrics + error taxonomy)"
poetry run python -m llm_etl_eval.eval.run \
  --inputs data/processed/llm_inputs.jsonl \
  --outputs data/llm/outputs_baseline.jsonl \
  --gold data/gold/labels.jsonl \
  --schema "$SCHEMA_PATH" \
  --out reports/baseline

poetry run python -m llm_etl_eval.manifest.run \
  --out reports/baseline/manifest.json \
  --label baseline \
  --config "$BASELINE_CONFIG" \
  --schema "$SCHEMA_PATH" \
  --inputs data/processed/llm_inputs.jsonl \
  --outputs data/llm/outputs_baseline.jsonl \
  --gold data/gold/labels.jsonl \
  --prompts data/llm/prompts_baseline.jsonl \
  --seed 7 \
  --error-rate "$ERROR_RATE"

poetry run python -m llm_etl_eval.eval.error_clusters_run \
  --rejected data/final/baseline/rejected.jsonl \
  --out reports/baseline/clusters.json

echo ""
echo ">> [7/9] Generating IMPROVED prompts (config-driven)"
poetry run python -m llm_etl_eval.prompting.run \
  --inputs data/processed/llm_inputs.jsonl \
  --schema "$SCHEMA_PATH" \
  --config "$IMPROVED_CONFIG" \
  --out data/llm/prompts_improved.jsonl

echo ""
echo ">> [8/9] Generating IMPROVED LLM outputs (same error rate)"
poetry run python -m llm_etl_eval.sim.run \
  --inputs data/processed/llm_inputs.jsonl \
  --outputs data/llm/outputs_improved.jsonl \
  --error-rate "$ERROR_RATE" \
  --seed 7

echo ""
echo ">> [9/9] Transform + validate + evaluate IMPROVED outputs"
poetry run python -m llm_etl_eval.transform.run \
  --schema "$SCHEMA_PATH" \
  --llm-outputs data/llm/outputs_improved.jsonl \
  --config "$IMPROVED_CONFIG" \
  --out-dir data/final/improved

poetry run python -m llm_etl_eval.checks.roundtrip \
  --accepted data/final/improved/accepted.jsonl \
  --schema "$SCHEMA_PATH" \
  --out data/final/improved/api_payloads.jsonl

poetry run python -m llm_etl_eval.eval.run \
  --inputs data/processed/llm_inputs.jsonl \
  --outputs data/llm/outputs_improved.jsonl \
  --gold data/gold/labels.jsonl \
  --schema "$SCHEMA_PATH" \
  --out reports/improved

poetry run python -m llm_etl_eval.manifest.run \
  --out reports/improved/manifest.json \
  --label improved \
  --config "$IMPROVED_CONFIG" \
  --schema "$SCHEMA_PATH" \
  --inputs data/processed/llm_inputs.jsonl \
  --outputs data/llm/outputs_improved.jsonl \
  --gold data/gold/labels.jsonl \
  --prompts data/llm/prompts_improved.jsonl \
  --seed 7 \
  --error-rate "$ERROR_RATE"

poetry run python -m llm_etl_eval.eval.error_clusters_run \
  --rejected data/final/improved/rejected.jsonl \
  --out reports/improved/clusters.json

echo ""
echo ">> Distribution drift: improved vs baseline (PSI + JSD)"
poetry run python -m llm_etl_eval.checks.distribution_drift_run \
  --reference data/llm/outputs_baseline.jsonl \
  --candidate data/llm/outputs_improved.jsonl \
  --fields category priority language \
  --out reports/improved/drift.json

poetry run python - <<'PY'
import json
from pathlib import Path

def load_report(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"Missing report file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def top_errors(report: dict, limit: int = 5) -> list[tuple[str, int]]:
    errors = report.get("error_taxonomy") or {}
    pairs = [(key, int(value)) for key, value in errors.items()]
    pairs.sort(key=lambda item: item[1], reverse=True)
    return pairs[:limit]


root = Path(".")
baseline = load_report(root / "reports" / "baseline" / "report.json")
improved = load_report(root / "reports" / "improved" / "report.json")

print("")
print("==============================================")
print("COMPARISON SUMMARY")
print("==============================================")
print(f"Baseline validity rate: {baseline.get('schema_validity_rate', 0.0) * 100:.2f}%")
print(f"Improved validity rate: {improved.get('schema_validity_rate', 0.0) * 100:.2f}%")
print("")
print("Top 5 error codes (baseline):")
base_errors = top_errors(baseline)
if not base_errors:
    print("  - none")
else:
    for key, count in base_errors:
        print(f"  - {key}: {count}")
print("")
print("Top 5 error codes (improved):")
imp_errors = top_errors(improved)
if not imp_errors:
    print("  - none")
else:
    for key, count in imp_errors:
        print(f"  - {key}: {count}")
print("")
print("Done.")
PY
