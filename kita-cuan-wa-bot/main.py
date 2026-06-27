# main.py — Bot WhatsApp laris.AI
import os
import sys
import base64
import httpx
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv
from groq import Groq

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
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
    resolve_user_id,
    core,
)

load_dotenv()

app = FastAPI(title=WA_BOT_TITLE)

WA_PROVIDER = os.environ.get("WA_PROVIDER", "fonnte")
WA_API_KEY = os.environ["WA_API_KEY"]
SAFEGUARD_MODEL = "openai/gpt-oss-safeguard-20b"
groq = Groq(api_key=os.environ["GROQ_API_KEY"])

# Ambang stok kritis: di bawah ini Logistik AI menyarankan PO (butuh approval owner).
STOCK_THRESHOLD = int(os.environ.get("STOCK_THRESHOLD", "10"))
REORDER_QTY = int(os.environ.get("REORDER_QTY", "5"))


def proactive_logistik_check(user_id: str, text: str) -> str:
    """Kolaborasi ala SOUL.md: setelah Admin catat penjualan, Logistik AI:
    1) kurangi stok produk di tabel products sesuai jumlah terjual,
    2) jika stok jatuh di bawah ambang, JANGAN buat PO langsung -> buat
       ApprovalRequest (PENDING) untuk owner.
    Mengembalikan catatan tambahan untuk balasan WA (atau string kosong)."""
    try:
        parsed = core.ai_logistik_parse(text)
        if not parsed or not parsed.get("product"):
            return ""
        product = parsed["product"]
        qty = max(0, int(parsed.get("qty") or 0))

        # Kurangi stok terjual (None = produk tidak terdaftar di katalog -> abaikan).
        new_stock = core.adjust_product_stock(user_id, product, -qty) if qty else None
        if new_stock is None:
            new_stock, found = core.get_product_stock(user_id, product)
            if found == 0:
                return ""

        if new_stock >= STOCK_THRESHOLD:
            return ""

        summary = (
            f"Stok {product} tinggal {new_stock}. Saran: pesan {REORDER_QTY} unit "
            f"ke supplier biar nggak kehabisan."
        )
        core.create_approval(
            user_id,
            agent_id="logistik",
            action_type="create_po",
            summary=summary,
            payload={"product": product, "current_stock": new_stock, "reorder_qty": REORDER_QTY},
        )
        return f"\n\n📦 *Logistik AI:* {summary}\nBuka *Ruang Komando* untuk Setujui/Tolak."
    except Exception as exc:
        print("ERROR proactive_logistik_check:", exc)
        return ""


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


async def send_wa_reply(phone: str, message: str):
    if WA_PROVIDER == "fonnte":
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://api.fonnte.com/send",
                headers={"Authorization": WA_API_KEY},
                data={"target": phone, "message": message},
            )
    elif WA_PROVIDER == "wablas":
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://solo.wablas.com/api/v2/send-message",
                headers={"Authorization": f"Bearer {WA_API_KEY}"},
                json={"data": [{"phone": phone, "message": message}]},
            )


async def detect_intent(text: str) -> str:
    try:
        res = groq.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{
                "role": "user",
                "content": f"""Klasifikasikan pesan berikut ke SATU kategori saja. Jawab dengan satu kata:
- CATAT (jika berisi transaksi: jual, beli, bayar, utang, piutang, prive)
- SKOR (jika tanya laris score, skor, kesehatan)
- SARAN (jika minta saran, tips, evaluasi, rekomendasi)
- PIUTANG (jika tanya siapa yang belum bayar, daftar utang)
- HAPUS (jika minta hapus transaksi terakhir)
- LAINNYA (jika tidak masuk kategori di atas)

Pesan: "{text}"

Jawab satu kata saja:""",
            }],
            temperature=0,
            max_tokens=10,
        )
        return res.choices[0].message.content.strip().upper()
    except Exception:
        return "LAINNYA"


@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()

    if WA_PROVIDER == "fonnte":
        phone = body.get("from", "")
        text = body.get("text", "")
        media_type = body.get("media_type", "")
        media_url = body.get("media_url", "")
    else:
        phone = body.get("phone", "")
        text = body.get("message", "")
        media_type = body.get("type", "")
        media_url = body.get("media_url", "")

    if not phone:
        raise HTTPException(status_code=400, detail="No phone number")

    phone = phone.replace("@s.whatsapp.net", "").strip()
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
                    is_prive=is_prv, user_id=user_id,
                )
            total = sum(d.get("amount", 0) for d in data)
            reply = f"✅ Struk terbaca!\nTotal: Rp {total:,.0f}\n{len(data)} transaksi tercatat."

        elif media_type in ["audio", "voice"] and media_url:
            async with httpx.AsyncClient() as client:
                resp = await client.get(media_url)
            data = voice_extractor_agent(resp.content)
            for d in data:
                is_prv = "prive" in str(d.get("category", "")).lower()
                db_insert_transaction(
                    d.get("type"), d.get("category"), d.get("amount"), d.get("note"),
                    is_prive=is_prv, user_id=user_id,
                )
            reply = f"✅ Suara terbaca!\n{len(data)} transaksi tercatat."

        elif text:
            if not await is_safe_message(text):
                reply = "⚠️ Pesan tidak dapat diproses. Silakan kirim transaksi atau pertanyaan seputar keuangan warung."
            else:
                intent = await detect_intent(text)

                if intent == "CATAT":
                    data = ai_extractor_agent(text)
                    for d in data:
                        is_prv = "prive" in str(d.get("category", "")).lower()
                        db_insert_transaction(
                            d.get("type"), d.get("category"), d.get("amount"), d.get("note"),
                            is_prive=is_prv, user_id=user_id,
                        )
                    lines = [f"• {d.get('type')} {d.get('category')}: Rp {d.get('amount', 0):,.0f}" for d in data]
                    reply = "✅ Tercatat!\n" + "\n".join(lines)
                    # Kolaborasi: Logistik AI cek stok & buat approval bila kritis.
                    reply += proactive_logistik_check(user_id, text)

                elif intent == "SKOR":
                    df = get_dashboard_data(user_id)
                    score = calculate_cuan_score(df)
                    reply = f"🔥 *{SCORE_LABEL}: {score['score']}/100*\n\n_{score['insight']}_"

                elif intent == "SARAN":
                    df = get_dashboard_data(user_id)
                    advice = get_ai_advisor_insights(df)
                    reply = f"💡 *Saran AI:*\n\n{advice}"

                elif intent == "PIUTANG":
                    df = get_dashboard_data(user_id)
                    piutang = df[df["category"].str.contains("piutang|kasbon", case=False, na=False)]
                    if piutang.empty:
                        reply = "✅ Tidak ada piutang tercatat."
                    else:
                        lines = [f"• {row['note']}: Rp {row['amount']:,.0f}" for _, row in piutang.iterrows()]
                        total = piutang["amount"].sum()
                        reply = f"📋 *Daftar Piutang:*\n" + "\n".join(lines) + f"\n\n*Total: Rp {total:,.0f}*"

                elif intent == "HAPUS":
                    txn = core.delete_last_transaction(user_id)
                    if txn:
                        reply = f"🗑️ Dihapus: {txn['note']} (Rp {txn['amount']:,.0f})"
                    else:
                        reply = "Tidak ada transaksi untuk dihapus."

                else:
                    reply = (
                        f"🤔 Maaf, saya belum paham.\n\n"
                        f"Coba kirim:\n"
                        f"• Transaksi: _Jual kopi 50rb_\n"
                        f"• Skor: _Berapa {SCORE_LABEL.lower()}?_\n"
                        f"• Saran: _Ada saran bisnis?_\n"
                        f"• Piutang: _Siapa yang belum bayar?_\n"
                        f"• Hapus: _Hapus transaksi terakhir_\n"
                        f"• Atau kirim foto struk / voice note!"
                    )

        else:
            reply = f"Kirim teks, foto struk, atau voice note ke {APP_NAME}! 😊"

    except Exception as e:
        reply = f"❌ Terjadi kesalahan: {str(e)[:200]}"

    await send_wa_reply(phone, reply)

    # Log percakapan untuk widget Chat History di Ruang Komando (best-effort).
    if user_id:
        if text:
            core.log_wa_message(user_id, "user", text, phone=phone)
        core.log_wa_message(user_id, "assistant", reply, phone=phone, agent_id="admin")

    return {"status": "ok"}


@app.get("/")
async def health():
    return {"status": f"{APP_NAME} WA Bot is running 🔥"}
