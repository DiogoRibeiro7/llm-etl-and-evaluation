"""CLI for running a real LLM provider over a prompt set.

Usage example (Anthropic):

    export ANTHROPIC_API_KEY=...
    python -m llm_etl_eval.llm.run \\
        --inputs data/processed/llm_inputs.jsonl \\
        --prompts data/llm/prompts_baseline.jsonl \\
        --outputs data/llm/outputs_real.jsonl \\
        --telemetry-out data/llm/telemetry.jsonl \\
        --telemetry-summary reports/baseline/telemetry.json \\
        --model claude-haiku-4-5 \\
        --max-records 20

Outputs match the simulator's shape, so the rest of the pipeline
(transform, eval, drift, clusters) consumes them unchanged.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from llm_etl_eval.llm.anthropic_provider import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    AnthropicProvider,
)
from llm_etl_eval.llm.runner import run_llm
from llm_etl_eval.llm.telemetry import load_and_aggregate


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(
        prog="llm-etl-eval-llm",
        description=(
            "Drive a real LLM provider over the prompt set; emit outputs + telemetry "
            "in the same shape as the deterministic simulator."
        ),
    )
    parser.add_argument(
        "--inputs",
        type=Path,
        required=True,
        help="Inputs JSONL (used for ticket_id ordering).",
    )
    parser.add_argument(
        "--prompts",
        type=Path,
        required=True,
        help="Prompts JSONL (system+user per record).",
    )
    parser.add_argument(
        "--outputs",
        type=Path,
        required=True,
        help="Where to write LLM output JSONL.",
    )
    parser.add_argument(
        "--telemetry-out",
        type=Path,
        required=True,
        help="Per-record telemetry JSONL (latency, tokens, model).",
    )
    parser.add_argument(
        "--telemetry-summary",
        type=Path,
        default=None,
        help="Optional aggregated telemetry JSON output.",
    )
    parser.add_argument(
        "--provider",
        choices=("anthropic",),
        default="anthropic",
        help="Which provider to use.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Model id (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help=f"Max output tokens per call (default: {DEFAULT_MAX_TOKENS}).",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=None,
        help="Cap the number of records processed (controls cost).",
    )
    parser.add_argument(
        "--api-key-env",
        default="ANTHROPIC_API_KEY",
        help="Environment variable holding the API key.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""

    parser = build_parser()
    args = parser.parse_args(argv)

    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        raise SystemExit(
            f"Missing {args.api_key_env} environment variable. "
            f"Export it before running, or use the simulator instead."
        )

    if args.provider == "anthropic":
        provider = AnthropicProvider(
            model=args.model,
            max_tokens=args.max_tokens,
            api_key=api_key,
        )
    else:  # pragma: no cover - guarded by argparse choices
        raise SystemExit(f"Unknown provider: {args.provider}")

    run_llm(
        inputs_path=args.inputs,
        prompts_path=args.prompts,
        outputs_path=args.outputs,
        telemetry_path=args.telemetry_out,
        provider=provider,
        max_records=args.max_records,
    )

    if args.telemetry_summary is not None:
        summary = load_and_aggregate(args.telemetry_out)
        args.telemetry_summary.parent.mkdir(parents=True, exist_ok=True)
        args.telemetry_summary.write_text(
            json.dumps(summary, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        cost = summary.get("cost_usd", {})
        latency = summary.get("latency_ms", {})
        print(
            f"records={summary['total_records']} "
            f"cost_usd={cost.get('total', 0.0)} "
            f"latency_p50_ms={latency.get('p50', 0.0)} "
            f"latency_p95_ms={latency.get('p95', 0.0)}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
