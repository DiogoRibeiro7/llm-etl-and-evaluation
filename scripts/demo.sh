#!/usr/bin/env bash
set -euo pipefail

# Demo: ETL -> LLM outputs (simulated) -> Transform/Validate -> Evaluate -> Improve
# Usage:
#   bash scripts/demo.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/demo_interview.sh" "$@"
