"""Tests for the run manifest builder and CLI."""

from __future__ import annotations

import json
from pathlib import Path

from llm_etl_eval.manifest.builder import (
    ManifestInputs,
    build_manifest,
    file_descriptor,
    file_hash,
    git_info,
    write_manifest,
)
from llm_etl_eval.manifest.run import main as manifest_main


def _write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")


def test_file_hash_is_deterministic(tmp_path: Path) -> None:
    file_path = tmp_path / "data.txt"
    file_path.write_text("hello\n", encoding="utf-8")

    assert file_hash(file_path) == file_hash(file_path)
    assert len(file_hash(file_path)) == 64


def test_file_descriptor_for_jsonl_counts_records(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "outputs.jsonl"
    _write_jsonl(jsonl_path, [{"a": 1}, {"a": 2}, {"a": 3}])

    descriptor = file_descriptor(jsonl_path)

    assert descriptor is not None
    assert descriptor["exists"] is True
    assert descriptor["records"] == 3
    assert descriptor["size_bytes"] > 0
    assert len(descriptor["sha256"]) == 64


def test_file_descriptor_handles_none_and_missing(tmp_path: Path) -> None:
    assert file_descriptor(None) is None

    missing = tmp_path / "nope.jsonl"
    descriptor = file_descriptor(missing)

    assert descriptor == {"path": str(missing), "exists": False}


def test_git_info_returns_dict_in_non_repo(tmp_path: Path) -> None:
    info = git_info(cwd=tmp_path)

    assert set(info.keys()) == {"sha", "branch", "dirty"}


def test_build_manifest_includes_all_sections(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("coercion:\n  enabled: true\n", encoding="utf-8")

    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps({"type": "object"}), encoding="utf-8")

    outputs_path = tmp_path / "outputs.jsonl"
    _write_jsonl(outputs_path, [{"x": 1}])

    manifest = build_manifest(
        ManifestInputs(
            config_path=config_path,
            schema_path=schema_path,
            outputs_path=outputs_path,
            seed=7,
            error_rate=0.35,
            run_id="20260101T000000Z",
            label="baseline",
        ),
        cwd=tmp_path,
    )

    assert manifest["run_id"] == "20260101T000000Z"
    assert manifest["label"] == "baseline"
    assert manifest["simulator"] == {"seed": 7, "error_rate": 0.35}
    assert manifest["config"]["sha256"] == file_hash(config_path)
    assert manifest["schema"]["sha256"] == file_hash(schema_path)
    assert manifest["outputs"]["records"] == 1
    assert manifest["inputs"] is None
    assert manifest["gold"] is None
    assert "git" in manifest
    assert "created_at" in manifest


def test_build_manifest_defaults_run_id_to_timestamp(tmp_path: Path) -> None:
    manifest = build_manifest(ManifestInputs(), cwd=tmp_path)

    assert manifest["run_id"]
    assert manifest["run_id"].endswith("Z")
    assert len(manifest["run_id"]) == 16


def test_write_manifest_roundtrip(tmp_path: Path) -> None:
    manifest = build_manifest(
        ManifestInputs(seed=1, error_rate=0.1, run_id="r1"),
        cwd=tmp_path,
    )
    out_path = tmp_path / "nested" / "manifest.json"

    write_manifest(manifest, out_path)

    assert out_path.exists()
    loaded = json.loads(out_path.read_text(encoding="utf-8"))
    assert loaded["run_id"] == "r1"
    assert loaded["simulator"]["seed"] == 1


def test_cli_writes_manifest(tmp_path: Path) -> None:
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps({"type": "object"}), encoding="utf-8")

    out_path = tmp_path / "manifest.json"

    exit_code = manifest_main(
        [
            "--out",
            str(out_path),
            "--schema",
            str(schema_path),
            "--seed",
            "7",
            "--error-rate",
            "0.35",
            "--run-id",
            "fixed",
            "--label",
            "baseline",
        ]
    )

    assert exit_code == 0
    loaded = json.loads(out_path.read_text(encoding="utf-8"))
    assert loaded["run_id"] == "fixed"
    assert loaded["label"] == "baseline"
    assert loaded["schema"]["sha256"] == file_hash(schema_path)
    assert loaded["simulator"] == {"seed": 7, "error_rate": 0.35}
