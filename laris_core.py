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
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.supabase = create_client(supabase_url, supabase_key)
        self.groq_client = Groq(api_key=groq_api_key)

    def set_access_token(self, token: str):
        """Teruskan JWT user login ke PostgREST agar RLS mengenali auth.uid().

        Tanpa ini, query berjalan sebagai role anon dan akan terblokir RLS.
        Tidak dipakai oleh bot WhatsApp (bot memakai service_role yang bypass RLS).
        """
        if not token:
            return
        try:
            self.supabase.postgrest.auth(token)
        except Exception as exc:
            print("ERROR set_access_token:", exc)

    @staticmethod
    def normalize_user_id(user_id) -> str:
        return str(user_id).strip() if user_id else ""

    def count_transactions(self, user_id: str) -> tuple[int, str | None]:
        """Hitung transaksi user (untuk diagnostik dashboard)."""
        uid = self.normalize_user_id(user_id)
        if not uid:
            return 0, "user_id kosong"
        try:
            resp = (
                self.supabase.table("transactions")
                .select("id", count="exact")
                .eq("user_id", uid)
                .execute()
            )
            return int(resp.count or 0), None
        except Exception as exc:
            return -1, str(exc)[:200]

    def get_dashboard_data(self, user_id: str) -> pd.DataFrame:
        uid = self.normalize_user_id(user_id)
        if not uid:
            return pd.DataFrame()
        response = (
            self.supabase.table("transactions")
            .select("*")
            .eq("user_id", uid)
            .order("id", desc=True)
            .execute()
        )
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()

    def create_client_account(self, email: str, password: str):
        """Buat akun client baru (Supabase Auth). Return (user_id, error_msg)."""
        try:
            # Client terpisah agar sesi admin yang sedang login tidak terganggu.
            tmp = create_client(self.supabase_url, self.supabase_key)
            res = tmp.auth.sign_up({"email": email, "password": password})
            user = getattr(res, "user", None)
            if user and getattr(user, "id", None):
                return user.id, None
            return None, "Gagal membuat akun. Cek format email / kemungkinan email sudah terdaftar."
        except Exception as exc:
            return None, str(exc)[:200]

    def list_all_wa_numbers(self):
        """Admin: ambil semua pemetaan nomor WA -> client."""
        try:
            resp = self.supabase.table("wa_users").select("*").order("id", desc=True).execute()
            return resp.data or []
        except Exception as exc:
            print("ERROR list_all_wa_numbers:", exc)
            return None

    @staticmethod
    def normalize_phone(phone: str) -> str:
        """Normalisasi nomor WA: buang +, spasi, suffix WA; awalan 0 -> 62."""
        normalized = phone.replace("@s.whatsapp.net", "").strip().lstrip("+")
        normalized = "".join(ch for ch in normalized if ch.isdigit())
        if normalized.startswith("0"):
            normalized = "62" + normalized[1:]
        return normalized

    def link_wa_number(self, user_id: str, phone: str, label: str = None):
        """Hubungkan nomor WA ke seorang client (user_id). Upsert berdasarkan phone."""
        normalized = self.normalize_phone(phone)
        if not normalized:
            raise ValueError("Nomor WA tidak valid.")
        data = {"phone": normalized, "user_id": user_id, "label": label}
        return self.supabase.table("wa_users").upsert(data, on_conflict="phone").execute()

    def list_wa_numbers(self, user_id: str):
        try:
            resp = self.supabase.table("wa_users").select("*").eq("user_id", user_id).order("id", desc=True).execute()
            return resp.data or []
        except Exception as exc:
            print("ERROR list_wa_numbers:", exc)
            return None

    def unlink_wa_number(self, user_id: str, phone: str):
        normalized = self.normalize_phone(phone)
        return (
            self.supabase.table("wa_users")
            .delete()
            .eq("phone", normalized)
            .eq("user_id", user_id)
            .execute()
        )

    def resolve_user_id_by_phone(self, phone: str) -> str:
        """Petakan nomor WA ke user_id Supabase."""
        normalized = self.normalize_phone(phone)

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

    def table_exists(self, table_name: str) -> bool:
        try:
            resp = self.supabase.table(table_name).select("id").limit(1).execute()
            return resp is not None
        except BaseException as exc:
            print(f"ERROR table_exists({table_name}):", exc)
            return False

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

    def recalculate_running_balance(self, user_id):
        """Hitung ulang running_balance semua transaksi user (urut kronologis/id asc).

        Wajib dipanggil setelah edit/hapus agar saldo berjalan tetap konsisten.
        """
        try:
            resp = (
                self.supabase.table("transactions")
                .select("id, type, amount")
                .eq("user_id", user_id)
                .order("id", desc=False)
                .execute()
            )
            rows = resp.data or []
            balance = 0
            for r in rows:
                amt = r.get("amount") or 0
                balance = balance + amt if r.get("type") == "Pemasukan" else balance - amt
                (
                    self.supabase.table("transactions")
                    .update({"running_balance": balance})
                    .eq("id", r["id"])
                    .eq("user_id", user_id)
                    .execute()
                )
            return balance
        except Exception as exc:
            print("ERROR recalculate_running_balance:", exc)
            return None

    def db_update_transaction(self, user_id, txn_id, type_txn, category, amount, note):
        (
            self.supabase.table("transactions")
            .update({"type": type_txn, "category": category, "amount": amount, "note": note})
            .eq("id", txn_id)
            .eq("user_id", user_id)
            .execute()
        )
        # Saldo bisa berubah karena tipe/nominal diedit -> hitung ulang.
        self.recalculate_running_balance(user_id)

    def db_delete_transaction(self, user_id, txn_id):
        (
            self.supabase.table("transactions")
            .delete()
            .eq("id", txn_id)
            .eq("user_id", user_id)
            .execute()
        )
        # Hapus satu baris menggeser saldo semua transaksi sesudahnya -> hitung ulang.
        self.recalculate_running_balance(user_id)

    # --------------------
    # Warehouses / Inventory
    # --------------------
    def create_warehouse(self, user_id: str, name: str, location: str = None, notes: str = None):
        data = {"user_id": user_id, "name": name, "location": location, "notes": notes, "created_at": datetime.now().isoformat()}
        return self.supabase.table("warehouses").insert(data).execute()

    def list_warehouses(self, user_id: str):
        try:
            resp = self.supabase.table("warehouses").select("*").eq("user_id", user_id).order("id", desc=False).execute()
            return resp.data or []
        except BaseException as exc:
            print("ERROR list_warehouses:", exc)
            return None

    def update_warehouse(self, user_id: str, warehouse_id: int, **fields):
        try:
            return (
                self.supabase.table("warehouses").update(fields).eq("id", warehouse_id).eq("user_id", user_id).execute()
            )
        except BaseException as exc:
            print("ERROR update_warehouse:", exc)
            return None

    def delete_warehouse(self, user_id: str, warehouse_id: int):
        try:
            return (
                self.supabase.table("warehouses").delete().eq("id", warehouse_id).eq("user_id", user_id).execute()
            )
        except BaseException as exc:
            print("ERROR delete_warehouse:", exc)
            return None

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
        try:
            insert_result = self.supabase.table("inventory_entries").insert(data).execute()
            try:
                print("DEBUG add_inventory_entry:", data)
                print("DEBUG add_inventory_entry result:", getattr(insert_result, "data", None), getattr(insert_result, "error", None))
            except Exception:
                pass
            return insert_result
        except Exception as exc:
            print("ERROR add_inventory_entry:", exc)
            return None

    def list_inventory(self, user_id: str, warehouse_id: int = None):
        try:
            q = self.supabase.table("inventory_entries").select("*").eq("user_id", user_id)
            if warehouse_id is not None:
                q = q.eq("warehouse_id", warehouse_id)
            resp = q.order("id", desc=True).execute()
            return resp.data or []
        except Exception as exc:
            print("ERROR list_inventory:", exc)
            return None

    # --------------------
    # Approvals (Ruang Komando / Proactive UI)
    # --------------------
    def create_approval(self, user_id: str, agent_id: str, action_type: str, summary: str, payload: dict = None):
        """Buat ApprovalRequest status PENDING. Dipakai agent saat butuh persetujuan owner."""
        data = {
            "user_id": user_id,
            "agent_id": agent_id,
            "action_type": action_type,
            "summary": summary,
            "payload": payload or {},
            "status": "PENDING",
        }
        try:
            return self.supabase.table("approvals").insert(data).execute()
        except Exception as exc:
            print("ERROR create_approval:", exc)
            return None

    def list_pending_approvals(self, user_id: str):
        try:
            resp = (
                self.supabase.table("approvals")
                .select("*")
                .eq("user_id", user_id)
                .eq("status", "PENDING")
                .order("id", desc=True)
                .execute()
            )
            return resp.data or []
        except Exception as exc:
            print("ERROR list_pending_approvals:", exc)
            return None

    def update_approval_status(self, user_id: str, approval_id, status: str):
        if status not in ("APPROVED", "REJECTED"):
            raise ValueError("status harus APPROVED atau REJECTED")
        try:
            return (
                self.supabase.table("approvals")
                .update({"status": status, "updated_at": datetime.now().isoformat()})
                .eq("id", approval_id)
                .eq("user_id", user_id)
                .execute()
            )
        except Exception as exc:
            print("ERROR update_approval_status:", exc)
            return None

    # --------------------
    # Logistik (cek stok & saran restock)
    # --------------------
    def find_product_row(self, user_id: str, name_hint: str):
        """Cari baris produk terdekat (nama fuzzy). Return dict atau None."""
        hint = (name_hint or "").strip()
        if not hint:
            return None
        uid = self.normalize_user_id(user_id)
        try:
            resp = (
                self.supabase.table("products")
                .select("id, name, price, stock")
                .eq("user_id", uid)
                .ilike("name", f"%{hint}%")
                .limit(1)
                .execute()
            )
            rows = resp.data or []
            return rows[0] if rows else None
        except Exception as exc:
            print("ERROR find_product_row:", exc)
            return None

    def get_product_stock(self, user_id: str, product: str):
        """Kembalikan (stok, jumlah_baris) dari tabel `products` untuk produk tertentu."""
        try:
            resp = (
                self.supabase.table("products")
                .select("stock")
                .eq("user_id", user_id)
                .ilike("name", f"%{product}%")
                .execute()
            )
            rows = resp.data or []
            stock = sum((r.get("stock") or 0) for r in rows)
            return stock, len(rows)
        except Exception as exc:
            print("ERROR get_product_stock:", exc)
            return 0, 0

    def adjust_product_stock(self, user_id: str, product: str, delta: int):
        """Tambah/kurangi stok produk (delta negatif = terjual). Return stok baru atau None."""
        uid = self.normalize_user_id(user_id)
        try:
            resp = (
                self.supabase.table("products")
                .select("id, stock")
                .eq("user_id", uid)
                .ilike("name", f"%{product}%")
                .limit(1)
                .execute()
            )
            rows = resp.data or []
            if not rows:
                return None
            row = rows[0]
            new_stock = max(0, (row.get("stock") or 0) + delta)
            self.supabase.table("products").update({"stock": new_stock}).eq("id", row["id"]).execute()
            return new_stock
        except Exception as exc:
            print("ERROR adjust_product_stock:", exc)
            return None

    def resolve_sale_quantity(
        self, user_id: str, product_name: str, raw_text: str, amount: int, unit_price: int | None
    ) -> int:
        """Hitung unit terjual: dari teks (jual kopi 5) atau nominal / harga (35000 / 3500 = 10)."""
        parsed = self.ai_logistik_parse(raw_text) or {}
        parsed_name = (parsed.get("product") or "").strip().lower()
        target = (product_name or "").strip().lower()
        qty = max(0, int(parsed.get("qty") or 0))

        # Pakai qty dari AI hanya jika masuk akal (bukan nominal rupiah).
        if qty > 0 and qty <= 500:
            if not parsed_name or parsed_name in target or target in parsed_name:
                return qty

        price = unit_price or 0
        if not price and target:
            row = self.find_product_row(user_id, target)
            price = int(row.get("price") or 0) if row else 0

        if price > 0 and amount > 0:
            inferred = int(round(amount / price))
            return max(1, inferred) if inferred > 0 else 0
        return qty if 0 < qty <= 500 else 0

    def resolve_product_for_sale(self, user_id: str, category: str, raw_text: str):
        """Cocokkan transaksi ke baris products (nama fuzzy / katalog / teks asli)."""
        hints = [category]
        parsed = self.ai_logistik_parse(raw_text) or {}
        pname = str(parsed.get("product") or "").strip()
        if pname:
            hints.append(pname)

        for hint in hints:
            if not hint:
                continue
            row = self.find_product_row(user_id, hint)
            if row:
                return row

        uid = self.normalize_user_id(user_id)
        haystack = f"{category} {raw_text}".lower()
        try:
            resp = (
                self.supabase.table("products")
                .select("id, name, price, stock")
                .eq("user_id", uid)
                .execute()
            )
            for row in resp.data or []:
                name = (row.get("name") or "").strip()
                if name and name.lower() in haystack:
                    return row
        except Exception as exc:
            print("ERROR resolve_product_for_sale:", exc)
        return None

    def run_logistik_after_sale(
        self,
        user_id: str,
        transaction: dict,
        raw_text: str,
        *,
        stock_threshold: int = 10,
        reorder_qty: int = 20,
    ) -> dict | None:
        """Logistik AI: kurangi stok gudang setelah penjualan; buat approval jika kritis."""
        category = str(transaction.get("category") or transaction.get("note") or "").strip()
        amount = int(transaction.get("amount") or 0)
        if not category:
            parsed = self.ai_logistik_parse(raw_text) or {}
            category = str(parsed.get("product") or "").strip()
        if not category:
            return None

        row = self.resolve_product_for_sale(user_id, category, raw_text)
        if not row:
            return {
                "message": (
                    f"📦 *Logistik AI:* Produk `{category}` belum ada di katalog gudang. "
                    f"Tambahkan di Supabase/products agar stok terpantau."
                ),
                "stock_updated": False,
            }

        product = row["name"]
        old_stock = int(row.get("stock") or 0)
        unit_price = int(row.get("price") or 0)
        qty = self.resolve_sale_quantity(user_id, product, raw_text, amount, unit_price)
        if qty <= 0:
            return {
                "message": (
                    f"📦 *Logistik AI:* Penjualan {product} tercatat, "
                    f"tapi jumlah unit tidak terbaca. Coba: _jual {product} 5_ "
                    f"atau nominal kelipatan harga Rp {unit_price:,}."
                ),
                "stock_updated": False,
            }

        new_stock = self.adjust_product_stock(user_id, product, -qty)
        if new_stock is None:
            return None

        price_txt = f" @ Rp {unit_price:,}" if unit_price else ""
        msg = (
            f"📦 *Logistik AI:* Stok *{product}*: {old_stock} → {new_stock} "
            f"(-{qty} unit{price_txt})"
        )

        approval_msg = ""
        if new_stock < stock_threshold:
            summary = (
                f"Stok {product} tinggal {new_stock} (ambang {stock_threshold}). "
                f"Saran pesan {reorder_qty} unit ke supplier."
            )
            self.create_approval(
                user_id,
                agent_id="logistik",
                action_type="create_po",
                summary=summary,
                payload={
                    "product": product,
                    "current_stock": new_stock,
                    "reorder_qty": reorder_qty,
                    "unit_price": unit_price,
                },
            )
            approval_msg = "\n⚠️ Stok menipis — buka *Ruang Komando* untuk Setujui/Tolak PO."

        return {
            "message": msg + approval_msg,
            "stock_updated": True,
            "product": product,
            "qty_sold": qty,
            "old_stock": old_stock,
            "new_stock": new_stock,
        }

    def ai_logistik_parse(self, text: str) -> dict:
        """Ekstrak {product, qty} dari teks penjualan, mis. 'jual indomie 5'. None jika gagal."""
        prompt = (
            f'Dari teks penjualan warung "{text}", ekstrak nama produk dan jumlah UNIT (bukan rupiah). '
            'Contoh: "jual kopi 5" → qty 5. "jual kopi 35000" jika 35000 nominal → qty 0. '
            'Balas HANYA JSON: {"product": "nama", "qty": angka_unit}. '
            'Jika tidak jelas: {"product": null, "qty": 0}.'
        )
        try:
            res = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="openai/gpt-oss-120b",
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            data = json.loads(res.choices[0].message.content)
            if not data.get("product"):
                return None
            return {"product": str(data["product"]).strip(), "qty": int(data.get("qty") or 0)}
        except Exception:
            return None

    # --------------------
    # Log percakapan WhatsApp (opsional, untuk Chat History)
    # --------------------
    def log_wa_message(self, user_id: str, role: str, content: str, phone: str = None, agent_id: str = None):
        uid = self.normalize_user_id(user_id)
        data = {"user_id": uid, "role": role, "content": content, "phone": phone, "agent_id": agent_id}
        try:
            result = self.supabase.table("wa_messages").insert(data).execute()
            if not getattr(result, "data", None):
                print("WARN log_wa_message: insert tanpa data balik", data)
            return result
        except Exception as exc:
            print("ERROR log_wa_message:", exc, "| payload:", {**data, "content": (content or "")[:80]})
            return None

    def list_wa_messages(self, user_id: str, limit: int = 30):
        try:
            resp = (
                self.supabase.table("wa_messages")
                .select("*")
                .eq("user_id", user_id)
                .order("id", desc=True)
                .limit(limit)
                .execute()
            )
            rows = resp.data or []
            return list(reversed(rows))
        except Exception as exc:
            print("ERROR list_wa_messages:", exc)
            return []

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

    @staticmethod
    def _parse_transactions(content: str) -> list:
        """Parse respons AI jadi list transaksi, tahan terhadap bentuk objek/array."""
        try:
            data = json.loads(content)
        except Exception as exc:
            print("ERROR parse transaksi (json):", exc, "| raw:", str(content)[:160])
            return []
        if isinstance(data, list):
            return [d for d in data if isinstance(d, dict)]
        if isinstance(data, dict):
            for key in ("transactions", "data", "items", "result", "transaksi"):
                if isinstance(data.get(key), list):
                    return [d for d in data[key] if isinstance(d, dict)]
            # Objek transaksi tunggal
            if "amount" in data and "type" in data:
                return [data]
        return []

    def ai_extractor_agent(self, text: str) -> list:
        prompt = (
            f'Anda akuntan warung Indonesia. Teks user: "{text}"\n\n'
            "Jika ini PERTANYAAN (skor, saran, siapa belum bayar, dll.) — balas {\"transactions\": []}.\n"
            "Hanya ekstrak jika user jelas MENCATAT transaksi jual/beli/bayar/piutang dengan nominal.\n"
            'Balas HANYA JSON: {"transactions":[...]} tiap item '
            '{"type":"Pemasukan|Pengeluaran","amount":angka,"category":"...","note":"..."}.'
        )
        try:
            res = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="openai/gpt-oss-120b",
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            return self._parse_transactions(res.choices[0].message.content)
        except Exception as exc:
            print("ERROR ai_extractor_agent:", exc)
            return []

    def vision_extractor_agent_from_b64(self, b64: str) -> list:
        prompt = (
            "Baca struk belanja warung Indonesia. Ambil HANYA nilai GRAND TOTAL / TOTAL akhir "
            "(jangan rincian per item agar tidak dobel). "
            'Balas HANYA objek JSON dengan key "transactions" berisi TEPAT SATU item: '
            '{"transactions":[{"type":"Pengeluaran","amount":<grand total>,"category":"Bahan Baku","note":"ringkasan belanja"}]}. '
            'Jika total tidak terbaca, balas {"transactions": []}.'
        )
        # Deteksi tipe gambar dari header base64 (PNG vs JPEG) agar mime cocok.
        mime = "image/png" if b64.startswith("iVBOR") else "image/jpeg"
        try:
            res = self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                        ],
                    }
                ],
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            return self._parse_transactions(res.choices[0].message.content)
        except Exception as exc:
            print("ERROR vision_extractor_agent:", exc)
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

    def classify_wa_intent(self, text: str) -> str:
        """Klasifikasi intent pesan WA via Groq (AI utama)."""
        t = (text or "").strip()
        if not t:
            return "LAINNYA"
        system = (
            "Anda router intent untuk asisten WhatsApp UMKM Indonesia. "
            'Balas HANYA JSON: {"intent":"..."} dengan intent salah satu dari: '
            "CATAT, SKOR, SARAN, PIUTANG, HAPUS, LAINNYA.\n\n"
            "CATAT = mencatat transaksi baru (jual/beli/bayar dengan nominal, atau catat piutang DENGAN nominal).\n"
            "SKOR = tanya skor/kesehatan bisnis.\n"
            "SARAN = minta saran/tips/evaluasi bisnis.\n"
            "PIUTANG = BERTANYA siapa yang belum bayar, daftar utang/piutang, cek outstanding — BUKAN mencatat.\n"
            "HAPUS = hapus transaksi terakhir.\n"
            "LAINNYA = di luar kategori.\n\n"
            'Contoh PIUTANG: "siapa belum bayar utang", "siapa yang ngutang", "daftar piutang".\n'
            'Contoh CATAT: "jual kopi 5", "piutang pak budi 50000".\n'
            "Pertanyaan utang/piutang TANPA nominal = PIUTANG, bukan CATAT."
        )
        try:
            res = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": t},
                ],
                model="openai/gpt-oss-120b",
                temperature=0,
                max_tokens=40,
                response_format={"type": "json_object"},
            )
            data = json.loads(res.choices[0].message.content or "{}")
            intent = str(data.get("intent", "LAINNYA")).strip().upper()
            valid = {"CATAT", "SKOR", "SARAN", "PIUTANG", "HAPUS", "LAINNYA"}
            return intent if intent in valid else "LAINNYA"
        except Exception as exc:
            print("ERROR classify_wa_intent:", exc)
            return "LAINNYA"

    def get_ai_piutang_answer(self, df: pd.DataFrame, question: str) -> str:
        """Jawab pertanyaan piutang/utang dengan AI + data buku kas."""
        if df.empty:
            return (
                "Belum ada data transaksi. Catat dulu piutang pelanggan, "
                "misalnya: _piutang pak budi 50000_"
            )
        piutang = df[df["category"].str.contains("piutang|kasbon", case=False, na=False)]
        utang = df[
            df["category"].str.contains("utang|hutang", case=False, na=False)
            & ~df["category"].str.contains("piutang|kasbon", case=False, na=False)
        ]
        if piutang.empty and utang.empty:
            return (
                "Belum ada piutang/utang tercatat. "
                "Catat dulu, misalnya: _piutang pak budi 50000_"
            )

        def _rows_to_text(frame, label):
            if frame.empty:
                return f"{label}: (kosong)"
            lines = [
                f"- {row.get('note') or row.get('category')}: Rp {int(row.get('amount') or 0):,}"
                for _, row in frame.iterrows()
            ]
            total = int(frame["amount"].sum())
            return f"{label} (total Rp {total:,}):\n" + "\n".join(lines)

        data_block = _rows_to_text(piutang, "Piutang (pelanggan berutang ke toko)")
        data_block += "\n\n" + _rows_to_text(utang, "Utang toko (toko berutang)")

        prompt = (
            f"Pemilik warung bertanya via WhatsApp:\n\"{question}\"\n\n"
            f"Data buku kas:\n{data_block}\n\n"
            "Jawab singkat, jelas, Bahasa Indonesia santai UMKM. "
            "Sebut nama jika ada. Jangan mengarang di luar data di atas."
        )
        try:
            res = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="openai/gpt-oss-120b",
                temperature=0.4,
                max_tokens=350,
            )
            return res.choices[0].message.content.strip()
        except Exception as exc:
            print("ERROR get_ai_piutang_answer:", exc)
            if not piutang.empty:
                lines = [f"• {row['note']}: Rp {row['amount']:,.0f}" for _, row in piutang.iterrows()]
                return "📋 *Daftar Piutang:*\n" + "\n".join(lines)
            return "Gagal mengambil jawaban AI. Coba lagi."

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
            
class TenantManager:
    """Handle multi-tenant. Belum dipakai, cuma siap-siap."""
    def _init_(self, sb):
        self.sb = sb
    def get_active_tenant(self, user_id):
        try:
            r = self.sb.table("active_tenant_session").select("tenant_id").eq("user_id", user_id).limit(1).execute()
            return str(r.data[0]["tenant_id"]) if r.data else None
        except Exception:
            return None
    def set_active_tenant(self, user_id, tenant_id):
        try:
            exp = (datetime.now() + timedelta(days=7)).isoformat()
            self.sb.table("active_tenant_session").upsert({"user_id": user_id, "tenant_id": tenant_id, "source": "manual", "expires_at": exp}, on_conflict="user_id").execute()
        except Exception:
            pass
    def get_user_tenants(self, user_id):
        try:
            r = self.sb.table("user_tenants").select("tenant_id, is_default, label").eq("user_id", user_id).execute()
            return r.data or []
        except Exception:
            return []
