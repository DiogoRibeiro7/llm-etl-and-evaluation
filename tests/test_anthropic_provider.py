"""Tests for the Anthropic provider with a mocked SDK client."""

from __future__ import annotations

from llm_etl_eval.llm.anthropic_provider import AnthropicProvider


class _FakeContent:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _FakeUsage:
    def __init__(self, input_tokens: int, output_tokens: int) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class _FakeResponse:
    def __init__(self, text: str, input_tokens: int, output_tokens: int) -> None:
        self.content = [_FakeContent(text)]
        self.usage = _FakeUsage(input_tokens, output_tokens)


class _FakeMessages:
    def __init__(self, response: _FakeResponse) -> None:
        self._response = response
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> _FakeResponse:
        self.calls.append(kwargs)
        return self._response


class _FakeClient:
    def __init__(self, response: _FakeResponse) -> None:
        self.messages = _FakeMessages(response)


def test_anthropic_provider_passes_request_correctly() -> None:
    fake_client = _FakeClient(_FakeResponse('{"ok": true}', 50, 10))
    provider = AnthropicProvider(
        model="claude-haiku-4-5",
        max_tokens=512,
        client=fake_client,
    )

    response = provider.complete(system="be precise", user="hello")

    assert response.text == '{"ok": true}'
    assert response.input_tokens == 50
    assert response.output_tokens == 10
    assert response.model == "claude-haiku-4-5"
    assert response.latency_ms >= 0

    assert len(fake_client.messages.calls) == 1
    call = fake_client.messages.calls[0]
    assert call["model"] == "claude-haiku-4-5"
    assert call["max_tokens"] == 512
    assert call["system"] == "be precise"
    assert call["messages"] == [{"role": "user", "content": "hello"}]


def test_anthropic_provider_concatenates_multiple_text_blocks() -> None:
    response = _FakeResponse("", 1, 1)
    response.content = [_FakeContent("part-A "), _FakeContent("part-B")]
    fake_client = _FakeClient(response)
    provider = AnthropicProvider(client=fake_client)

    result = provider.complete(system="s", user="u")
    assert result.text == "part-A part-B"


def test_anthropic_provider_skips_non_text_blocks() -> None:
    response = _FakeResponse("", 1, 1)
    non_text = _FakeContent("ignored")
    non_text.type = "tool_use"
    response.content = [_FakeContent("kept"), non_text]
    fake_client = _FakeClient(response)
    provider = AnthropicProvider(client=fake_client)

    result = provider.complete(system="s", user="u")
    assert result.text == "kept"


def test_anthropic_provider_name_includes_model() -> None:
    provider = AnthropicProvider(model="claude-sonnet-4-6", client=object())
    assert provider.name == "anthropic:claude-sonnet-4-6"
