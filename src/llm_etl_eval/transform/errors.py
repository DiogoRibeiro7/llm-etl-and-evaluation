"""Structured error objects for transformation failures."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TransformError:
    """Structured error with field path and severity."""

    code: str
    message: str
    field_path: str | None
    severity: str
    raw_value: Any | None
