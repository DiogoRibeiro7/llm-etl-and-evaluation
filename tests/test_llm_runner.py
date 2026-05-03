"""Tests for the real-LLM runner using a fake provider."""

from __future__ import annotations

import json
from pathlib import Path

from llm_etl_eval.llm.provider import LLMResponse
from llm_etl_eval.llm.runner import run_llm
from llm_etl_eval.llm.telemetry import (
    aggregate_telemetry,
    cost_for,
    load_and_aggregate,
)


class FakeProvider:
    """Provider that replays a list of pre-canned responses in order."""

    name = "fake"

    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = list(responses)
        self._idx = 0
        self.calls: list[dict[str, str]] = []

    def complete(self, *, system: str, user: str) -> LLMResponse:
        self.calls.append({"system": system, "user": user})
        response = self._responses[self._idx]
        self._idx += 1
        return response


def _write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")


def test_run_llm_writes_outputs_and_telemetry(tmp_path: Path) -> None:
    inputs_path = tmp_path / "inputs.jsonl"
    prompts_path = tmp_path / "prompts.jsonl"
    outputs_path = tmp_path / "outputs.jsonl"
    telemetry_path = tmp_path / "telemetry.jsonl"

    _write_jsonl(inputs_path, [{"ticket_id": "T1"}, {"ticket_id": "T2"}])
    _write_jsonl(prompts_path, [
        {"system": "s1", "user": "u1"},
        {"system": "s2", "user": "u2"},
    ])

    provider = FakeProvider(
        responses=[
            LLMResponse(
                text='{"ticket_id": "T1", "category": "billing"}',
                input_tokens=100, output_tokens=20,
                latency_ms=500, model="claude-haiku-4-5",
            ),
            LLMResponse(
                text='{"ticket_id": "T2", "category": "account"}',
                input_tokens=120, output_tokens=22,
                latency_ms=600, model="claude-haiku-4-5",
            ),
        ]
    )

    run_llm(inputs_path, prompts_path, outputs_path, telemetry_path, provider)

    out_lines = outputs_path.read_text(encoding="utf-8").splitlines()
    tel_lines = telemetry_path.read_text(encoding="utf-8").splitlines()

    assert len(out_lines) == 2
    first = json.loads(out_lines[0])
    assert first["ticket_id"] == "T1"
    assert first["category"] == "billing"

    assert len(tel_lines) == 2
    tel0 = json.loads(tel_lines[0])
    assert tel0 == {
        "ticket_id": "T1",
        "latency_ms": 500,
        "input_tokens": 100,
        "output_tokens": 20,
        "model": "claude-haiku-4-5",
    }

    assert provider.calls[0] == {"system": "s1", "user": "u1"}
    assert provider.calls[1] == {"system": "s2", "user": "u2"}


def test_run_llm_caps_records_via_max_records(tmp_path: Path) -> None:
    inputs_path = tmp_path / "i.jsonl"
    prompts_path = tmp_path / "p.jsonl"
    outputs_path = tmp_path / "o.jsonl"
    telemetry_path = tmp_path / "t.jsonl"

    _write_jsonl(inputs_path, [{"ticket_id": f"T{i}"} for i in range(5)])
    _write_jsonl(prompts_path, [{"system": "s", "user": f"u{i}"} for i in range(5)])

    provider = FakeProvider(
        responses=[
            LLMResponse(text="{}", input_tokens=10, output_tokens=5,
                        latency_ms=100, model="m")
            for _ in range(2)
        ]
    )

    run_llm(
        inputs_path, prompts_path, outputs_path, telemetry_path,
        provider, max_records=2,
    )

    assert len(outputs_path.read_text(encoding="utf-8").splitlines()) == 2
    assert len(telemetry_path.read_text(encoding="utf-8").splitlines()) == 2


def test_run_llm_handles_unparseable_text(tmp_path: Path) -> None:
    inputs_path = tmp_path / "i.jsonl"
    prompts_path = tmp_path / "p.jsonl"
    outputs_path = tmp_path / "o.jsonl"
    telemetry_path = tmp_path / "t.jsonl"

    _write_jsonl(inputs_path, [{"ticket_id": "T1"}])
    _write_jsonl(prompts_path, [{"system": "s", "user": "u"}])

    provider = FakeProvider(
        responses=[
            LLMResponse(
                text="some\nrandom\ngarbage with newlines",
                input_tokens=10, output_tokens=5,
                latency_ms=100, model="m",
            )
        ]
    )

    run_llm(inputs_path, prompts_path, outputs_path, telemetry_path, provider)

    lines = outputs_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert "\n" not in lines[0]
    assert "garbage" in lines[0]


def test_run_llm_normalizes_valid_json_output(tmp_path: Path) -> None:
    inputs_path = tmp_path / "i.jsonl"
    prompts_path = tmp_path / "p.jsonl"
    _write_jsonl(inputs_path, [{"ticket_id": "T1"}])
    _write_jsonl(prompts_path, [{"system": "s", "user": "u"}])

    provider = FakeProvider(
        responses=[
            LLMResponse(
                text='  {\n  "ticket_id": "T1",\n  "category": "billing"\n}\n',
                input_tokens=10, output_tokens=5,
                latency_ms=100, model="m",
            )
        ]
    )

    out_path = tmp_path / "o.jsonl"
    run_llm(inputs_path, prompts_path, out_path, tmp_path / "t.jsonl", provider)

    line = out_path.read_text(encoding="utf-8").splitlines()[0]
    assert json.loads(line) == {"ticket_id": "T1", "category": "billing"}


def test_run_llm_raises_on_length_mismatch(tmp_path: Path) -> None:
    import pytest

    inputs_path = tmp_path / "i.jsonl"
    prompts_path = tmp_path / "p.jsonl"
    _write_jsonl(inputs_path, [{"ticket_id": "T1"}, {"ticket_id": "T2"}])
    _write_jsonl(prompts_path, [{"system": "s", "user": "u"}])

    provider = FakeProvider(responses=[])
    with pytest.raises(ValueError, match="Length mismatch"):
        run_llm(
            inputs_path, prompts_path,
            tmp_path / "o.jsonl", tmp_path / "t.jsonl", provider,
        )


def test_aggregate_telemetry_computes_p50_p95_cost() -> None:
    records = [
        {"ticket_id": "T1", "latency_ms": 100, "input_tokens": 1000,
         "output_tokens": 200, "model": "claude-haiku-4-5"},
        {"ticket_id": "T2", "latency_ms": 200, "input_tokens": 1500,
         "output_tokens": 300, "model": "claude-haiku-4-5"},
    ]
    summary = aggregate_telemetry(records)

    assert summary["total_records"] == 2
    assert summary["model"] == "claude-haiku-4-5"
    assert summary["tokens"]["input_total"] == 2500
    assert summary["tokens"]["output_total"] == 500
    # cost = (2500 / 1M * $1) + (500 / 1M * $5) = 0.0025 + 0.0025 = 0.005
    assert summary["cost_usd"]["total"] == 0.005
    assert summary["cost_usd"]["model_known"] is True
    assert summary["latency_ms"]["max"] == 200


def test_aggregate_telemetry_empty() -> None:
    assert aggregate_telemetry([]) == {"total_records": 0}


def test_aggregate_telemetry_unknown_model_marks_cost_as_unknown() -> None:
    records = [
        {"ticket_id": "T1", "latency_ms": 100, "input_tokens": 100,
         "output_tokens": 50, "model": "claude-future-99"}
    ]
    summary = aggregate_telemetry(records)

    assert summary["cost_usd"]["model_known"] is False
    assert summary["cost_usd"]["total"] == 0.0


def test_aggregate_telemetry_mixed_models() -> None:
    records = [
        {"ticket_id": "T1", "latency_ms": 100, "input_tokens": 100,
         "output_tokens": 50, "model": "claude-haiku-4-5"},
        {"ticket_id": "T2", "latency_ms": 200, "input_tokens": 100,
         "output_tokens": 50, "model": "claude-sonnet-4-6"},
    ]
    summary = aggregate_telemetry(records)
    assert summary["model"] == "(mixed)"
    assert summary["models"] == ["claude-haiku-4-5", "claude-sonnet-4-6"]
    assert summary["cost_usd"]["model_known"] is False


def test_cost_for_haiku_matches_pricing_map() -> None:
    cost = cost_for("claude-haiku-4-5", input_tokens=1_000_000, output_tokens=1_000_000)
    assert cost["input"] == 1.0
    assert cost["output"] == 5.0
    assert cost["total"] == 6.0
    assert cost["model_known"] is True


def test_load_and_aggregate_reads_jsonl(tmp_path: Path) -> None:
    telemetry_path = tmp_path / "telemetry.jsonl"
    _write_jsonl(telemetry_path, [
        {"ticket_id": "T1", "latency_ms": 100, "input_tokens": 100,
         "output_tokens": 50, "model": "claude-haiku-4-5"},
        {"ticket_id": "T2", "latency_ms": 200, "input_tokens": 200,
         "output_tokens": 100, "model": "claude-haiku-4-5"},
    ])

    summary = load_and_aggregate(telemetry_path)
    assert summary["total_records"] == 2
    assert summary["tokens"]["input_total"] == 300
