"""Normalize cleaned data into LLM-ready payloads."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from llm_etl_eval.contracts import ActionRecord, CanonicalInputRecord, EntityRecord
from llm_etl_eval.etl.models import CleanEvent, CleanTicket, JoinedRecord

CATEGORY_ENUM = {"billing", "account", "technical", "security", "shipping", "product"}
PRIORITY_ENUM = {"low", "medium", "high", "urgent"}


def _pick_created_at(ticket: CleanTicket, events: list[CleanEvent]) -> datetime:
    """Select a created_at timestamp from ticket or earliest event."""

    if ticket.created_at is not None:
        return ticket.created_at
    fallback = datetime.max.replace(tzinfo=timezone.utc)
    for event in sorted(events, key=lambda item: item.occurred_at or fallback):
        if event.occurred_at is not None:
            return event.occurred_at
    raise ValueError(f"Missing created_at for ticket {ticket.ticket_id}")


def _pick_summary(ticket: CleanTicket, events: list[CleanEvent]) -> str:
    """Ensure summary is non-empty, using event payloads as fallback."""

    if ticket.summary:
        return ticket.summary
    for event in events:
        message = event.payload.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()
    return "Summary unavailable"


def _pick_category(ticket: CleanTicket, events: list[CleanEvent]) -> str:
    """Select a valid category, falling back to event suggestions."""

    if ticket.category in CATEGORY_ENUM:
        return ticket.category
    for event in events:
        suggestion = event.payload.get("suggested_category")
        if isinstance(suggestion, str):
            cleaned = suggestion.strip().lower()
            if cleaned in CATEGORY_ENUM:
                return cleaned
    return "technical"


def _pick_priority(ticket: CleanTicket, events: list[CleanEvent]) -> str:
    """Select a priority, optionally boosted by escalation events."""

    if ticket.priority in PRIORITY_ENUM:
        return ticket.priority

    for event in events:
        if event.event_type == "escalation":
            return "high"

    return "medium"


def _pick_language(ticket: CleanTicket) -> str:
    """Select a language value for downstream systems."""

    if ticket.language:
        return ticket.language
    return "en"


def _build_entities(ticket: CleanTicket) -> list[EntityRecord]:
    """Extract minimal entities from ticket metadata."""

    entities: list[EntityRecord] = []
    for key in ("region", "browser"):
        value = ticket.metadata.get(key)
        if isinstance(value, str) and value.strip():
            entities.append(EntityRecord(type=key, value=value, confidence=0.7))
    return entities


def _build_actions(created_at: datetime, events: list[CleanEvent]) -> list[ActionRecord]:
    """Create a default action list using event data."""

    owner = "system"
    for event in events:
        agent = event.payload.get("agent")
        if isinstance(agent, str) and agent.strip():
            owner = agent
            break

    due_at = created_at + timedelta(days=1)
    return [
        ActionRecord(
            action="triage",
            owner=owner,
            due_at=due_at.isoformat(),
            status="open",
        )
    ]


def normalize_record(joined: JoinedRecord) -> CanonicalInputRecord:
    """Normalize a joined record into the LLM-ready schema."""

    ticket = joined.ticket
    events = joined.events

    created_at = _pick_created_at(ticket, events)

    return CanonicalInputRecord(
        ticket_id=ticket.ticket_id,
        customer_id=ticket.customer_id,
        created_at=created_at.isoformat(),
        language=_pick_language(ticket),
        summary=_pick_summary(ticket, events),
        category=_pick_category(ticket, events),
        priority=_pick_priority(ticket, events),
        entities=_build_entities(ticket),
        actions=_build_actions(created_at, events),
    )


def normalize_all(joined_records: list[JoinedRecord]) -> list[CanonicalInputRecord]:
    """Normalize all joined records."""

    return [normalize_record(record) for record in joined_records]
