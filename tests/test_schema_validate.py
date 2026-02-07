"""Tests for schema validation issues."""

from __future__ import annotations

from llm_etl_eval.eval.schema_validate import group_issues, validate_schema


def _base_record() -> dict[str, object]:
    return {
        "ticket_id": "TKT-1",
        "customer_id": "C-1",
        "created_at": "2025-11-10T14:30:00+00:00",
        "language": "en",
        "summary": "Good summary",
        "category": "billing",
        "priority": "high",
        "entities": [],
        "actions": [{"action": "triage", "owner": "AG-1", "due_at": "2025-11-11T00:00:00+00:00"}],
    }


def _schema() -> dict[str, object]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "ticket_id",
            "customer_id",
            "created_at",
            "language",
            "summary",
            "category",
            "priority",
            "entities",
            "actions",
        ],
        "properties": {
            "ticket_id": {"type": "string"},
            "customer_id": {"type": "string"},
            "created_at": {"type": "string", "format": "date-time"},
            "language": {"type": "string"},
            "summary": {"type": "string", "minLength": 1},
            "category": {"type": "string", "enum": ["billing", "account"]},
            "priority": {"type": "string", "enum": ["low", "high"]},
            "entities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["type", "value", "confidence"],
                    "properties": {
                        "type": {"type": "string"},
                        "value": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                },
            },
            "actions": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["action", "owner", "due_at"],
                    "properties": {
                        "action": {"type": "string"},
                        "owner": {"type": "string"},
                        "due_at": {"type": "string", "format": "date-time"},
                        "status": {"type": "string", "enum": ["open", "done"]},
                    },
                },
            },
        },
    }


def test_schema_missing_required() -> None:
    record = _base_record()
    record.pop("summary")
    issues = validate_schema(record, _schema())
    assert any(issue.code == "required" for issue in issues)


def test_schema_invalid_enum() -> None:
    record = _base_record()
    record["priority"] = "urgent"
    issues = validate_schema(record, _schema())
    assert any(issue.code == "enum" for issue in issues)


def test_schema_wrong_type() -> None:
    record = _base_record()
    record["entities"] = "not-a-list"
    issues = validate_schema(record, _schema())
    assert any(issue.code == "type" for issue in issues)


def test_schema_min_items() -> None:
    record = _base_record()
    record["actions"] = []
    issues = validate_schema(record, _schema())
    assert any(issue.code == "minItems" for issue in issues)


def test_schema_format_error() -> None:
    record = _base_record()
    record["created_at"] = "not-a-date"
    issues = validate_schema(record, _schema())
    assert any(issue.code == "format" for issue in issues)


def test_schema_additional_properties() -> None:
    record = _base_record()
    record["extra"] = "boom"
    issues = validate_schema(record, _schema())
    assert any(issue.code == "additionalProperties" for issue in issues)


def test_schema_nested_confidence_range() -> None:
    record = _base_record()
    record["entities"] = [{"type": "region", "value": "EU", "confidence": 2}]
    issues = validate_schema(record, _schema())
    assert any(issue.code == "maximum" for issue in issues)


def test_schema_grouped_issues() -> None:
    record = _base_record()
    record["actions"] = []
    record["priority"] = "urgent"
    issues = validate_schema(record, _schema())
    grouped = group_issues(issues)
    assert "actions" in grouped or "actions.0" in grouped
    assert "priority" in grouped
