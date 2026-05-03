"""Cluster transformation rejections by (code, field_path).

The transform stage emits `rejected.jsonl` with structured `TransformError`
or `SchemaIssue` entries. The flat error_taxonomy in the eval report only
counts message strings; clustering by (code, field_path) gives a much
sharper "where do failures actually live" view, with sample messages and
remediation hints attached.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

REMEDIATIONS: dict[str, str] = {
    "invalid_json": "JSON parser failed. Raise prompt strictness or enable lenient parsing.",
    "invalid_type": "Wrong type for a field (or top-level non-object). Add a coercion rule or strengthen the schema reminder.",
    "unsafe_single_quotes": "Single-quoted output reached the parser. Reinforce JSON-format requirement in the prompt.",
    "required": "Required field omitted. Reinforce the required-fields list in the prompt.",
    "missing_required": "Required field omitted. Reinforce the required-fields list in the prompt.",
    "enum": "Value outside allowed set. Add an allowed-values reminder to the prompt.",
    "type": "Type mismatch. Add a coercion rule or strengthen the schema reminder.",
    "format": "Format violation (e.g., date-time). Show a format example in the prompt.",
    "minimum": "Value below allowed minimum. Add a range hint to the prompt.",
    "maximum": "Value above allowed maximum. Add a range hint to the prompt.",
    "minItems": "Array shorter than required. Reinforce non-empty-array instruction.",
    "maxItems": "Array longer than allowed. Add a length cap to the prompt.",
    "pattern": "Pattern mismatch. Show a matching example in the prompt.",
    "additionalProperties": "Unexpected fields. Add a do-not-include instruction or enable strict mode.",
}

DEFAULT_SAMPLES_PER_CLUSTER = 3
DEFAULT_VALUE_TRUNCATE_CHARS = 200


@dataclass(frozen=True)
class ErrorCluster:
    """A cluster of rejections sharing (code, field_path)."""

    code: str
    field_path: str | None
    count: int
    affected_records: int
    sample_messages: list[str] = field(default_factory=list)
    sample_raw_values: list[Any] = field(default_factory=list)
    remediation: str = ""


@dataclass(frozen=True)
class ClusterReport:
    """Top-level cluster report."""

    clusters: list[ErrorCluster]
    totals: dict[str, int]


def remediation_for(code: str) -> str:
    """Return a short remediation hint for a known error code."""

    return REMEDIATIONS.get(code, "Investigate sample messages and tighten prompt or coercion.")


def _truncate_value(value: Any, max_chars: int) -> Any:
    if isinstance(value, str) and len(value) > max_chars:
        return value[:max_chars] + "..."
    return value


def cluster_rejections(
    rejected: list[dict[str, Any]],
    *,
    samples_per_cluster: int = DEFAULT_SAMPLES_PER_CLUSTER,
    value_truncate_chars: int = DEFAULT_VALUE_TRUNCATE_CHARS,
) -> ClusterReport:
    """Group rejections by (code, field_path) with sample evidence."""

    counts: dict[tuple[str, str | None], int] = {}
    messages: dict[tuple[str, str | None], list[str]] = {}
    values: dict[tuple[str, str | None], list[Any]] = {}
    affected: dict[tuple[str, str | None], set[int]] = {}
    total_errors = 0

    for idx, record in enumerate(rejected):
        errors = record.get("errors")
        if not isinstance(errors, list):
            continue
        for err in errors:
            if not isinstance(err, dict):
                continue
            code = str(err.get("code", "unknown"))
            field_path_raw = err.get("field_path")
            field_path = str(field_path_raw) if field_path_raw is not None else None
            key = (code, field_path)

            counts[key] = counts.get(key, 0) + 1
            total_errors += 1
            affected.setdefault(key, set()).add(idx)

            message = err.get("message")
            if isinstance(message, str):
                bucket = messages.setdefault(key, [])
                if len(bucket) < samples_per_cluster and message not in bucket:
                    bucket.append(message)

            raw_value = err.get("raw_value")
            value_bucket = values.setdefault(key, [])
            if len(value_bucket) < samples_per_cluster:
                value_bucket.append(_truncate_value(raw_value, value_truncate_chars))

    clusters = [
        ErrorCluster(
            code=code,
            field_path=field_path,
            count=count,
            affected_records=len(affected[(code, field_path)]),
            sample_messages=list(messages.get((code, field_path), [])),
            sample_raw_values=list(values.get((code, field_path), [])),
            remediation=remediation_for(code),
        )
        for (code, field_path), count in counts.items()
    ]

    clusters.sort(key=lambda c: (-c.count, c.code, c.field_path or ""))

    totals = {
        "rejected_records": len(rejected),
        "total_errors": total_errors,
        "distinct_clusters": len(clusters),
    }

    return ClusterReport(clusters=clusters, totals=totals)
