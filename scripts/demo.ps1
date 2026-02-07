# Demo: ETL -> LLM outputs (simulated) -> Transform/Validate -> Evaluate -> Improve
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\scripts\demo.ps1

$ErrorActionPreference = "Stop"

function Step([string]$title) {
  Write-Host ""
  Write-Host "=============================================="
  Write-Host $title
  Write-Host "=============================================="
  Write-Host ""
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Step "Demo: llm-etl-and-evaluation (interview run)"

Step "[0/6] Install dependencies"
poetry install --no-interaction | Out-Host

Step "[1/6] Run ETL (raw -> processed)"
poetry run python -m llm_etl_eval.etl.run `
  --input-dir data/raw `
  --output-dir data/processed | Out-Host

Step "[2/6] Generate BASELINE LLM outputs (simulated errors)"
poetry run python -m llm_etl_eval.sim.run `
  --inputs data/processed/llm_inputs.jsonl `
  --outputs data/llm/outputs_baseline.jsonl `
  --error-rate 0.35 `
  --seed 7 | Out-Host

Step "[3/6] Transform + validate BASELINE outputs"
poetry run python -m llm_etl_eval.transform.run `
  --schema data/expected/target_schema.json `
  --llm-outputs data/llm/outputs_baseline.jsonl `
  --out-dir data/final/baseline | Out-Host

Step "[4/6] Evaluate BASELINE (metrics + error taxonomy)"
poetry run python -m llm_etl_eval.eval.run `
  --inputs data/processed/llm_inputs.jsonl `
  --outputs data/llm/outputs_baseline.jsonl `
  --gold data/gold/labels.jsonl `
  --schema data/expected/target_schema.json `
  --out reports/baseline | Out-Host

Step "[5/6] Generate IMPROVED LLM outputs (fewer errors)"
poetry run python -m llm_etl_eval.sim.run `
  --inputs data/processed/llm_inputs.jsonl `
  --outputs data/llm/outputs_improved.jsonl `
  --error-rate 0.15 `
  --seed 7 | Out-Host

Step "[6/6] Transform + validate + evaluate IMPROVED outputs"
poetry run python -m llm_etl_eval.transform.run `
  --schema data/expected/target_schema.json `
  --llm-outputs data/llm/outputs_improved.jsonl `
  --out-dir data/final/improved | Out-Host

poetry run python -m llm_etl_eval.eval.run `
  --inputs data/processed/llm_inputs.jsonl `
  --outputs data/llm/outputs_improved.jsonl `
  --gold data/gold/labels.jsonl `
  --schema data/expected/target_schema.json `
  --out reports/improved | Out-Host

Step "BASELINE REPORT"
$baselineReport = Join-Path $repoRoot "reports/baseline/report.md"
if (Test-Path $baselineReport) {
  Get-Content $baselineReport -Raw | Write-Host
} else {
  Write-Host "Missing: $baselineReport"
}

Step "IMPROVED REPORT"
$improvedReport = Join-Path $repoRoot "reports/improved/report.md"
if (Test-Path $improvedReport) {
  Get-Content $improvedReport -Raw | Write-Host
} else {
  Write-Host "Missing: $improvedReport"
}

Write-Host ""
Write-Host "Done."
