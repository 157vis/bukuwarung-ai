"""Unit tests Fonnte WhatsApp utils — mock HTTP."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from utils import whatsapp


@pytest.mark.asyncio
async def test_send_message_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("httpx.AsyncClient") as client_cls:
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.__aexit__.return_value = None
        client.post = AsyncMock(return_value=mock_resp)
        client_cls.return_value = client

        ok = await whatsapp.send_message("62811", "halo", token="test-token")
        assert ok is True


@pytest.mark.asyncio
async def test_send_message_retry_on_error():
    with patch("httpx.AsyncClient") as client_cls:
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.__aexit__.return_value = None
        client.post = AsyncMock(side_effect=httpx.ConnectError("fail"))
        client_cls.return_value = client
        with patch("utils.whatsapp.asyncio.sleep", new_callable=AsyncMock):
            ok = await whatsapp.send_message("62811", "halo", token="test-token")
        assert ok is False


@pytest.mark.asyncio
async def test_send_image():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch("utils.whatsapp._fonnte_post", new_callable=AsyncMock, return_value=True) as post:
        ok = await whatsapp.send_image("62811", "https://img.test/a.jpg", "caption", token="tok")
        assert ok is True
        post.assert_awaited_once()
        assert post.call_args[0][0]["url"] == "https://img.test/a.jpg"


@pytest.mark.asyncio
async def test_send_button():
    with patch("utils.whatsapp._fonnte_post", new_callable=AsyncMock, return_value=True) as post:
        ok = await whatsapp.send_button("62811", "Pilih:", ["Ya", "Tidak"])
        assert ok is True
        payload = post.call_args[0][0]
        assert payload["button1"] == "Ya"
        assert payload["button2"] == "Tidak"
