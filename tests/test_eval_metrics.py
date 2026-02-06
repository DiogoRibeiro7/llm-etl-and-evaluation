"""Tests for evaluation metrics."""

from __future__ import annotations

import json
from pathlib import Path

from llm_etl_eval.eval.metrics import compute_metrics


def _write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")


def test_metrics_basic(tmp_path: Path) -> None:
    outputs = [
        {
            "ticket_id": "TKT-1",
            "customer_id": "C-1",
            "created_at": "2025-11-10T14:30:00+00:00",
            "language": "en",
            "summary": "Good summary",
            "category": "billing",
            "priority": "high",
            "entities": [],
            "actions": [{"action": "triage", "owner": "AG-1", "due_at": "2025-11-11T00:00:00+00:00"}],
        },
        {
            "ticket_id": "TKT-2",
            "customer_id": "C-2",
            "created_at": "2025-11-10T14:30:00+00:00",
            "language": "en",
            "summary": "",
            "category": "invalid",
            "priority": "critical",
            "entities": [{"type": "region", "value": "EU", "confidence": 2}],
            "actions": [],
        },
    ]

    gold = [
        {"ticket_id": "TKT-1", "category": "billing", "priority": "high"},
        {"ticket_id": "TKT-2", "category": "account", "priority": "low"},
    ]

    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
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
            "created_at": {"type": "string"},
            "language": {"type": "string"},
            "summary": {"type": "string"},
            "category": {"type": "string", "enum": ["billing", "account"]},
            "priority": {"type": "string", "enum": ["low", "high"]},
            "entities": {"type": "array"},
            "actions": {"type": "array", "minItems": 1},
        },
    }

    outputs_path = tmp_path / "outputs.jsonl"
    gold_path = tmp_path / "gold.jsonl"

    _write_jsonl(outputs_path, outputs)
    _write_jsonl(gold_path, gold)

    result = compute_metrics(str(outputs_path), str(gold_path), schema)

    assert result.totals["records"] == 2
    assert result.schema_validity_rate == 0.5
    assert result.completeness_rate < 1.0
    assert result.field_accuracy == 0.25
    assert result.constraint_violations_per_record > 0
