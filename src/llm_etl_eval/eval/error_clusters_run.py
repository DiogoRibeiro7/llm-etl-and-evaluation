"""CLI for clustering transformation rejections."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from llm_etl_eval.eval.error_clusters import (
    ClusterReport,
    cluster_rejections,
)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        records.append(json.loads(line))
    return records


def _report_to_dict(report: ClusterReport, top: int | None) -> dict[str, Any]:
    clusters = report.clusters
    if top is not None and top >= 0:
        clusters = clusters[:top]
    return {
        "totals": dict(report.totals),
        "clusters": [asdict(cluster) for cluster in clusters],
    }


def write_cluster_report(report: ClusterReport, out_path: Path, top: int | None = None) -> None:
    """Write a cluster report as JSON next to a regular run report."""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(_report_to_dict(report, top), indent=2, sort_keys=True),
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(
        prog="llm-etl-eval-clusters",
        description="Cluster rejected records by (code, field_path) with remediation hints.",
    )
    parser.add_argument(
        "--rejected",
        type=Path,
        required=True,
        help="Path to rejected.jsonl produced by transform.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output cluster report JSON path.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=None,
        help="Optional cap on number of clusters written to the report.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""

    parser = build_parser()
    args = parser.parse_args(argv)

    rejected = _load_jsonl(args.rejected)
    report = cluster_rejections(rejected)
    write_cluster_report(report, args.out, top=args.top)

    print(
        f"rejected_records={report.totals['rejected_records']} "
        f"total_errors={report.totals['total_errors']} "
        f"distinct_clusters={report.totals['distinct_clusters']}"
    )
    for cluster in report.clusters[: args.top if args.top else 5]:
        field_label = cluster.field_path or "<root>"
        print(
            f"  [{cluster.count}x / {cluster.affected_records} records] "
            f"{cluster.code} @ {field_label} -> {cluster.remediation}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
