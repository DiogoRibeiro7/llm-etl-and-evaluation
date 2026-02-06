"""Prompt payload construction utilities."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from llm_etl_eval.prompting.templates import TARGET_SCHEMA_INSTRUCTIONS


@dataclass(frozen=True)
class PromptPayload:
    """Represents a prompt payload for an LLM call."""

    system: str
    user: str


def build_prompt_payload(record: dict[str, Any]) -> PromptPayload:
    """Build a system/user prompt payload for a single record."""

    user_payload = {
        "task": "Normalize the ticket record to the target schema.",
        "input": record,
    }
    return PromptPayload(system=TARGET_SCHEMA_INSTRUCTIONS, user=json.dumps(user_payload))


def build_single_prompt(record: dict[str, Any]) -> str:
    """Build a single instruction prompt for models that don't support system messages."""

    payload = {
        "instructions": TARGET_SCHEMA_INSTRUCTIONS,
        "task": "Normalize the ticket record to the target schema.",
        "input": record,
    }
    return json.dumps(payload)
