"""Pipeline configuration loading utilities."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class PipelineConfig:
    """Configuration toggles for parsing, coercion, and prompting."""

    coercion_enabled: bool = True
    strict_parsing: bool = False
    prompt_strictness: str = "minimal"
    schema_reminders: bool = False


def _require_mapping(value: Any, field_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    raise ValueError(f"{field_name} must be a mapping.")


def _load_raw(path: Path) -> dict[str, Any]:
    if path.suffix.lower() in {".json"}:
        return json.loads(path.read_text(encoding="utf-8"))
    if path.suffix.lower() in {".yaml", ".yml"}:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return {} if data is None else data
    raise ValueError(f"Unsupported config format: {path.suffix}")


def load_config(path: Path) -> PipelineConfig:
    """Load pipeline config from a YAML or JSON file."""

    data = _load_raw(path)
    if not isinstance(data, dict):
        raise ValueError("Config must be a mapping at the top level.")

    coercion = _require_mapping(data.get("coercion"), "coercion")
    parsing = _require_mapping(data.get("parsing"), "parsing")
    prompt = _require_mapping(data.get("prompt"), "prompt")

    prompt_strictness = str(prompt.get("strictness", "minimal")).lower()
    if prompt_strictness not in {"minimal", "strict"}:
        raise ValueError("prompt.strictness must be 'minimal' or 'strict'.")

    return PipelineConfig(
        coercion_enabled=bool(coercion.get("enabled", True)),
        strict_parsing=bool(parsing.get("strict", False)),
        prompt_strictness=prompt_strictness,
        schema_reminders=bool(prompt.get("schema_reminders", False)),
    )
