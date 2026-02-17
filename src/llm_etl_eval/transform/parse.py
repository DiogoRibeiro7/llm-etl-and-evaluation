"""Tolerant JSON parsing utilities."""

from __future__ import annotations

import ast
import json
import math
import re
from typing import Any

from llm_etl_eval.transform.errors import TransformError

JSON_BLOCK_RE = re.compile(r"```(?:json)?\n(.*?)```", re.DOTALL | re.IGNORECASE)
TRAILING_COMMA_RE = re.compile(r",\s*(?=[}\]])")


def _strip_markdown_fences(text: str) -> str:
    """Strip markdown JSON fences if present."""

    match = JSON_BLOCK_RE.search(text)
    if match:
        return match.group(1).strip()
    return text.strip()


def _trim_to_json(text: str) -> str:
    """Trim leading/trailing text around the first JSON object."""

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return text
    return text[start : end + 1]


def _strip_trailing_commas(text: str) -> str:
    """Remove trailing commas before object/array close."""

    return TRAILING_COMMA_RE.sub("", text)


def _is_json_number(value: float | int) -> bool:
    if isinstance(value, bool):
        return True
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    return False


def _is_json_compatible(value: Any, path: list[str]) -> tuple[bool, str | None]:
    if value is None or isinstance(value, (str, bool)):
        return True, None
    if _is_json_number(value):
        return True, None
    if isinstance(value, dict):
        for key in value.keys():
            if not isinstance(key, str):
                return False, ".".join(path + ["<non-string-key>"])
        for key, child in value.items():
            ok, bad_path = _is_json_compatible(child, path + [key])
            if not ok:
                return False, bad_path
        return True, None
    if isinstance(value, list):
        for index, child in enumerate(value):
            ok, bad_path = _is_json_compatible(child, path + [str(index)])
            if not ok:
                return False, bad_path
        return True, None
    return False, ".".join(path) if path else "<root>"


def _try_literal_eval(text: str) -> tuple[dict[str, Any] | None, str | None]:
    """Attempt to parse Python-style literals (single quotes) safely."""

    try:
        parsed = ast.literal_eval(text)
    except (SyntaxError, ValueError):
        return None, None
    if not isinstance(parsed, dict):
        return None, "<root>"
    ok, bad_path = _is_json_compatible(parsed, [])
    if not ok:
        return None, bad_path
    return parsed, None


def parse_json(text: str, *, strict: bool = False) -> tuple[dict[str, Any] | None, list[TransformError]]:
    """Parse JSON with optional strictness."""

    errors: list[TransformError] = []
    if strict:
        try:
            parsed = json.loads(text.strip())
        except json.JSONDecodeError as exc:
            errors.append(
                TransformError(
                    code="invalid_json",
                    message=f"Failed to parse JSON: {exc}",
                    field_path=None,
                    severity="error",
                    raw_value=text,
                )
            )
            return None, errors

        if not isinstance(parsed, dict):
            errors.append(
                TransformError(
                    code="invalid_type",
                    message="Parsed JSON is not an object.",
                    field_path=None,
                    severity="error",
                    raw_value=parsed,
                )
            )
            return None, errors

        return parsed, errors

    cleaned = _strip_markdown_fences(text)
    trimmed = _trim_to_json(cleaned)
    normalized = _strip_trailing_commas(trimmed)

    parsed: dict[str, Any] | None = None
    last_error: Exception | None = None
    for candidate in (trimmed, normalized):
        try:
            parsed = json.loads(candidate)
            break
        except json.JSONDecodeError as exc:
            last_error = exc

    if parsed is None:
        parsed, bad_path = _try_literal_eval(normalized)
        if parsed is None:
            if bad_path is not None:
                errors.append(
                    TransformError(
                        code="unsafe_single_quotes",
                        message=(
                            "Single-quoted input contains non-JSON values or non-string keys."
                        ),
                        field_path=bad_path,
                        severity="error",
                        raw_value=text,
                    )
                )
                return None, errors
            errors.append(
                TransformError(
                    code="invalid_json",
                    message=f"Failed to parse JSON: {last_error}",
                    field_path=None,
                    severity="error",
                    raw_value=text,
                )
            )
            return None, errors

    if not isinstance(parsed, dict):
        errors.append(
            TransformError(
                code="invalid_type",
                message="Parsed JSON is not an object.",
                field_path=None,
                severity="error",
                raw_value=parsed,
            )
        )
        return None, errors

    return parsed, errors
