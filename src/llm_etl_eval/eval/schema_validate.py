"""Enterprise-grade JSON Schema validation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from datetime import datetime

from jsonschema import Draft202012Validator, FormatChecker


@dataclass(frozen=True)
class SchemaIssue:
    """Represents a JSON Schema validation issue."""

    code: str
    message: str
    field_path: str | None
    severity: str
    raw_value: Any


def _format_path(parts: tuple[Any, ...]) -> str | None:
    if not parts:
        return None
    return ".".join(str(part) for part in parts)


def _build_format_checker() -> FormatChecker:
    checker = FormatChecker()

    @checker.checks("date-time")
    def _is_datetime(value: Any) -> bool:
        if not isinstance(value, str):
            return False
        cleaned = value.strip()
        if cleaned.endswith("Z"):
            cleaned = cleaned.replace("Z", "+00:00")
        try:
            datetime.fromisoformat(cleaned)
            return True
        except ValueError:
            return False

    return checker


def validate_schema(payload: dict[str, Any], schema: dict[str, Any]) -> list[SchemaIssue]:
    """Validate a payload against JSON Schema and return structured issues."""

    validator = Draft202012Validator(schema, format_checker=_build_format_checker())
    issues: list[SchemaIssue] = []
    for error in sorted(validator.iter_errors(payload), key=lambda err: err.path):
        field_path = _format_path(tuple(error.absolute_path))
        issues.append(
            SchemaIssue(
                code=str(error.validator),
                message=error.message,
                field_path=field_path,
                severity="error",
                raw_value=error.instance,
            )
        )
    return issues


def group_issues(issues: list[SchemaIssue]) -> dict[str, list[SchemaIssue]]:
    """Group issues by field path for easier reporting."""

    grouped: dict[str, list[SchemaIssue]] = {}
    for issue in issues:
        key = issue.field_path or "__root__"
        grouped.setdefault(key, []).append(issue)
    return grouped
