"""Integration test for end-to-end pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from llm_etl_eval.etl.run import run_pipeline
from llm_etl_eval.eval.metrics import compute_metrics
from llm_etl_eval.eval.report import write_report_json, write_report_md
from llm_etl_eval.sim.llm_simulator import SimulationConfig, load_inputs, simulate_records, write_outputs
from llm_etl_eval.transform.run import run_transform


def _load_schema(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_end_to_end_pipeline(tmp_path: Path) -> None:
    raw_dir = Path("data/raw")
    processed_dir = tmp_path / "processed"
    llm_dir = tmp_path / "llm"
    final_dir = tmp_path / "final"
    report_dir = tmp_path / "reports"

    run_pipeline(raw_dir, processed_dir)

    inputs = load_inputs(processed_dir / "llm_inputs.jsonl")
    results = simulate_records(inputs, SimulationConfig(error_rate=0.0, seed=123))
    write_outputs(results, llm_dir / "outputs.jsonl")

    schema = _load_schema(Path("data/expected/target_schema.json"))
    run_transform(
        Path("data/expected/target_schema.json"),
        llm_dir / "outputs.jsonl",
        final_dir,
    )

    metrics = compute_metrics(
        str(llm_dir / "outputs.jsonl"),
        str(Path("data/gold/labels.jsonl")),
        schema,
    )

    write_report_json(metrics, report_dir / "report.json")
    write_report_md(metrics, report_dir / "report.md")

    assert (final_dir / "accepted.jsonl").exists()
    assert (report_dir / "report.json").exists()
