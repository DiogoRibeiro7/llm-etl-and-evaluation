"""CLI for the categorical distribution drift check (PSI + JSD)."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from llm_etl_eval.checks.distribution_drift import (
    DEFAULT_JSD_THRESHOLD,
    DEFAULT_PSI_THRESHOLD,
    DriftReport,
    compute_drift,
)

DEFAULT_FIELDS = ["category", "priority", "language"]


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        records.append(json.loads(line))
    return records


def _report_to_dict(report: DriftReport) -> dict[str, Any]:
    return {
        "ok": report.ok,
        "psi_threshold": report.psi_threshold,
        "jsd_threshold": report.jsd_threshold,
        "fields": [asdict(field_drift) for field_drift in report.fields],
    }


def write_drift_report(report: DriftReport, out_path: Path) -> None:
    """Write a drift report as JSON next to a regular run report."""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(_report_to_dict(report), indent=2, sort_keys=True),
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(
        prog="llm-etl-eval-drift",
        description=(
            "Compute PSI and Jensen-Shannon divergence between two record "
            "sets across categorical fields."
        ),
    )
    parser.add_argument(
        "--reference",
        type=Path,
        required=True,
        help="JSONL file of reference records (e.g., gold labels or baseline).",
    )
    parser.add_argument(
        "--candidate",
        type=Path,
        required=True,
        help="JSONL file of candidate records (e.g., current LLM outputs).",
    )
    parser.add_argument(
        "--fields",
        nargs="+",
        default=DEFAULT_FIELDS,
        help="Fields to check (default: category priority language).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output drift report JSON path.",
    )
    parser.add_argument(
        "--psi-threshold",
        type=float,
        default=DEFAULT_PSI_THRESHOLD,
        help=f"PSI threshold for breach (default: {DEFAULT_PSI_THRESHOLD}).",
    )
    parser.add_argument(
        "--jsd-threshold",
        type=float,
        default=DEFAULT_JSD_THRESHOLD,
        help=f"JSD threshold for breach (default: {DEFAULT_JSD_THRESHOLD}).",
    )
    parser.add_argument(
        "--fail-on-drift",
        action="store_true",
        help="Exit non-zero when any field breaches a threshold.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""

    parser = build_parser()
    args = parser.parse_args(argv)

    reference_records = _load_jsonl(args.reference)
    candidate_records = _load_jsonl(args.candidate)

    report = compute_drift(
        reference_records,
        candidate_records,
        list(args.fields),
        psi_threshold=args.psi_threshold,
        jsd_threshold=args.jsd_threshold,
    )

    write_drift_report(report, args.out)

    for field_drift in report.fields:
        line = (
            f"{field_drift.field_name}: psi={field_drift.psi:.4f} "
            f"jsd={field_drift.jsd:.4f} severity={field_drift.severity}"
        )
        if field_drift.breaches:
            line += " BREACH(" + "; ".join(field_drift.breaches) + ")"
        print(line)

    if args.fail_on_drift and not report.ok:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
