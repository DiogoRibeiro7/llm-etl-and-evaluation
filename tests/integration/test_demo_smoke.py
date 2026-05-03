"""End-to-end smoke test that mirrors the interview demo.

Runs the full pipeline (ETL -> simulator -> transform -> roundtrip -> eval
-> manifest -> clusters -> drift) for both baseline and improved configs
against the repo's own data fixtures. Asserts:

  - Each stage's expected artifacts exist.
  - Schema validity, completeness, and field accuracy meet sane floors.
  - Improved config matches or beats baseline on validity.
  - Manifest, drift, and cluster reports are structurally valid.

This is the regression net for everything we built: if the demo silently
breaks (a metric regresses, an artifact disappears, a CLI changes shape),
this test fails in CI.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from llm_etl_eval.checks.distribution_drift_run import main as drift_main
from llm_etl_eval.checks.roundtrip import roundtrip_accepteds
from llm_etl_eval.config import load_config
from llm_etl_eval.etl.run import run_pipeline
from llm_etl_eval.eval.error_clusters_run import main as cluster_main
from llm_etl_eval.eval.metrics import compute_metrics
from llm_etl_eval.manifest.builder import (
    ManifestInputs,
    build_manifest,
    write_manifest,
)
from llm_etl_eval.prompting.run import run_prompting
from llm_etl_eval.sim.llm_simulator import (
    SimulationConfig,
    load_inputs,
    simulate_records,
    write_outputs,
)
from llm_etl_eval.transform.run import run_transform

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = REPO_ROOT / "data" / "raw"
SCHEMA_PATH = REPO_ROOT / "data" / "expected" / "target_schema.json"
GOLD_PATH = REPO_ROOT / "data" / "gold" / "labels.jsonl"
BASELINE_CONFIG = REPO_ROOT / "configs" / "baseline.yaml"
IMPROVED_CONFIG = REPO_ROOT / "configs" / "improved.yaml"

ERROR_RATE = 0.35
SEED = 7


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def _run_full_pipeline(label: str, config_path: Path, work_dir: Path) -> dict[str, Path]:
    """Run every demo stage for one config; return artifact paths."""

    processed_dir = work_dir / "processed"
    llm_dir = work_dir / "llm"
    final_dir = work_dir / "final" / label
    api_dir = work_dir / "api" / label
    report_dir = work_dir / "reports" / label

    run_pipeline(DATA_RAW, processed_dir)
    inputs_path = processed_dir / "llm_inputs.jsonl"

    prompts_path = llm_dir / f"prompts_{label}.jsonl"
    run_prompting(inputs_path, prompts_path, SCHEMA_PATH, config_path)

    sim_config = SimulationConfig(error_rate=ERROR_RATE, seed=SEED)
    inputs = load_inputs(inputs_path)
    outputs_path = llm_dir / f"outputs_{label}.jsonl"
    write_outputs(simulate_records(inputs, sim_config), outputs_path)

    run_transform(SCHEMA_PATH, outputs_path, final_dir, config_path)

    accepted_path = final_dir / "accepted.jsonl"
    rejected_path = final_dir / "rejected.jsonl"
    api_path = api_dir / "payloads.jsonl"
    roundtrip_accepteds(accepted_path, SCHEMA_PATH, api_path)

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    metrics = compute_metrics(str(outputs_path), str(GOLD_PATH), schema)
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "report.json"
    from dataclasses import asdict
    report_path.write_text(
        json.dumps(asdict(metrics), indent=2, sort_keys=True),
        encoding="utf-8",
    )

    manifest = build_manifest(
        ManifestInputs(
            config_path=config_path,
            schema_path=SCHEMA_PATH,
            inputs_path=inputs_path,
            outputs_path=outputs_path,
            gold_path=GOLD_PATH,
            prompts_path=prompts_path,
            seed=SEED,
            error_rate=ERROR_RATE,
            run_id=f"smoke-{label}",
            label=label,
        ),
        cwd=REPO_ROOT,
    )
    manifest_path = report_dir / "manifest.json"
    write_manifest(manifest, manifest_path)

    cluster_path = report_dir / "clusters.json"
    cluster_main(["--rejected", str(rejected_path), "--out", str(cluster_path)])

    return {
        "inputs": inputs_path,
        "prompts": prompts_path,
        "outputs": outputs_path,
        "accepted": accepted_path,
        "rejected": rejected_path,
        "api": api_path,
        "report": report_path,
        "manifest": manifest_path,
        "clusters": cluster_path,
    }


def test_demo_pipeline_smoke(tmp_path: Path) -> None:
    baseline_artifacts = _run_full_pipeline("baseline", BASELINE_CONFIG, tmp_path)
    improved_artifacts = _run_full_pipeline("improved", IMPROVED_CONFIG, tmp_path)

    # Every artifact exists and is non-empty.
    for label, artifacts in [("baseline", baseline_artifacts), ("improved", improved_artifacts)]:
        for name, path in artifacts.items():
            assert path.exists(), f"{label}/{name} missing at {path}"
            assert path.stat().st_size > 0, f"{label}/{name} is empty at {path}"

    # Pipeline configs we shipped should each meet sane metric floors.
    baseline_report = json.loads(baseline_artifacts["report"].read_text(encoding="utf-8"))
    improved_report = json.loads(improved_artifacts["report"].read_text(encoding="utf-8"))

    for report in (baseline_report, improved_report):
        assert report["totals"]["records"] >= 50
        assert report["totals"]["gold_records"] >= 50
        assert report["schema_validity_rate"] >= 0.60
        assert report["completeness_rate"] >= 0.95
        assert report["field_accuracy"] >= 0.85

    # Improved config should not regress validity.
    assert improved_report["schema_validity_rate"] >= baseline_report["schema_validity_rate"]

    # Manifests carry the run identity and the right shape.
    baseline_manifest = json.loads(baseline_artifacts["manifest"].read_text(encoding="utf-8"))
    assert baseline_manifest["label"] == "baseline"
    assert baseline_manifest["simulator"] == {"seed": SEED, "error_rate": ERROR_RATE}
    assert baseline_manifest["config"]["sha256"]
    assert baseline_manifest["schema"]["sha256"]
    assert baseline_manifest["outputs"]["records"] > 0

    # Cluster reports are structurally valid.
    baseline_clusters = json.loads(baseline_artifacts["clusters"].read_text(encoding="utf-8"))
    assert "totals" in baseline_clusters and "clusters" in baseline_clusters
    for cluster in baseline_clusters["clusters"]:
        assert cluster["count"] >= 1
        assert cluster["affected_records"] >= 1
        assert cluster["remediation"]

    # Drift check: improved vs baseline outputs across our three semantic fields.
    drift_path = tmp_path / "reports" / "improved" / "drift.json"
    exit_code = drift_main(
        [
            "--reference", str(baseline_artifacts["outputs"]),
            "--candidate", str(improved_artifacts["outputs"]),
            "--fields", "category", "priority", "language",
            "--out", str(drift_path),
        ]
    )
    assert exit_code == 0
    assert drift_path.exists()

    drift_report = json.loads(drift_path.read_text(encoding="utf-8"))
    assert "fields" in drift_report and "ok" in drift_report
    field_names = {field["field_name"] for field in drift_report["fields"]}
    assert field_names == {"category", "priority", "language"}
    for field_drift in drift_report["fields"]:
        assert "psi" in field_drift and "jsd" in field_drift
        assert field_drift["severity"] in {"stable", "moderate", "significant", "no_data"}


def test_baseline_config_loads_and_matches_yaml() -> None:
    config = load_config(BASELINE_CONFIG)
    assert config.coercion_enabled is False
    assert config.prompt_strictness == "minimal"
    assert config.schema_reminders is False


def test_improved_config_loads_and_matches_yaml() -> None:
    config = load_config(IMPROVED_CONFIG)
    assert config.coercion_enabled is True
    assert config.prompt_strictness == "strict"
    assert config.schema_reminders is True
