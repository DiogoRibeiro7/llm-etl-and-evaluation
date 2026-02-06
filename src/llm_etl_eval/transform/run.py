"""CLI for transforming LLM outputs into target system records."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from llm_etl_eval.transform.errors import TransformError
from llm_etl_eval.transform.map import map_payload
from llm_etl_eval.transform.parse import parse_json


def _load_schema(path: Path) -> dict[str, Any]:
    """Load the JSON schema."""

    return json.loads(path.read_text(encoding="utf-8"))


def _load_lines(path: Path) -> list[str]:
    """Load raw LLM output lines."""

    return path.read_text(encoding="utf-8").splitlines()


def _write_jsonl(records: list[dict[str, Any]], path: Path) -> None:
    """Write JSONL records to disk."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")


def _write_rejected(records: list[dict[str, Any]], path: Path) -> None:
    """Write rejected records with errors."""

    _write_jsonl(records, path)


def _validate_schema(payload: dict[str, Any], schema: dict[str, Any]) -> list[TransformError]:
    """Validate payload against schema and capture errors."""

    validator = Draft202012Validator(schema)
    errors: list[TransformError] = []
    for error in validator.iter_errors(payload):
        field_path = ".".join(str(part) for part in error.path) if error.path else None
        errors.append(
            TransformError(
                code="schema_violation",
                message=error.message,
                field_path=field_path,
                severity="error",
            )
        )
    return errors


def run_transform(schema_path: Path, llm_outputs_path: Path, out_dir: Path) -> None:
    """Run the transformation pipeline."""

    schema = _load_schema(schema_path)
    lines = _load_lines(llm_outputs_path)

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for line in lines:
        if not line.strip():
            continue

        parsed, parse_errors = parse_json(line)
        if parsed is None:
            rejected.append(
                {
                    "raw": line,
                    "errors": [asdict(error) for error in parse_errors],
                }
            )
            continue

        mapped, map_errors = map_payload(parsed)
        schema_errors = _validate_schema(mapped, schema)
        errors = parse_errors + map_errors + schema_errors

        if any(error.severity == "error" for error in errors):
            rejected.append(
                {
                    "record": mapped,
                    "errors": [asdict(error) for error in errors],
                }
            )
            continue

        accepted.append(mapped)

    _write_jsonl(accepted, out_dir / "accepted.jsonl")
    _write_rejected(rejected, out_dir / "rejected.jsonl")


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(
        prog="llm-etl-eval-transform",
        description="Transform LLM outputs into target system records.",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        required=True,
        help="Path to target JSON schema.",
    )
    parser.add_argument(
        "--llm-outputs",
        type=Path,
        required=True,
        help="Path to LLM outputs JSONL.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        required=True,
        help="Output directory for accepted/rejected records.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""

    parser = build_parser()
    args = parser.parse_args(argv)
    run_transform(args.schema, args.llm_outputs, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
