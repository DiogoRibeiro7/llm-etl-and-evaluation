"""Generate deterministic demo data for the LLM ETL + evaluation workflow."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

SEED = 42

RAW_DIR = Path("data/raw")
EXPECTED_DIR = Path("data/expected")

CATEGORIES = ["billing", "account", "technical", "security", "shipping", "product"]
PRIORITIES = ["low", "medium", "high", "urgent"]
LANGUAGES = ["en", "es", "fr", "de", "pt"]


@dataclass(frozen=True)
class TicketRow:
    """Representation of a raw CSV ticket row."""

    ticket_id: str
    customer_id: str
    created_at: str
    category: str
    priority: str
    summary: str
    language: str
    metadata: str


@dataclass(frozen=True)
class EventRow:
    """Representation of a raw JSONL event row."""

    ticket_id: str
    event_type: str
    occurred_at: str
    payload: dict[str, object]


def deterministic_index(seed: int, index: int, modulus: int) -> int:
    """Generate a deterministic index based on a seed and position."""

    return (seed * 31 + index * 17) % modulus


def build_ticket_rows() -> list[TicketRow]:
    """Create messy CSV ticket rows with missing values and inconsistent fields."""

    base_time = datetime(2025, 11, 10, 14, 30, tzinfo=timezone.utc)
    rows: list[TicketRow] = []

    summaries = [
        "Charged twice for order 9832",
        "Cannot reset password using email link",
        "Login fails after update",
        "Package arrived damaged",
        "Suspicious login detected",
        "Feature request: bulk export",
        "Payment failed but card was charged",
        "Invoice mismatch between portal and email",
        "App crashes on launch",
        "Account locked after too many attempts",
    ]

    for idx in range(10):
        ticket_id = f"TKT-{1000 + idx}"
        customer_id = f"CUST-{200 + deterministic_index(SEED, idx, 50)}"
        created_at = (base_time + timedelta(hours=idx * 6)).isoformat()

        category = CATEGORIES[deterministic_index(SEED, idx, len(CATEGORIES))]
        priority = PRIORITIES[deterministic_index(SEED + 1, idx, len(PRIORITIES))]
        language = LANGUAGES[deterministic_index(SEED + 2, idx, len(LANGUAGES))]

        summary = summaries[idx]

        # Introduce some messy fields.
        if idx % 3 == 0:
            category = category.title()
        if idx % 4 == 0:
            priority = priority.upper()
        if idx % 5 == 0:
            language = ""
        if idx % 7 == 0:
            summary = ""

        metadata = {
            "source": "web" if idx % 2 == 0 else "email",
            "tags": ["vip"] if idx % 4 == 0 else ["standard"],
            "browser": "Chrome" if idx % 3 == 0 else "Firefox",
            "ticket_version": 1 + (idx % 2),
        }

        rows.append(
            TicketRow(
                ticket_id=ticket_id,
                customer_id=customer_id,
                created_at=created_at,
                category=category,
                priority=priority,
                summary=summary,
                language=language,
                metadata=json.dumps(metadata),
            )
        )

    # Add intentionally malformed timestamps and category variants.
    rows.append(
        TicketRow(
            ticket_id="TKT-1010",
            customer_id="CUST-999",
            created_at="11/12/2025 09:15",
            category="tech support",
            priority="med",
            summary="Latency spikes in EU region",
            language="en-US",
            metadata=json.dumps({"source": "chat", "tags": ["sla"], "region": "EU"}),
        )
    )
    rows.append(
        TicketRow(
            ticket_id="TKT-1011",
            customer_id="CUST-420",
            created_at="2025-11-13T07:20:00Z",
            category="Billing",
            priority="High",
            summary="Refund requested for duplicate charge",
            language="EN",
            metadata=json.dumps({"source": "phone", "tags": ["refund"], "agent_id": "AG-7"}),
        )
    )

    return rows


def build_event_rows() -> list[EventRow]:
    """Create semi-structured JSONL events with nested metadata."""

    events: list[EventRow] = []
    base_time = datetime(2025, 11, 10, 15, 0, tzinfo=timezone.utc)

    for idx in range(8):
        ticket_id = f"TKT-{1000 + idx}"
        occurred_at = (base_time + timedelta(hours=idx * 5)).isoformat()
        events.append(
            EventRow(
                ticket_id=ticket_id,
                event_type="triage",
                occurred_at=occurred_at,
                payload={
                    "agent": f"AG-{10 + idx}",
                    "confidence": round(0.5 + idx * 0.05, 2),
                    "suggested_category": CATEGORIES[idx % len(CATEGORIES)],
                    "signals": {"keywords": ["login", "billing"][idx % 2]},
                },
            )
        )

    events.append(
        EventRow(
            ticket_id="TKT-1003",
            event_type="customer_update",
            occurred_at="2025-11-12 08:04",
            payload={
                "channel": "email",
                "message": "Still waiting on a fix; issue persists after reset.",
                "attachments": [{"name": "screenshot.png", "size_kb": 512}],
            },
        )
    )

    events.append(
        EventRow(
            ticket_id="TKT-1010",
            event_type="escalation",
            occurred_at="2025-11-12T10:00:00+00:00",
            payload={
                "reason": "SLA breach risk",
                "manager": "AG-99",
                "impact": {"region": "EU", "affected_customers": 12},
            },
        )
    )

    return events


def write_csv(rows: Iterable[TicketRow], path: Path) -> None:
    """Write ticket rows to CSV."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "ticket_id",
                "customer_id",
                "created_at",
                "category",
                "priority",
                "summary",
                "language",
                "metadata",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.ticket_id,
                    row.customer_id,
                    row.created_at,
                    row.category,
                    row.priority,
                    row.summary,
                    row.language,
                    row.metadata,
                ]
            )


def write_jsonl(rows: Iterable[EventRow], path: Path) -> None:
    """Write event rows to JSONL."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(
                json.dumps(
                    {
                        "ticket_id": row.ticket_id,
                        "event_type": row.event_type,
                        "occurred_at": row.occurred_at,
                        "payload": row.payload,
                    }
                )
                + "\n"
            )


def write_schema(path: Path) -> None:
    """Write the expected target JSON schema."""

    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "NormalizedTicket",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "ticket_id",
            "customer_id",
            "created_at",
            "language",
            "summary",
            "category",
            "priority",
            "entities",
            "actions",
        ],
        "properties": {
            "ticket_id": {"type": "string", "minLength": 1},
            "customer_id": {"type": "string", "minLength": 1},
            "created_at": {"type": "string", "format": "date-time"},
            "language": {"type": "string", "minLength": 2},
            "summary": {"type": "string", "minLength": 1},
            "category": {"type": "string", "enum": CATEGORIES},
            "priority": {"type": "string", "enum": PRIORITIES},
            "entities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["type", "value", "confidence"],
                    "properties": {
                        "type": {"type": "string"},
                        "value": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                },
            },
            "actions": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["action", "owner", "due_at"],
                    "properties": {
                        "action": {"type": "string", "minLength": 1},
                        "owner": {"type": "string", "minLength": 1},
                        "due_at": {"type": "string", "format": "date-time"},
                        "status": {"type": "string", "enum": ["open", "in_progress", "done"]},
                    },
                },
            },
        },
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(schema, indent=2), encoding="utf-8")


def main() -> None:
    """Generate demo data and schema artifacts."""

    tickets = build_ticket_rows()
    events = build_event_rows()

    write_csv(tickets, RAW_DIR / "tickets.csv")
    write_jsonl(events, RAW_DIR / "events.jsonl")
    write_schema(EXPECTED_DIR / "target_schema.json")


if __name__ == "__main__":
    main()
