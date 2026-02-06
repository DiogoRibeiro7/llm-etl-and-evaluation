"""Tests for tolerant JSON parsing and coercion rules."""

from __future__ import annotations

from llm_etl_eval.transform.coerce import coerce_list
from llm_etl_eval.transform.errors import TransformError
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


def test_coerce_list_from_single_item() -> None:
    errors: list[TransformError] = []
    value = {"action": "triage"}
    result = coerce_list(value, "actions", errors)

    assert result == [value]
    assert errors
    assert errors[0].code == "coerce_list"
