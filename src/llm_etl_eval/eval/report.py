"""Reporting utilities for evaluation metrics."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from llm_etl_eval.eval.metrics import MetricResult


def write_report_json(result: MetricResult, path: Path) -> None:
    """Write report JSON to disk."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")


def write_report_md(result: MetricResult, path: Path) -> None:
    """Write a human-readable markdown report."""

    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Evaluation Report",
        "",
        "## Summary",
        f"- Records: {result.totals['records']}",
        f"- Gold records: {result.totals['gold_records']}",
        f"- Schema validity rate: {result.schema_validity_rate:.2%}",
        f"- Completeness rate: {result.completeness_rate:.2%}",
        f"- Field accuracy: {result.field_accuracy:.2%}",
        f"- Constraint violations per record: {result.constraint_violations_per_record:.2f}",
        f"- Consistency rate: {result.consistency_rate:.2%}",
        "",
        "## Error Taxonomy",
    ]

    if not result.error_taxonomy:
        lines.append("- No schema errors detected.")
    else:
        for message, count in result.error_taxonomy.items():
            lines.append(f"- {message}: {count}")

    path.write_text("\n".join(lines), encoding="utf-8")
