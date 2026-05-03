# Demo: ETL -> LLM outputs (simulated) -> Transform/Validate -> Evaluate -> Improve
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\scripts\demo_interview.ps1

$ErrorActionPreference = "Stop"

function Step([string]$title) {
  Write-Host ""
  Write-Host "=============================================="
  Write-Host $title
  Write-Host "=============================================="
  Write-Host ""
}

function Read-Report([string]$path) {
  if (-not (Test-Path $path)) {
    throw "Missing report file: $path"
  }
  return Get-Content $path -Raw | ConvertFrom-Json
}

function Top-Errors([object]$report) {
  $errors = $report.error_taxonomy
  if ($null -eq $errors) { return @() }

  $pairs = @()
  foreach ($key in $errors.PSObject.Properties.Name) {
    $pairs += [pscustomobject]@{ Message = $key; Count = [int]$errors.$key }
  }

  return $pairs | Sort-Object -Property Count -Descending | Select-Object -First 5
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot
$errorRate = 0.35
$baselineConfig = "configs/baseline.yaml"
$improvedConfig = "configs/improved.yaml"
$schemaPath = "data/expected/target_schema.json"

Step "Demo: llm-etl-and-evaluation (interview run)"

Step "[0/9] Install dependencies"
poetry install --no-interaction | Out-Host

Step "[1/9] Run ETL (raw -> processed)"
poetry run python -m llm_etl_eval.etl.run `
  --input-dir data/raw `
  --output-dir data/processed | Out-Host

Step "[2/9] Generate BASELINE prompts (config-driven)"
poetry run python -m llm_etl_eval.prompting.run `
  --inputs data/processed/llm_inputs.jsonl `
  --schema $schemaPath `
  --config $baselineConfig `
  --out data/llm/prompts_baseline.jsonl | Out-Host

Step "[3/9] Generate BASELINE LLM outputs (simulated errors)"
poetry run python -m llm_etl_eval.sim.run `
  --inputs data/processed/llm_inputs.jsonl `
  --outputs data/llm/outputs_baseline.jsonl `
  --error-rate $errorRate `
  --seed 7 | Out-Host

Step "[4/9] Transform + validate BASELINE outputs"
poetry run python -m llm_etl_eval.transform.run `
  --schema $schemaPath `
  --llm-outputs data/llm/outputs_baseline.jsonl `
  --config $baselineConfig `
  --out-dir data/final/baseline | Out-Host

Step "[5/9] Round-trip BASELINE accepted outputs"
poetry run python -m llm_etl_eval.checks.roundtrip `
  --accepted data/final/baseline/accepted.jsonl `
  --schema $schemaPath `
  --out data/final/baseline/api_payloads.jsonl | Out-Host

Step "[6/9] Evaluate BASELINE (metrics + error taxonomy)"
poetry run python -m llm_etl_eval.eval.run `
  --inputs data/processed/llm_inputs.jsonl `
  --outputs data/llm/outputs_baseline.jsonl `
  --gold data/gold/labels.jsonl `
  --schema $schemaPath `
  --out reports/baseline | Out-Host

poetry run python -m llm_etl_eval.manifest.run `
  --out reports/baseline/manifest.json `
  --label baseline `
  --config $baselineConfig `
  --schema $schemaPath `
  --inputs data/processed/llm_inputs.jsonl `
  --outputs data/llm/outputs_baseline.jsonl `
  --gold data/gold/labels.jsonl `
  --prompts data/llm/prompts_baseline.jsonl `
  --seed 7 `
  --error-rate $errorRate | Out-Host

poetry run python -m llm_etl_eval.eval.error_clusters_run `
  --rejected data/final/baseline/rejected.jsonl `
  --out reports/baseline/clusters.json | Out-Host

Step "[7/9] Generate IMPROVED prompts (config-driven)"
poetry run python -m llm_etl_eval.prompting.run `
  --inputs data/processed/llm_inputs.jsonl `
  --schema $schemaPath `
  --config $improvedConfig `
  --out data/llm/prompts_improved.jsonl | Out-Host

Step "[8/9] Generate IMPROVED LLM outputs (same error rate)"
poetry run python -m llm_etl_eval.sim.run `
  --inputs data/processed/llm_inputs.jsonl `
  --outputs data/llm/outputs_improved.jsonl `
  --error-rate $errorRate `
  --seed 7 | Out-Host

Step "[9/9] Transform + validate + evaluate IMPROVED outputs"
poetry run python -m llm_etl_eval.transform.run `
  --schema $schemaPath `
  --llm-outputs data/llm/outputs_improved.jsonl `
  --config $improvedConfig `
  --out-dir data/final/improved | Out-Host

poetry run python -m llm_etl_eval.checks.roundtrip `
  --accepted data/final/improved/accepted.jsonl `
  --schema $schemaPath `
  --out data/final/improved/api_payloads.jsonl | Out-Host

poetry run python -m llm_etl_eval.eval.run `
  --inputs data/processed/llm_inputs.jsonl `
  --outputs data/llm/outputs_improved.jsonl `
  --gold data/gold/labels.jsonl `
  --schema $schemaPath `
  --out reports/improved | Out-Host

poetry run python -m llm_etl_eval.manifest.run `
  --out reports/improved/manifest.json `
  --label improved `
  --config $improvedConfig `
  --schema $schemaPath `
  --inputs data/processed/llm_inputs.jsonl `
  --outputs data/llm/outputs_improved.jsonl `
  --gold data/gold/labels.jsonl `
  --prompts data/llm/prompts_improved.jsonl `
  --seed 7 `
  --error-rate $errorRate | Out-Host

poetry run python -m llm_etl_eval.eval.error_clusters_run `
  --rejected data/final/improved/rejected.jsonl `
  --out reports/improved/clusters.json | Out-Host

Step "Distribution drift: improved vs baseline (PSI + JSD)"
poetry run python -m llm_etl_eval.checks.distribution_drift_run `
  --reference data/llm/outputs_baseline.jsonl `
  --candidate data/llm/outputs_improved.jsonl `
  --fields category priority language `
  --out reports/improved/drift.json | Out-Host

$baselineMd = Join-Path $repoRoot "reports/baseline/report.md"
$improvedMd = Join-Path $repoRoot "reports/improved/report.md"

if (-not (Test-Path $baselineMd)) { throw "Missing report.md: $baselineMd" }
if (-not (Test-Path $improvedMd)) { throw "Missing report.md: $improvedMd" }

$baselineReport = Read-Report (Join-Path $repoRoot "reports/baseline/report.json")
$improvedReport = Read-Report (Join-Path $repoRoot "reports/improved/report.json")

$baselineErrors = Top-Errors $baselineReport
$improvedErrors = Top-Errors $improvedReport

Write-Host ""
Write-Host "=============================================="
Write-Host "COMPARISON SUMMARY"
Write-Host "=============================================="
Write-Host "Baseline validity rate: $([math]::Round($baselineReport.schema_validity_rate * 100, 2))%"
Write-Host "Improved validity rate: $([math]::Round($improvedReport.schema_validity_rate * 100, 2))%"
Write-Host ""
Write-Host "Top 5 error codes (baseline):"
if ($baselineErrors.Count -eq 0) {
  Write-Host "  - none"
} else {
  foreach ($item in $baselineErrors) {
    Write-Host "  - $($item.Message): $($item.Count)"
  }
}
Write-Host ""
Write-Host "Top 5 error codes (improved):"
if ($improvedErrors.Count -eq 0) {
  Write-Host "  - none"
} else {
  foreach ($item in $improvedErrors) {
    Write-Host "  - $($item.Message): $($item.Count)"
  }
}
Write-Host ""
Write-Host "Done."
