"""Tests for the rejection-clustering module."""

from __future__ import annotations

import json
from pathlib import Path

from llm_etl_eval.eval.error_clusters import (
    cluster_rejections,
    remediation_for,
)
from llm_etl_eval.eval.error_clusters_run import main as cluster_main


def _rejection(errors: list[dict[str, object]], record_id: str = "r1") -> dict[str, object]:
    return {"record": {"id": record_id}, "errors": errors}


def _write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")


def test_cluster_empty_input() -> None:
    report = cluster_rejections([])
    assert report.clusters == []
    assert report.totals == {
        "rejected_records": 0,
        "total_errors": 0,
        "distinct_clusters": 0,
    }


def test_cluster_groups_by_code_and_field_path() -> None:
    rejected = [
        _rejection([
            {"code": "enum", "field_path": "category", "message": "x", "raw_value": "bogus"},
        ]),
        _rejection([
            {"code": "enum", "field_path": "category", "message": "y", "raw_value": "other"},
        ]),
        _rejection([
            {"code": "required", "field_path": "summary", "message": "missing", "raw_value": None},
        ]),
    ]

    report = cluster_rejections(rejected)

    assert report.totals == {
        "rejected_records": 3,
        "total_errors": 3,
        "distinct_clusters": 2,
    }
    assert report.clusters[0].code == "enum"
    assert report.clusters[0].count == 2
    assert report.clusters[0].affected_records == 2
    assert report.clusters[0].field_path == "category"


def test_cluster_separates_same_code_different_fields() -> None:
    rejected = [
        _rejection([
            {"code": "type", "field_path": "summary", "message": "a", "raw_value": 1},
            {"code": "type", "field_path": "category", "message": "b", "raw_value": 2},
        ]),
    ]

    report = cluster_rejections(rejected)

    assert report.totals["distinct_clusters"] == 2
    paths = {cluster.field_path for cluster in report.clusters}
    assert paths == {"summary", "category"}


def test_cluster_dedups_sample_messages_and_caps_samples() -> None:
    rejected = [
        _rejection([
            {"code": "enum", "field_path": "category", "message": "msg-A", "raw_value": "v1"},
        ]),
        _rejection([
            {"code": "enum", "field_path": "category", "message": "msg-A", "raw_value": "v2"},
        ]),
        _rejection([
            {"code": "enum", "field_path": "category", "message": "msg-B", "raw_value": "v3"},
        ]),
        _rejection([
            {"code": "enum", "field_path": "category", "message": "msg-C", "raw_value": "v4"},
        ]),
        _rejection([
            {"code": "enum", "field_path": "category", "message": "msg-D", "raw_value": "v5"},
        ]),
    ]

    report = cluster_rejections(rejected, samples_per_cluster=3)

    cluster = report.clusters[0]
    assert cluster.count == 5
    assert cluster.affected_records == 5
    assert cluster.sample_messages == ["msg-A", "msg-B", "msg-C"]
    assert len(cluster.sample_raw_values) == 3


def test_cluster_truncates_long_raw_values() -> None:
    long_value = "x" * 1000
    rejected = [
        _rejection([
            {"code": "invalid_json", "field_path": None, "message": "bad", "raw_value": long_value},
        ]),
    ]

    report = cluster_rejections(rejected, value_truncate_chars=200)

    sample = report.clusters[0].sample_raw_values[0]
    assert isinstance(sample, str)
    assert len(sample) == 203  # 200 + "..."
    assert sample.endswith("...")


def test_cluster_handles_root_field_path() -> None:
    rejected = [
        _rejection([
            {"code": "invalid_json", "field_path": None, "message": "x", "raw_value": "bad"},
        ]),
    ]
    report = cluster_rejections(rejected)
    assert report.clusters[0].field_path is None


def test_cluster_sort_order_count_then_code_then_field() -> None:
    rejected = [
        _rejection([
            {"code": "type", "field_path": "summary", "message": "a", "raw_value": 1},
            {"code": "enum", "field_path": "category", "message": "b", "raw_value": 2},
            {"code": "enum", "field_path": "priority", "message": "c", "raw_value": 3},
        ]),
        _rejection([
            {"code": "enum", "field_path": "category", "message": "b", "raw_value": 4},
        ]),
    ]

    report = cluster_rejections(rejected)
    sorted_keys = [(c.count, c.code, c.field_path) for c in report.clusters]

    # category enum (count=2) should come before priority enum and summary type (count=1 each)
    assert sorted_keys[0] == (2, "enum", "category")
    # The two count=1 clusters should be sorted by code asc, then field
    assert sorted_keys[1][0] == 1
    assert sorted_keys[2][0] == 1
    assert sorted_keys[1][1] <= sorted_keys[2][1]


def test_cluster_attaches_remediation() -> None:
    rejected = [
        _rejection([
            {"code": "required", "field_path": "summary", "message": "x", "raw_value": None},
        ]),
        _rejection([
            {"code": "made_up_code", "field_path": "x", "message": "y", "raw_value": None},
        ]),
    ]

    report = cluster_rejections(rejected)
    by_code = {cluster.code: cluster for cluster in report.clusters}

    assert by_code["required"].remediation == remediation_for("required")
    assert by_code["made_up_code"].remediation == remediation_for("made_up_code")
    assert by_code["required"].remediation != by_code["made_up_code"].remediation


def test_cluster_skips_malformed_error_entries() -> None:
    rejected: list[dict[str, object]] = [
        {"errors": [None, "bad", {"code": "enum", "field_path": "category", "message": "ok"}]},
        {"errors": "not-a-list"},
        {},
    ]

    report = cluster_rejections(rejected)

    assert report.totals["total_errors"] == 1
    assert len(report.clusters) == 1
    assert report.clusters[0].code == "enum"


def test_cluster_cli_writes_report(tmp_path: Path) -> None:
    rejected_path = tmp_path / "rejected.jsonl"
    out_path = tmp_path / "clusters.json"

    _write_jsonl(rejected_path, [
        _rejection([
            {"code": "enum", "field_path": "category", "message": "x", "raw_value": "bogus"},
        ]),
        _rejection([
            {"code": "enum", "field_path": "category", "message": "y", "raw_value": "other"},
        ]),
    ])

    exit_code = cluster_main(
        [
            "--rejected", str(rejected_path),
            "--out", str(out_path),
        ]
    )

    assert exit_code == 0
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["totals"]["rejected_records"] == 2
    assert payload["clusters"][0]["code"] == "enum"
    assert payload["clusters"][0]["remediation"]


def test_cluster_cli_top_flag_truncates(tmp_path: Path) -> None:
    rejected_path = tmp_path / "rejected.jsonl"
    out_path = tmp_path / "clusters.json"

    _write_jsonl(rejected_path, [
        _rejection([{"code": "enum", "field_path": "a", "message": "x", "raw_value": 1}]),
        _rejection([{"code": "type", "field_path": "b", "message": "y", "raw_value": 2}]),
        _rejection([{"code": "required", "field_path": "c", "message": "z", "raw_value": None}]),
    ])

    exit_code = cluster_main(
        [
            "--rejected", str(rejected_path),
            "--out", str(out_path),
            "--top", "1",
        ]
    )

    assert exit_code == 0
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["totals"]["distinct_clusters"] == 3  # totals unchanged
    assert len(payload["clusters"]) == 1               # output truncated
