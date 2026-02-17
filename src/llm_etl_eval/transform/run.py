"""CLI for transforming LLM outputs into target system records."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from llm_etl_eval.config import PipelineConfig, load_config
from llm_etl_eval.contracts import (
    ContractError,
    parse_llm_output_record,
    parse_target_system_record,
)
from llm_etl_eval.eval.schema_validate import SchemaIssue, validate_schema
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
            handle.write(json.dumps(record, sort_keys=True) + "\n")


def _write_rejected(records: list[dict[str, Any]], path: Path) -> None:
    """Write rejected records with errors."""

    _write_jsonl(records, path)


def _validate_schema(payload: dict[str, Any], schema: dict[str, Any]) -> list[TransformError]:
    """Validate payload against schema and capture errors."""

    errors: list[TransformError] = []
    issues = validate_schema(payload, schema)
    for issue in issues:
        errors.append(
            TransformError(
                code=issue.code,
                message=issue.message,
                field_path=issue.field_path,
                severity=issue.severity,
                raw_value=issue.raw_value,
            )
        )
    return errors


def _contract_errors_to_transform(errors: list[ContractError]) -> list[TransformError]:
    return [
        TransformError(
            code=error.code,
            message=error.message,
            field_path=error.field_path,
            severity="error",
            raw_value=error.raw_value,
        )
        for error in errors
    ]


def _load_config(path: Path | None) -> PipelineConfig:
    if path is None:
        return PipelineConfig()
    return load_config(path)


def run_transform(
    schema_path: Path,
    llm_outputs_path: Path,
    out_dir: Path,
    config_path: Path | None = None,
) -> None:
    """Run the transformation pipeline."""

    schema = _load_schema(schema_path)
    lines = _load_lines(llm_outputs_path)
    config = _load_config(config_path)

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for line in lines:
        if not line.strip():
            continue

        parsed, parse_errors = parse_json(line, strict=config.strict_parsing)
        if parsed is None:
            rejected.append(
                {
                    "raw": line,
                    "errors": [asdict(error) for error in parse_errors],
                }
            )
            continue

        _, llm_contract_errors = parse_llm_output_record(parsed)
        errors = parse_errors + _contract_errors_to_transform(llm_contract_errors)

        if any(error.severity == "error" for error in errors):
            rejected.append(
                {
                    "record": parsed,
                    "errors": [asdict(error) for error in errors],
                }
            )
            continue

        mapped, map_errors = map_payload(parsed, allow_coercion=config.coercion_enabled)
        _, contract_errors = parse_target_system_record(mapped)
        errors = errors + map_errors + _contract_errors_to_transform(contract_errors)

        if any(error.severity == "error" for error in errors):
            rejected.append(
                {
                    "record": mapped,
                    "errors": [asdict(error) for error in errors],
                }
            )
            continue

        schema_errors = _validate_schema(mapped, schema)
        errors = errors + schema_errors

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
        "--config",
        type=Path,
        required=False,
        help="Optional pipeline config (YAML/JSON) for parsing/coercion.",
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
    run_transform(args.schema, args.llm_outputs, args.out_dir, args.config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
