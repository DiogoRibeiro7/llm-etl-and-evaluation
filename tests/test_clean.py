"""Tests for cleaning rules and timestamp parsing."""

from __future__ import annotations

from datetime import datetime, timezone

from llm_etl_eval.etl.clean import (
    normalize_category,
    normalize_language,
    normalize_priority,
    normalize_summary,
    parse_timestamp,
)


def test_parse_timestamp_iso_z() -> None:
    parsed = parse_timestamp("2025-11-13T07:20:00Z")
    assert parsed == datetime(2025, 11, 13, 7, 20, tzinfo=timezone.utc)


def test_parse_timestamp_slash_format() -> None:
    parsed = parse_timestamp("11/12/2025 09:15")
    assert parsed == datetime(2025, 11, 12, 9, 15, tzinfo=timezone.utc)


def test_normalize_category_synonym() -> None:
    assert normalize_category("Tech Support") == "technical"


def test_normalize_priority_synonym() -> None:
    assert normalize_priority("MED") == "medium"


def test_normalize_language() -> None:
    assert normalize_language("EN-US") == "en"


def test_normalize_summary_trim() -> None:
    assert normalize_summary("  Reset password issue  ") == "Reset password issue"
    assert normalize_summary("   ") is None
