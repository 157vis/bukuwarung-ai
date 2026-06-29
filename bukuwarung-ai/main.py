"""FastAPI entry point — BukuWarung-AI multi-agent WhatsApp CS UMKM."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from agents import build_agents
from config import PROJECT_ROOT, ensure_data_dir, get_settings
from core.client_registry import ClientConfig, get_client_registry
from core.otak_ai import OtakAI
from core.personality import PersonalityEngine
from core.semantic_router import SemanticRouter
from orchestrator import Orchestrator
from utils.embeddings import GroqEmbeddingClient
from utils.openrouter import OpenRouterClient
from utils.rate_limit import RateLimiter
from utils.whatsapp import send_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

APP_VERSION = "1.0.1"
_orchestrator: Orchestrator | None = None
_client_registry = None
_rate_limiter = RateLimiter(max_requests=60, window_seconds=60.0)
_shutting_down = False

# Anti-loop: abaikan echo balasan bot / pesan error berulang (Fonnte Quick ON)
BOT_ECHO_MARKERS = (
    "gangguan sebentar",
    "ada gangguan",
    "ada kendala teknis",
    "coba kirim lagi",
    "selamat datang! kami siap bantu",
    "mohon maaf atas ketidaknyamanannya",
)
ERROR_REPLY_COOLDOWN_SEC = 120.0
DEDUP_WINDOW_SEC = 30.0
_recent_inbound: dict[str, float] = {}
_recent_error_sent: dict[str, float] = {}
TXN_CMD_INCOME = ("jual", "pemasukan", "masuk", "terima", "bayar masuk")
TXN_CMD_EXPENSE = ("beli", "pengeluaran", "keluar", "bayar", "belanja")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    configured: bool
    shutting_down: bool = False
    missing_env: list[str] = Field(default_factory=list)


class WebhookResponse(BaseModel):
    status: str
    agent: str | None = None
    intent: str | None = None
    version: str = APP_VERSION
    reason: str | None = None


class FeedbackRequest(BaseModel):
    user_id: str = Field(..., description="ID pelanggan / nomor WA")
    memory_id: str = Field(..., description="ID memory yang di-feedback")
    rating: float = Field(..., ge=-1.0, le=1.0, description="👍=1.0, 👎=-1.0")
    komentar: str = ""


class FeedbackResponse(BaseModel):
    status: str
    memory_id: str
    rating: float


class StatsResponse(BaseModel):
    total_messages: int
    avg_response_ms: float
    agent_usage: dict[str, int]
    errors: int
    clarifications: int
    escalations: int
    version: str = APP_VERSION


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------


class _OfflineDB:
    """Fallback DB saat Supabase belum dikonfigurasi."""

    def table(self, name: str):
        raise ConnectionError("supabase offline")


def _get_db():
    """Supabase client atau offline fallback (USB / smoke test tanpa DB)."""
    settings = get_settings()
    if not settings.is_supabase_live:
        logger.info("Supabase offline mode — pakai memory lokal")
        return _OfflineDB()
    try:
        from utils.supabase import get_supabase_client

        return get_supabase_client()
    except RuntimeError:
        return _OfflineDB()


def _build_orchestrator() -> Orchestrator:
    settings = get_settings()
    db = _get_db()

    otak = OtakAI(db, GroqEmbeddingClient(settings.groq_api_key))
    personality = PersonalityEngine(db)
    llm = OpenRouterClient()
    router = SemanticRouter(llm)
    agents = build_agents(otak, personality, llm)
    return Orchestrator(otak, router, personality, agents)


def get_registry():
    global _client_registry
    if _client_registry is None:
        _client_registry = get_client_registry(_get_db())
    return _client_registry


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = _build_orchestrator()
    return _orchestrator


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _shutting_down
    settings = get_settings()
    ensure_data_dir()
    missing = settings.validate_required()
    if missing:
        logger.warning("Env belum lengkap: %s", ", ".join(missing))
    else:
        logger.info("BukuWarung-AI v%s | model: %s", APP_VERSION, settings.primary_model)
    get_orchestrator()
    yield
    _shutting_down = True
    logger.info("Graceful shutdown — BukuWarung-AI stopped")


app = FastAPI(
    title=get_settings().app_name,
    description="Sistem AI multi-agent untuk WhatsApp CS UMKM Indonesia",
    version=APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _parse_body(request: Request) -> dict[str, Any]:
    raw = await request.body()
    ctype = (request.headers.get("content-type") or "").lower()
    if raw and ("application/json" in ctype or raw[:1] in (b"{", b"[")):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    if raw and b"=" in raw:
        parsed = parse_qs(raw.decode("utf-8", errors="replace"), keep_blank_values=True)
        return {k: (v[0] if v else "") for k, v in parsed.items()}
    try:
        form = await request.form()
        return dict(form) if form else {}
    except (RuntimeError, ValueError):
        return {}


def _extract_webhook_fields(body: dict[str, Any]) -> tuple[str, str, str | None, str]:
    phone = str(
        body.get("member")
        or body.get("sender")
        or body.get("from")
        or body.get("phone")
        or body.get("user_id")
        or ""
    )
    text = str(body.get("message") or body.get("text") or body.get("pesan") or "").strip()
    inboxid = body.get("inboxid")
    client_id = str(body.get("client_id") or get_settings().app_name)
    phone = "".join(c for c in phone if c.isdigit())
    return phone, text, str(inboxid) if inboxid else None, client_id


def _normalize_digits(value: Any) -> str:
    return "".join(c for c in str(value or "") if c.isdigit())


def _resolve_fonnte_token(client_config: ClientConfig | None) -> str | None:
    """Token per-client, fallback ke FONNTE_TOKEN global di Railway."""
    per_client = (client_config.fonnte_token if client_config else "") or ""
    global_token = get_settings().fonnte_token or ""
    token = (per_client or global_token).strip()
    return token or None


def _is_outgoing_echo(body: dict[str, Any], phone: str, text: str = "") -> bool:
    """Abaikan pesan keluar / echo balasan bot (Fonnte Quick ON)."""
    device = _normalize_digits(body.get("device"))
    sender = _normalize_digits(phone)
    if device and sender and device == sender:
        return True

    for key in ("fromMe", "from_me", "isme", "is_me", "outgoing", "isOutgoing"):
        val = str(body.get(key) or "").lower()
        if val in ("1", "true", "yes", "outgoing"):
            return True

    lower = (text or "").strip().lower()
    if lower and any(marker in lower for marker in BOT_ECHO_MARKERS):
        return True
    return False


def _is_duplicate_inbound(body: dict[str, Any], phone: str, text: str) -> bool:
    """Debounce webhook identik dalam beberapa detik."""
    ts = str(body.get("timestamp") or body.get("id") or body.get("message_id") or "")
    key = f"{_normalize_digits(phone)}:{ts}:{text.strip().lower()[:160]}"
    now = time.time()
    stale = [k for k, t0 in _recent_inbound.items() if now - t0 > DEDUP_WINDOW_SEC]
    for k in stale:
        _recent_inbound.pop(k, None)
    if key in _recent_inbound:
        return True
    _recent_inbound[key] = now
    return False


async def _send_error_once(
    phone: str,
    *,
    token: str | None,
    inboxid: str | None,
) -> bool:
    """Kirim pesan error maksimal sekali per nomor per cooldown — cegah loop WA."""
    key = _normalize_digits(phone)
    now = time.time()
    last = _recent_error_sent.get(key, 0.0)
    if key and now - last < ERROR_REPLY_COOLDOWN_SEC:
        logger.warning("error reply suppressed (cooldown) user=%s", key)
        return False
    fallback = "Maaf, ada gangguan sebentar. Coba kirim lagi ya 🙏"
    sent = await send_message(phone, fallback, token=token, inboxid=inboxid)
    if sent and key:
        _recent_error_sent[key] = now
    return sent


async def _resolve_dashboard_user_id(phone: str) -> str | None:
    """Map nomor WA ke user_id dashboard (tabel wa_users)."""
    normalized = _normalize_digits(phone)
    if not normalized:
        return None
    db = _get_db()
    try:
        result = await asyncio.to_thread(
            lambda: (
                db.table("wa_users")
                .select("user_id")
                .eq("phone", normalized)
                .limit(1)
                .execute()
            )
        )
        rows = result.data or []
        if rows:
            return str(rows[0].get("user_id") or "")
    except Exception as exc:
        logger.warning("resolve dashboard user gagal phone=%s: %s", normalized, exc)
    return None


async def _log_wa_message(
    *,
    user_id: str | None,
    phone: str,
    role: str,
    content: str,
    agent_id: str | None = None,
) -> None:
    """Simpan log chat ke wa_messages agar terlihat di Ruang Komando."""
    if not user_id or not content.strip():
        return
    db = _get_db()
    row: dict[str, Any] = {
        "user_id": str(user_id),
        "phone": _normalize_digits(phone),
        "role": role,
        "content": content[:1200],
    }
    if agent_id and role == "assistant":
        row["agent_id"] = agent_id
    try:
        await asyncio.to_thread(lambda: db.table("wa_messages").insert(row).execute())
    except Exception as exc:
        logger.warning("log wa_messages gagal user=%s: %s", user_id, exc)


def _parse_amount(text: str) -> int | None:
    """Ambil nominal dari teks: 50rb, 50.000, 50000."""
    cleaned = (text or "").lower().replace(".", "").replace(",", "")
    m = re.search(r"(\d+)\s*(rb|ribu|k)?", cleaned)
    if not m:
        return None
    val = int(m.group(1))
    if m.group(2) in ("rb", "ribu", "k"):
        val *= 1000
    return val if val > 0 else None


async def _record_dashboard_transaction_if_any(
    *,
    user_id: str | None,
    text: str,
) -> None:
    """Catat transaksi sederhana ke transactions dari chat owner."""
    if not user_id:
        return
    lower = (text or "").lower()
    txn_type = None
    if any(k in lower for k in TXN_CMD_INCOME):
        txn_type = "Pemasukan"
    elif any(k in lower for k in TXN_CMD_EXPENSE):
        txn_type = "Pengeluaran"
    if not txn_type:
        return
    amount = _parse_amount(lower)
    if not amount:
        return

    category = "Penjualan" if txn_type == "Pemasukan" else "Belanja"
    note = text[:200]
    db = _get_db()
    try:
        prev = await asyncio.to_thread(
            lambda: (
                db.table("transactions")
                .select("running_balance")
                .eq("user_id", user_id)
                .order("id", desc=True)
                .limit(1)
                .execute()
            )
        )
        last_balance = float((prev.data or [{}])[0].get("running_balance") or 0)
        new_balance = last_balance + amount if txn_type == "Pemasukan" else last_balance - amount
        row = {
            "user_id": user_id,
            "date": time.strftime("%Y-%m-%d %H:%M"),
            "type": txn_type,
            "category": category,
            "amount": amount,
            "note": note,
            "running_balance": new_balance,
            "is_prive": False,
        }
        await asyncio.to_thread(lambda: db.table("transactions").insert(row).execute())
        logger.info("auto-catat transaction user=%s type=%s amount=%s", user_id, txn_type, amount)
    except Exception as exc:
        logger.warning("auto-catat transaction gagal user=%s: %s", user_id, exc)


def _client_key(request: Request, user_id: str = "") -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
    return user_id or ip


def _check_rate_limit(request: Request, user_id: str = "") -> None:
    key = _client_key(request, user_id)
    if not _rate_limiter.is_allowed(key):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")


def _check_shutdown() -> None:
    if _shutting_down:
        raise HTTPException(status_code=503, detail="Server shutting down")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok" if not _shutting_down else "shutting_down",
        app=settings.app_name,
        version=APP_VERSION,
        configured=settings.is_configured,
        shutting_down=_shutting_down,
        missing_env=settings.validate_required(),
    )


@app.get("/")
async def root() -> dict[str, Any]:
    return {
        "status": "running",
        "health": "/health",
        "webhook": "/webhook-whatsapp/{client_id}",
        "webhook_legacy": "/webhook-whatsapp",
        "clients": "/clients",
        "stats": "/stats",
        "version": APP_VERSION,
    }


@app.get("/stats", response_model=StatsResponse)
async def stats() -> StatsResponse:
    orch = get_orchestrator()
    s = orch.stats.to_dict()
    return StatsResponse(**s)


@app.post("/feedback", response_model=FeedbackResponse)
async def feedback(req: FeedbackRequest, request: Request) -> FeedbackResponse:
    _check_shutdown()
    _check_rate_limit(request, req.user_id)

    rating = 1.0 if req.rating > 0 else (-1.0 if req.rating < 0 else 0.0)
    orch = get_orchestrator()
    result = await orch._otak.terima_feedback(req.memory_id, rating, req.komentar)
    if result is None:
        raise HTTPException(status_code=404, detail="Memory tidak ditemukan")

    logger.info("feedback user=%s memory=%s rating=%.1f", req.user_id, req.memory_id, rating)
    return FeedbackResponse(status="ok", memory_id=req.memory_id, rating=rating)


@app.get("/clients")
async def list_clients() -> dict[str, Any]:
    """Daftar client aktif (multi-tenant)."""
    registry = get_registry()
    clients = await registry.list_active()
    return {
        "count": len(clients),
        "clients": [
            {"client_id": c.client_id, "name": c.name, "profile_key": c.profile_key}
            for c in clients
        ],
    }


async def _process_webhook(
    *,
    client_id: str,
    phone: str,
    text: str,
    inboxid: str | None,
    client_config: ClientConfig | None,
) -> WebhookResponse | JSONResponse:
    orch = get_orchestrator()
    fonnte_token = _resolve_fonnte_token(client_config)
    dashboard_user_id = await _resolve_dashboard_user_id(phone)
    await _log_wa_message(user_id=dashboard_user_id, phone=phone, role="user", content=text)
    await _record_dashboard_transaction_if_any(user_id=dashboard_user_id, text=text)

    result = await orch.process(
        client_id=client_id,
        user_id=phone,
        message=text,
        client_config=client_config,
    )
    sent = await send_message(phone, result.text, token=fonnte_token, inboxid=inboxid)
    await _log_wa_message(
        user_id=dashboard_user_id,
        phone=phone,
        role="assistant",
        content=result.text,
        agent_id=result.agent_id,
    )
    reason = None
    if not sent and not fonnte_token:
        reason = "fonnte_token_missing"
    elif not sent:
        reason = "fonnte_send_failed"
    return WebhookResponse(
        status="ok" if sent else "ok_unsent",
        agent=result.agent_id,
        intent=result.intent,
        reason=reason,
    )


@app.post("/webhook-whatsapp/{client_id}", response_model=WebhookResponse)
async def webhook_whatsapp_client(client_id: str, request: Request) -> WebhookResponse | JSONResponse:
    """Webhook per toko — RECOMMENDED untuk banyak client."""
    _check_shutdown()
    body = await _parse_body(request)
    phone, text, inboxid, _ = _extract_webhook_fields(body)

    if not phone or not text:
        logger.info("webhook ignored client=%s keys=%s", client_id, list(body.keys()))
        return WebhookResponse(status="ignored", reason="no phone or text")

    if _is_outgoing_echo(body, phone, text):
        return WebhookResponse(status="ignored", reason="outgoing echo")

    if _is_duplicate_inbound(body, phone, text):
        return WebhookResponse(status="ignored", reason="duplicate")

    registry = get_registry()
    client_config = await registry.get(client_id)
    if not client_config or not client_config.is_active:
        raise HTTPException(status_code=404, detail=f"Client '{client_id}' tidak ditemukan atau nonaktif")

    _check_rate_limit(request, f"{client_id}:{phone}")
    logger.info("webhook in client=%s user=%s msg=%r", client_id, phone, text[:80])

    try:
        return await _process_webhook(
            client_id=client_id,
            phone=phone,
            text=text,
            inboxid=inboxid,
            client_config=client_config,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("webhook error client=%s: %s", client_id, exc)
        await _send_error_once(phone, token=_resolve_fonnte_token(client_config), inboxid=inboxid)
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(exc)[:120]})


@app.post("/webhook-whatsapp", response_model=WebhookResponse)
async def webhook_whatsapp(request: Request) -> WebhookResponse | JSONResponse:
    """Webhook legacy — client_id dari body atau default APP_NAME."""
    _check_shutdown()
    body = await _parse_body(request)
    phone, text, inboxid, client_id = _extract_webhook_fields(body)

    if not phone or not text:
        logger.info("webhook ignored: no phone/text body_keys=%s", list(body.keys()))
        return WebhookResponse(status="ignored", reason="no phone or text")

    if _is_outgoing_echo(body, phone, text):
        return WebhookResponse(status="ignored", reason="outgoing echo")

    if _is_duplicate_inbound(body, phone, text):
        return WebhookResponse(status="ignored", reason="duplicate")

    registry = get_registry()
    client_config = await registry.get(client_id)
    if not client_config:
        client_config = ClientConfig(client_id=client_id, name=client_id)

    _check_rate_limit(request, phone)
    logger.info("webhook in user=%s client=%s msg=%r", phone, client_id, text[:80])

    try:
        return await _process_webhook(
            client_id=client_id,
            phone=phone,
            text=text,
            inboxid=inboxid,
            client_config=client_config,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("webhook error: %s", exc)
        await _send_error_once(phone, token=_resolve_fonnte_token(client_config), inboxid=inboxid)
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(exc)[:120]})


@app.api_route("/webhook", methods=["GET", "POST"])
async def webhook_legacy(request: Request) -> Any:
    """Backward-compatible alias untuk Fonnte webhook lama."""
    if request.method == "GET":
        return JSONResponse({"status": "webhook_ready", "version": APP_VERSION})
    return await webhook_whatsapp(request)


if __name__ == "__main__":
    import uvicorn

    s = get_settings()
    uvicorn.run("main:app", host=s.host, port=s.port, reload=s.debug)
