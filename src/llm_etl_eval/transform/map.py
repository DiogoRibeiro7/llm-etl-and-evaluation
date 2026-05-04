"""Map LLM output fields to the target system format."""

from __future__ import annotations

from typing import Any

from llm_etl_eval.transform.coerce import (
    CATEGORY_SYNONYMS,
    CATEGORY_VALID,
    PRIORITY_SYNONYMS,
    PRIORITY_VALID,
    coerce_enum,
    coerce_float,
    coerce_list,
    coerce_string,
)
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


def _map_entities(
    value: Any, errors: list[TransformError], allow_coercion: bool
) -> list[dict[str, Any]]:
    entities = coerce_list(value, "entities", errors, allow_coercion=allow_coercion)
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
                "type": coerce_string(
                    entity.get("type"),
                    f"entities[{idx}].type",
                    errors,
                    allow_coercion=allow_coercion,
                )
                or "",
                "value": coerce_string(
                    entity.get("value"),
                    f"entities[{idx}].value",
                    errors,
                    allow_coercion=allow_coercion,
                )
                or "",
                "confidence": coerce_float(
                    entity.get("confidence"),
                    f"entities[{idx}].confidence",
                    errors,
                    allow_coercion=allow_coercion,
                )
                or 0.0,
            }
        )
    return mapped


def _map_actions(
    value: Any, errors: list[TransformError], allow_coercion: bool
) -> list[dict[str, Any]]:
    actions = coerce_list(value, "actions", errors, allow_coercion=allow_coercion)
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
                "action": coerce_string(
                    action.get("action"),
                    f"actions[{idx}].action",
                    errors,
                    allow_coercion=allow_coercion,
                )
                or "",
                "owner": coerce_string(
                    action.get("owner"),
                    f"actions[{idx}].owner",
                    errors,
                    allow_coercion=allow_coercion,
                )
                or "",
                "due_at": coerce_string(
                    action.get("due_at"),
                    f"actions[{idx}].due_at",
                    errors,
                    allow_coercion=allow_coercion,
                )
                or "",
                "status": coerce_string(
                    action.get("status"),
                    f"actions[{idx}].status",
                    errors,
                    allow_coercion=allow_coercion,
                ),
            }
        )
    return mapped


def map_payload(
    payload: dict[str, Any], *, allow_coercion: bool = True
) -> tuple[dict[str, Any], list[TransformError]]:
    """Map and coerce payload into target system field structure."""

    errors: list[TransformError] = []
    _validate_required(payload, errors)

    mapped = {
        "ticket_id": coerce_string(
            payload.get("ticket_id"), "ticket_id", errors, allow_coercion=allow_coercion
        )
        or "",
        "customer_id": coerce_string(
            payload.get("customer_id"), "customer_id", errors, allow_coercion=allow_coercion
        )
        or "",
        "created_at": coerce_string(
            payload.get("created_at"), "created_at", errors, allow_coercion=allow_coercion
        )
        or "",
        "language": coerce_string(
            payload.get("language"), "language", errors, allow_coercion=allow_coercion
        )
        or "",
        "summary": coerce_string(
            payload.get("summary"), "summary", errors, allow_coercion=allow_coercion
        )
        or "",
        "category": coerce_enum(
            coerce_string(
                payload.get("category"), "category", errors, allow_coercion=allow_coercion
            ),
            CATEGORY_VALID,
            CATEGORY_SYNONYMS,
            "category",
            errors,
            allow_coercion=allow_coercion,
        )
        or "",
        "priority": coerce_enum(
            coerce_string(
                payload.get("priority"), "priority", errors, allow_coercion=allow_coercion
            ),
            PRIORITY_VALID,
            PRIORITY_SYNONYMS,
            "priority",
            errors,
            allow_coercion=allow_coercion,
        )
        or "",
        "entities": _map_entities(payload.get("entities"), errors, allow_coercion=allow_coercion),
        "actions": _map_actions(payload.get("actions"), errors, allow_coercion=allow_coercion),
    }

    return mapped, errors
