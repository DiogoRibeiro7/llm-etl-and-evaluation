"""Input loading for the ETL pipeline."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from llm_etl_eval.etl.models import RawEvent, RawTicket


@dataclass(frozen=True)
class IngestConfig:
    """Configuration for ingesting raw data."""

    tickets_path: Path
    events_path: Path


class IngestError(RuntimeError):
    """Raised when raw data does not match expectations."""


REQUIRED_TICKET_COLUMNS = {
    "ticket_id",
    "customer_id",
    "created_at",
    "category",
    "priority",
    "summary",
    "language",
    "metadata",
}

REQUIRED_EVENT_FIELDS = {"ticket_id", "event_type", "occurred_at", "payload"}


def load_tickets_csv(path: Path) -> list[RawTicket]:
    """Load tickets from a CSV file and validate required columns."""

    if not path.exists():
        raise IngestError(f"Tickets file not found: {path}")

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise IngestError("Tickets CSV missing header row.")

        missing = REQUIRED_TICKET_COLUMNS - set(reader.fieldnames)
        if missing:
            raise IngestError(f"Tickets CSV missing columns: {sorted(missing)}")

        rows: list[RawTicket] = []
        for idx, row in enumerate(reader, start=2):
            try:
                rows.append(
                    RawTicket(
                        ticket_id=str(row["ticket_id"]).strip(),
                        customer_id=str(row["customer_id"]).strip(),
                        created_at=str(row["created_at"]).strip(),
                        category=str(row["category"]).strip(),
                        priority=str(row["priority"]).strip(),
                        summary=str(row["summary"]).strip(),
                        language=str(row["language"]).strip(),
                        metadata=str(row["metadata"]).strip(),
                    )
                )
            except KeyError as exc:
                raise IngestError(f"Tickets CSV missing column at line {idx}: {exc}") from exc

    return rows


def load_events_jsonl(path: Path) -> list[RawEvent]:
    """Load events from a JSONL file and validate required fields."""

    if not path.exists():
        raise IngestError(f"Events file not found: {path}")

    rows: list[RawEvent] = []
    with path.open("r", encoding="utf-8") as handle:
        for idx, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise IngestError(f"Invalid JSON at line {idx}: {exc}") from exc

            missing = REQUIRED_EVENT_FIELDS - set(payload)
            if missing:
                raise IngestError(f"Events JSONL missing fields at line {idx}: {sorted(missing)}")

            if not isinstance(payload["payload"], dict):
                raise IngestError(f"Events JSONL payload is not an object at line {idx}")

            rows.append(
                RawEvent(
                    ticket_id=str(payload["ticket_id"]).strip(),
                    event_type=str(payload["event_type"]).strip(),
                    occurred_at=str(payload["occurred_at"]).strip(),
                    payload=payload["payload"],
                )
            )

    return rows


def load_raw(config: IngestConfig) -> tuple[list[RawTicket], list[RawEvent]]:
    """Load raw tickets and events from disk."""

    tickets = load_tickets_csv(config.tickets_path)
    events = load_events_jsonl(config.events_path)
    return tickets, events
