"""Sync→async LLM adapter tests."""
from __future__ import annotations

import asyncio

import pytest

from app.policy_core_v3.invoker import LLMProviderError, LLMTimeout
from app.policy_core_v3_shadow.llm_adapter import (
    SyncLLMResponse,
    SyncToAsyncLLMAdapter,
)


class _StubProvider:
    def __init__(self, response):
        self._response = response
        self.calls: list[dict] = []

    def generate(
        self,
        messages,
        model=None,
        temperature=None,
        max_tokens=1000,
        timeout_seconds=None,
        response_format=None,
        reasoning_effort=None,
    ):
        self.calls.append(
            {
                "messages": messages,
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "timeout_seconds": timeout_seconds,
                "response_format": response_format,
                "reasoning_effort": reasoning_effort,
            }
        )
        if isinstance(self._response, BaseException):
            raise self._response
        return self._response


@pytest.mark.asyncio
async def test_returns_content_string() -> None:
    provider = _StubProvider(SyncLLMResponse(content='{"ok":true}', model="x"))
    adapter = SyncToAsyncLLMAdapter(provider, model="m", max_tokens=42)
    out = await adapter("hello")
    assert out == '{"ok":true}'
    assert provider.calls[0]["messages"] == [{"role": "user", "content": "hello"}]
    assert provider.calls[0]["model"] == "m"
    assert provider.calls[0]["max_tokens"] == 42


@pytest.mark.asyncio
async def test_handles_plain_string_response() -> None:
    provider = _StubProvider("hello world")
    adapter = SyncToAsyncLLMAdapter(provider)
    assert await adapter("p") == "hello world"


@pytest.mark.asyncio
async def test_handles_dict_response_with_content_field() -> None:
    provider = _StubProvider({"content": "yo", "model": "m"})
    adapter = SyncToAsyncLLMAdapter(provider)
    assert await adapter("p") == "yo"


@pytest.mark.asyncio
async def test_response_without_content_raises_provider_error() -> None:
    provider = _StubProvider({"model": "m"})
    adapter = SyncToAsyncLLMAdapter(provider)
    with pytest.raises(LLMProviderError):
        await adapter("p")


@pytest.mark.asyncio
async def test_timeout_translated() -> None:
    provider = _StubProvider(asyncio.TimeoutError("boom"))
    adapter = SyncToAsyncLLMAdapter(provider)
    with pytest.raises(LLMTimeout):
        await adapter("p")


@pytest.mark.asyncio
async def test_builtin_timeout_error_translated() -> None:
    provider = _StubProvider(TimeoutError("nope"))
    adapter = SyncToAsyncLLMAdapter(provider)
    with pytest.raises(LLMTimeout):
        await adapter("p")


@pytest.mark.asyncio
async def test_generic_exception_translated_to_provider_error() -> None:
    provider = _StubProvider(RuntimeError("upstream 500"))
    adapter = SyncToAsyncLLMAdapter(provider)
    with pytest.raises(LLMProviderError):
        await adapter("p")
