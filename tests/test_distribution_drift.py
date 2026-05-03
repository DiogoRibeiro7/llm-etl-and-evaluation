"""Tests for the distribution drift module."""

from __future__ import annotations

import json
from pathlib import Path

from llm_etl_eval.checks.distribution_drift import (
    categorical_counts,
    compute_drift,
    jsd,
    psi,
)
from llm_etl_eval.checks.distribution_drift_run import main as drift_main


def _records(values: list[str], field: str = "category") -> list[dict[str, object]]:
    return [{field: value} for value in values]


def _write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")


def test_categorical_counts_ignores_empty_and_non_string() -> None:
    records: list[dict[str, object]] = [
        {"category": "billing"},
        {"category": "  "},
        {"category": None},
        {"category": 42},
        {"category": "billing"},
        {"category": "account"},
    ]
    counts, total = categorical_counts(records, "category")
    assert total == 3
    assert counts == {"billing": 2, "account": 1}


def test_psi_and_jsd_are_zero_for_identical_distributions() -> None:
    distribution = {"a": 0.5, "b": 0.5}
    assert psi(distribution, distribution) == 0.0
    assert jsd(distribution, distribution) == 0.0


def test_jsd_disjoint_supports_approaches_one() -> None:
    p = {"a": 0.999999, "b": 0.000001}
    q = {"a": 0.000001, "b": 0.999999}
    assert jsd(p, q) > 0.95


def test_psi_known_small_example() -> None:
    import math

    p = {"a": 0.5, "b": 0.5}
    q = {"a": 0.7, "b": 0.3}
    expected = (0.7 - 0.5) * math.log(0.7 / 0.5) + (0.3 - 0.5) * math.log(0.3 / 0.5)
    assert abs(psi(p, q) - expected) < 1e-12


def test_compute_drift_stable_when_distributions_match() -> None:
    reference = _records(["billing", "billing", "account", "technical"])
    candidate = _records(["billing", "billing", "account", "technical"])

    report = compute_drift(reference, candidate, ["category"])

    assert report.ok is True
    assert len(report.fields) == 1
    drift = report.fields[0]
    assert drift.severity == "stable"
    assert drift.reference_n == 4
    assert drift.candidate_n == 4
    assert drift.psi < 1e-9
    assert drift.jsd < 1e-9
    assert drift.breaches == []


def test_compute_drift_flags_significant_shift() -> None:
    reference = _records(["billing"] * 50 + ["account"] * 50)
    candidate = _records(["billing"] * 5 + ["account"] * 95)

    report = compute_drift(
        reference,
        candidate,
        ["category"],
        psi_threshold=0.25,
        jsd_threshold=0.10,
    )

    assert report.ok is False
    drift = report.fields[0]
    assert drift.severity == "significant"
    assert drift.psi > 0.25
    assert drift.breaches  # at least one breach reported


def test_compute_drift_handles_unseen_category_via_smoothing() -> None:
    reference = _records(["billing", "account"])
    candidate = _records(["security"])

    report = compute_drift(reference, candidate, ["category"])

    drift = report.fields[0]
    assert "billing" in drift.candidate
    assert "security" in drift.reference
    assert drift.psi > 0


def test_compute_drift_marks_no_data_when_field_missing() -> None:
    reference = _records(["billing"])
    candidate: list[dict[str, str]] = [{"other": "x"}]

    report = compute_drift(reference, candidate, ["category"])

    assert report.ok is False
    drift = report.fields[0]
    assert drift.severity == "no_data"
    assert drift.candidate_n == 0
    assert "no_data" in drift.breaches


def test_compute_drift_handles_multiple_fields() -> None:
    reference = [
        {"category": "billing", "priority": "low", "language": "en"},
        {"category": "account", "priority": "high", "language": "en"},
    ]
    candidate = [
        {"category": "billing", "priority": "low", "language": "en"},
        {"category": "account", "priority": "high", "language": "es"},
    ]

    report = compute_drift(reference, candidate, ["category", "priority", "language"])

    field_names = [field.field_name for field in report.fields]
    assert field_names == ["category", "priority", "language"]


def test_drift_cli_writes_report_and_returns_zero(tmp_path: Path) -> None:
    reference_path = tmp_path / "reference.jsonl"
    candidate_path = tmp_path / "candidate.jsonl"
    out_path = tmp_path / "drift.json"

    _write_jsonl(reference_path, _records(["billing", "account"]))
    _write_jsonl(candidate_path, _records(["billing", "account"]))

    exit_code = drift_main(
        [
            "--reference",
            str(reference_path),
            "--candidate",
            str(candidate_path),
            "--fields",
            "category",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    report = json.loads(out_path.read_text(encoding="utf-8"))
    assert report["ok"] is True
    assert report["fields"][0]["field_name"] == "category"


def test_drift_cli_returns_nonzero_with_fail_flag_on_breach(tmp_path: Path) -> None:
    reference_path = tmp_path / "reference.jsonl"
    candidate_path = tmp_path / "candidate.jsonl"
    out_path = tmp_path / "drift.json"

    _write_jsonl(reference_path, _records(["billing"] * 100))
    _write_jsonl(candidate_path, _records(["account"] * 100))

    exit_code = drift_main(
        [
            "--reference",
            str(reference_path),
            "--candidate",
            str(candidate_path),
            "--fields",
            "category",
            "--out",
            str(out_path),
            "--fail-on-drift",
        ]
    )

    assert exit_code == 1
    report = json.loads(out_path.read_text(encoding="utf-8"))
    assert report["ok"] is False


def test_drift_cli_breach_without_fail_flag_returns_zero(tmp_path: Path) -> None:
    reference_path = tmp_path / "reference.jsonl"
    candidate_path = tmp_path / "candidate.jsonl"
    out_path = tmp_path / "drift.json"

    _write_jsonl(reference_path, _records(["billing"] * 100))
    _write_jsonl(candidate_path, _records(["account"] * 100))

    exit_code = drift_main(
        [
            "--reference",
            str(reference_path),
            "--candidate",
            str(candidate_path),
            "--fields",
            "category",
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    report = json.loads(out_path.read_text(encoding="utf-8"))
    assert report["ok"] is False
