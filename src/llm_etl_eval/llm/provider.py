"""Provider abstractions for real LLM backends."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LLMResponse:
    """Single completion result with token usage and latency."""

    text: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    model: str


class LLMProvider(Protocol):
    """Minimal provider interface for completion-style calls.

    Any class with a `name` string and a `complete(*, system, user)` method
    that returns an `LLMResponse` satisfies this Protocol.
    """

    name: str

    def complete(self, *, system: str, user: str) -> LLMResponse:
        ...
