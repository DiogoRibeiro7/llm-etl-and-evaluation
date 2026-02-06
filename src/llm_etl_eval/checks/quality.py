"""Monitoring-style checks for data quality and outputs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from llm_etl_eval.eval.schema_validate import validate_schema


@dataclass(frozen=True)
class CheckResult:
    """Result of a monitoring check."""

    name: str
    ok: bool
    message: str


@dataclass(frozen=True)
class NullRateThresholds:
    """Thresholds for allowed null rates by field."""

    max_null_rate: dict[str, float]


@dataclass(frozen=True)
class DriftThreshold:
    """Threshold for category distribution drift."""

    max_abs_diff: float


@dataclass(frozen=True)
class TimestampSanity:
    """Sanity bounds for timestamps."""

    min_year: int
    max_future_days: int


@dataclass(frozen=True)
class OutputMonitoringThresholds:
    """Thresholds for output monitoring checks."""

    max_schema_validity_drop: float
    error_spike_ratio: float
    error_spike_min_increase: int


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if cleaned.endswith("Z"):
        cleaned = cleaned.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def check_null_rates(
    records: list[dict[str, Any]], thresholds: NullRateThresholds
) -> CheckResult:
    """Check null rate thresholds for required fields."""

    if not records:
        return CheckResult(
            name="null_rate",
            ok=False,
            message="No records to evaluate null rates.",
        )

    field_counts = {field: 0 for field in thresholds.max_null_rate}
    for record in records:
        for field in thresholds.max_null_rate:
            value = record.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                field_counts[field] += 1

    total = len(records)
    failures = []
    for field, max_rate in thresholds.max_null_rate.items():
        null_rate = field_counts[field] / total
        if null_rate > max_rate:
            failures.append(f"{field} null rate {null_rate:.2%} > {max_rate:.2%}")

    if failures:
        return CheckResult(name="null_rate", ok=False, message="; ".join(failures))
    return CheckResult(name="null_rate", ok=True, message="Null rates within thresholds.")


def check_category_drift(
    records: list[dict[str, Any]],
    baseline_distribution: dict[str, float],
    threshold: DriftThreshold,
) -> CheckResult:
    """Check drift between current and baseline category distributions."""

    if not records:
        return CheckResult(
            name="category_drift",
            ok=False,
            message="No records to evaluate category drift.",
        )

    counts: dict[str, int] = {}
    total = 0
    for record in records:
        category = record.get("category")
        if isinstance(category, str):
            counts[category] = counts.get(category, 0) + 1
            total += 1

    if total == 0:
        return CheckResult(
            name="category_drift",
            ok=False,
            message="No categories found in records.",
        )

    current = {key: value / total for key, value in counts.items()}

    failures = []
    for category, baseline_rate in baseline_distribution.items():
        current_rate = current.get(category, 0.0)
        diff = abs(current_rate - baseline_rate)
        if diff > threshold.max_abs_diff:
            failures.append(f"{category} drift {diff:.2%} > {threshold.max_abs_diff:.2%}")

    if failures:
        return CheckResult(name="category_drift", ok=False, message="; ".join(failures))
    return CheckResult(name="category_drift", ok=True, message="Category drift within thresholds.")


def check_timestamp_sanity(
    records: list[dict[str, Any]], threshold: TimestampSanity
) -> CheckResult:
    """Check timestamps are within a sane range."""

    now = datetime.now(timezone.utc)
    max_future = now + timedelta(days=threshold.max_future_days)

    failures = []
    for record in records:
        parsed = _parse_datetime(record.get("created_at"))
        if parsed is None:
            failures.append("Missing or invalid created_at")
            continue
        if parsed.year < threshold.min_year:
            failures.append(f"created_at year {parsed.year} < {threshold.min_year}")
        if parsed > max_future:
            failures.append("created_at is too far in the future")

    if failures:
        return CheckResult(name="timestamp_sanity", ok=False, message="; ".join(failures))
    return CheckResult(name="timestamp_sanity", ok=True, message="Timestamps within expected range.")


def check_schema_validity_drop(
    baseline_rate: float, current_rate: float, thresholds: OutputMonitoringThresholds
) -> CheckResult:
    """Alert if schema validity drops beyond threshold."""

    drop = baseline_rate - current_rate
    if drop > thresholds.max_schema_validity_drop:
        return CheckResult(
            name="schema_validity_drop",
            ok=False,
            message=f"Schema validity dropped by {drop:.2%} (> {thresholds.max_schema_validity_drop:.2%}).",
        )
    return CheckResult(
        name="schema_validity_drop",
        ok=True,
        message="Schema validity within acceptable range.",
    )


def check_error_spike(
    baseline: dict[str, int],
    current: dict[str, int],
    thresholds: OutputMonitoringThresholds,
) -> CheckResult:
    """Alert if any error code spikes beyond configured ratio."""

    spikes: list[str] = []
    for code, count in current.items():
        base = baseline.get(code, 0)
        if count >= base + thresholds.error_spike_min_increase:
            if base == 0 or count / max(base, 1) >= thresholds.error_spike_ratio:
                spikes.append(f"{code}: {base} -> {count}")

    if spikes:
        return CheckResult(name="error_spike", ok=False, message="; ".join(spikes))
    return CheckResult(name="error_spike", ok=True, message="No error spikes detected.")


def schema_validity_rate(records: list[dict[str, Any]], schema: dict[str, Any]) -> float:
    """Compute schema validity rate for records."""

    if not records:
        return 0.0
    valid = 0
    for record in records:
        if not validate_schema(record, schema):
            valid += 1
    return valid / len(records)
