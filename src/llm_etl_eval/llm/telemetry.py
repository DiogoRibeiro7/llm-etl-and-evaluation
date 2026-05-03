"""Aggregate per-record LLM telemetry into latency + cost summaries."""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any

# Approximate Anthropic pricing in USD per 1M tokens.
# Source: https://www.anthropic.com/pricing — keep in sync when prices change.
PRICING_USD_PER_MTOK: dict[str, dict[str, float]] = {
    "claude-haiku-4-5": {"input": 1.0, "output": 5.0},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-opus-4-7": {"input": 15.0, "output": 75.0},
}


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = round(pct / 100 * (len(sorted_vals) - 1))
    idx = max(0, min(len(sorted_vals) - 1, idx))
    return float(sorted_vals[idx])


def cost_for(model: str, input_tokens: int, output_tokens: int) -> dict[str, Any]:
    """Compute USD cost for a model+token-count pair using the pricing map."""

    pricing = PRICING_USD_PER_MTOK.get(model)
    if pricing is None:
        return {"input": 0.0, "output": 0.0, "total": 0.0, "model_known": False}
    input_cost = pricing["input"] * (input_tokens / 1_000_000)
    output_cost = pricing["output"] * (output_tokens / 1_000_000)
    return {
        "input": round(input_cost, 6),
        "output": round(output_cost, 6),
        "total": round(input_cost + output_cost, 6),
        "model_known": True,
    }


def aggregate_telemetry(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate per-record telemetry into a single summary dict."""

    if not records:
        return {"total_records": 0}

    latencies = [float(r["latency_ms"]) for r in records]
    input_total = sum(int(r["input_tokens"]) for r in records)
    output_total = sum(int(r["output_tokens"]) for r in records)
    models = sorted({str(r["model"]) for r in records})
    primary_model = models[0] if len(models) == 1 else "(mixed)"

    return {
        "total_records": len(records),
        "model": primary_model,
        "models": models,
        "latency_ms": {
            "p50": _percentile(latencies, 50),
            "p95": _percentile(latencies, 95),
            "mean": round(statistics.mean(latencies), 2),
            "max": max(latencies),
        },
        "tokens": {
            "input_total": input_total,
            "output_total": output_total,
        },
        "cost_usd": cost_for(primary_model, input_total, output_total),
    }


def load_and_aggregate(telemetry_path: Path) -> dict[str, Any]:
    """Load a telemetry JSONL file and return its aggregated summary."""

    records: list[dict[str, Any]] = []
    for line in telemetry_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return aggregate_telemetry(records)
