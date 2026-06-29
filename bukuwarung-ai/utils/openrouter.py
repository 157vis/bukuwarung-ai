"""OpenRouter client — model routing (primary / backup / free)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

from config import get_settings

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


@dataclass
class TokenUsage:
    """Akumulasi token OpenRouter per request / session."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def add(self, other: TokenUsage) -> None:
        self.prompt_tokens += other.prompt_tokens
        self.completion_tokens += other.completion_tokens
        self.total_tokens += other.total_tokens


class OpenRouterClient:
    """Async chat client untuk OpenRouter API."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        primary_model: str | None = None,
        backup_model: str | None = None,
        free_model: str | None = None,
    ) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.openrouter_api_key
        self._primary = primary_model or settings.primary_model
        self._backup = backup_model or settings.backup_model
        self._free = free_model or settings.free_model
        self.last_usage = TokenUsage()
        self.session_usage = TokenUsage()

    async def complete(self, prompt: str, *, model: str | None = None) -> str:
        """Single-turn completion (untuk personality LLM fallback)."""
        messages = [{"role": "user", "content": prompt}]
        return await self.chat(messages, model=model)

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 512,
    ) -> str:
        """Kirim chat completion; fallback model jika gagal."""
        chain = [m for m in [model, self._primary, self._backup, self._free] if m]
        last_err: Exception | None = None

        for m in chain:
            try:
                return await self._request(messages, m, temperature, max_tokens)
            except (httpx.HTTPError, ValueError, KeyError) as exc:
                logger.warning("OpenRouter model %s gagal: %s", m, exc)
                last_err = exc

        raise RuntimeError(f"Semua model OpenRouter gagal: {last_err}")

    async def _request(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        if not self._api_key:
            raise ValueError("OPENROUTER_API_KEY kosong")

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://bukuwarung-ai.local",
            "X-Title": "BukuWarung-AI",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(OPENROUTER_URL, headers=headers, json=payload)
            if resp.status_code == 429:
                raise httpx.HTTPStatusError(
                    "rate limited",
                    request=resp.request,
                    response=resp,
                )
            resp.raise_for_status()
            data = resp.json()
            usage_raw = data.get("usage") or {}
            usage = TokenUsage(
                prompt_tokens=int(usage_raw.get("prompt_tokens") or 0),
                completion_tokens=int(usage_raw.get("completion_tokens") or 0),
                total_tokens=int(usage_raw.get("total_tokens") or 0),
            )
            self.last_usage = usage
            self.session_usage.add(usage)
            if usage.total_tokens:
                logger.debug(
                    "OpenRouter tokens model=%s prompt=%d completion=%d",
                    model,
                    usage.prompt_tokens,
                    usage.completion_tokens,
                )
            return str(data["choices"][0]["message"]["content"]).strip()
