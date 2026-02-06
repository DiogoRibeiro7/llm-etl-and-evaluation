"""Tolerant JSON parsing utilities."""

from __future__ import annotations

import json
import re
from typing import Any

from llm_etl_eval.transform.errors import TransformError

JSON_BLOCK_RE = re.compile(r"```(?:json)?\n(.*?)```", re.DOTALL | re.IGNORECASE)


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


def parse_json(text: str) -> tuple[dict[str, Any] | None, list[TransformError]]:
    """Parse JSON with tolerance for markdown wrappers and trailing text."""

    errors: list[TransformError] = []
    cleaned = _strip_markdown_fences(text)
    trimmed = _trim_to_json(cleaned)

    try:
        parsed = json.loads(trimmed)
    except json.JSONDecodeError as exc:
        errors.append(
            TransformError(
                code="invalid_json",
                message=f"Failed to parse JSON: {exc}",
                field_path=None,
                severity="error",
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
            )
        )
        return None, errors

    return parsed, errors
