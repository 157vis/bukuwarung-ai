# main.py — Bot WhatsApp laris.AI
import json
import os
import re
import sys
import base64
import time
import asyncio
import random
from datetime import datetime
from urllib.parse import parse_qs

import httpx
from pathlib import Path
from fastapi import FastAPI, Request
from dotenv import load_dotenv
from groq import Groq

_BOT_DIR = Path(__file__).resolve().parent
_ROOT_DIR = _BOT_DIR.parent
# Root repo: brand.py, laris_core.py | Bot dir: agents.py
sys.path.insert(0, str(_ROOT_DIR))
sys.path.insert(0, str(_BOT_DIR))

from brand import APP_NAME, WA_BOT_TITLE, SCORE_LABEL

from agents import (
    ai_extractor_agent,
    vision_extractor_agent,
    voice_extractor_agent,
    db_insert_transaction,
    db_delete_transaction,
    get_dashboard_data,
    calculate_cuan_score,
    get_ai_advisor_insights,
    classify_wa_intent,
    get_ai_piutang_answer,
    resolve_user_id,
    core,
)
from orchestrator import orchestrate_transaction_created

load_dotenv(_BOT_DIR / ".env")

# ═══════════════════════════════════════════════
# KONFIGURASI NAMA BOT — Ganti di sini!
# ═══════════════════════════════════════════════
BOT_NAME = "Laris"          # Nama bot (manusiawi)
BOT_EMOJI = "🛒"            # Emoji ikon bot

app = FastAPI(title=WA_BOT_TITLE)

_raw_provider = os.environ.get("WA_PROVIDER", "fonnte").lower().strip()
# Toleransi typo "fonte" dari user
WA_PROVIDER = "fonnte" if _raw_provider in ("fonnte", "fonte") else _raw_provider
WA_API_KEY = os.environ.get("WA_API_KEY", "")
SAFEGUARD_MODEL = "openai/gpt-oss-safeguard-20b"
groq = Groq(api_key=os.environ["GROQ_API_KEY"])

# Ambang stok kritis: di bawah ini Logistik AI menyarankan PO (butuh approval owner).
STOCK_THRESHOLD = int(os.environ.get("STOCK_THRESHOLD", "10"))
REORDER_QTY = int(os.environ.get("REORDER_QTY", "5"))
BOT_LOGIC_VERSION = "2026-06-28-realistic-v5"

# Cegah loop: Fonnte autoread kadang mengirim balasan bot kembali ke webhook.
_BOT_TEXT_MARKERS = (
    "tercatat!",
    "webhook ok",
    "bot aktif",
    "belum paham",
    "logistik ai",
    "ruang komando",
    "saran ai",
    "tidak ada piutang",
    "daftar piutang",
    "struk terbaca",
    "suara terbaca",
    "belum terdaftar",
    "udah dicatat",
    "masuk buku",
    "noted!",
    "skor tokomu",
    "belum nangkep",
    "gangguan sebentar",
    BOT_NAME.lower(),
)
_recent_inbound: dict[str, float] = {}


# ═══════════════════════════════════════════════
# HELPER: Realistic Bot Behavior
# ═══════════════════════════════════════════════

def _bot_header() -> str:
    """Header pesan bot — pakai nama manusiawi."""
    return f"{BOT_EMOJI} *{BOT_NAME}*"


def _get_greeting() -> str:
    """Sapaan berdasarkan waktu (WIB)."""
    hour = datetime.now().hour
    if 5 <= hour < 11:
        return "Selamat pagi"
    elif 11 <= hour < 15:
        return "Selamat siang"
    elif 15 <= hour < 18:
        return "Selamat sore"
    else:
        return "Selamat malam"


def _random_confirm(data: list[dict]) -> str:
    """Variasi konfirmasi transaksi supaya tidak monoton."""
    lines = []
    for d in data:
        tipe = d.get("type", "")
        kat = d.get("category", "")
        amt = d.get("amount", 0)
        emoji = "💰" if tipe == "Pemasukan" else "💸"
        lines.append(f"{emoji} {kat}: Rp {amt:,.0f}")
    detail = "\n".join(lines)

    total = sum(d.get("amount", 0) for d in data)
    n = len(data)

    templates = [
        f"✅ Tercatat!\n{detail}",
        f"📝 Sip, udah dicatat!\n{detail}",
        f"👌 Masuk buku!\n{detail}",
        f"✅ Oke, tercatat ya~\n{detail}",
        f"📝 Noted!\n{detail}",
    ]
    base = random.choice(templates)
    if n > 1:
        base += f"\n\nTotal: Rp {total:,.0f} ({n} transaksi)"
    return base


def _random_typing_delay() -> float:
    """Delay acak supaya terasa seperti orang ngetik."""
    return random.uniform(0.8, 2.5)


async def is_safe_message(text: str) -> bool:
    try:
        res = groq.chat.completions.create(
            model=SAFEGUARD_MODEL,
            messages=[{
                "role": "user",
                "content": (
                    "Apakah pesan ini aman dan relevan dengan pencatatan keuangan UMKM? "
                    f"Jawab YA atau TIDAK saja.\nPesan: {text}"
                ),
            }],
            temperature=0,
            max_tokens=5,
        )
        return "YA" in res.choices[0].message.content.upper()
    except Exception:
        return True


def _normalize_wa_phone(phone: str) -> str:
    """Normalisasi nomor untuk kirim/baca WA (sama dengan laris_core.normalize_phone)."""
    return core.normalize_phone(phone or "")


def _is_outgoing_or_bot_echo(body: dict, phone: str, text: str) -> bool:
    """Abaikan pesan keluar / echo balasan bot (penyebab loop 'jual kopi' berulang)."""
    sender = _normalize_wa_phone(phone)
    device = _normalize_wa_phone(str(body.get("device") or ""))

    # Pesan dari device sendiri (Quick autoread ON di Fonnte).
    if device and sender and device == sender:
        return True

    for key in ("fromMe", "from_me", "isme", "is_me", "outgoing", "isOutgoing"):
        val = str(body.get(key) or "").lower()
        if val in ("1", "true", "yes", "outgoing"):
            return True

    t = (text or "").strip()
    if not t:
        return False

    if t[0] in "✅❌🤔💡🔥📋🗑️📦🛒📝👌📊📈💪💰💸🎉":
        return True

    lower = t.lower()
    if lower.startswith("• pemasukan") or lower.startswith("• pengeluaran"):
        return True

    return any(marker in lower for marker in _BOT_TEXT_MARKERS)


def _is_duplicate_inbound(body: dict, phone: str, text: str, window_sec: int = 30) -> bool:
    """Debounce pesan identik dalam beberapa detik (anti-spam loop)."""
    ts = str(body.get("timestamp") or body.get("id") or "")
    key = f"{_normalize_wa_phone(phone)}:{ts}:{text.strip().lower()[:160]}"
    now = time.time()
    # Bersihkan entri lama
    stale = [k for k, t0 in _recent_inbound.items() if now - t0 > window_sec]
    for k in stale:
        _recent_inbound.pop(k, None)
    if key in _recent_inbound:
        return True
    _recent_inbound[key] = now
    return False


def _is_debt_inquiry(text: str) -> bool:
    """Deteksi pertanyaan piutang/utang — jangan salah masuk CATAT karena kata 'bayar'."""
    t = (text or "").strip().lower()
    if not t or re.search(r"\d", t):
        return False
    if any(
        p in t
        for p in (
            "belum bayar",
            "belum lunas",
            "siapa belum",
            "siapa yang belum",
            "daftar piutang",
            "daftar utang",
            "yang ngutang",
            "yang hutang",
            "siapa ngutang",
            "siapa hutang",
        )
    ):
        return True
    if any(w in t for w in ("utang", "piutang", "kasbon", "hutang", "ngutang")):
        if any(w in t for w in ("siapa", "berapa", "daftar", "list", "tunjuk", "cek", "belum")):
            return True
    return False


def _is_skor_inquiry(text: str) -> bool:
    t = (text or "").strip().lower()
    return bool(
        re.search(r"\b(skor|score)\b", t)
        or "laris score" in t
        or "kesehatan bisnis" in t
        or "sehat tidak" in t
    )


def _is_saran_inquiry(text: str) -> bool:
    t = (text or "").strip().lower()
    return any(
        w in t
        for w in ("saran", "tips", "rekomendasi", "evaluasi bisnis", "masukan bisnis", "minta saran")
    )


def _is_hapus_command(text: str) -> bool:
    t = (text or "").strip().lower()
    return t.startswith("hapus") or t in ("hapus", "batal", "undo") or "hapus transaksi" in t


def _is_likely_record_command(text: str) -> bool:
    """Hanya true jika pesan benar-benar perintah catat transaksi."""
    if _is_debt_inquiry(text) or _is_skor_inquiry(text) or _is_saran_inquiry(text) or _is_hapus_command(text):
        return False
    t = (text or "").strip().lower()
    if re.search(r"\b(jual|beli)\b", t):
        return True
    if ("piutang" in t or "utang" in t or "prive" in t or "bayar" in t) and re.search(r"\d", t):
        return "belum bayar" not in t
    return False


def _sanitize_intent(text: str, intent: str) -> str:
    """Paksa intent benar — pertanyaan tidak boleh CATAT."""
    if _is_debt_inquiry(text):
        return "PIUTANG"
    if _is_skor_inquiry(text):
        return "SKOR"
    if _is_saran_inquiry(text):
        return "SARAN"
    if _is_hapus_command(text):
        return "HAPUS"
    if intent == "CATAT" and not _is_likely_record_command(text):
        alt = classify_wa_intent(text)
        return alt if alt != "CATAT" else "LAINNYA"
    return intent


def _detect_intent_rules(text: str) -> str | None:
    """Jalur cepat hanya untuk perintah sangat jelas (sisanya AI Groq)."""
    t = (text or "").strip().lower()
    if not t:
        return None

    if _is_debt_inquiry(t):
        return "PIUTANG"
    if _is_skor_inquiry(t):
        return "SKOR"
    if _is_saran_inquiry(t):
        return "SARAN"
    if _is_hapus_command(t):
        return "HAPUS"

    if any(kw in t for kw in ("hapus transaksi", "hapus terakhir", "batal transaksi", "undo")):
        return "HAPUS"
    if t.startswith("hapus") or t in ("hapus", "batal"):
        return "HAPUS"

    # Catat transaksi jelas — jual/beli + angka
    if re.search(r"\b(jual|beli)\b", t) and re.search(r"\d", t):
        return "CATAT"

    return None


def _resolve_user_id_safe(phone: str) -> str | None:
    """Petakan nomor WA ke user_id; fallback WA_DEFAULT_USER_ID."""
    try:
        return resolve_user_id(phone)
    except Exception as exc:
        print("WARN resolve_user_id:", exc)
        default = os.environ.get("WA_DEFAULT_USER_ID")
        return default if default else None


def _persist_wa_log(phone: str, text: str, reply: str, user_id: str | None = None) -> bool:
    """Simpan percakapan ke wa_messages (best-effort). Return True jika tersimpan."""
    uid = core.normalize_user_id(user_id) if user_id else None
    if not uid:
        uid = _resolve_user_id_safe(phone)
    if not uid:
        print(f"WARN wa_messages skip: nomor {phone} belum terdaftar di wa_users")
        return False
    ok = True
    if text:
        ok = core.log_wa_message(uid, "user", text, phone=phone) is not None and ok
    if reply:
        ok = core.log_wa_message(uid, "assistant", reply, phone=phone, agent_id="admin") is not None and ok
    return ok


async def _parse_webhook_body(request: Request) -> dict:
    """Fonnte bisa kirim JSON atau form-urlencoded."""
    raw = await request.body()
    print(f"DEBUG webhook raw ({len(raw)} bytes): {raw[:1000]!r}")
    ctype = (request.headers.get("content-type") or "").lower()

    if raw:
        if "application/json" in ctype or raw[:1] in (b"{", b"["):
            try:
                return json.loads(raw)
            except Exception as exc:
                print("WARN json parse:", exc)
        if "application/x-www-form-urlencoded" in ctype or (b"=" in raw and b"&" in raw):
            try:
                parsed = parse_qs(raw.decode("utf-8", errors="replace"), keep_blank_values=True)
                return {k: (v[0] if isinstance(v, list) and v else v) for k, v in parsed.items()}
            except Exception as exc:
                print("WARN urlencoded parse:", exc)

    if "multipart/form-data" in ctype:
        try:
            form = await request.form()
            if form:
                return {k: (v if isinstance(v, str) else getattr(v, "filename", str(v))) for k, v in form.items()}
        except Exception as exc:
            print("WARN multipart parse:", exc)

    return {}


def _extract_incoming(body: dict) -> tuple[str, str, str, str, str | None]:
    """Ambil phone, text, media_type, media_url, inboxid dari payload Fonnte/Wablas."""
    if WA_PROVIDER == "fonnte":
        # Chat pribadi: sender. Grup WA: member = pengirim asli.
        phone = body.get("member") or body.get("sender") or body.get("from") or body.get("phone") or ""
        text = (body.get("message") or body.get("text") or "").strip()
        media_url = body.get("url") or body.get("media_url") or ""
        ext = str(body.get("extension") or "").lower()
        inboxid = body.get("inboxid")
        media_type = ""
        if media_url:
            if ext in ("jpg", "jpeg", "png", "webp", "gif", "image"):
                media_type = "image"
            elif ext in ("ogg", "opus", "mp3", "m4a", "wav", "audio", "ptt"):
                media_type = "audio"
            else:
                media_type = "image"
    else:
        phone = body.get("phone") or body.get("sender") or ""
        text = body.get("message") or body.get("text") or ""
        media_type = body.get("type") or body.get("media_type") or ""
        media_url = body.get("media_url") or body.get("url") or ""
        inboxid = None
    return _normalize_wa_phone(phone), text, media_type, media_url, inboxid


async def send_wa_reply(phone: str, message: str, inboxid: str | None = None):
    if not phone or not message:
        print("WARN send_wa_reply: phone/message kosong")
        return
    if not WA_API_KEY:
        print("ERROR send_wa_reply: WA_API_KEY kosong di Railway Variables")
        return
    target = _normalize_wa_phone(phone)
    try:
        if WA_PROVIDER == "fonnte":
            payload = {"target": target, "message": message}
            if inboxid:
                payload["inboxid"] = inboxid
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://api.fonnte.com/send",
                    headers={"Authorization": WA_API_KEY},
                    data=payload,
                )
            print(f"DEBUG fonnte send → {resp.status_code}: {resp.text[:300]}")
            if resp.status_code >= 400:
                print("ERROR fonnte send gagal — cek WA_API_KEY & format nomor target")
        elif WA_PROVIDER == "wablas":
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://solo.wablas.com/api/v2/send-message",
                    headers={"Authorization": f"Bearer {WA_API_KEY}"},
                    json={"data": [{"phone": target, "message": message}]},
                )
            print(f"DEBUG wablas send → {resp.status_code}: {resp.text[:300]}")
    except Exception as exc:
        print("ERROR send_wa_reply:", exc)


async def detect_intent(text: str) -> str:
    """AI Groq utama; aturan cepat hanya untuk kasus sangat jelas."""
    ruled = _detect_intent_rules(text)
    if ruled:
        return ruled
    intent = classify_wa_intent(text)
    print(f"DEBUG AI intent={intent!r}")
    return intent


@app.api_route("/webhook", methods=["GET", "POST"])
async def webhook(request: Request):
    if request.method == "GET":
        return {
            "status": "webhook_ready",
            "provider": WA_PROVIDER,
            "bot_name": BOT_NAME,
            "bot_logic_version": BOT_LOGIC_VERSION,
            "hint": "POST dari Fonnte ke URL ini. Tes WA: kirim pesan 'test'",
        }

    body = await _parse_webhook_body(request)
    print(f"DEBUG webhook payload keys: {list(body.keys())}")

    phone, text, media_type, media_url, inboxid = _extract_incoming(body)

    if not phone:
        print("ERROR webhook: nomor pengirim tidak ditemukan. Body:", str(body)[:500])
        return {"status": "error", "detail": "No phone number (cek field sender/message Fonnte)"}

    if _is_outgoing_or_bot_echo(body, phone, text):
        print(f"DEBUG webhook ignored (echo/outgoing): sender={phone} text={text[:80]!r}")
        return {"status": "ignored", "reason": "outgoing_or_bot_echo"}

    if text and _is_duplicate_inbound(body, phone, text):
        print(f"DEBUG webhook ignored (duplicate): sender={phone} text={text[:80]!r}")
        return {"status": "ignored", "reason": "duplicate"}

    # Tes koneksi cepat — greeting natural sesuai waktu
    if text.lower() in ("test", "ping", "tes", "halo", "hi"):
        greeting = _get_greeting()
        reply = (
            f"{greeting}! 👋\n\n"
            f"Aku {BOT_NAME}, asisten pembukuan tokomu~\n\n"
            f"Mau catat apa hari ini?\n"
            f"• _jual kopi 15rb_\n"
            f"• _beli bensin 50rb_\n"
            f"• _utang budi 100rb_\n\n"
            f"Atau tanya: _{BOT_NAME.lower()}, gimana bisnis aku?_"
        )
        await asyncio.sleep(random.uniform(0.5, 1.5))
        await send_wa_reply(phone, reply, inboxid=inboxid)
        logged = _persist_wa_log(phone, text, reply)
        return {"status": "ok", "mode": "ping", "wa_logged": logged}

    reply = ""
    user_id = None

    try:
        user_id = resolve_user_id(phone)

        if media_type in ["image", "photo"] and media_url:
            async with httpx.AsyncClient() as client:
                resp = await client.get(media_url)
                b64 = base64.b64encode(resp.content).decode("utf-8")
            data = vision_extractor_agent(b64)
            for d in data:
                is_prv = "prive" in str(d.get("category", "")).lower()
                db_insert_transaction(
                    d.get("type"), d.get("category"), d.get("amount"), d.get("note"),
                    is_prv=is_prv, user_id=user_id,
                )
            total = sum(d.get("amount", 0) for d in data)
            struk_templates = [
                f"📸 Struk kebaca!\nTotal: Rp {total:,.0f}\n{len(data)} transaksi masuk buku~",
                f"✅ Sip, struk terbaca!\nTotal: Rp {total:,.0f}\n{len(data)} transaksi tercatat.",
                f"👌 Oke struknya udah aku baca!\nTotal: Rp {total:,.0f}\n{len(data)} transaksi masuk~",
            ]
            reply = f"{_bot_header()}\n\n{random.choice(struk_templates)}"
            reply += orchestrate_transaction_created(user_id, text or "struk", data)

        elif media_type in ["audio", "voice"] and media_url:
            async with httpx.AsyncClient() as client:
                resp = await client.get(media_url)
            data = voice_extractor_agent(resp.content)
            for d in data:
                is_prv = "prive" in str(d.get("category", "")).lower()
                db_insert_transaction(
                    d.get("type"), d.get("category"), d.get("amount"), d.get("note"),
                    is_prv=is_prv, user_id=user_id,
                )
            voice_templates = [
                f"🎤 Suara kebaca!\n{len(data)} transaksi masuk buku~",
                f"✅ Sip, suaramu aku dengerin!\n{len(data)} transaksi tercatat.",
                f"👌 Oke voice note-nya udah aku proses!\n{len(data)} transaksi masuk~",
            ]
            reply = f"{_bot_header()}\n\n{random.choice(voice_templates)}"
            reply += orchestrate_transaction_created(user_id, text or "voice", data)

        elif text:
            intent = _sanitize_intent(text, await detect_intent(text))
            print(f"DEBUG intent={intent!r} text={text[:80]!r}")

            if intent == "CATAT" and _is_likely_record_command(text):
                data = ai_extractor_agent(text)
                if not data:
                    confusions = [
                        "Hmm, aku belum nangkep transaksinya 🤔",
                        "Waduh, kurang jelas nih~",
                        f"{BOT_NAME} bingung bacanya 😅",
                    ]
                    reply = (
                        f"{_bot_header()}\n\n"
                        f"{random.choice(confusions)}\n"
                        f"Coba kirim seperti:\n"
                        f"• _jual kopi 50rb_\n"
                        f"• _beli minyak 18000_"
                    )
                else:
                    for d in data:
                        is_prv = "prive" in str(d.get("category", "")).lower()
                        db_insert_transaction(
                            d.get("type"), d.get("category"), d.get("amount"), d.get("note"),
                            is_prv=is_prv, user_id=user_id,
                        )
                    reply = f"{_bot_header()}\n\n{_random_confirm(data)}"
                    reply += orchestrate_transaction_created(user_id, text, data)

            elif intent == "SKOR":
                df = get_dashboard_data(user_id)
                score = calculate_cuan_score(df)
                s = score['score']
                if s >= 80:
                    emoji = "🔥"
                    compliment = "Mantap, bisnis kamu sehat banget!"
                elif s >= 60:
                    emoji = "👍"
                    compliment = "Lumayan, tinggal poles dikit lagi!"
                elif s >= 40:
                    emoji = "💪"
                    compliment = "Masih bisa ditingkatkan nih~"
                else:
                    emoji = "📈"
                    compliment = "Yuk perbaiki, aku bantu pantau!"
                reply = (
                    f"{_bot_header()}\n\n"
                    f"{compliment}\n\n"
                    f"{emoji} *{SCORE_LABEL}: {s}/100*\n\n"
                    f"_{score['insight']}_"
                )

            elif intent == "SARAN":
                df = get_dashboard_data(user_id)
                advice = get_ai_advisor_insights(df)
                intros = [
                    f"Nih saran buat tokomu dari {BOT_NAME} 💡",
                    f"Berdasarkan data kamu, coba ini ya~",
                    f"Aku udah analisa datamu, ini sarannya:",
                ]
                intro = random.choice(intros)
                reply = f"{_bot_header()}\n\n{intro}\n\n{advice}"

            elif intent == "PIUTANG":
                df = get_dashboard_data(user_id)
                answer = get_ai_piutang_answer(df, text)
                reply = f"{_bot_header()}\n\n{answer}"

            elif intent == "HAPUS":
                txn = core.delete_last_transaction(user_id)
                if txn:
                    reply = (
                        f"{_bot_header()}\n\n"
                        f"🗑️ Oke, udah dihapus ya~\n"
                        f"• {txn['note']} — Rp {txn['amount']:,.0f}"
                    )
                else:
                    reply = (
                        f"{_bot_header()}\n\n"
                        f"Hmm, nggak ada transaksi yg bisa dihapus nih 🤔"
                    )

            else:
                confusions = [
                    f"Hmm, {BOT_NAME} belum paham maksudmu 🤔",
                    "Waduh, kurang ngerti nih~",
                    f"Maaf, {BOT_NAME.lower()} belum nangkep maksudnya 😅",
                ]
                reply = (
                    f"{_bot_header()}\n\n"
                    f"{random.choice(confusions)}\n\n"
                    f"Coba kirim seperti:\n"
                    f"• _jual kopi 50rb_\n"
                    f"• _beli beras 25rb_\n"
                    f"• _utang budi 100rb_\n"
                    f"• _berapa skor_\n"
                    f"• _saran bisnis_\n"
                    f"• _siapa belum bayar_\n"
                    f"• _hapus_"
                )

        else:
            reply = (
                f"{_bot_header()}\n\n"
                f"Kirim teks, foto struk, atau voice note ya~ 😊"
            )

    except Exception as e:
        print(f"ERROR webhook: {e}")
        reply = (
            f"{_bot_header()}\n\n"
            f"😅 Waduh, ada gangguan sebentar.\n"
            f"Coba kirim lagi ya~"
        )

    # Typing delay — biar terasa natural seperti orang ngetik
    await asyncio.sleep(_random_typing_delay())
    await send_wa_reply(phone, reply, inboxid=inboxid)

    _persist_wa_log(phone, text, reply, user_id=user_id)

    return {"status": "ok"}


@app.get("/")
async def health():
    return {
        "status": f"{APP_NAME} WA Bot is running",
        "bot_name": BOT_NAME,
        "provider": WA_PROVIDER,
        "bot_logic_version": BOT_LOGIC_VERSION,
        "wa_key_set": bool(WA_API_KEY),
        "supabase_set": bool(os.environ.get("SUPABASE_URL")),
        "groq_set": bool(os.environ.get("GROQ_API_KEY")),
        "webhook": "/webhook",
    }
