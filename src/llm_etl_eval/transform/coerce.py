"""Type coercion rules for transforming LLM outputs."""

from __future__ import annotations

from typing import Any

from llm_etl_eval.transform.errors import TransformError


def coerce_list(value: Any, field_path: str, errors: list[TransformError]) -> list[Any]:
    """Coerce a value into a list when possible."""

    if isinstance(value, list):
        return value
    if value is None:
        return []
    errors.append(
        TransformError(
            code="coerce_list",
            message=f"Coerced {field_path} into a list.",
            field_path=field_path,
            severity="warning",
        )
    )
    return [value]


def coerce_string(value: Any, field_path: str, errors: list[TransformError]) -> str | None:
    """Coerce a value to string when possible."""

    if value is None:
        return None
    if isinstance(value, str):
        return value
    errors.append(
        TransformError(
            code="coerce_string",
            message=f"Coerced {field_path} into a string.",
            field_path=field_path,
            severity="warning",
        )
    )
    return str(value)


def coerce_float(value: Any, field_path: str, errors: list[TransformError]) -> float | None:
    """Coerce a value to float when possible."""

    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    errors.append(
        TransformError(
            code="coerce_float",
            message=f"Coerced {field_path} into a float.",
            field_path=field_path,
            severity="warning",
        )
    )
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
