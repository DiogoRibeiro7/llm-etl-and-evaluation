"""Anthropic SDK provider for the Claude family.

The `anthropic` package is intentionally an optional dependency: the
import is deferred until the provider is actually used so that environments
without an API key (CI, the simulator-only demo) don't pay for it.

For tests, pass `client=...` to inject a fake; the lazy import path is
skipped entirely.
"""

from __future__ import annotations

import os
import time
from typing import Any

from llm_etl_eval.llm.provider import LLMResponse

DEFAULT_MODEL = "claude-haiku-4-5"
DEFAULT_MAX_TOKENS = 1024


class AnthropicProvider:
    """Provider that calls Anthropic's Messages API."""

    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        api_key: str | None = None,
        client: Any | None = None,
    ) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self._api_key = api_key
        self._client = client

    @property
    def name(self) -> str:
        return f"anthropic:{self.model}"

    def _ensure_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            import anthropic  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - exercised only without the SDK
            raise RuntimeError(
                "The 'anthropic' package is not installed. "
                "Install it with `pip install anthropic` (or use the simulator)."
            ) from exc
        api_key = self._api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._client = anthropic.Anthropic(api_key=api_key)
        return self._client

    def complete(self, *, system: str, user: str) -> LLMResponse:
        """Send a single message and return the parsed response."""

        client = self._ensure_client()
        start = time.monotonic()
        response = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        latency_ms = int((time.monotonic() - start) * 1000)

        text_parts: list[str] = []
        for block in response.content:
            if getattr(block, "type", None) == "text":
                text_parts.append(block.text)
        text = "".join(text_parts)

        return LLMResponse(
            text=text,
            input_tokens=int(response.usage.input_tokens),
            output_tokens=int(response.usage.output_tokens),
            latency_ms=latency_ms,
            model=self.model,
        )
