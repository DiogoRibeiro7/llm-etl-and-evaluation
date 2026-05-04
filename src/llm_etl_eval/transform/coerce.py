"""Type coercion rules for transforming LLM outputs."""

from __future__ import annotations

from typing import Any

from llm_etl_eval.transform.errors import TransformError

PRIORITY_VALID: set[str] = {"low", "medium", "high", "urgent"}
PRIORITY_SYNONYMS: dict[str, str] = {
    "critical": "urgent",
    "crit": "urgent",
    "blocker": "urgent",
    "p0": "urgent",
    "important": "high",
    "hi": "high",
    "p1": "high",
    "med": "medium",
    "normal": "medium",
    "moderate": "medium",
    "p2": "medium",
    "minor": "low",
    "p3": "low",
    "p4": "low",
}

CATEGORY_VALID: set[str] = {
    "billing", "account", "technical", "security", "shipping", "product",
}
CATEGORY_SYNONYMS: dict[str, str] = {
    "tech": "technical",
    "tech support": "technical",
    "technical issue": "technical",
    "bug": "technical",
    "bug report": "technical",
    "billing issue": "billing",
    "payment": "billing",
    "payments": "billing",
    "refund": "billing",
    "refunds": "billing",
    "invoice": "billing",
    "acct": "account",
    "accounting": "account",
    "user account": "account",
    "sec": "security",
    "auth": "security",
    "authentication": "security",
    "fraud": "security",
    "delivery": "shipping",
    "logistics": "shipping",
    "shipping issue": "shipping",
    "feature": "product",
    "feature request": "product",
}


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


def backfill_required_summary(
    parsed: dict[str, Any],
    input_record: dict[str, Any] | None,
    errors: list[TransformError],
    *,
    allow_coercion: bool = True,
) -> dict[str, Any]:
    """Backfill a missing or empty `summary` from the canonical input record.

    Returns a new dict with `summary` replaced when:
      - allow_coercion is True
      - input_record is provided and has a non-empty summary
      - the parsed output's summary is missing, None, or whitespace-only

    Otherwise returns `parsed` unchanged. Emits a warning-severity
    TransformError so the rescue is visible in the rejected/cluster report
    rather than silently masking model failures.
    """

    if not allow_coercion or input_record is None:
        return parsed

    current = parsed.get("summary")
    if isinstance(current, str) and current.strip():
        return parsed

    fallback = input_record.get("summary")
    if not isinstance(fallback, str) or not fallback.strip():
        return parsed

    new_parsed = dict(parsed)
    new_parsed["summary"] = fallback.strip()
    errors.append(
        TransformError(
            code="backfill_summary",
            message="Backfilled missing summary from input record.",
            field_path="summary",
            severity="warning",
            raw_value=current,
        )
    )
    return new_parsed


def coerce_enum(
    value: Any,
    valid_values: set[str],
    synonyms: dict[str, str],
    field_path: str,
    errors: list[TransformError],
    *,
    allow_coercion: bool = True,
) -> Any:
    """Coerce an enum-like value to a canonical valid form.

    When `allow_coercion=True`:
      - Lowercases and strips whitespace before lookup.
      - Returns the canonical form when the cleaned value is already valid
        (e.g., "URGENT" -> "urgent").
      - Maps known near-miss synonyms to a canonical valid form
        (e.g., "critical" -> "urgent", "med" -> "medium").

    When `allow_coercion=False`, the value is returned unchanged so the
    schema validator stays the single source of truth for rejections.

    Non-string values are passed through; downstream coercers/validators
    handle them.
    """

    if not isinstance(value, str):
        return value

    cleaned = value.strip().lower()
    if not cleaned:
        return value

    if cleaned in valid_values:
        if cleaned == value:
            return value
        if not allow_coercion:
            return value
        errors.append(
            TransformError(
                code="coerce_enum",
                message=f"Normalized {field_path} casing to '{cleaned}'.",
                field_path=field_path,
                severity="warning",
                raw_value=value,
            )
        )
        return cleaned

    if allow_coercion and cleaned in synonyms:
        canonical = synonyms[cleaned]
        errors.append(
            TransformError(
                code="coerce_enum",
                message=f"Mapped {field_path} '{value}' to '{canonical}'.",
                field_path=field_path,
                severity="warning",
                raw_value=value,
            )
        )
        return canonical

    return value


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
