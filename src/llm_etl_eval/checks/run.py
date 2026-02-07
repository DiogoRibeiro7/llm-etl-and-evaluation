"""CLI for running monitoring-style checks."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from llm_etl_eval.checks.quality import (
    CheckResult,
    DriftThreshold,
    NullRateThresholds,
    OutputMonitoringThresholds,
    TimestampSanity,
    check_category_drift,
    check_error_spike,
    check_null_rates,
    check_schema_validity_drop,
    check_timestamp_sanity,
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        records.append(json.loads(line))
    return records


def _category_distribution(records: list[dict[str, Any]]) -> dict[str, float]:
    counts: dict[str, int] = {}
    total = 0
    for record in records:
        category = record.get("category")
        if isinstance(category, str):
            counts[category] = counts.get(category, 0) + 1
            total += 1
    if total == 0:
        return {}
    return {key: value / total for key, value in counts.items()}


def run_checks(
    baseline_path: Path,
    current_path: Path,
    inputs_path: Path | None = None,
    baseline_inputs_path: Path | None = None,
) -> list[CheckResult]:
    """Run monitoring checks comparing baseline and current reports."""

    baseline = _load_json(baseline_path)
    current = _load_json(current_path)

    results: list[CheckResult] = []

    output_thresholds = OutputMonitoringThresholds(
        max_schema_validity_drop=0.05,
        error_spike_ratio=2.0,
        error_spike_min_increase=2,
    )

    results.append(
        check_schema_validity_drop(
            baseline_rate=baseline.get("schema_validity_rate", 0.0),
            current_rate=current.get("schema_validity_rate", 0.0),
            thresholds=output_thresholds,
        )
    )

    results.append(
        check_error_spike(
            baseline=baseline.get("error_taxonomy", {}),
            current=current.get("error_taxonomy", {}),
            thresholds=output_thresholds,
        )
    )

    if inputs_path is not None:
        input_records = _load_jsonl(inputs_path)
        results.append(
            check_null_rates(
                input_records,
                NullRateThresholds(
                    max_null_rate={
                        "ticket_id": 0.0,
                        "customer_id": 0.05,
                        "created_at": 0.05,
                        "category": 0.1,
                        "priority": 0.1,
                        "summary": 0.15,
                        "language": 0.2,
                    }
                ),
            )
        )
        results.append(
            check_timestamp_sanity(
                input_records,
                TimestampSanity(min_year=2020, max_future_days=2),
            )
        )

        if baseline_inputs_path is not None:
            baseline_records = _load_jsonl(baseline_inputs_path)
            results.append(
                check_category_drift(
                    input_records,
                    baseline_distribution=_category_distribution(baseline_records),
                    threshold=DriftThreshold(max_abs_diff=0.25),
                )
            )

    return results


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""

    parser = argparse.ArgumentParser(
        prog="llm-etl-eval-checks",
        description="Run monitoring-style checks for data quality and outputs.",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        required=True,
        help="Path to baseline report.json.",
    )
    parser.add_argument(
        "--current",
        type=Path,
        required=True,
        help="Path to current report.json.",
    )
    parser.add_argument(
        "--inputs",
        type=Path,
        help="Optional JSONL inputs to run data quality checks.",
    )
    parser.add_argument(
        "--baseline-inputs",
        type=Path,
        help="Optional JSONL baseline inputs for drift checks.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""

    parser = build_parser()
    args = parser.parse_args(argv)

    results = run_checks(args.baseline, args.current, args.inputs, args.baseline_inputs)

    for result in results:
        print(json.dumps(asdict(result), sort_keys=True))

    if any(not result.ok for result in results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
