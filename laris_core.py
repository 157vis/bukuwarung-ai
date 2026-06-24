"""Logika bisnis bersama — dipakai app Streamlit & bot WhatsApp."""

import re
import json
import base64
import random
import os
from datetime import datetime, timedelta

import pandas as pd
from supabase import create_client
from groq import Groq


class LarisCore:
    def __init__(self, supabase_url: str, supabase_key: str, groq_api_key: str):
        self.supabase = create_client(supabase_url, supabase_key)
        self.groq_client = Groq(api_key=groq_api_key)

    def resolve_user_id_by_phone(self, phone: str) -> str:
        """Petakan nomor WA ke user_id Supabase."""
        normalized = phone.replace("@s.whatsapp.net", "").strip().lstrip("+")
        if normalized.startswith("0"):
            normalized = "62" + normalized[1:]

        for candidate in {phone, normalized, f"+{normalized}"}:
            resp = (
                self.supabase.table("wa_users")
                .select("user_id")
                .eq("phone", candidate)
                .limit(1)
                .execute()
            )
            if resp.data:
                return resp.data[0]["user_id"]

        default_user = os.environ.get("WA_DEFAULT_USER_ID")
        if default_user:
            return default_user

        raise ValueError(
            f"Nomor {phone} belum terdaftar. Hubungkan di dashboard atau set WA_DEFAULT_USER_ID."
        )

    def get_dashboard_data(self, user_id: str) -> pd.DataFrame:
        response = (
            self.supabase.table("transactions")
            .select("*")
            .eq("user_id", user_id)
            .order("id", desc=True)
            .execute()
        )
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()

    def db_insert_transaction(
        self, user_id: str, type_txn, category, amount, note, is_prive=False
    ):
        prev = (
            self.supabase.table("transactions")
            .select("running_balance")
            .eq("user_id", user_id)
            .order("id", desc=True)
            .limit(1)
            .execute()
        )
        last_balance = prev.data[0]["running_balance"] if prev.data else 0
        new_balance = last_balance + amount if type_txn == "Pemasukan" else last_balance - amount
        prefix = "PRV" if is_prive else ("KM" if type_txn == "Pemasukan" else "KK")
        today = datetime.now().strftime("%y%m%d")
        count_resp = (
            self.supabase.table("transactions")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .like("date", f"{today}%")
            .execute()
        )
        seq = (count_resp.count or 0) + 1
        receipt_no = f"{prefix}-{today}-{seq:03d}"
        data = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "type": type_txn,
            "category": category,
            "amount": amount,
            "note": note,
            "receipt_no": receipt_no,
            "running_balance": new_balance,
            "is_prive": is_prive,
            "user_id": user_id,
        }
        # Temporary debug logging for troubleshooting missing transactions
        try:
            print("DEBUG db_insert_transaction: input=", {
                "user_id": user_id,
                "type": type_txn,
                "category": category,
                "amount": amount,
                "note": note,
                "is_prive": is_prive,
            })
            print("DEBUG db_insert_transaction: last_balance=", last_balance, "new_balance=", new_balance, "receipt_no=", receipt_no)
        except Exception:
            pass

        insert_result = self.supabase.table("transactions").insert(data).execute()

        try:
            # Log response details (data, count, error if present)
            print("DEBUG db_insert_transaction: insert_result.data=", getattr(insert_result, "data", None))
            print("DEBUG db_insert_transaction: insert_result.count=", getattr(insert_result, "count", None))
            print("DEBUG db_insert_transaction: insert_result.error=", getattr(insert_result, "error", None))
        except Exception:
            pass
        return insert_result

    def db_update_transaction(self, user_id, txn_id, type_txn, category, amount, note):
        (
            self.supabase.table("transactions")
            .update({"type": type_txn, "category": category, "amount": amount, "note": note})
            .eq("id", txn_id)
            .eq("user_id", user_id)
            .execute()
        )

    def db_delete_transaction(self, user_id, txn_id):
        (
            self.supabase.table("transactions")
            .delete()
            .eq("id", txn_id)
            .eq("user_id", user_id)
            .execute()
        )

    # --------------------
    # Warehouses / Inventory
    # --------------------
    def create_warehouse(self, user_id: str, name: str, location: str = None, notes: str = None):
        data = {"user_id": user_id, "name": name, "location": location, "notes": notes, "created_at": datetime.now().isoformat()}
        return self.supabase.table("warehouses").insert(data).execute()

    def list_warehouses(self, user_id: str):
        resp = self.supabase.table("warehouses").select("*").eq("user_id", user_id).order("id", desc=False).execute()
        return resp.data or []

    def update_warehouse(self, user_id: str, warehouse_id: int, **fields):
        return (
            self.supabase.table("warehouses").update(fields).eq("id", warehouse_id).eq("user_id", user_id).execute()
        )

    def delete_warehouse(self, user_id: str, warehouse_id: int):
        return (
            self.supabase.table("warehouses").delete().eq("id", warehouse_id).eq("user_id", user_id).execute()
        )

    def add_inventory_entry(self, user_id: str, warehouse_id: int, barang: str, qty_in: int = 0, qty_out: int = 0, note: str = None):
        data = {
            "user_id": user_id,
            "warehouse_id": warehouse_id,
            "barang": barang,
            "qty_in": int(qty_in or 0),
            "qty_out": int(qty_out or 0),
            "note": note,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        # insert inventory entry
        insert_result = self.supabase.table("inventory_entries").insert(data).execute()
        try:
            print("DEBUG add_inventory_entry:", data)
            print("DEBUG add_inventory_entry result:", getattr(insert_result, "data", None), getattr(insert_result, "error", None))
        except Exception:
            pass
        return insert_result

    def list_inventory(self, user_id: str, warehouse_id: int = None):
        q = self.supabase.table("inventory_entries").select("*").eq("user_id", user_id)
        if warehouse_id is not None:
            q = q.eq("warehouse_id", warehouse_id)
        resp = q.order("id", desc=True).execute()
        return resp.data or []

    def delete_last_transaction(self, user_id):
        last = (
            self.supabase.table("transactions")
            .select("id, note, amount")
            .eq("user_id", user_id)
            .order("id", desc=True)
            .limit(1)
            .execute()
        )
        if not last.data:
            return None
        txn = last.data[0]
        self.db_delete_transaction(user_id, txn["id"])
        return txn

    @staticmethod
    def clean_json_response(text: str) -> str:
        match = re.search(r"```(?:json)?\n(.*?)\n```", text, re.DOTALL)
        if match:
            return match.group(1)
        if not text.strip().startswith("["):
            return f"[{text}]"
        return text

    def ai_extractor_agent(self, text: str) -> list:
        prompt = (
            f'Anda akuntan warung Indonesia. Ekstrak teks "{text}" jadi array JSON. '
            'Aturan: type(Pemasukan/Pengeluaran), amount(angka), category, note. '
            'Jika ada "prive"/"ambil pribadi" set category="Prive". HANYA JSON array.'
        )
        try:
            res = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="openai/gpt-oss-120b",
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            return json.loads(self.clean_json_response(res.choices[0].message.content))
        except Exception:
            return []

    def vision_extractor_agent_from_b64(self, b64: str) -> list:
        prompt = (
            "Baca struk warung Indonesia. Cari GRAND TOTAL. "
            "Output JSON: [{'type':'Pengeluaran','amount':angka,'category':'Bahan Baku','note':'ringkasan'}]. "
            "Hanya JSON."
        )
        try:
            res = self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                        ],
                    }
                ],
                model="openai/gpt-oss-120b",
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            return json.loads(self.clean_json_response(res.choices[0].message.content))
        except Exception:
            return []

    def vision_extractor_agent_from_upload(self, uploaded_file) -> list:
        b64 = base64.b64encode(uploaded_file.getvalue()).decode("utf-8")
        return self.vision_extractor_agent_from_b64(b64)

    def voice_extractor_agent_from_bytes(self, audio_bytes: bytes, filename="rec.wav") -> list:
        try:
            trans = self.groq_client.audio.transcriptions.create(
                file=(filename, audio_bytes),
                model="whisper-large-v3-turbo",
                language="id",
                response_format="text",
            )
            return self.ai_extractor_agent(trans)
        except Exception:
            return []

    def voice_extractor_agent_from_file(self, audio_file) -> list:
        return self.voice_extractor_agent_from_bytes(audio_file.read(), audio_file.name)

    @staticmethod
    def calculate_laris_score(df: pd.DataFrame) -> dict:
        if df.empty:
            return {"score": 0, "insight": "Mulai catat transaksi pertama Anda!", "level": "low"}
        income = df[df["type"] == "Pemasukan"]["amount"].sum()
        expense = df[df["type"] == "Pengeluaran"]["amount"].sum()
        profit = income - expense
        margin_score = min(40, max(0, (profit / income) * 80)) if income > 0 else 0
        df_c = df.copy()
        df_c["date"] = pd.to_datetime(df_c["date"])
        last_30 = df_c[df_c["date"] >= (datetime.now() - timedelta(days=30))]
        consistency_score = min(30, (last_30["date"].dt.date.nunique() / 30) * 30)
        utang = df[df["category"].str.contains("utang|kasbon|piutang", case=False, na=False)][
            "amount"
        ].sum()
        debt_score = max(0, 20 - ((utang / income) * 40)) if income > 0 else 10
        volume_score = min(10, len(last_30) * 0.5)
        total = int(min(100, max(0, margin_score + consistency_score + debt_score + volume_score)))
        if total >= 75:
            lv, ins = "high", ["Warung sangat sehat! 🔥", "Margin konsisten 💪", "Siap ekspansi? 🚀"]
        elif total >= 45:
            lv, ins = "mid", ["Tingkatkan pencatatan 📝", "Evaluasi harga 💡", "Perhatikan bocoran 🔍"]
        else:
            lv, ins = "low", ["Evaluasi biaya ⚠️", "Rapikan pencatatan 💪", "Kurangi stok mati 📉"]
        return {"score": total, "insight": random.choice(ins), "level": lv}

    def get_ai_advisor_insights(self, df: pd.DataFrame) -> str:
        if df.empty or len(df) < 5:
            return "Belum cukup data. Catat minimal 5 transaksi dulu ya! 📝"
        income = df[df["type"] == "Pemasukan"]["amount"].sum()
        expense = df[df["type"] == "Pengeluaran"]["amount"].sum()
        profit = income - expense
        margin = round((profit / income) * 100, 1) if income > 0 else 0
        top_exp = df[df["type"] == "Pengeluaran"].groupby("category")["amount"].sum().nlargest(3)
        top_str = ", ".join([f"{c}: Rp {a:,.0f}" for c, a in top_exp.items()])
        piutang = df[df["category"].str.contains("piutang|kasbon", case=False, na=False)][
            "amount"
        ].sum()
        utang = df[
            df["category"].str.contains("utang", case=False, na=False)
            & ~df["category"].str.contains("piutang|kasbon", case=False, na=False)
        ]["amount"].sum()
        prompt = (
            f"Anda konsultan UMKM Indonesia. Data: Pendapatan Rp {income:,.0f}, "
            f"Pengeluaran Rp {expense:,.0f}, Laba Rp {profit:,.0f} (Margin {margin}%), "
            f"Top pengeluaran: {top_str}, Piutang Rp {piutang:,.0f}, Utang Rp {utang:,.0f}. "
            "Beri 2-3 saran singkat actionable. Bahasa santai warung, emoji secukupnya."
        )
        try:
            res = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="openai/gpt-oss-120b",
                temperature=0.7,
                max_tokens=300,
            )
            return res.choices[0].message.content.strip()
        except Exception:
            return "Gagal mengambil saran AI."
