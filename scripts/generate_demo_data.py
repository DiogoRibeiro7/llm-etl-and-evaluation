"""Generate deterministic demo data for the LLM ETL + evaluation workflow.

Produces:
  - data/raw/tickets.csv         50 tickets with realistic variety + injected messiness
  - data/raw/events.jsonl        triage event per ticket plus escalations + customer updates
  - data/expected/target_schema.json
  - data/gold/labels.jsonl       gold labels derived by running the ETL pipeline
                                 over the raw data, so a perfect model output
                                 matches gold by construction.
"""

from __future__ import annotations

import csv
import json
import sys
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from llm_etl_eval.etl.clean import clean_all  # noqa: E402
from llm_etl_eval.etl.ingest import IngestConfig, load_raw  # noqa: E402
from llm_etl_eval.etl.join import join_by_ticket  # noqa: E402
from llm_etl_eval.etl.normalize import normalize_all  # noqa: E402

SEED = 42
TICKET_COUNT = 50

RAW_DIR = REPO_ROOT / "data" / "raw"
EXPECTED_DIR = REPO_ROOT / "data" / "expected"
GOLD_DIR = REPO_ROOT / "data" / "gold"

CATEGORIES = ["billing", "account", "technical", "security", "shipping", "product"]
PRIORITIES = ["low", "medium", "high", "urgent"]
LANGUAGES = ["en", "es", "fr", "de", "pt"]

SUMMARIES_BY_CATEGORY: dict[str, list[str]] = {
    "billing": [
        "Charged twice for order 9832",
        "Refund requested for duplicate charge",
        "Payment failed but card was charged",
        "Invoice mismatch between portal and email",
        "Subscription renewed without consent",
        "Promo code did not apply at checkout",
        "Currency conversion looks wrong on receipt",
        "Annual plan billed monthly by mistake",
    ],
    "account": [
        "Cannot reset password using email link",
        "Account locked after too many attempts",
        "Two-factor codes never arrive",
        "Email change request pending for two weeks",
        "Profile picture upload fails silently",
        "Cannot delete account from settings",
        "Username already taken on signup",
    ],
    "technical": [
        "App crashes on launch after recent update",
        "Login fails after update on iOS",
        "Page loads infinitely in Safari",
        "API returning 500 on /v2/tickets",
        "Search results are empty for valid queries",
        "Mobile app freezes on dashboard",
        "Sync fails between desktop and mobile",
    ],
    "security": [
        "Suspicious login detected from new device",
        "Unauthorized access alert from Italy",
        "Phishing email impersonating support",
        "Session token leaked in URL params",
        "Strange device listed in active sessions",
    ],
    "shipping": [
        "Package arrived damaged",
        "Order shows delivered but never received",
        "Wrong item shipped instead of order",
        "Tracking number invalid on carrier site",
        "Shipping address changed without permission",
        "Customs hold for two weeks and counting",
    ],
    "product": [
        "Feature request: bulk export to CSV",
        "Request for dark mode in mobile app",
        "PDF export missing footer information",
        "Filter by date does nothing on results",
        "Need API endpoint for entity search",
        "Bulk import via CSV would help workflow",
    ],
}

ESCALATION_TICKET_INDICES = (10, 18, 27, 36, 45)
CUSTOMER_UPDATE_TICKET_INDICES = (3, 12, 22, 31, 41)


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
    """Generate a deterministic index based on seed and position."""

    return (seed * 31 + index * 17) % modulus


def _category_for(idx: int) -> str:
    return CATEGORIES[deterministic_index(SEED, idx, len(CATEGORIES))]


def _priority_for(idx: int) -> str:
    return PRIORITIES[deterministic_index(SEED + 1, idx, len(PRIORITIES))]


def _language_for(idx: int) -> str:
    return LANGUAGES[deterministic_index(SEED + 2, idx, len(LANGUAGES))]


def _summary_for(idx: int, category: str) -> str:
    pool = SUMMARIES_BY_CATEGORY[category]
    pool_idx = deterministic_index(SEED + 3, idx, len(pool))
    return pool[pool_idx]


def build_ticket_rows() -> list[TicketRow]:
    """Create messy CSV ticket rows with missing values and inconsistent fields."""

    base_time = datetime(2025, 11, 10, 14, 30, tzinfo=UTC)
    rows: list[TicketRow] = []

    for idx in range(TICKET_COUNT):
        ticket_id = f"TKT-{1000 + idx}"
        customer_id = f"CUST-{200 + deterministic_index(SEED, idx, 50)}"
        created_at = (base_time + timedelta(hours=idx * 6)).isoformat()

        category = _category_for(idx)
        priority = _priority_for(idx)
        language = _language_for(idx)
        summary = _summary_for(idx, category)

        # Inject realistic messiness so the ETL's tolerant-cleaning story shows up.
        if idx % 3 == 0:
            category = category.title()
        if idx % 4 == 0:
            priority = priority.upper()
        if idx % 5 == 0:
            language = ""
        if idx % 7 == 0:
            summary = ""

        # Pepper a couple of fully malformed examples.
        if idx == 10:
            category = "tech support"
            priority = "med"
            language = "en-US"
            created_at = "11/12/2025 09:15"
            summary = "Latency spikes in EU region"
        if idx == 11:
            category = "Billing"
            priority = "High"
            language = "EN"
            created_at = "2025-11-13T07:20:00Z"
            summary = "Refund requested for duplicate charge"

        metadata = {
            "source": "web" if idx % 2 == 0 else "email",
            "tags": ["vip"] if idx % 4 == 0 else ["standard"],
            "browser": "Chrome" if idx % 3 == 0 else "Firefox",
            "ticket_version": 1 + (idx % 2),
        }
        if idx == 10:
            metadata = {"source": "chat", "tags": ["sla"], "region": "EU"}
        if idx == 11:
            metadata = {"source": "phone", "tags": ["refund"], "agent_id": "AG-7"}

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

    return rows


def build_event_rows(tickets: list[TicketRow]) -> list[EventRow]:
    """Create one triage event per ticket plus escalations and customer updates."""

    events: list[EventRow] = []
    base_time = datetime(2025, 11, 10, 15, 0, tzinfo=UTC)

    for idx, ticket in enumerate(tickets):
        occurred_at = (base_time + timedelta(hours=idx * 5)).isoformat()
        category_for_event = CATEGORIES[idx % len(CATEGORIES)]
        events.append(
            EventRow(
                ticket_id=ticket.ticket_id,
                event_type="triage",
                occurred_at=occurred_at,
                payload={
                    "agent": f"AG-{10 + (idx % 40)}",
                    "confidence": round(0.5 + (idx % 10) * 0.05, 2),
                    "suggested_category": category_for_event,
                    "signals": {"keywords": ["login", "billing"][idx % 2]},
                },
            )
        )

    customer_messages = [
        "Still waiting on a fix; issue persists after reset.",
        "Tried again today, same problem.",
        "Workaround helped temporarily, but error is back.",
        "Can you escalate this? Affects our team.",
        "Adding screenshots; please review.",
    ]
    for slot, ticket_idx in enumerate(CUSTOMER_UPDATE_TICKET_INDICES):
        if ticket_idx >= len(tickets):
            continue
        events.append(
            EventRow(
                ticket_id=tickets[ticket_idx].ticket_id,
                event_type="customer_update",
                occurred_at=(base_time + timedelta(days=2, hours=slot)).isoformat(),
                payload={
                    "channel": "email",
                    "message": customer_messages[slot],
                    "attachments": [{"name": "screenshot.png", "size_kb": 512}],
                },
            )
        )

    escalation_reasons = [
        ("SLA breach risk", {"region": "EU", "affected_customers": 12}),
        ("Repeated occurrence", {"region": "US", "affected_customers": 4}),
        ("VIP customer", {"region": "APAC", "affected_customers": 1}),
        ("Regulatory follow-up required", {"region": "EU", "affected_customers": 30}),
        ("Public-facing outage", {"region": "global", "affected_customers": 200}),
    ]
    for slot, ticket_idx in enumerate(ESCALATION_TICKET_INDICES):
        if ticket_idx >= len(tickets):
            continue
        reason, impact = escalation_reasons[slot]
        events.append(
            EventRow(
                ticket_id=tickets[ticket_idx].ticket_id,
                event_type="escalation",
                occurred_at=(base_time + timedelta(days=3, hours=slot)).isoformat(),
                payload={
                    "reason": reason,
                    "manager": "AG-99",
                    "impact": impact,
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


def write_gold_labels(raw_dir: Path, gold_path: Path) -> None:
    """Run the ETL pipeline over the raw data and emit gold labels.

    Gold values are derived from the cleaned + normalized canonical records,
    so a perfect simulator/LLM output (which echoes the input) matches gold
    by construction. Field-accuracy then becomes a real measurement signal.
    """

    config = IngestConfig(
        tickets_path=raw_dir / "tickets.csv",
        events_path=raw_dir / "events.jsonl",
    )
    raw_tickets, raw_events = load_raw(config)
    clean_tickets, clean_events = clean_all(raw_tickets, raw_events)
    joined = join_by_ticket(clean_tickets, clean_events)
    canonical = normalize_all(joined)

    gold_path.parent.mkdir(parents=True, exist_ok=True)
    with gold_path.open("w", encoding="utf-8") as handle:
        for record in canonical:
            payload = asdict(record)
            label = {
                "ticket_id": payload["ticket_id"],
                "customer_id": payload["customer_id"],
                "category": payload["category"],
                "priority": payload["priority"],
                "summary": payload["summary"],
            }
            handle.write(json.dumps(label, sort_keys=True) + "\n")


def main() -> None:
    """Generate demo data, schema, and pipeline-derived gold labels."""

    tickets = build_ticket_rows()
    events = build_event_rows(tickets)

    write_csv(tickets, RAW_DIR / "tickets.csv")
    write_jsonl(events, RAW_DIR / "events.jsonl")
    write_schema(EXPECTED_DIR / "target_schema.json")
    write_gold_labels(RAW_DIR, GOLD_DIR / "labels.jsonl")

    print(
        f"Wrote {len(tickets)} tickets, {len(events)} events, "
        f"and gold labels to {GOLD_DIR / 'labels.jsonl'}"
    )


if __name__ == "__main__":
    main()
