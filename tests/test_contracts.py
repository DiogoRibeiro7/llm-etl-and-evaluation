"""Tests for typed data contracts."""

from __future__ import annotations

from llm_etl_eval.contracts import (
    parse_canonical_input_record,
    parse_llm_output_record,
    parse_target_system_record,
)


def _valid_payload() -> dict[str, object]:
    return {
        "ticket_id": "TKT-100",
        "customer_id": "CUST-1",
        "created_at": "2024-01-01T00:00:00Z",
        "language": "en",
        "summary": "Reset password request",
        "category": "account",
        "priority": "low",
        "entities": [{"type": "region", "value": "us", "confidence": 0.9}],
        "actions": [
            {
                "action": "triage",
                "owner": "system",
                "due_at": "2024-01-02T00:00:00Z",
                "status": "open",
            }
        ],
    }


def test_parse_canonical_input_record_ok() -> None:
    record, errors = parse_canonical_input_record(_valid_payload())
    assert errors == []
    assert record is not None
    assert record.ticket_id == "TKT-100"


def test_parse_llm_output_record_rejects_bad_entities() -> None:
    payload = _valid_payload()
    payload["entities"] = ["not-an-object"]
    record, errors = parse_llm_output_record(payload)
    assert record is None
    assert errors


def test_parse_llm_output_record_missing_field() -> None:
    payload = _valid_payload()
    payload.pop("priority")
    record, errors = parse_llm_output_record(payload)
    assert record is None
    assert errors


def test_parse_llm_output_record_rejects_non_string_key() -> None:
    payload = _valid_payload()
    payload["entities"] = [{"type": "region", "value": "us", "confidence": 0.5}]
    payload["actions"] = [
        {
            "action": "triage",
            "owner": "system",
            "due_at": "2024-01-02T00:00:00Z",
            "status": "open",
        }
    ]
    payload[1] = "bad-key"
    record, errors = parse_llm_output_record(payload)
    assert record is None
    assert errors


def test_parse_llm_output_record_rejects_wrong_types() -> None:
    payload = _valid_payload()
    payload["ticket_id"] = 123
    payload["entities"] = [{"type": "region", "value": "us", "confidence": "high"}]
    payload["actions"] = [{"action": "triage", "owner": "system", "due_at": 123}]
    record, errors = parse_llm_output_record(payload)
    assert record is None
    assert errors


def test_parse_llm_output_record_rejects_action_status_type() -> None:
    payload = _valid_payload()
    payload["actions"][0]["status"] = 1
    record, errors = parse_llm_output_record(payload)
    assert record is None
    assert errors


def test_parse_target_system_record_missing_field() -> None:
    payload = _valid_payload()
    payload.pop("priority")
    record, errors = parse_target_system_record(payload)
    assert record is None
    assert errors
