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
