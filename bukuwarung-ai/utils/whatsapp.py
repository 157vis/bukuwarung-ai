"""Fonnte WhatsApp integration — kirim pesan, gambar, tombol."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from config import get_settings

logger = logging.getLogger(__name__)

FONNTE_SEND_URL = "https://api.fonnte.com/send"
MAX_RETRIES = 3
RETRY_DELAY_SEC = 1.5


async def _fonnte_post(payload: dict[str, Any], *, token: str | None = None) -> bool:
    """POST ke Fonnte dengan retry exponential backoff."""
    api_key = token or get_settings().fonnte_token
    if not api_key:
        logger.warning("fonnte: token kosong")
        return False

    headers = {"Authorization": api_key}
    last_err: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(FONNTE_SEND_URL, headers=headers, data=payload)
            if resp.status_code < 400:
                logger.info("fonnte OK target=%s attempt=%d", payload.get("target"), attempt)
                return True
            if resp.status_code == 429:
                logger.warning("fonnte rate limit attempt=%d", attempt)
            else:
                logger.warning("fonnte HTTP %s: %s", resp.status_code, resp.text[:120])
        except httpx.HTTPError as exc:
            last_err = exc
            logger.warning("fonnte error attempt=%d: %s", attempt, exc)

        if attempt < MAX_RETRIES:
            await asyncio.sleep(RETRY_DELAY_SEC * attempt)

    logger.error("fonnte gagal setelah %d percobaan: %s", MAX_RETRIES, last_err)
    return False


def _normalize_phone(phone: str) -> str:
    return "".join(c for c in phone if c.isdigit())


async def send_message(
    phone: str,
    message: str,
    *,
    token: str | None = None,
    inboxid: str | None = None,
) -> bool:
    """Kirim pesan teks via Fonnte.

    Args:
        phone: Nomor tujuan (628xx).
        message: Teks balasan.
        token: Fonnte token; default dari env.
        inboxid: Opsional inbox Fonnte.

    Returns:
        True jika berhasil.
    """
    target = _normalize_phone(phone)
    if not target or not message:
        logger.warning("send_message: phone/message kosong")
        return False

    payload: dict[str, Any] = {"target": target, "message": message}
    if inboxid:
        payload["inboxid"] = inboxid
    return await _fonnte_post(payload, token=token)


async def send_image(
    phone: str,
    image_url: str,
    caption: str = "",
    *,
    token: str | None = None,
    inboxid: str | None = None,
) -> bool:
    """Kirim gambar dengan caption opsional."""
    target = _normalize_phone(phone)
    if not target or not image_url:
        logger.warning("send_image: phone/image_url kosong")
        return False

    payload: dict[str, Any] = {
        "target": target,
        "url": image_url,
        "message": caption or " ",
    }
    if inboxid:
        payload["inboxid"] = inboxid
    return await _fonnte_post(payload, token=token)


async def send_button(
    phone: str,
    text: str,
    buttons: list[str],
    *,
    token: str | None = None,
    inboxid: str | None = None,
) -> bool:
    """Kirim pesan dengan tombol quick-reply (Fonnte button format)."""
    target = _normalize_phone(phone)
    if not target or not text or not buttons:
        logger.warning("send_button: parameter kosong")
        return False

    # Fonnte: button1, button2, ...
    payload: dict[str, Any] = {"target": target, "message": text}
    for i, label in enumerate(buttons[:3], start=1):
        payload[f"button{i}"] = label
    if inboxid:
        payload["inboxid"] = inboxid
    return await _fonnte_post(payload, token=token)


# Backward-compatible alias
async def send_whatsapp_message(
    phone: str,
    message: str,
    *,
    token: str | None = None,
    inboxid: str | None = None,
) -> bool:
    return await send_message(phone, message, token=token, inboxid=inboxid)
