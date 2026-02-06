"""CLI for evaluation metrics and report generation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from llm_etl_eval.eval.metrics import compute_metrics
from llm_etl_eval.eval.report import write_report_json, write_report_md


def _load_schema(path: Path) -> dict[str, Any]:
    """Load the JSON schema."""

    return json.loads(path.read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""

    parser = argparse.ArgumentParser(
        prog="llm-etl-eval-report",
        description="Compute evaluation metrics and generate reports.",
    )
    parser.add_argument(
        "--inputs",
        type=Path,
        required=True,
        help="Path to processed inputs (currently unused; reserved for consistency checks).",
    )
    parser.add_argument(
        "--outputs",
        type=Path,
        required=True,
        help="Path to LLM outputs JSONL.",
    )
    parser.add_argument(
        "--gold",
        type=Path,
        required=True,
        help="Path to gold labels JSONL.",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        required=True,
        help="Path to target JSON schema.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output directory for report artifacts.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""

    parser = build_parser()
    args = parser.parse_args(argv)

    schema = _load_schema(args.schema)
    result = compute_metrics(str(args.outputs), str(args.gold), schema)

    write_report_json(result, args.out / "report.json")
    write_report_md(result, args.out / "report.md")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
