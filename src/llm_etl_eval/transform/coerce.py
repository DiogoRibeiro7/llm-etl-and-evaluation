"""Type coercion rules for transforming LLM outputs."""

from __future__ import annotations

from typing import Any

from llm_etl_eval.transform.errors import TransformError


def coerce_list(
    value: Any, field_path: str, errors: list[TransformError], allow_coercion: bool = True
) -> list[Any]:
    """Coerce a value into a list when possible."""

    if isinstance(value, list):
        return value
    if value is None:
        return []
    if allow_coercion:
        errors.append(
            TransformError(
                code="coerce_list",
                message=f"Coerced {field_path} into a list.",
                field_path=field_path,
                severity="warning",
                raw_value=value,
            )
        )
        return [value]
    errors.append(
        TransformError(
            code="invalid_type",
            message="Expected list.",
            field_path=field_path,
            severity="error",
            raw_value=value,
        )
    )
    return []


def coerce_string(
    value: Any, field_path: str, errors: list[TransformError], allow_coercion: bool = True
) -> str | None:
    """Coerce a value to string when possible."""

    if value is None:
        return None
    if isinstance(value, str):
        return value
    if allow_coercion:
        errors.append(
            TransformError(
                code="coerce_string",
                message=f"Coerced {field_path} into a string.",
                field_path=field_path,
                severity="warning",
                raw_value=value,
            )
        )
        return str(value)
    errors.append(
        TransformError(
            code="invalid_type",
            message="Expected string.",
            field_path=field_path,
            severity="error",
            raw_value=value,
        )
    )
    return None


def coerce_float(
    value: Any, field_path: str, errors: list[TransformError], allow_coercion: bool = True
) -> float | None:
    """Coerce a value to float when possible."""

    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if allow_coercion:
        errors.append(
            TransformError(
                code="coerce_float",
                message=f"Coerced {field_path} into a float.",
                field_path=field_path,
                severity="warning",
                raw_value=value,
            )
        )
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    errors.append(
        TransformError(
            code="invalid_type",
            message="Expected number.",
            field_path=field_path,
            severity="error",
            raw_value=value,
        )
    )
    return None
