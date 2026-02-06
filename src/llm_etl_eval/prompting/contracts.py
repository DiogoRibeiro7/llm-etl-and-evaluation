"""Contracts defining expected LLM output structure."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Entity:
    """Entity extracted from the ticket."""

    type: str
    value: str
    confidence: float


@dataclass(frozen=True)
class Action:
    """Action item for downstream processing."""

    action: str
    owner: str
    due_at: str
    status: str | None = None


@dataclass(frozen=True)
class LlmOutput:
    """LLM output payload expected by the target system."""

    ticket_id: str
    customer_id: str
    created_at: str
    language: str
    summary: str
    category: str
    priority: str
    entities: list[Entity]
    actions: list[Action]
