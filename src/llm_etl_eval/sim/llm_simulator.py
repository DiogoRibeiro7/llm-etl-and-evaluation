"""LLM output simulator with configurable error modes."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

ERROR_MODES = (
    "valid",
    "missing_required",
    "invalid_enum",
    "wrong_type",
    "extra_fields",
    "low_quality_summary",
)


@dataclass(frozen=True)
class SimulationConfig:
    """Configuration for simulated LLM output generation."""

    error_rate: float
    seed: int


@dataclass(frozen=True)
class SimulationResult:
    """Simulated output plus the applied error mode."""

    output: dict[str, Any]
    mode: str


def _choose_mode(rng: random.Random, error_rate: float) -> str:
    """Choose an error mode based on the error rate."""

    if rng.random() > error_rate:
        return "valid"
    return rng.choice([mode for mode in ERROR_MODES if mode != "valid"])


def _apply_missing_required(record: dict[str, Any]) -> dict[str, Any]:
    output = dict(record)
    output.pop("summary", None)
    return output


def _apply_invalid_enum(record: dict[str, Any]) -> dict[str, Any]:
    output = dict(record)
    output["priority"] = "critical"
    return output


def _apply_wrong_type(record: dict[str, Any]) -> dict[str, Any]:
    output = dict(record)
    output["entities"] = "not-a-list"
    return output


def _apply_extra_fields(record: dict[str, Any]) -> dict[str, Any]:
    output = dict(record)
    output["hallucinated"] = {"note": "extra field"}
    return output


def _apply_low_quality_summary(record: dict[str, Any]) -> dict[str, Any]:
    output = dict(record)
    output["summary"] = "N/A"
    return output


def simulate_output(record: dict[str, Any], mode: str) -> dict[str, Any]:
    """Return a simulated output record with the given error mode."""

    if mode == "valid":
        return dict(record)
    if mode == "missing_required":
        return _apply_missing_required(record)
    if mode == "invalid_enum":
        return _apply_invalid_enum(record)
    if mode == "wrong_type":
        return _apply_wrong_type(record)
    if mode == "extra_fields":
        return _apply_extra_fields(record)
    if mode == "low_quality_summary":
        return _apply_low_quality_summary(record)
    raise ValueError(f"Unknown mode: {mode}")


def simulate_records(
    records: Iterable[dict[str, Any]], config: SimulationConfig
) -> list[SimulationResult]:
    """Simulate outputs for each record."""

    rng = random.Random(config.seed)
    results: list[SimulationResult] = []

    for record in records:
        mode = _choose_mode(rng, config.error_rate)
        results.append(SimulationResult(output=simulate_output(record, mode), mode=mode))

    return results


def load_inputs(path: Path) -> list[dict[str, Any]]:
    """Load input records from JSONL."""

    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        records.append(json.loads(line))
    return records


def write_outputs(results: Iterable[SimulationResult], path: Path) -> None:
    """Write simulated outputs to JSONL (one record per line)."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(result.output, sort_keys=True) + "\n")
