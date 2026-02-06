"""Validate demo data against the target JSON schema."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jsonschema
from jsonschema import Draft202012Validator

RAW_DIR = Path("data/raw")
EXPECTED_DIR = Path("data/expected")


@dataclass(frozen=True)
class ValidationIssue:
    """Represents a validation error for a normalized payload."""

    ticket_id: str
    message: str


def load_schema(path: Path) -> dict[str, Any]:
    """Load the JSON schema from disk."""

    return json.loads(path.read_text(encoding="utf-8"))


def load_llm_outputs(path: Path) -> list[dict[str, Any]]:
    """Load demo LLM outputs from JSONL."""

    outputs: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        outputs.append(json.loads(line))
    return outputs


def validate_outputs(
    outputs: list[dict[str, Any]], schema: dict[str, Any]
) -> list[ValidationIssue]:
    """Validate each output against the schema and return issues."""

    validator = Draft202012Validator(schema)
    issues: list[ValidationIssue] = []

    for output in outputs:
        ticket_id = str(output.get("ticket_id", "unknown"))
        for error in validator.iter_errors(output):
            issues.append(ValidationIssue(ticket_id=ticket_id, message=error.message))

    return issues


def main() -> None:
    """Run schema validation for demo outputs."""

    schema_path = EXPECTED_DIR / "target_schema.json"
    outputs_path = RAW_DIR / "llm_outputs.jsonl"

    if not outputs_path.exists():
        raise SystemExit(
            "No demo outputs found. Create data/raw/llm_outputs.jsonl with normalized records."
        )

    schema = load_schema(schema_path)
    outputs = load_llm_outputs(outputs_path)
    issues = validate_outputs(outputs, schema)

    if issues:
        for issue in issues:
            print(f"{issue.ticket_id}: {issue.message}")
        raise SystemExit(f"Validation failed with {len(issues)} issue(s).")

    print(f"Validation passed for {len(outputs)} output record(s).")


if __name__ == "__main__":
    main()
