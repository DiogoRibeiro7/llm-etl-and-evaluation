# Demo: ETL -> LLM outputs (simulated) -> Transform/Validate -> Evaluate -> Improve
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\scripts\demo.ps1

$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "demo_interview.ps1"
if (-not (Test-Path $scriptPath)) {
  throw "Missing interview demo script: $scriptPath"
}

& $scriptPath
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$baselineReport = Join-Path $repoRoot "reports/baseline/report.md"
$improvedReport = Join-Path $repoRoot "reports/improved/report.md"

Write-Host ""
Write-Host "Reports:"
Write-Host "  - $baselineReport"
Write-Host "  - $improvedReport"
