"""Metric computations for LLM output evaluation."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from llm_etl_eval.eval.schema_validate import SchemaIssue, validate_schema

CATEGORY_ENUM = {"billing", "account", "technical", "security", "shipping", "product"}
PRIORITY_ENUM = {"low", "medium", "high", "urgent"}
STATUS_ENUM = {"open", "in_progress", "done"}

REQUIRED_FIELDS = [
    "ticket_id",
    "customer_id",
    "created_at",
    "language",
    "summary",
    "category",
    "priority",
    "entities",
    "actions",
]


@dataclass(frozen=True)
class MetricResult:
    """Computed metrics and supporting details."""

    schema_validity_rate: float
    completeness_rate: float
    field_accuracy: float
    field_accuracy_breakdown: dict[str, float]
    constraint_violations_per_record: float
    consistency_rate: float
    error_taxonomy: dict[str, int]
    totals: dict[str, int]


def _load_jsonl(path: str) -> list[dict[str, Any]]:
    """Load JSONL records from a file path."""

    records: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            records.append(__import__("json").loads(line))
    return records


def _load_gold(path: str) -> dict[str, dict[str, Any]]:
    """Load gold labels indexed by ticket_id."""

    gold: dict[str, dict[str, Any]] = {}
    for record in _load_jsonl(path):
        ticket_id = str(record.get("ticket_id", ""))
        if ticket_id:
            gold[ticket_id] = record
    return gold


def _is_non_empty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return len(value) > 0
    return True


def _compute_completeness(records: list[dict[str, Any]]) -> float:
    if not records:
        return 0.0
    total_fields = len(records) * len(REQUIRED_FIELDS)
    present = 0
    for record in records:
        for field in REQUIRED_FIELDS:
            if field in record and _is_non_empty(record[field]):
                present += 1
    return present / total_fields if total_fields else 0.0


def _compute_schema_validity(
    records: list[dict[str, Any]], schema: dict[str, Any]
) -> tuple[float, list[list[SchemaIssue]]]:
    if not records:
        return 0.0, []
    issues: list[list[SchemaIssue]] = []
    valid_count = 0
    for record in records:
        record_issues = validate_schema(record, schema)
        issues.append(record_issues)
        if not record_issues:
            valid_count += 1
    return valid_count / len(records), issues


def _compute_field_accuracy(
    records: list[dict[str, Any]], gold: dict[str, dict[str, Any]]
) -> tuple[float, dict[str, float]]:
    if not gold:
        return 0.0, {}

    fields = ["ticket_id", "customer_id", "category", "priority", "summary"]
    correct = {field: 0 for field in fields}
    total = {field: 0 for field in fields}

    for record in records:
        ticket_id = str(record.get("ticket_id", ""))
        if ticket_id not in gold:
            continue
        expected = gold[ticket_id]
        for field in fields:
            if field not in expected:
                continue
            expected_value = expected.get(field)
            total[field] += 1
            if field == "summary":
                if _summary_similarity(record.get(field), expected_value) >= 0.6:
                    correct[field] += 1
            else:
                if record.get(field) == expected_value:
                    correct[field] += 1

    total_count = sum(total.values())
    correct_count = sum(correct.values())
    overall = correct_count / total_count if total_count else 0.0
    breakdown = {
        field: (correct[field] / total[field] if total[field] else 0.0) for field in fields
    }
    return overall, breakdown


def _summary_similarity(value: Any, expected: Any) -> float:
    if not isinstance(value, str) or not isinstance(expected, str):
        return 0.0
    tokens_a = _tokenize(value)
    tokens_b = _tokenize(expected)
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a.intersection(tokens_b)
    union = tokens_a.union(tokens_b)
    return len(intersection) / len(union) if union else 0.0


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _compute_constraint_violations(records: list[dict[str, Any]]) -> float:
    if not records:
        return 0.0

    violations = 0
    for record in records:
        category = record.get("category")
        if category is not None and category not in CATEGORY_ENUM:
            violations += 1
        priority = record.get("priority")
        if priority is not None and priority not in PRIORITY_ENUM:
            violations += 1
        for entity in record.get("entities", []) or []:
            confidence = entity.get("confidence") if isinstance(entity, dict) else None
            if confidence is None or not (0 <= confidence <= 1):
                violations += 1
        for action in record.get("actions", []) or []:
            status = action.get("status") if isinstance(action, dict) else None
            if status is not None and status not in STATUS_ENUM:
                violations += 1
    return violations / len(records)


def _compute_consistency(records: list[dict[str, Any]]) -> float:
    """Compute consistency for repeated outputs with the same ticket_id."""

    by_ticket: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        ticket_id = str(record.get("ticket_id", ""))
        if ticket_id:
            by_ticket[ticket_id].append(record)

    if not by_ticket:
        return 0.0

    consistent = 0
    total = 0
    for ticket_id, versions in by_ticket.items():
        if len(versions) < 2:
            continue
        total += 1
        first = versions[0]
        if all(version == first for version in versions[1:]):
            consistent += 1

    return consistent / total if total else 1.0


def _build_error_taxonomy(schema_issues: list[list[SchemaIssue]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for record_issues in schema_issues:
        for issue in record_issues:
            counter[issue.message] += 1
    sorted_items = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    return dict(sorted_items)


def compute_metrics(
    outputs_path: str, gold_path: str, schema: dict[str, Any]
) -> MetricResult:
    """Compute metrics for evaluation."""

    records = _load_jsonl(outputs_path)
    gold = _load_gold(gold_path)

    schema_validity_rate, schema_issues = _compute_schema_validity(records, schema)
    completeness_rate = _compute_completeness(records)
    field_accuracy, field_accuracy_breakdown = _compute_field_accuracy(records, gold)
    constraint_violations = _compute_constraint_violations(records)
    consistency_rate = _compute_consistency(records)
    error_taxonomy = _build_error_taxonomy(schema_issues)

    totals = {
        "records": len(records),
        "gold_records": len(gold),
    }

    return MetricResult(
        schema_validity_rate=schema_validity_rate,
        completeness_rate=completeness_rate,
        field_accuracy=field_accuracy,
        field_accuracy_breakdown=field_accuracy_breakdown,
        constraint_violations_per_record=constraint_violations,
        consistency_rate=consistency_rate,
        error_taxonomy=error_taxonomy,
        totals=totals,
    )
