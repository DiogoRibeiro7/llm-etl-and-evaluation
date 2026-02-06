"""Metric computations for LLM output evaluation."""

from __future__ import annotations

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
) -> float:
    if not gold:
        return 0.0

    correct = 0
    total = 0
    for record in records:
        ticket_id = str(record.get("ticket_id", ""))
        if ticket_id not in gold:
            continue
        expected = gold[ticket_id]
        for field, expected_value in expected.items():
            if field == "ticket_id":
                continue
            total += 1
            if record.get(field) == expected_value:
                correct += 1
    return correct / total if total else 0.0


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
    return dict(counter.most_common())


def compute_metrics(
    outputs_path: str, gold_path: str, schema: dict[str, Any]
) -> MetricResult:
    """Compute metrics for evaluation."""

    records = _load_jsonl(outputs_path)
    gold = _load_gold(gold_path)

    schema_validity_rate, schema_issues = _compute_schema_validity(records, schema)
    completeness_rate = _compute_completeness(records)
    field_accuracy = _compute_field_accuracy(records, gold)
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
        constraint_violations_per_record=constraint_violations,
        consistency_rate=consistency_rate,
        error_taxonomy=error_taxonomy,
        totals=totals,
    )
