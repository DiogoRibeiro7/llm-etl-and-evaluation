"""Map LLM output fields to the target system format."""

from __future__ import annotations

from typing import Any

from llm_etl_eval.transform.coerce import coerce_float, coerce_list, coerce_string
from llm_etl_eval.transform.errors import TransformError

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


def _validate_required(payload: dict[str, Any], errors: list[TransformError]) -> None:
    """Ensure required fields are present."""

    for field in REQUIRED_FIELDS:
        if field not in payload:
            errors.append(
                TransformError(
                    code="missing_required",
                    message=f"Missing required field: {field}",
                    field_path=field,
                    severity="error",
                    raw_value=None,
                )
            )


def _map_entities(value: Any, errors: list[TransformError]) -> list[dict[str, Any]]:
    entities = coerce_list(value, "entities", errors)
    mapped: list[dict[str, Any]] = []
    for idx, entity in enumerate(entities):
        if not isinstance(entity, dict):
            errors.append(
                TransformError(
                    code="invalid_entity",
                    message="Entity must be an object.",
                    field_path=f"entities[{idx}]",
                    severity="error",
                    raw_value=entity,
                )
            )
            continue

        mapped.append(
            {
                "type": coerce_string(entity.get("type"), f"entities[{idx}].type", errors) or "",
                "value": coerce_string(entity.get("value"), f"entities[{idx}].value", errors) or "",
                "confidence": coerce_float(
                    entity.get("confidence"), f"entities[{idx}].confidence", errors
                )
                or 0.0,
            }
        )
    return mapped


def _map_actions(value: Any, errors: list[TransformError]) -> list[dict[str, Any]]:
    actions = coerce_list(value, "actions", errors)
    mapped: list[dict[str, Any]] = []
    for idx, action in enumerate(actions):
        if not isinstance(action, dict):
            errors.append(
                TransformError(
                    code="invalid_action",
                    message="Action must be an object.",
                    field_path=f"actions[{idx}]",
                    severity="error",
                    raw_value=action,
                )
            )
            continue

        mapped.append(
            {
                "action": coerce_string(action.get("action"), f"actions[{idx}].action", errors) or "",
                "owner": coerce_string(action.get("owner"), f"actions[{idx}].owner", errors) or "",
                "due_at": coerce_string(action.get("due_at"), f"actions[{idx}].due_at", errors) or "",
                "status": coerce_string(action.get("status"), f"actions[{idx}].status", errors),
            }
        )
    return mapped


def map_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], list[TransformError]]:
    """Map and coerce payload into target system field structure."""

    errors: list[TransformError] = []
    _validate_required(payload, errors)

    mapped = {
        "ticket_id": coerce_string(payload.get("ticket_id"), "ticket_id", errors) or "",
        "customer_id": coerce_string(payload.get("customer_id"), "customer_id", errors) or "",
        "created_at": coerce_string(payload.get("created_at"), "created_at", errors) or "",
        "language": coerce_string(payload.get("language"), "language", errors) or "",
        "summary": coerce_string(payload.get("summary"), "summary", errors) or "",
        "category": coerce_string(payload.get("category"), "category", errors) or "",
        "priority": coerce_string(payload.get("priority"), "priority", errors) or "",
        "entities": _map_entities(payload.get("entities"), errors),
        "actions": _map_actions(payload.get("actions"), errors),
    }

    return mapped, errors
