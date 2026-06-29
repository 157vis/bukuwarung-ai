"""Unit tests FastAPI webhook & endpoints — mock Fonnte."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


@pytest.fixture
def client():
    import main

    mock_orch = MagicMock()
    mock_result = MagicMock()
    mock_result.text = "Halo dari bot"
    mock_result.agent_id = "cs"
    mock_result.intent = "greeting"
    mock_result.data = {}
    mock_orch.process = AsyncMock(return_value=mock_result)
    mock_orch.stats.to_dict.return_value = {
        "total_messages": 5,
        "avg_response_ms": 120.5,
        "agent_usage": {"cs": 3, "sales": 2},
        "errors": 0,
        "clarifications": 1,
        "escalations": 0,
    }
    mock_orch._otak = MagicMock()
    mock_orch._otak.terima_feedback = AsyncMock(return_value={"id": "mem1"})

    with patch.object(main, "get_orchestrator", return_value=mock_orch):
        with patch("main.send_message", new_callable=AsyncMock, return_value=True):
            yield TestClient(main.app), mock_orch


def test_health(client):
    tc, _ = client
    resp = tc.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "shutting_down")
    assert "version" in data


def test_stats(client):
    tc, _ = client
    resp = tc.get("/stats")
    assert resp.status_code == 200
    assert resp.json()["total_messages"] == 5


def test_webhook_whatsapp_ok(client):
    tc, mock_orch = client
    resp = tc.post(
        "/webhook-whatsapp",
        json={"sender": "628123456789", "message": "halo", "client_id": "toko_test"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["agent"] == "cs"
    mock_orch.process.assert_awaited_once()


def test_webhook_ignored_no_text(client):
    tc, mock_orch = client
    resp = tc.post("/webhook-whatsapp", json={"sender": "62811"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"
    mock_orch.process.assert_not_awaited()


def test_webhook_ignored_bot_echo(client):
    tc, mock_orch = client
    resp = tc.post(
        "/webhook-whatsapp",
        json={
            "sender": "628123456789",
            "message": "Maaf, ada gangguan sebentar. Coba kirim lagi ya",
            "client_id": "toko_test",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"
    assert resp.json()["reason"] == "outgoing echo"
    mock_orch.process.assert_not_awaited()


def test_webhook_ignored_from_me(client):
    tc, mock_orch = client
    resp = tc.post(
        "/webhook-whatsapp",
        json={"sender": "628123456789", "message": "halo", "fromMe": "true"},
    )
    assert resp.status_code == 200
    assert resp.json()["reason"] == "outgoing echo"
    mock_orch.process.assert_not_awaited()


def test_feedback_endpoint(client):
    tc, mock_orch = client
    resp = tc.post(
        "/feedback",
        json={"user_id": "62811", "memory_id": "mem-abc", "rating": 1.0, "komentar": "bagus"},
    )
    assert resp.status_code == 200
    assert resp.json()["rating"] == 1.0
    mock_orch._otak.terima_feedback.assert_awaited_once()
