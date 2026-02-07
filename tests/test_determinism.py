"""Determinism tests for JSON output ordering."""

from __future__ import annotations

import json
from pathlib import Path

from llm_etl_eval.sim.llm_simulator import SimulationConfig, simulate_records, write_outputs


def test_simulator_write_outputs_deterministic(tmp_path: Path) -> None:
    record = {
        "b": 2,
        "a": 1,
        "ticket_id": "TKT-1",
        "entities": [],
        "actions": [],
    }
    results = simulate_records([record], SimulationConfig(error_rate=0.0, seed=1))

    out_path = tmp_path / "outputs.jsonl"
    write_outputs(results, out_path)

    line = out_path.read_text(encoding="utf-8").strip()
    assert line == json.dumps(record, sort_keys=True)


def test_simulator_seed_reproducible() -> None:
    record = {
        "ticket_id": "TKT-1",
        "customer_id": "C-1",
        "created_at": "2025-11-10T14:30:00+00:00",
        "language": "en",
        "summary": "Test",
        "category": "billing",
        "priority": "high",
        "entities": [],
        "actions": [{"action": "triage", "owner": "AG-1", "due_at": "2025-11-11T00:00:00+00:00"}],
    }
    records = [record, record]
    config = SimulationConfig(error_rate=0.5, seed=9)

    first = simulate_records(records, config)
    second = simulate_records(records, config)

    assert [result.mode for result in first] == [result.mode for result in second]
    assert [result.output for result in first] == [result.output for result in second]
