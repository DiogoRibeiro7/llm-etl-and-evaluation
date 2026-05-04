"""Tests for tolerant JSON parsing and coercion rules."""

from __future__ import annotations

from llm_etl_eval.contracts import ALLOWED_FIELDS
from llm_etl_eval.transform.coerce import (
    CATEGORY_SYNONYMS,
    CATEGORY_VALID,
    PRIORITY_SYNONYMS,
    PRIORITY_VALID,
    backfill_required_summary,
    coerce_enum,
    coerce_list,
    coerce_string,
    strip_unexpected_fields,
)
from llm_etl_eval.transform.errors import TransformError
from llm_etl_eval.transform.map import map_payload
from llm_etl_eval.transform.parse import parse_json


def test_parse_json_with_markdown() -> None:
    text = """```json\n{\"ticket_id\": \"TKT-1\"}\n```"""
    parsed, errors = parse_json(text)
    assert errors == []
    assert parsed == {"ticket_id": "TKT-1"}


def test_parse_json_with_trailing_text() -> None:
    text = "Here you go: {\"ticket_id\": \"TKT-2\"} Thanks!"
    parsed, errors = parse_json(text)
    assert errors == []
    assert parsed == {"ticket_id": "TKT-2"}


def test_parse_json_with_single_quotes() -> None:
    text = "{'ticket_id': 'TKT-3', 'summary': 'Reset password'}"
    parsed, errors = parse_json(text)
    assert errors == []
    assert parsed == {"ticket_id": "TKT-3", "summary": "Reset password"}


def test_parse_json_with_trailing_commas() -> None:
    text = "{\"ticket_id\": \"TKT-4\",}"
    parsed, errors = parse_json(text)
    assert errors == []
    assert parsed == {"ticket_id": "TKT-4"}


def test_parse_json_rejects_invalid_single_quotes() -> None:
    text = "{'ticket_id': 'TKT-5', 'summary': \"oops}"
    parsed, errors = parse_json(text)
    assert parsed is None
    assert errors


def test_parse_json_rejects_unsafe_single_quotes() -> None:
    text = "{1: 'TKT-6'}"
    parsed, errors = parse_json(text)
    assert parsed is None
    assert errors
    assert errors[0].code == "unsafe_single_quotes"


def test_parse_json_strict_rejects_markdown() -> None:
    text = "```json\n{\"ticket_id\": \"TKT-7\"}\n```"
    parsed, errors = parse_json(text, strict=True)
    assert parsed is None
    assert errors


def test_parse_json_strict_rejects_trailing_text() -> None:
    text = "Here: {\"ticket_id\": \"TKT-8\"} Thanks"
    parsed, errors = parse_json(text, strict=True)
    assert parsed is None
    assert errors


def test_parse_json_strict_rejects_single_quotes() -> None:
    text = "{'ticket_id': 'TKT-9'}"
    parsed, errors = parse_json(text, strict=True)
    assert parsed is None
    assert errors


def test_parse_json_strict_rejects_trailing_commas() -> None:
    text = "{\"ticket_id\": \"TKT-10\",}"
    parsed, errors = parse_json(text, strict=True)
    assert parsed is None
    assert errors


def test_map_payload_without_coercion_flags_errors() -> None:
    payload = {
        "ticket_id": 123,
        "customer_id": "CUST-1",
        "created_at": "2024-01-01T00:00:00Z",
        "language": "en",
        "summary": "Summary",
        "category": "account",
        "priority": "low",
        "entities": "not-a-list",
        "actions": [],
    }
    _, errors = map_payload(payload, allow_coercion=False)
    assert errors
    assert any(error.code == "invalid_type" for error in errors)


def test_coerce_string_disabled_returns_none_and_error() -> None:
    errors: list[TransformError] = []
    value = 123
    result = coerce_string(value, "ticket_id", errors, allow_coercion=False)
    assert result is None
    assert errors
    assert errors[0].code == "invalid_type"


def test_coerce_list_disabled_returns_empty_and_error() -> None:
    errors: list[TransformError] = []
    value = "not-a-list"
    result = coerce_list(value, "entities", errors, allow_coercion=False)
    assert result == []
    assert errors
    assert errors[0].code == "invalid_type"


def test_coerce_list_from_single_item() -> None:
    errors: list[TransformError] = []
    value = {"action": "triage"}
    result = coerce_list(value, "actions", errors)

    assert result == [value]
    assert errors
    assert errors[0].code == "coerce_list"


def test_coerce_enum_passes_through_canonical_value() -> None:
    errors: list[TransformError] = []
    result = coerce_enum(
        "urgent", PRIORITY_VALID, PRIORITY_SYNONYMS, "priority", errors,
    )
    assert result == "urgent"
    assert errors == []


def test_coerce_enum_normalizes_casing_when_allowed() -> None:
    errors: list[TransformError] = []
    result = coerce_enum(
        "URGENT", PRIORITY_VALID, PRIORITY_SYNONYMS, "priority", errors,
    )
    assert result == "urgent"
    assert errors and errors[0].code == "coerce_enum"
    assert errors[0].severity == "warning"


def test_coerce_enum_maps_priority_synonym_when_allowed() -> None:
    errors: list[TransformError] = []
    result = coerce_enum(
        "critical", PRIORITY_VALID, PRIORITY_SYNONYMS, "priority", errors,
    )
    assert result == "urgent"
    assert errors and errors[0].code == "coerce_enum"
    assert errors[0].severity == "warning"


def test_coerce_enum_disabled_passes_value_through_unchanged() -> None:
    errors: list[TransformError] = []
    result = coerce_enum(
        "critical",
        PRIORITY_VALID,
        PRIORITY_SYNONYMS,
        "priority",
        errors,
        allow_coercion=False,
    )
    # Schema validation is the source of truth when coercion is off.
    assert result == "critical"
    assert errors == []


def test_coerce_enum_unknown_value_passes_through_for_schema_to_reject() -> None:
    errors: list[TransformError] = []
    result = coerce_enum(
        "totally-made-up",
        PRIORITY_VALID,
        PRIORITY_SYNONYMS,
        "priority",
        errors,
    )
    assert result == "totally-made-up"
    assert errors == []


def test_coerce_enum_maps_category_synonym() -> None:
    errors: list[TransformError] = []
    result = coerce_enum(
        "Tech Support",
        CATEGORY_VALID,
        CATEGORY_SYNONYMS,
        "category",
        errors,
    )
    assert result == "technical"
    assert errors and errors[0].code == "coerce_enum"


def test_coerce_enum_handles_none_and_non_string() -> None:
    errors: list[TransformError] = []
    assert coerce_enum(None, PRIORITY_VALID, PRIORITY_SYNONYMS, "p", errors) is None
    assert coerce_enum(7, PRIORITY_VALID, PRIORITY_SYNONYMS, "p", errors) == 7
    assert errors == []


def test_map_payload_coerces_priority_synonym_when_enabled() -> None:
    payload = {
        "ticket_id": "TKT-1",
        "customer_id": "CUST-1",
        "created_at": "2025-01-01T00:00:00+00:00",
        "language": "en",
        "summary": "x",
        "category": "billing",
        "priority": "critical",
        "entities": [],
        "actions": [
            {
                "action": "triage",
                "owner": "AG-1",
                "due_at": "2025-01-02T00:00:00+00:00",
            }
        ],
    }

    mapped, errors = map_payload(payload, allow_coercion=True)
    assert mapped["priority"] == "urgent"
    assert any(error.code == "coerce_enum" for error in errors)


def test_strip_unexpected_fields_removes_unknown_top_level_keys() -> None:
    errors: list[TransformError] = []
    parsed = {
        "ticket_id": "TKT-1",
        "summary": "x",
        "hallucinated": {"note": "extra"},
        "another_extra": 42,
    }

    result = strip_unexpected_fields(parsed, ALLOWED_FIELDS, errors)

    assert "hallucinated" not in result
    assert "another_extra" not in result
    assert result["ticket_id"] == "TKT-1"
    assert result["summary"] == "x"
    # Original parsed dict is not mutated.
    assert "hallucinated" in parsed
    assert len(errors) == 2
    codes = {e.code for e in errors}
    field_paths = {e.field_path for e in errors}
    assert codes == {"strip_unexpected_field"}
    assert field_paths == {"another_extra", "hallucinated"}
    assert all(e.severity == "warning" for e in errors)


def test_strip_unexpected_fields_returns_unchanged_when_all_known() -> None:
    errors: list[TransformError] = []
    parsed = {"ticket_id": "TKT-1", "summary": "x", "category": "billing"}

    result = strip_unexpected_fields(parsed, ALLOWED_FIELDS, errors)

    assert result is parsed  # no rebuild needed
    assert errors == []


def test_strip_unexpected_fields_disabled_passes_through_for_contract_to_reject() -> None:
    errors: list[TransformError] = []
    parsed = {"ticket_id": "TKT-1", "hallucinated": "extra"}

    result = strip_unexpected_fields(
        parsed, ALLOWED_FIELDS, errors, allow_coercion=False,
    )

    assert "hallucinated" in result
    assert errors == []


def test_strip_unexpected_fields_emits_one_warning_per_field() -> None:
    """Per-field warnings let cluster reports show which hallucinations dominate."""
    errors: list[TransformError] = []
    parsed = {"ticket_id": "TKT-1", "foo": 1, "bar": 2, "baz": 3}

    strip_unexpected_fields(parsed, ALLOWED_FIELDS, errors)

    field_paths = sorted(e.field_path for e in errors)
    assert field_paths == ["bar", "baz", "foo"]


def test_backfill_summary_uses_input_when_output_missing_summary() -> None:
    errors: list[TransformError] = []
    parsed = {"ticket_id": "TKT-1", "category": "billing"}
    input_record = {"ticket_id": "TKT-1", "summary": "Charged twice for order 9832"}

    result = backfill_required_summary(parsed, input_record, errors)

    assert result["summary"] == "Charged twice for order 9832"
    assert errors and errors[0].code == "backfill_summary"
    assert errors[0].severity == "warning"
    # Original parsed dict is not mutated.
    assert "summary" not in parsed


def test_backfill_summary_handles_empty_string_in_output() -> None:
    errors: list[TransformError] = []
    parsed = {"ticket_id": "TKT-1", "summary": "   "}
    input_record = {"ticket_id": "TKT-1", "summary": "real summary"}

    result = backfill_required_summary(parsed, input_record, errors)

    assert result["summary"] == "real summary"
    assert errors and errors[0].code == "backfill_summary"


def test_backfill_summary_leaves_valid_summary_alone() -> None:
    errors: list[TransformError] = []
    parsed = {"ticket_id": "TKT-1", "summary": "model produced this"}
    input_record = {"ticket_id": "TKT-1", "summary": "input had this"}

    result = backfill_required_summary(parsed, input_record, errors)

    assert result["summary"] == "model produced this"
    assert errors == []


def test_backfill_summary_disabled_does_not_backfill() -> None:
    errors: list[TransformError] = []
    parsed = {"ticket_id": "TKT-1"}
    input_record = {"ticket_id": "TKT-1", "summary": "real summary"}

    result = backfill_required_summary(
        parsed, input_record, errors, allow_coercion=False,
    )

    assert "summary" not in result
    assert errors == []


def test_backfill_summary_returns_unchanged_when_input_missing() -> None:
    errors: list[TransformError] = []
    parsed = {"ticket_id": "TKT-1"}

    result = backfill_required_summary(parsed, None, errors)

    assert "summary" not in result
    assert errors == []


def test_backfill_summary_returns_unchanged_when_input_summary_empty() -> None:
    errors: list[TransformError] = []
    parsed = {"ticket_id": "TKT-1"}
    input_record = {"ticket_id": "TKT-1", "summary": ""}

    result = backfill_required_summary(parsed, input_record, errors)

    assert "summary" not in result
    assert errors == []


def test_map_payload_leaves_priority_synonym_alone_when_disabled() -> None:
    payload = {
        "ticket_id": "TKT-1",
        "customer_id": "CUST-1",
        "created_at": "2025-01-01T00:00:00+00:00",
        "language": "en",
        "summary": "x",
        "category": "billing",
        "priority": "critical",
        "entities": [],
        "actions": [
            {
                "action": "triage",
                "owner": "AG-1",
                "due_at": "2025-01-02T00:00:00+00:00",
            }
        ],
    }

    mapped, errors = map_payload(payload, allow_coercion=False)
    assert mapped["priority"] == "critical"
    # No coercion warning was emitted.
    assert not any(error.code == "coerce_enum" for error in errors)
