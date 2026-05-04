"""Typed data contracts for pipeline boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ContractError:
    """Structured contract validation error."""

    code: str
    message: str
    field_path: str | None
    raw_value: Any | None


@dataclass(frozen=True)
class EntityRecord:
    """Entity extracted from the input."""

    type: str
    value: str
    confidence: float


@dataclass(frozen=True)
class ActionRecord:
    """Action item for downstream processing."""

    action: str
    owner: str
    due_at: str
    status: str | None = None


@dataclass(frozen=True)
class CanonicalInputRecord:
    """Canonical ETL output used as LLM input."""

    ticket_id: str
    customer_id: str
    created_at: str
    language: str
    summary: str
    category: str
    priority: str
    entities: list[EntityRecord]
    actions: list[ActionRecord]


@dataclass(frozen=True)
class LLMOutputRecord:
    """Expected LLM output payload structure."""

    ticket_id: str
    customer_id: str
    created_at: str
    language: str
    summary: str
    category: str
    priority: str
    entities: list[EntityRecord]
    actions: list[ActionRecord]


@dataclass(frozen=True)
class TargetSystemRecord:
    """Normalized record sent to the target system."""

    ticket_id: str
    customer_id: str
    created_at: str
    language: str
    summary: str
    category: str
    priority: str
    entities: list[EntityRecord]
    actions: list[ActionRecord]


ALLOWED_FIELDS: frozenset[str] = frozenset({
    "ticket_id",
    "customer_id",
    "created_at",
    "language",
    "summary",
    "category",
    "priority",
    "entities",
    "actions",
})

# Backwards-compat alias for internal callers still using the underscored name.
_ALLOWED_FIELDS = ALLOWED_FIELDS


def _add_error(
    errors: list[ContractError],
    code: str,
    message: str,
    field_path: str | None,
    raw_value: Any | None,
) -> None:
    errors.append(
        ContractError(
            code=code,
            message=message,
            field_path=field_path,
            raw_value=raw_value,
        )
    )


def _require_str(value: Any, field_path: str, errors: list[ContractError]) -> str | None:
    if isinstance(value, str):
        return value
    _add_error(errors, "invalid_type", "Expected string.", field_path, value)
    return None


def _require_number(value: Any, field_path: str, errors: list[ContractError]) -> float | None:
    if isinstance(value, bool):
        _add_error(errors, "invalid_type", "Expected number.", field_path, value)
        return None
    if isinstance(value, (int, float)):
        return float(value)
    _add_error(errors, "invalid_type", "Expected number.", field_path, value)
    return None


def _require_list(value: Any, field_path: str, errors: list[ContractError]) -> list[Any] | None:
    if isinstance(value, list):
        return value
    _add_error(errors, "invalid_type", "Expected list.", field_path, value)
    return None


def _parse_entity(value: Any, field_path: str, errors: list[ContractError]) -> EntityRecord | None:
    if not isinstance(value, dict):
        _add_error(errors, "invalid_type", "Entity must be an object.", field_path, value)
        return None

    entity_type = _require_str(value.get("type"), f"{field_path}.type", errors)
    entity_value = _require_str(value.get("value"), f"{field_path}.value", errors)
    confidence = _require_number(value.get("confidence"), f"{field_path}.confidence", errors)

    if entity_type is None or entity_value is None or confidence is None:
        return None

    return EntityRecord(type=entity_type, value=entity_value, confidence=confidence)


def _parse_action(value: Any, field_path: str, errors: list[ContractError]) -> ActionRecord | None:
    if not isinstance(value, dict):
        _add_error(errors, "invalid_type", "Action must be an object.", field_path, value)
        return None

    action = _require_str(value.get("action"), f"{field_path}.action", errors)
    owner = _require_str(value.get("owner"), f"{field_path}.owner", errors)
    due_at = _require_str(value.get("due_at"), f"{field_path}.due_at", errors)
    status_raw = value.get("status")
    status: str | None
    if status_raw is None:
        status = None
    elif isinstance(status_raw, str):
        status = status_raw
    else:
        _add_error(errors, "invalid_type", "Expected string.", f"{field_path}.status", status_raw)
        status = None

    if action is None or owner is None or due_at is None:
        return None

    return ActionRecord(action=action, owner=owner, due_at=due_at, status=status)


def _parse_entities(
    payload: dict[str, Any],
    errors: list[ContractError],
) -> list[EntityRecord] | None:
    raw_entities = _require_list(_require_field(payload, "entities", errors), "entities", errors)
    if raw_entities is None:
        return None

    parsed: list[EntityRecord] = []
    for index, item in enumerate(raw_entities):
        entity = _parse_entity(item, f"entities[{index}]", errors)
        if entity is None:
            return None
        parsed.append(entity)
    return parsed


def _parse_actions(
    payload: dict[str, Any],
    errors: list[ContractError],
) -> list[ActionRecord] | None:
    raw_actions = _require_list(_require_field(payload, "actions", errors), "actions", errors)
    if raw_actions is None:
        return None

    parsed: list[ActionRecord] = []
    for index, item in enumerate(raw_actions):
        action = _parse_action(item, f"actions[{index}]", errors)
        if action is None:
            return None
        parsed.append(action)
    return parsed


def _require_field(payload: dict[str, Any], field_path: str, errors: list[ContractError]) -> Any | None:
    if field_path not in payload:
        _add_error(errors, "missing_required", "Missing required field.", field_path, None)
        return None
    return payload.get(field_path)


def _parse_record(
    payload: dict[str, Any],
    errors: list[ContractError],
) -> tuple[
    str | None,
    str | None,
    str | None,
    str | None,
    str | None,
    str | None,
    str | None,
    list[EntityRecord] | None,
    list[ActionRecord] | None,
]:
    for key in payload.keys():
        if not isinstance(key, str):
            _add_error(errors, "invalid_key", "Record keys must be strings.", "<key>", key)
            continue
        if key not in _ALLOWED_FIELDS:
            _add_error(errors, "unexpected_field", "Unexpected field in record.", key, payload[key])

    ticket_id = _require_str(_require_field(payload, "ticket_id", errors), "ticket_id", errors)
    customer_id = _require_str(_require_field(payload, "customer_id", errors), "customer_id", errors)
    created_at = _require_str(_require_field(payload, "created_at", errors), "created_at", errors)
    language = _require_str(_require_field(payload, "language", errors), "language", errors)
    summary = _require_str(_require_field(payload, "summary", errors), "summary", errors)
    category = _require_str(_require_field(payload, "category", errors), "category", errors)
    priority = _require_str(_require_field(payload, "priority", errors), "priority", errors)
    entities = _parse_entities(payload, errors)
    actions = _parse_actions(payload, errors)

    return (
        ticket_id,
        customer_id,
        created_at,
        language,
        summary,
        category,
        priority,
        entities,
        actions,
    )


def parse_canonical_input_record(
    payload: dict[str, Any]
) -> tuple[CanonicalInputRecord | None, list[ContractError]]:
    errors: list[ContractError] = []
    if not isinstance(payload, dict):
        _add_error(errors, "invalid_type", "Expected object.", None, payload)
        return None, errors

    (
        ticket_id,
        customer_id,
        created_at,
        language,
        summary,
        category,
        priority,
        entities,
        actions,
    ) = _parse_record(payload, errors)

    if errors:
        return None, errors

    assert ticket_id is not None
    assert customer_id is not None
    assert created_at is not None
    assert language is not None
    assert summary is not None
    assert category is not None
    assert priority is not None
    assert entities is not None
    assert actions is not None

    return (
        CanonicalInputRecord(
            ticket_id=ticket_id,
            customer_id=customer_id,
            created_at=created_at,
            language=language,
            summary=summary,
            category=category,
            priority=priority,
            entities=entities,
            actions=actions,
        ),
        errors,
    )


def parse_llm_output_record(
    payload: dict[str, Any]
) -> tuple[LLMOutputRecord | None, list[ContractError]]:
    errors: list[ContractError] = []
    if not isinstance(payload, dict):
        _add_error(errors, "invalid_type", "Expected object.", None, payload)
        return None, errors

    (
        ticket_id,
        customer_id,
        created_at,
        language,
        summary,
        category,
        priority,
        entities,
        actions,
    ) = _parse_record(payload, errors)

    if errors:
        return None, errors

    assert ticket_id is not None
    assert customer_id is not None
    assert created_at is not None
    assert language is not None
    assert summary is not None
    assert category is not None
    assert priority is not None
    assert entities is not None
    assert actions is not None

    return (
        LLMOutputRecord(
            ticket_id=ticket_id,
            customer_id=customer_id,
            created_at=created_at,
            language=language,
            summary=summary,
            category=category,
            priority=priority,
            entities=entities,
            actions=actions,
        ),
        errors,
    )


def parse_target_system_record(
    payload: dict[str, Any]
) -> tuple[TargetSystemRecord | None, list[ContractError]]:
    errors: list[ContractError] = []
    if not isinstance(payload, dict):
        _add_error(errors, "invalid_type", "Expected object.", None, payload)
        return None, errors

    (
        ticket_id,
        customer_id,
        created_at,
        language,
        summary,
        category,
        priority,
        entities,
        actions,
    ) = _parse_record(payload, errors)

    if errors:
        return None, errors

    assert ticket_id is not None
    assert customer_id is not None
    assert created_at is not None
    assert language is not None
    assert summary is not None
    assert category is not None
    assert priority is not None
    assert entities is not None
    assert actions is not None

    return (
        TargetSystemRecord(
            ticket_id=ticket_id,
            customer_id=customer_id,
            created_at=created_at,
            language=language,
            summary=summary,
            category=category,
            priority=priority,
            entities=entities,
            actions=actions,
        ),
        errors,
    )
