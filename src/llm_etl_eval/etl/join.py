"""Join tickets and events by ticket_id."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from llm_etl_eval.etl.models import CleanEvent, CleanTicket, JoinedRecord


def join_by_ticket(
    tickets: list[CleanTicket], events: list[CleanEvent]
) -> list[JoinedRecord]:
    """Group events by ticket and return joined records."""

    events_by_ticket: dict[str, list[CleanEvent]] = defaultdict(list)
    for event in events:
        events_by_ticket[event.ticket_id].append(event)

    joined: list[JoinedRecord] = []
    for ticket in tickets:
        joined.append(
            JoinedRecord(
                ticket=ticket,
                events=sorted(
                    events_by_ticket.get(ticket.ticket_id, []),
                    key=lambda event: event.occurred_at
                    or datetime.max.replace(tzinfo=timezone.utc),
                ),
            )
        )

    return joined
