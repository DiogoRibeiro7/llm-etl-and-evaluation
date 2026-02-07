"""ETL CLI: ingest, clean, join, normalize, and write outputs."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
import importlib.util
from typing import Any

from llm_etl_eval.etl.clean import clean_all
from llm_etl_eval.etl.ingest import IngestConfig, load_raw
from llm_etl_eval.etl.join import join_by_ticket
from llm_etl_eval.etl.normalize import normalize_all


def _write_jsonl(records: list[dict[str, Any]], path: Path) -> None:
    """Write JSONL records to disk."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")


def _write_parquet(records: list[dict[str, Any]], path: Path) -> None:
    """Write parquet records if pyarrow is available."""

    if importlib.util.find_spec("pyarrow") is None:
        print("pyarrow not installed; skipping parquet output.")
        return

    import pyarrow as pa  # type: ignore[import-not-found]
    import pyarrow.parquet as pq  # type: ignore[import-not-found]

    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(records)
    pq.write_table(table, path)


def run_pipeline(input_dir: Path, output_dir: Path) -> None:
    """Run the ETL pipeline from raw inputs to normalized outputs."""

    config = IngestConfig(
        tickets_path=input_dir / "tickets.csv",
        events_path=input_dir / "events.jsonl",
    )

    tickets, events = load_raw(config)
    clean_tickets, clean_events = clean_all(tickets, events)
    joined = join_by_ticket(clean_tickets, clean_events)
    normalized = normalize_all(joined)

    records = [asdict(record) for record in normalized]

    _write_jsonl(records, output_dir / "llm_inputs.jsonl")
    _write_parquet(records, output_dir / "records.parquet")


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(
        prog="llm-etl-eval-etl",
        description="Run the ETL pipeline for demo data.",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing raw tickets.csv and events.jsonl.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory to write processed outputs.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""

    parser = build_parser()
    args = parser.parse_args(argv)
    run_pipeline(args.input_dir, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
