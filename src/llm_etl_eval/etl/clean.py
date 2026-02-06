"""Cleaning and standardization helpers for raw inputs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from llm_etl_eval.etl.models import CleanEvent, CleanTicket, RawEvent, RawTicket

CATEGORY_SYNONYMS = {
    "tech support": "technical",
    "tech": "technical",
    "technical issue": "technical",
    "billing issue": "billing",
    "acct": "account",
    "accounting": "account",
    "sec": "security",
}

PRIORITY_SYNONYMS = {
    "med": "medium",
    "hi": "high",
    "urgent": "urgent",
    "low": "low",
    "medium": "medium",
    "high": "high",
}

LANGUAGE_SYNONYMS = {
    "en-us": "en",
    "en-gb": "en",
    "pt-br": "pt",
}


def parse_timestamp(value: str | None) -> datetime | None:
    """Parse timestamps with tolerant formats, returning UTC-aware datetime."""

    if value is None:
        return None

    cleaned = value.strip()
    if not cleaned:
        return None

    # Normalize Zulu time.
    if cleaned.endswith("Z"):
        cleaned = cleaned.replace("Z", "+00:00")

    for fmt in (None, "%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M"):
        try:
            if fmt is None:
                parsed = datetime.fromisoformat(cleaned)
            else:
                parsed = datetime.strptime(cleaned, fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            continue

    return None


def normalize_category(value: str | None) -> str | None:
    """Normalize category names and map synonyms."""

    if value is None:
        return None
    cleaned = value.strip().lower()
    if not cleaned:
        return None
    return CATEGORY_SYNONYMS.get(cleaned, cleaned)


def normalize_priority(value: str | None) -> str | None:
    """Normalize priority values and map synonyms."""

    if value is None:
        return None
    cleaned = value.strip().lower()
    if not cleaned:
        return None
    return PRIORITY_SYNONYMS.get(cleaned, cleaned)


def normalize_language(value: str | None) -> str | None:
    """Normalize language codes to lowercase base language."""

    if value is None:
        return None
    cleaned = value.strip().lower()
    if not cleaned:
        return None
    normalized = LANGUAGE_SYNONYMS.get(cleaned, cleaned)
    return normalized.split("-")[0]


def normalize_summary(value: str | None) -> str | None:
    """Trim summaries and return None when empty."""

    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    return cleaned


def parse_metadata(value: str | None) -> dict[str, Any]:
    """Parse metadata JSON strings into dictionaries."""

    if value is None:
        return {}
    cleaned = value.strip()
    if not cleaned:
        return {}
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return {}
    if isinstance(parsed, dict):
        return parsed
    return {}


def clean_ticket(raw: RawTicket) -> CleanTicket:
    """Clean a raw ticket into normalized fields."""

    return CleanTicket(
        ticket_id=raw.ticket_id.strip(),
        customer_id=raw.customer_id.strip(),
        created_at=parse_timestamp(raw.created_at),
        category=normalize_category(raw.category),
        priority=normalize_priority(raw.priority),
        summary=normalize_summary(raw.summary),
        language=normalize_language(raw.language),
        metadata=parse_metadata(raw.metadata),
    )


def clean_event(raw: RawEvent) -> CleanEvent:
    """Clean a raw event into normalized fields."""

    return CleanEvent(
        ticket_id=raw.ticket_id.strip(),
        event_type=raw.event_type.strip(),
        occurred_at=parse_timestamp(raw.occurred_at),
        payload=raw.payload,
    )


def clean_all(
    tickets: list[RawTicket], events: list[RawEvent]
) -> tuple[list[CleanTicket], list[CleanEvent]]:
    """Clean collections of tickets and events."""

    clean_tickets = [clean_ticket(ticket) for ticket in tickets]
    clean_events = [clean_event(event) for event in events]
    return clean_tickets, clean_events
