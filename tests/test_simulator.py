"""Tests for deterministic simulator error modes."""

from __future__ import annotations

from llm_etl_eval.sim.llm_simulator import SimulationConfig, simulate_records


def _base_record() -> dict[str, object]:
    return {
        "ticket_id": "TKT-1000",
        "customer_id": "CUST-1",
        "created_at": "2025-11-10T14:30:00+00:00",
        "language": "en",
        "summary": "Charged twice for order 9832",
        "category": "billing",
        "priority": "high",
        "entities": [],
        "actions": [
            {
                "action": "triage",
                "owner": "AG-10",
                "due_at": "2025-11-11T14:30:00+00:00",
                "status": "open",
            }
        ],
    }


def test_simulator_modes_deterministic() -> None:
    records = [_base_record() for _ in range(12)]
    config = SimulationConfig(error_rate=1.0, seed=1)
    results = simulate_records(records, config)

    modes = [result.mode for result in results]
    assert modes == [
        "missing_required",
        "extra_fields",
        "extra_fields",
        "invalid_enum",
        "missing_required",
        "extra_fields",
        "missing_required",
        "wrong_type",
        "invalid_enum",
        "missing_required",
        "missing_required",
        "low_quality_summary",
    ]


def test_simulator_outputs_match_modes() -> None:
    records = [_base_record() for _ in range(12)]
    config = SimulationConfig(error_rate=1.0, seed=1)
    results = simulate_records(records, config)

    assert "summary" not in results[0].output
    assert "hallucinated" in results[1].output
    assert results[3].output["priority"] == "critical"
    assert isinstance(results[7].output["entities"], str)
    assert results[11].output["summary"] == "N/A"
