"""Halaman ⚙️ Pengaturan Bot — konfigurasi Multi-Tenant per user (RLS Supabase)."""

from __future__ import annotations

import streamlit as st

from config_runtime import get_secret
from laris_core import LarisCore

DEFAULT_RAILWAY_URL = "https://bukuwarung-ai-larisai.up.railway.app"


def railway_base_url() -> str:
    """URL deploy FastAPI (satu base untuk webhook CS & Catat)."""
    raw = get_secret("RAILWAY_URL") or get_secret(
        "BUKUWARUNG_BASE_URL", DEFAULT_RAILWAY_URL
    )
    return str(raw).rstrip("/")


def parse_authorized_owners(raw: str, normalize=None) -> list[str]:
    """Ubah teks '628111,628222' menjadi list nomor ter-normalisasi."""
    norm = normalize or (lambda p: "".join(c for c in str(p) if c.isdigit()))
    phones: list[str] = []
    for part in (raw or "").replace("\n", ",").split(","):
        digits = norm(part.strip())
        if digits:
            phones.append(digits)
    return phones


def owners_to_text(owners) -> str:
    if isinstance(owners, list):
        return ", ".join(str(p) for p in owners if p)
    if isinstance(owners, str):
        return owners
    return ""


def settings_incomplete(settings: dict | None) -> bool:
    """True jika pengaturan wajib belum lengkap."""
    if not settings:
        return True
    if not (settings.get("business_name") or "").strip():
        return True
    if not (settings.get("fonnte_token_cs") or "").strip():
        return True
    if not (settings.get("fonnte_token_catat") or "").strip():
        return True
    owners = settings.get("authorized_owners") or []
    if isinstance(owners, str):
        owners = parse_authorized_owners(owners)
    return len(owners) == 0


def render_pengaturan_bot(core: LarisCore, user_id: str) -> None:
    """Tampilkan form pengaturan bot & URL webhook untuk tenant yang login."""
    st.title("⚙️ Pengaturan Bot")
    st.caption(
        "Token Fonnte dan nomor owner disimpan aman di Supabase (`client_settings`). "
        "Hanya akun Anda yang bisa melihat data ini (RLS)."
    )

    uid = core.normalize_user_id(user_id)
    st.caption(f"User ID: `{uid}` — isi form lalu **Simpan Pengaturan**.")

    existing = core.get_client_settings(uid)
    if settings_incomplete(existing):
        st.warning(
            "Pengaturan bot belum lengkap. Isi form di bawah lalu simpan agar webhook "
            "WhatsApp bisa berjalan."
        )

    with st.form("bot_settings_form"):
        business_name = st.text_input(
            "Nama Bisnis",
            value=(existing or {}).get("business_name", ""),
            placeholder="Warung Berkah",
        )
        wa_cs = st.text_input(
            "Nomor WA CS",
            value=(existing or {}).get("wa_cs", ""),
            placeholder="0857xxxxxxxx",
            help="Nomor yang dipakai pelanggan untuk chat CS toko.",
        )
        token_cs = st.text_input(
            "Token Fonnte CS",
            type="password",
            placeholder="Kosongkan jika tidak ingin mengubah token yang sudah tersimpan",
        )
        wa_catat = st.text_input(
            "Nomor WA Catat",
            value=(existing or {}).get("wa_catat", ""),
            placeholder="0812xxxxxxxx",
            help="Nomor HP owner untuk perintah catat jual/beli.",
        )
        token_catat = st.text_input(
            "Token Fonnte Catat",
            type="password",
            placeholder="Kosongkan jika tidak ingin mengubah token yang sudah tersimpan",
        )
        owners_raw = st.text_area(
            "Authorized Owners",
            value=owners_to_text((existing or {}).get("authorized_owners")),
            placeholder="628111111111, 628222222222",
            help="Nomor HP yang boleh mengirim perintah catat. Pisahkan dengan koma.",
        )
        submitted = st.form_submit_button("Simpan Pengaturan", type="primary")

        if submitted:
            if not business_name.strip():
                st.error("Nama Bisnis wajib diisi.")
            elif not wa_cs.strip() or not wa_catat.strip():
                st.error("Nomor WA CS dan Nomor WA Catat wajib diisi.")
            else:
                owners = parse_authorized_owners(owners_raw, normalize=core.normalize_phone)
                if not owners:
                    st.error("Authorized Owners wajib diisi minimal satu nomor.")
                else:
                    fonnte_cs = (token_cs or "").strip() or (existing or {}).get(
                        "fonnte_token_cs", ""
                    )
                    fonnte_catat = (token_catat or "").strip() or (existing or {}).get(
                        "fonnte_token_catat", ""
                    )
                    if not fonnte_cs or not fonnte_catat:
                        st.error("Token Fonnte CS dan Catat wajib diisi (minimal sekali).")
                    else:
                        row = {
                            "business_name": business_name.strip(),
                            "wa_cs": core.normalize_phone(wa_cs),
                            "wa_catat": core.normalize_phone(wa_catat),
                            "fonnte_token_cs": fonnte_cs,
                            "fonnte_token_catat": fonnte_catat,
                            "authorized_owners": owners,
                            "is_active": True,
                        }
                        try:
                            core.upsert_client_settings(uid, row)
                            st.success("Pengaturan bot berhasil disimpan!")
                            st.rerun()
                        except Exception as exc:
                            err = str(exc)
                            st.error(f"Gagal menyimpan: {err[:200]}")
                            low = err.lower()
                            if "pgrst205" in low or "schema cache" in low:
                                st.info(
                                    "Cache schema Supabase belum refresh. Di **SQL Editor** jalankan: "
                                    "`NOTIFY pgrst, 'reload schema';` lalu coba simpan lagi."
                                )
                            elif "pgrst205" in low or "schema cache" in low:
                                st.info(
                                    "Cache schema Supabase perlu di-refresh. Di **SQL Editor** jalankan: "
                                    "`NOTIFY pgrst, 'reload schema';` lalu coba simpan lagi."
                                )

    st.markdown("---")
    st.subheader("🔗 URL Webhook Anda")
    st.caption("Salin URL berikut ke dashboard Fonnte (device CS & device Catat).")

    base = railway_base_url()
    webhook_cs = f"{base}/webhook/csat/{uid}"
    webhook_catat = f"{base}/webhook/catat/{uid}"

    st.markdown("**Webhook CS (pelanggan):**")
    st.code(webhook_cs, language=None)
    st.markdown("**Webhook Catat (owner):**")
    st.code(webhook_catat, language=None)

    with st.expander("🔧 Bantuan koneksi database"):
        status = core.probe_table("client_settings")
        labels = {
            "ok": "✅ Tabel `client_settings` terbaca — lanjut isi form di atas.",
            "stale_cache": "⚠️ Jalankan di SQL Editor: `NOTIFY pgrst, 'reload schema';` lalu refresh.",
            "missing": "❌ Tabel belum ada di project ini — jalankan `bukuwarung-ai/sql/create_client_settings.sql`.",
            "denied": "❌ Logout & login ulang (token JWT / RLS).",
        }
        st.write(labels.get(status, "✅ Coba isi dan simpan form."))
        if not st.session_state.get("access_token"):
            st.warning("Token login tidak ada. Klik **Keluar** lalu masuk kembali.")
