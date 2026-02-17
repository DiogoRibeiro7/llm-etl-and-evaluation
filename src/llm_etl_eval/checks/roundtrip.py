"""Round-trip checks for accepted outputs."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from llm_etl_eval.contracts import parse_target_system_record
from llm_etl_eval.eval.schema_validate import validate_schema


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        records.append(json.loads(line))
    return records


def _write_jsonl(records: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")


def _load_schema(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _to_api_payload(record: dict[str, Any]) -> dict[str, Any]:
    """Wrap a target record in a mock API payload."""

    return {"payload": record}


def roundtrip_accepteds(
    accepted_path: Path, schema_path: Path, out_path: Path
) -> list[dict[str, Any]]:
    """Validate accepted records again and emit mock API payloads."""

    schema = _load_schema(schema_path)
    records = _load_jsonl(accepted_path)
    payloads: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for index, record in enumerate(records):
        _, contract_errors = parse_target_system_record(record)
        schema_issues = validate_schema(record, schema)

        if contract_errors or schema_issues:
            errors.append(
                {
                    "index": index,
                    "errors": [asdict(error) for error in contract_errors]
                    + [asdict(issue) for issue in schema_issues],
                }
            )
            continue

        payloads.append(_to_api_payload(record))

    if errors:
        raise ValueError(f"Round-trip validation failed: {errors[:3]}")

    _write_jsonl(payloads, out_path)
    return payloads


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="llm-etl-eval-roundtrip",
        description="Validate accepted outputs and emit mock API payloads.",
    )
    parser.add_argument(
        "--accepted",
        type=Path,
        required=True,
        help="Path to accepted.jsonl from transform.",
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
        help="Output JSONL path for mock API payloads.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    roundtrip_accepteds(args.accepted, args.schema, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
