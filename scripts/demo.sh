#!/usr/bin/env bash
set -euo pipefail

# Demo: ETL -> LLM outputs (simulated) -> Transform/Validate -> Evaluate -> Improve
# Usage:
#   bash scripts/demo_interview.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo ""
echo "=============================================="
echo "Demo: llm-etl-and-evaluation (interview run)"
echo "=============================================="
echo ""

cd "$ROOT_DIR"

echo ">> [0/6] Installing dependencies"
poetry install --no-interaction

echo ""
echo ">> [1/6] Running ETL (raw -> processed)"
poetry run python -m llm_etl_eval.etl.run \
  --input-dir data/raw \
  --output-dir data/processed

echo ""
echo ">> [2/6] Generating BASELINE LLM outputs (simulated errors)"
poetry run python -m llm_etl_eval.sim.run \
  --inputs data/processed/llm_inputs.jsonl \
  --outputs data/llm/outputs_baseline.jsonl \
  --error-rate 0.35 \
  --seed 7

echo ""
echo ">> [3/6] Transform + validate BASELINE outputs"
poetry run python -m llm_etl_eval.transform.run \
  --schema data/expected/target_schema.json \
  --llm-outputs data/llm/outputs_baseline.jsonl \
  --out-dir data/final/baseline

echo ""
echo ">> [4/6] Evaluate BASELINE (metrics + error taxonomy)"
poetry run python -m llm_etl_eval.eval.run \
  --inputs data/processed/llm_inputs.jsonl \
  --outputs data/llm/outputs_baseline.jsonl \
  --schema data/expected/target_schema.json \
  --out reports/baseline

echo ""
echo ">> [5/6] Generating IMPROVED LLM outputs (fewer errors)"
poetry run python -m llm_etl_eval.sim.run \
  --inputs data/processed/llm_inputs.jsonl \
  --outputs data/llm/outputs_improved.jsonl \
  --error-rate 0.15 \
  --seed 7

echo ""
echo ">> [6/6] Transform + validate + evaluate IMPROVED outputs"
poetry run python -m llm_etl_eval.transform.run \
  --schema data/expected/target_schema.json \
  --llm-outputs data/llm/outputs_improved.jsonl \
  --out-dir data/final/improved

poetry run python -m llm_etl_eval.eval.run \
  --inputs data/processed/llm_inputs.jsonl \
  --outputs data/llm/outputs_improved.jsonl \
  --schema data/expected/target_schema.json \
  --out reports/improved

echo ""
echo "----------------------------------------------"
echo "BASELINE REPORT:"
echo "----------------------------------------------"
if [[ -f "reports/baseline/report.md" ]]; then
  cat "reports/baseline/report.md"
else
  echo "Missing reports/baseline/report.md"
fi

echo ""
echo "----------------------------------------------"
echo "IMPROVED REPORT:"
echo "----------------------------------------------"
if [[ -f "reports/improved/report.md" ]]; then
  cat "reports/improved/report.md"
else
  echo "Missing reports/improved/report.md"
fi

echo ""
echo "Done."
