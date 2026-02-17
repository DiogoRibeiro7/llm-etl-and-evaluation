"""Tests for LLM output contract enforcement in transform stage."""

from __future__ import annotations

import json
from pathlib import Path

from llm_etl_eval.transform.run import run_transform


def _write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


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


def test_transform_rejects_llm_output_missing_required(tmp_path: Path) -> None:
    payload = _valid_payload()
    payload.pop("priority")

    outputs_path = tmp_path / "llm" / "outputs.jsonl"
    _write_jsonl(outputs_path, [payload])

    out_dir = tmp_path / "final"
    schema_path = Path("data/expected/target_schema.json")
    run_transform(schema_path, outputs_path, out_dir)

    accepted = _read_jsonl(out_dir / "accepted.jsonl")
    rejected = _read_jsonl(out_dir / "rejected.jsonl")

    assert accepted == []
    assert len(rejected) == 1
    errors = rejected[0]["errors"]
    assert any(
        error["code"] == "missing_required" and error["field_path"] == "priority"
        for error in errors
    )


def test_transform_rejects_llm_output_wrong_entity_type(tmp_path: Path) -> None:
    payload = _valid_payload()
    payload["entities"] = [{"type": "region", "value": "us", "confidence": "high"}]

    outputs_path = tmp_path / "llm" / "outputs.jsonl"
    _write_jsonl(outputs_path, [payload])

    out_dir = tmp_path / "final"
    schema_path = Path("data/expected/target_schema.json")
    run_transform(schema_path, outputs_path, out_dir)

    rejected = _read_jsonl(out_dir / "rejected.jsonl")
    assert len(rejected) == 1
    errors = rejected[0]["errors"]
    assert any(
        error["code"] == "invalid_type" and error["field_path"] == "entities[0].confidence"
        for error in errors
    )
