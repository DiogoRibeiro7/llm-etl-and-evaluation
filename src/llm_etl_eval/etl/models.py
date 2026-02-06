"""ETL data models for tickets and events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class RawTicket:
    """Raw CSV ticket data."""

    ticket_id: str
    customer_id: str
    created_at: str
    category: str
    priority: str
    summary: str
    language: str
    metadata: str


@dataclass(frozen=True)
class RawEvent:
    """Raw JSONL event data."""

    ticket_id: str
    event_type: str
    occurred_at: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class CleanTicket:
    """Cleaned ticket with normalized fields and parsed timestamps."""

    ticket_id: str
    customer_id: str
    created_at: datetime | None
    category: str | None
    priority: str | None
    summary: str | None
    language: str | None
    metadata: dict[str, Any]


@dataclass(frozen=True)
class CleanEvent:
    """Cleaned event with parsed timestamps."""

    ticket_id: str
    event_type: str
    occurred_at: datetime | None
    payload: dict[str, Any]


@dataclass(frozen=True)
class JoinedRecord:
    """Ticket joined with its related events."""

    ticket: CleanTicket
    events: list[CleanEvent]


@dataclass(frozen=True)
class LlmInputRecord:
    """Normalized output expected by downstream systems."""

    ticket_id: str
    customer_id: str
    created_at: str
    language: str
    summary: str
    category: str
    priority: str
    entities: list[dict[str, object]]
    actions: list[dict[str, object]]
