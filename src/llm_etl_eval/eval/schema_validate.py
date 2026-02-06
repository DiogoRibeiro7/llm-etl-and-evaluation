"""JSON Schema validation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator


@dataclass(frozen=True)
class SchemaIssue:
    """Represents a JSON Schema validation issue."""

    message: str
    field_path: str | None


def validate_schema(payload: dict[str, Any], schema: dict[str, Any]) -> list[SchemaIssue]:
    """Validate a payload against JSON Schema and return issues."""

    validator = Draft202012Validator(schema)
    issues: list[SchemaIssue] = []
    for error in validator.iter_errors(payload):
        field_path = ".".join(str(part) for part in error.path) if error.path else None
        issues.append(SchemaIssue(message=error.message, field_path=field_path))
    return issues
