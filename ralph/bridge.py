"""SDK bridge — unified interface to Anthropic, OpenAI, and Google AI models.

Routes through cli-proxy when available, falls back to direct SDK calls.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, AsyncIterator

import httpx

logger = logging.getLogger("ralph.bridge")


class ModelBridge:
    """Unified interface for multi-provider LLM calls."""

    def __init__(self, cli_proxy_url: str = "http://localhost:8317"):
        self.cli_proxy_url = cli_proxy_url
        self._http: httpx.AsyncClient | None = None
        self._anthropic = None
        self._openai = None

    @property
    def http(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=120.0)
        return self._http

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: str = "claude-sonnet-4-20250514",
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Send a completion request, routing through cli-proxy or direct SDK."""

        # Try cli-proxy first (handles rotation, failover, auth)
        try:
            return await self._via_proxy(messages, model, system, temperature, max_tokens, tools)
        except Exception as e:
            logger.warning(f"cli-proxy failed: {e}, falling back to direct SDK")

        # Fall back to direct SDK
        if "claude" in model or "anthropic" in model:
            return await self._via_anthropic(messages, model, system, temperature, max_tokens, tools)
        elif "gpt" in model or "o1" in model or "o3" in model:
            return await self._via_openai(messages, model, system, temperature, max_tokens, tools)
        else:
            raise ValueError(f"No provider available for model: {model}")

    async def _via_proxy(self, messages, model, system, temperature, max_tokens, tools) -> dict:
        """Route through cli-proxy with OpenAI-compatible API."""
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system:
            payload["messages"] = [{"role": "system", "content": system}] + messages
        if tools:
            payload["tools"] = tools

        resp = await self.http.post(
            f"{self.cli_proxy_url}/v1/chat/completions",
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()

    async def _via_anthropic(self, messages, model, system, temperature, max_tokens, tools) -> dict:
        """Direct Anthropic SDK call."""
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("anthropic SDK not installed. Run: pip install anthropic")

        if self._anthropic is None:
            self._anthropic = anthropic.AsyncAnthropic(
                api_key=os.environ.get("ANTHROPIC_API_KEY", "")
            )

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools

        response = await self._anthropic.messages.create(**kwargs)
        # Normalize to dict
        return {
            "id": response.id,
            "model": response.model,
            "content": [{"type": b.type, "text": getattr(b, "text", None)} for b in response.content],
            "usage": {"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens},
            "stop_reason": response.stop_reason,
        }

    async def _via_openai(self, messages, model, system, temperature, max_tokens, tools) -> dict:
        """Direct OpenAI SDK call."""
        try:
            import openai
        except ImportError:
            raise RuntimeError("openai SDK not installed. Run: pip install openai")

        if self._openai is None:
            self._openai = openai.AsyncOpenAI(
                api_key=os.environ.get("OPENAI_API_KEY", "")
            )

        if system:
            messages = [{"role": "system", "content": system}] + messages

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools

        response = await self._openai.chat.completions.create(**kwargs)
        choice = response.choices[0]
        return {
            "id": response.id,
            "model": response.model,
            "content": [{"type": "text", "text": choice.message.content}],
            "usage": {"input_tokens": response.usage.prompt_tokens, "output_tokens": response.usage.completion_tokens},
            "stop_reason": choice.finish_reason,
        }

    async def close(self):
        if self._http:
            await self._http.aclose()
