"""Sync→async LLM adapter for shadow-run.

Spec: SPECS/SHADOW_RUN_V3.md section 3.

Duck-types against the legacy `LLMProvider` interface via a local Protocol;
no import dependency on `app.services.llm`.

Translates `TimeoutError` and generic exceptions into the typed
`policy_core_v3.invoker.LLMTimeout` / `LLMProviderError` so that v3's
deterministic retry policy can route them.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from app.policy_core_v3.invoker import LLMProviderError, LLMTimeout


@dataclass
class SyncLLMResponse:
    """Mirror of the legacy `LLMResponse` shape — local copy to avoid the
    `app.services.llm` import dependency."""

    content: str
    model: str
    usage: dict | None = None


@runtime_checkable
class SyncLLMProvider(Protocol):
    """Subset of the legacy `LLMProvider.generate` signature.

    Only the fields actually used by the shadow path are listed; production
    providers carry more keyword arguments which we forward via **kwargs.
    """

    def generate(
        self,
        messages: list[dict],
        model: str | None = ...,
        temperature: float | None = ...,
        max_tokens: int = ...,
        timeout_seconds: float | None = ...,
        response_format: dict[str, Any] | None = ...,
        reasoning_effort: str | None = ...,
    ) -> SyncLLMResponse: ...


class SyncToAsyncLLMAdapter:
    """Async-callable wrapper for a synchronous LLM provider.

    Instances are `policy_core_v3.LLMCallable`-compatible: `await adapter(prompt)`
    returns the raw model text or raises `LLMTimeout` / `LLMProviderError`.
    """

    def __init__(
        self,
        provider: SyncLLMProvider,
        *,
        model: str | None = None,
        temperature: float | None = 0.0,
        max_tokens: int = 1500,
        timeout_seconds: float | None = 30.0,
        response_format: dict[str, Any] | None = None,
        reasoning_effort: str | None = None,
    ) -> None:
        self._provider = provider
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._timeout_seconds = timeout_seconds
        self._response_format = response_format
        self._reasoning_effort = reasoning_effort

    async def __call__(self, prompt: str) -> str:
        messages = [{"role": "user", "content": prompt}]
        try:
            response = await asyncio.to_thread(
                self._provider.generate,
                messages,
                self._model,
                self._temperature,
                self._max_tokens,
                self._timeout_seconds,
                self._response_format,
                self._reasoning_effort,
            )
        except (TimeoutError, asyncio.TimeoutError) as exc:
            raise LLMTimeout(str(exc)) from exc
        except LLMTimeout:
            raise
        except LLMProviderError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            raise LLMProviderError(str(exc)) from exc

        # `response` should be a SyncLLMResponse-like; tolerate plain str/dict
        # too so test stubs and minor provider drift do not leak as
        # provider_error.
        content = _extract_content(response)
        if content is None:
            raise LLMProviderError("provider returned no content field")
        return content


def _extract_content(response: Any) -> str | None:
    if isinstance(response, str):
        return response
    if hasattr(response, "content"):
        value = getattr(response, "content")
        if isinstance(value, str):
            return value
    if isinstance(response, dict):
        value = response.get("content")
        if isinstance(value, str):
            return value
    return None
