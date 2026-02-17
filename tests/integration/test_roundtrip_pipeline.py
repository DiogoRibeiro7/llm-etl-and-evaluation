"""Integration-like test for full pipeline round-trip."""

from __future__ import annotations

from pathlib import Path

from llm_etl_eval.checks.roundtrip import roundtrip_accepteds
from llm_etl_eval.etl.run import run_pipeline
from llm_etl_eval.sim.llm_simulator import SimulationConfig, load_inputs, simulate_records, write_outputs
from llm_etl_eval.transform.run import run_transform


def test_pipeline_roundtrip(tmp_path: Path) -> None:
    raw_dir = Path("data/raw")
    processed_dir = tmp_path / "processed"
    llm_dir = tmp_path / "llm"
    final_dir = tmp_path / "final"
    api_dir = tmp_path / "api"

    run_pipeline(raw_dir, processed_dir)

    inputs = load_inputs(processed_dir / "llm_inputs.jsonl")
    results = simulate_records(inputs, SimulationConfig(error_rate=0.0, seed=42))
    write_outputs(results, llm_dir / "outputs.jsonl")

    schema_path = Path("data/expected/target_schema.json")
    run_transform(schema_path, llm_dir / "outputs.jsonl", final_dir)

    api_payloads = roundtrip_accepteds(
        final_dir / "accepted.jsonl", schema_path, api_dir / "payloads.jsonl"
    )

    assert api_payloads
    assert (api_dir / "payloads.jsonl").exists()
