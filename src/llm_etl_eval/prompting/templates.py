"""Prompt templates for LLM output generation."""

from __future__ import annotations

MINIMAL_INSTRUCTIONS = """
You are a data normalization assistant. Produce a JSON object that matches the target schema.

Rules:
- Output only JSON (no markdown, no commentary).
- Required fields: ticket_id, customer_id, created_at, language, summary, category, priority, entities, actions.
- Do not include additional fields.
""".strip()

STRICT_INSTRUCTIONS = """
You are a data normalization assistant. Produce a JSON object that matches the target schema.

Rules:
- Output only JSON (no markdown, no commentary).
- Required fields: ticket_id, customer_id, created_at, language, summary, category, priority, entities, actions.
- created_at and actions[].due_at must be ISO-8601 date-time strings.
- category must be one of: billing, account, technical, security, shipping, product.
- priority must be one of: low, medium, high, urgent.
- summary must be non-empty.
- entities is an array of objects with keys: type, value, confidence (0-1).
- actions is a non-empty array of objects with keys: action, owner, due_at; optional status.
- Do not include additional fields.
""".strip()


def build_system_instructions(
    strictness: str = "minimal",
    *,
    schema_reminders: bool = False,
    schema_json: str | None = None,
) -> str:
    """Build system instructions with optional schema reminders."""

    strictness_value = strictness.lower()
    if strictness_value == "strict":
        instructions = STRICT_INSTRUCTIONS
    else:
        instructions = MINIMAL_INSTRUCTIONS

    if schema_reminders and schema_json:
        return f"{instructions}\n\nSchema reminder:\n{schema_json}"
    return instructions


TARGET_SCHEMA_INSTRUCTIONS = STRICT_INSTRUCTIONS
