"""FastAPI entry point — BukuWarung-AI multi-agent WhatsApp CS UMKM."""

from __future__ import annotations

import json
import logging
import sys
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

APP_VERSION = "1.0.0"
_orchestrator: Orchestrator | None = None
_rate_limiter = RateLimiter(max_requests=60, window_seconds=60.0)
_shutting_down = False


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    configured: bool
    shutting_down: bool = False


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
    phone = str(body.get("member") or body.get("sender") or body.get("phone") or body.get("user_id") or "")
    text = str(body.get("message") or body.get("text") or "").strip()
    inboxid = body.get("inboxid")
    client_id = str(body.get("client_id") or get_settings().app_name)
    phone = "".join(c for c in phone if c.isdigit())
    return phone, text, str(inboxid) if inboxid else None, client_id


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
    )


@app.get("/")
async def root() -> dict[str, Any]:
    return {
        "status": "running",
        "health": "/health",
        "webhook": "/webhook-whatsapp",
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


@app.post("/webhook-whatsapp", response_model=WebhookResponse)
async def webhook_whatsapp(request: Request) -> WebhookResponse | JSONResponse:
    _check_shutdown()
    body = await _parse_body(request)
    phone, text, inboxid, client_id = _extract_webhook_fields(body)

    if not phone or not text:
        logger.info("webhook ignored: no phone/text body_keys=%s", list(body.keys()))
        return WebhookResponse(status="ignored", reason="no phone or text")

    _check_rate_limit(request, phone)
    logger.info("webhook in user=%s client=%s msg=%r", phone, client_id, text[:80])

    try:
        orch = get_orchestrator()
        result = await orch.process(client_id=client_id, user_id=phone, message=text)
        sent = await send_message(phone, result.text, inboxid=inboxid)
        return WebhookResponse(
            status="ok" if sent else "ok_unsent",
            agent=result.agent_id,
            intent=result.intent,
        )
    except HTTPException:
        raise
    except (httpx.HTTPError, RuntimeError, ValueError) as exc:
        logger.exception("webhook error: %s", exc)
        fallback = "Maaf, ada gangguan sebentar. Coba kirim lagi ya 🙏"
        await send_message(phone, fallback, inboxid=inboxid)
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
