import html
import urllib.parse

import streamlit as st
import pandas as pd

from brand import APP_NAME, PAGE_ICON, PAGE_TITLE, DASHBOARD_TITLE, DEMO_QUERY
from config_runtime import get_secret, require_secret
from demo_dashboard import render_demo_dashboard
from landing import render_landing
from login import show_login_page, get_current_user, logout, ensure_valid_session
from laris_core import LarisCore
from log_config import get_logger
from pengaturan_bot import render_pengaturan_bot
from ui.components import (
    empty_state,
    hero_welcome,
    info_pill,
    section_card,
    stat_card_row,
)
from ui.dasher_nav import (
    render_sidebar_nav,
)
from ui.laris_theme import inject_dashboard_theme
from ui.constants import MENU_SESSION_KEY
from ui.menus import build_menu_keys, display_label

logger = get_logger(__name__)


AGENT_LABELS = {"admin": "Admin AI", "logistik": "Logistik AI"}

# Hanya email ini yang boleh menambah & mengedit client baru.
SUPER_ADMIN_EMAILS = ("rafihrr1@gmail.com",)

def is_super_admin(user_email: str | None) -> bool:
    """Cek apakah email ini adalah Super Admin."""
    return (user_email or "").strip().lower() in (
        e.lower() for e in SUPER_ADMIN_EMAILS
    )

# Default deploy production (bisa override di secrets.toml)
DEFAULT_BUKUWARUNG_URL = "https://bukuwarung-ai-larisai.up.railway.app"
DEFAULT_CATAT_BOT_URL = "https://kita-cuan-wa-bot-larisai.up.railway.app"


def _bot_base_urls() -> tuple[str, str]:
    """URL webhook BukuWarung CS & bot AI Catat dari secrets atau default."""
    bw = get_secret("BUKUWARUNG_BASE_URL", DEFAULT_BUKUWARUNG_URL)
    catat = get_secret("CATAT_BOT_BASE_URL", DEFAULT_CATAT_BOT_URL)
    return str(bw).rstrip("/"), str(catat).rstrip("/")


def agent_label(agent_id) -> str:
    return AGENT_LABELS.get(agent_id, agent_id or "AI")


def render_wa_sync_hint(user_id: str, user_email: str | None, df_empty: bool) -> None:
    """Petunjuk jika data bot WA belum terlihat di dashboard."""
    if not df_empty:
        return
    is_admin = is_super_admin(user_email)
    if is_admin:
        st.warning(
            "Anda login sebagai **Admin**. Transaksi dari WhatsApp masuk ke akun **client** "
            "(bukan admin). Login dengan email client trial yang nomornya terhubung di Pengaturan."
        )
    st.info(
        f"**Data WA belum muncul?** Pastikan:\n"
        f"1. Login pakai email **client** yang nomor WA-nya terdaftar (`wa_users`).\n"
        f"2. Nomor `082112826851` sudah dihubungkan (jalankan `sql/link_wa_number.sql`).\n"
        f"3. Setelah kirim WA, buka **Buku Kas** atau refresh halaman.\n\n"
        f"User ID sesi ini: `{user_id}`"
    )


def get_admin_core() -> LarisCore | None:
    """Core service role untuk panel Super Admin (opsional di secrets.toml)."""
    try:
        service_key = get_secret("SUPABASE_SERVICE_KEY", "") or ""
        if not service_key:
            return None
        return LarisCore.from_service_client(
            require_secret("SUPABASE_URL"),
            service_key,
            require_secret("GROQ_API_KEY"),
        )
    except (KeyError, FileNotFoundError, RuntimeError):
        return None


def get_core() -> LarisCore:
    core = LarisCore(
        require_secret("SUPABASE_URL"),
        require_secret("SUPABASE_KEY"),
        require_secret("GROQ_API_KEY"),
    )
    # Teruskan token login agar RLS Supabase mengenali user (auth.uid()).
    token = st.session_state.get("access_token")
    if token:
        core.set_access_token(token)
    elif st.session_state.get("user"):
        st.error("Sesi login tidak lengkap. Klik **Keluar** lalu masuk kembali.")
    return core


def render_connection_status(core: LarisCore, user_id: str, user_email: str | None) -> None:
    """Panel diagnostik singkat — bantu jika Buku Kas kosong."""
    token_ok = bool(st.session_state.get("access_token"))
    txn_count, txn_err = core.count_transactions(user_id)
    with st.expander("🔍 Status koneksi database", expanded=not token_ok or txn_count == 0):
        st.write(f"**Email login:** `{user_email or '-'}`")
        st.write(f"**User ID:** `{user_id}`")
        st.write(f"**Token JWT:** {'✅ ada' if token_ok else '❌ hilang — logout & login ulang'}")
        if txn_err:
            st.error(f"Gagal baca transaksi: {txn_err}")
        else:
            st.write(f"**Transaksi di database:** {txn_count} baris")
        if st.button("🔄 Muat ulang data", key="reload_dashboard_data"):
            st.rerun()


def page_config() -> None:
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon=PAGE_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
    )


def render_header() -> None:
    st.markdown(
        """
        <style>
            /* Hide Streamlit footer only - JANGAN hide header (ada tombol toggle sidebar) */
            footer { visibility: hidden; }
            .css-18e3th9 { padding-top: 1rem; }
            .app-link-button {
                background: linear-gradient(135deg, #7c3aed, #1e40af);
                border: none;
                border-radius: 999px;
                color: white;
                padding: 0.85rem 1.4rem;
                text-decoration: none;
                font-weight: 700;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_dashboard_style() -> None:
    """Background & tampilan profesional untuk area dashboard."""
    st.markdown(
        """
        <style>
            /* Latar utama: lebih terang & kontras agar nyaman di dark mode */
            .stApp {
                background:
                    radial-gradient(1100px 600px at 90% -10%, rgba(99,102,241,0.30), transparent 60%),
                    radial-gradient(1000px 550px at -10% 110%, rgba(56,189,248,0.24), transparent 58%),
                    linear-gradient(160deg, #101a2d 0%, #17233a 48%, #1b2a45 100%);
                color: #f8fafc;
            }
            /* Sidebar: lebih terang + teks lebih jelas */
            section[data-testid="stSidebar"] > div {
                background: rgba(30, 41, 59, 0.88);
                backdrop-filter: blur(10px);
                border-right: 1px solid rgba(148,163,184,0.28);
            }
            section[data-testid="stSidebar"] * {
                color: #e2e8f0 !important;
            }
            /* Heading + teks umum */
            h1, h2, h3, h4 { color: #f8fafc !important; letter-spacing: 0.2px; }
            p, li, label, span, div, .stMarkdown, .stCaption {
                color: #e2e8f0;
            }
            /* Metric & expander jadi kartu kaca */
            div[data-testid="stMetric"],
            div[data-testid="stExpander"],
            div[data-testid="stForm"] {
                background: rgba(255,255,255,0.10);
                border: 1px solid rgba(148,163,184,0.30);
                border-radius: 16px;
                padding: 1rem 1.1rem;
                box-shadow: 0 10px 28px rgba(2,6,23,0.35);
            }
            div[data-testid="stMetricValue"] { color: #ffffff; }
            /* Input/select lebih terbaca */
            .stTextInput input,
            .stNumberInput input,
            .stTextArea textarea {
                background: rgba(15, 23, 42, 0.78) !important;
                color: #f8fafc !important;
                border: 1px solid rgba(148,163,184,0.35) !important;
            }
            div[data-baseweb="select"] > div,
            .stMultiSelect div[data-baseweb="select"] > div {
                background: rgba(15, 23, 42, 0.78) !important;
                border-color: rgba(148,163,184,0.35) !important;
            }
            /* Tombol primer bergaya brand */
            .stButton > button[kind="primary"] {
                background: linear-gradient(135deg, #6366f1, #0ea5e9);
                border: none;
                border-radius: 12px;
                font-weight: 700;
                color: white;
            }
            .stButton > button { border-radius: 12px; }
            /* Dataframe sedikit transparan */
            div[data-testid="stDataFrame"] {
                border-radius: 14px; overflow: hidden;
                border: 1px solid rgba(148,163,184,0.30);
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def get_query_value(name: str):
    params = getattr(st, "query_params", {}) or {}
    value = params.get(name)
    if isinstance(value, list):
        return value[0] if value else None
    return value


def get_query_flag(name: str) -> bool:
    value = get_query_value(name)
    if value is None:
        return False
    if isinstance(value, str):
        normalized = value.strip().lower()
        # Trigger kalau ada query param dengan nama tsb, BAHKAN tanpa "=1"
        # (mis. ?login, ?login=, ?login=1, ?login=true, ?login=yes)
        if normalized == "":
            return True
        return normalized in ("1", "true", "yes", "on")
    return bool(value)


def render_home() -> None:
    from landing import render_landing as _landing

    _landing()


def render_dashboard(core: LarisCore, user) -> None:
    inject_dashboard_theme()
    user_id = None
    user_email = None
    if isinstance(user, dict):
        user_id = user.get("id") or user.get("user", {}).get("id")
        user_email = user.get("email") or user.get("user", {}).get("email")
    else:
        user_id = getattr(user, "id", None)
        user_email = getattr(user, "email", None)
        nested = getattr(user, "user", None)
        if not user_id and nested is not None:
            user_id = getattr(nested, "id", None)
        if not user_email and nested is not None:
            user_email = getattr(nested, "email", None)

    if not user_id:
        st.error("ID pengguna tidak ditemukan. Silakan keluar dan masuk kembali.")
        st.json(user)
        return

    user_id = core.normalize_user_id(user_id)

    if "show_menu" not in st.session_state:
        st.session_state.show_menu = True

    warehouse_enabled = core.table_exists("warehouses")

    # Tentukan role user SEBELUM render sidebar — supaya menu admin
    # (Tambah Gudang, Pengaturan Bot) muncul untuk super admin saja.
    is_admin = is_super_admin(user_email)

    # Sidebar: selalu di-render, tapi visibility-nya diatur oleh CSS via
    # `aria-expanded` attribute (Streamlit built-in toggle button).
    # Konfigurasi: [client] initialSidebarState = "collapsed" di config.toml.
    try:
        menu = render_sidebar_nav(
            warehouse_enabled=warehouse_enabled,
            user_email=user_email,
            is_admin=is_admin,
        )
        logger.debug(
            "Sidebar nav rendered. Active menu: %s, is_admin=%s",
            menu,
            is_admin,
        )
    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        logger.exception("Gagal render sidebar nav: %s", exc)
        st.error(f"❌ Gagal render menu sidebar: {exc}")
        with st.expander("Traceback lengkap", expanded=False):
            st.code(tb, language="python")
        menu = "Ringkasan"

    try:
        df = core.get_dashboard_data(user_id)
    except Exception as exc:
        st.error(
            "Gagal memuat data dashboard. Pastikan tabel database sudah dibuat "
            "(jalankan `setup_laris_ai.sql` di Supabase)."
        )
        st.caption(f"Detail: {str(exc)[:200]}")
        df = pd.DataFrame(columns=["type", "amount", "created_at", "description"])
    score = core.calculate_laris_score(df)

    if menu == "Ruang Komando":
        section_card(
            "Ruang Komando",
            "Keputusan yang disodorkan tim AI. Setujui atau tolak langsung di sini.",
            icon="ti-layout-dashboard",
        )

        if not core.table_exists("approvals"):
            empty_state(
                "ti-database",
                "Modul Ruang Komando belum aktif",
                "Jalankan setup_laris_ai.sql di Supabase untuk mengaktifkan approvals.",
            )
        else:
            approvals = core.list_pending_approvals(user_id)
            if approvals is None:
                st.error("Gagal memuat data approval. Pastikan tabel 'approvals' tersedia di Supabase.")
            elif not approvals:
                info_pill("Tidak ada keputusan menunggu. Semua aman, Bos!", "success")
            else:
                st.markdown(
                    f'<p class="text-muted mb-3">{len(approvals)} keputusan menunggu persetujuan Anda:</p>',
                    unsafe_allow_html=True,
                )
                for a in approvals:
                    summary = a.get("summary", "")
                    agent_id = a.get("agent_id", "AI")
                    agent_name = agent_label(agent_id)
                    icon = "ti-robot" if agent_id == "admin" else "ti-truck-delivery"
                    payload = a.get("payload") or {}
                    with st.container(border=True):
                        col_h, col_a = st.columns([7, 3])
                        with col_h:
                            st.markdown(
                                f'<div class="d-flex align-items-center gap-2 mb-2">'
                                f'<span class="laris-page-badge"><i class="ti {icon}"></i> {agent_name}</span>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )
                            st.write(summary)
                        with col_a:
                            c1, c2 = st.columns(2)
                            if c1.button(
                                "✅ Setujui",
                                key=f"approve_{a['id']}",
                                type="primary",
                                use_container_width=True,
                            ):
                                core.update_approval_status(user_id, a["id"], "APPROVED")
                                st.success("Disetujui & diproses!")
                                st.rerun()
                            if c2.button(
                                "❌ Tolak",
                                key=f"reject_{a['id']}",
                                use_container_width=True,
                            ):
                                core.update_approval_status(user_id, a["id"], "REJECTED")
                                st.info("Keputusan ditolak.")
                                st.rerun()
                        if payload:
                            with st.expander("Lihat detail aksi"):
                                st.json(payload)

        st.markdown("---")
        section_card(
            "Aktivitas WhatsApp Terbaru",
            "Log percakapan antara pelanggan, owner, dan AI.",
            icon="ti-brand-whatsapp",
        )
        if not core.table_exists("wa_messages"):
            empty_state(
                "ti-message-dots",
                "Belum ada log percakapan",
                "Aktifkan tabel wa_messages dengan setup_laris_ai.sql.",
            )
        else:
            msgs = core.list_wa_messages(user_id, limit=20)
            if not msgs:
                empty_state(
                    "ti-message-circle",
                    "Belum ada percakapan WhatsApp",
                    "Hubungkan nomor di Pengaturan Bot untuk mulai menerima pesan.",
                )
            else:
                for m in msgs:
                    role = m.get("role", "user")
                    content = m.get("content", "")
                    with st.chat_message(role):
                        if role == "assistant":
                            st.markdown(f"**{agent_label(m.get('agent_id'))}**")
                        st.write(content)

    elif menu == "Ringkasan":
        hero_welcome(user_name=user_email or "Bos")
        render_wa_sync_hint(user_id, user_email, df.empty)
        total_income = int(df[df["type"] == "Pemasukan"]["amount"].sum()) if not df.empty else 0
        total_expense = int(df[df["type"] == "Pengeluaran"]["amount"].sum()) if not df.empty else 0
        balance = total_income - total_expense
        stat_card_row(
            [
                ("Total Pemasukan", f"Rp {total_income:,}", "success"),
                ("Total Pengeluaran", f"Rp {total_expense:,}", "danger"),
                ("Saldo Bersih", f"Rp {balance:,}", "purple"),
                ("Laris Score", f"{score['score']}/100", "info"),
            ]
        )

        st.markdown("---")
        if df.empty:
            empty_state(
                "ti-notebook",
                "Belum ada transaksi",
                "Catat transaksi pertama Anda lewat menu 'Catat Transaksi' atau lewat WhatsApp.",
            )
        else:
            if not warehouse_enabled:
                info_pill("Fitur gudang belum tersedia — jalankan setup_laris_ai.sql untuk mengaktifkan.", "warning")

            section_card(
                "Statistik Ringkas",
                "Tren saldo kumulatif dari waktu ke waktu.",
                icon="ti-chart-line",
            )
            df_recent = df.copy()
            df_recent["date"] = pd.to_datetime(df_recent["date"])
            df_recent = df_recent.sort_values(by="date")
            cumulative = df_recent.set_index("date")["amount"].cumsum()
            st.line_chart(cumulative)

            top_costs = (
                df[df["type"] == "Pengeluaran"]
                .groupby("category")["amount"]
                .sum()
                .sort_values(ascending=False)
            )
            if not top_costs.empty:
                section_card(
                    "Top Pengeluaran",
                    "5 kategori dengan pengeluaran terbesar.",
                    icon="ti-arrows-down",
                )
                st.bar_chart(top_costs.head(5))

            section_card(
                "Saran AI",
                "Rekomendasi berbasis data transaksi Anda.",
                icon="ti-sparkles",
            )
            if len(df) >= 5:
                st.markdown(
                    f'<div class="alert alert-info mb-0" role="alert">{core.get_ai_advisor_insights(df)}</div>',
                    unsafe_allow_html=True,
                )
            else:
                info_pill("Catat minimal 5 transaksi agar AI dapat memberi rekomendasi.", "warning")

            with st.expander("Tampilkan aktivitas terbaru", expanded=False):
                recent = df.sort_values(by="date", ascending=False).head(6).reset_index(drop=True)
                st.table(recent[["date", "type", "category", "amount", "note"]])

    elif menu == "Catat Transaksi":
        section_card(
            "Catat Transaksi",
            "Input manual pemasukan / pengeluaran. Otomatis tersinkron dengan Buku Kas.",
            icon="ti-pencil-plus",
        )
        with st.form("transaction_form"):
            c1, c2 = st.columns(2)
            with c1:
                type_txn = st.radio(
                    "Jenis Transaksi",
                    ["Pemasukan", "Pengeluaran"],
                    horizontal=True,
                )
                category = st.text_input("Kategori", value="Penjualan")
            with c2:
                amount = st.number_input("Jumlah (Rp)", min_value=0, step=1000)
                is_prive = st.checkbox("Prive / ambil pribadi")
            note = st.text_input("Catatan", value="")
            submitted = st.form_submit_button("Simpan Transaksi", type="primary", use_container_width=True)

            if submitted:
                if amount <= 0:
                    st.error("Masukkan jumlah transaksi yang valid.")
                else:
                    core.db_insert_transaction(user_id, type_txn, category, int(amount), note, is_prive=is_prive)
                    st.success("Transaksi berhasil dicatat.")
                    st.rerun()

        info_pill(
            "💡 Atau kirim lewat WhatsApp ke nomor AI Catat Anda, contoh: 'jual kopi 50rb'.",
            "info",
        )

    elif menu == "Buku Kas":
        section_card(
            "Buku Kas",
            "Daftar transaksi lengkap, edit, hapus, atau unduh CSV.",
            icon="ti-cash",
        )
        render_connection_status(core, user_id, user_email)
        if df.empty:
            empty_state(
                "ti-receipt",
                "Buku kas masih kosong",
                "Tambahkan transaksi lewat menu 'Catat Transaksi' atau lewat WhatsApp.",
            )
        else:
            section_card(
                "Ringkasan buku kas terbaru",
                "Transaksi paling baru muncul di atas.",
                icon="ti-list",
            )
            summary = df.sort_values(by="date", ascending=False).reset_index(drop=True)
            st.dataframe(summary, height=320)
            if st.checkbox("Tampilkan semua entri buku kas", value=False):
                st.dataframe(df.sort_values(by="date", ascending=False).reset_index(drop=True))

            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Unduh CSV",
                csv,
                file_name="buku_kas.csv",
                mime="text/csv",
                type="primary",
            )

            st.markdown("---")
            section_card(
                "Edit atau Hapus Transaksi",
                "Pilih transaksi, ubah nilai, atau hapus permanen.",
                icon="ti-edit",
            )
            transaction_options = [
                f"{str(row['date'])} | {row['type']} | {row['category']} | Rp {int(row['amount']):,} | id:{row['id']}"
                for _, row in summary.iterrows()
            ]
            selected_label = st.selectbox(
                "Pilih transaksi untuk diedit atau dihapus",
                ["-- Pilih transaksi --"] + transaction_options,
                index=0,
            )

            selected_txn = None
            if selected_label != "-- Pilih transaksi --":
                try:
                    selected_id = int(selected_label.split("id:")[-1])
                    selected_txn = summary[summary["id"] == selected_id].iloc[0]
                except Exception:
                    selected_txn = None

            if selected_txn is not None:
                with st.form("edit_transaction_form"):
                    type_txn = st.radio(
                        "Jenis Transaksi",
                        ["Pemasukan", "Pengeluaran"],
                        index=0 if selected_txn["type"] == "Pemasukan" else 1,
                        horizontal=True,
                    )
                    category = st.text_input("Kategori", value=selected_txn["category"])
                    amount = st.number_input(
                        "Jumlah (Rp)",
                        min_value=0,
                        step=1000,
                        value=int(selected_txn["amount"]),
                    )
                    note = st.text_input("Catatan", value=selected_txn.get("note", ""))
                    updated = st.form_submit_button("Simpan Perubahan", type="primary")
                    if updated:
                        if amount <= 0:
                            st.error("Masukkan jumlah transaksi yang valid.")
                        else:
                            core.db_update_transaction(
                                user_id,
                                selected_txn["id"],
                                type_txn,
                                category,
                                int(amount),
                                note,
                            )
                            st.success("Transaksi berhasil diperbarui.")
                            st.rerun()

                if st.button("🗑️ Hapus transaksi ini", key="delete_txn_button", type="secondary"):
                    core.db_delete_transaction(user_id, selected_txn["id"])
                    st.success("Transaksi berhasil dihapus.")
                    st.rerun()

    elif menu == "Laporan KUR":
        section_card(
            "Laporan KUR",
            "Ringkasan otomatis untuk pengajuan Kredit Usaha Rakyat ke bank.",
            icon="ti-report-analytics",
        )
        if df.empty:
            empty_state(
                "ti-report-money",
                "Belum ada data untuk laporan",
                "Catat transaksi terlebih dahulu agar AI bisa membuat ringkasan.",
            )
        else:
            total_income = int(df[df["type"] == "Pemasukan"]["amount"].sum())
            total_expense = int(df[df["type"] == "Pengeluaran"]["amount"].sum())
            net_profit = total_income - total_expense
            stat_card_row(
                [
                    ("Pendapatan", f"Rp {total_income:,}", "success"),
                    ("Biaya", f"Rp {total_expense:,}", "danger"),
                    ("Laba Bersih", f"Rp {net_profit:,}", "purple"),
                ]
            )
            st.markdown(
                f"""
                <div class="card card-lg mt-3" style="border:1px solid var(--ds-gray-200);border-radius:1rem;">
                  <div class="card-body">
                    <h5 class="mb-1"><i class="ti ti-bulb text-warning me-2"></i>Insight AI</h5>
                    <p class="mb-1"><strong>Insight:</strong> {score['insight']}</p>
                    <p class="mb-0"><strong>Kesehatan:</strong> {score['level'].capitalize()}</p>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    elif menu == "Pengaturan":
        # === SEMUA USER: Keluar + Chat Admin (WhatsApp) ===
        _render_pengaturan_user(core, user_id, user_email)

    elif menu == "Pengaturan Bot":
        # === KHUSUS ADMIN ===
        if not is_super_admin(user_email):
            st.error("⛔ Akses ditolak. Menu ini khusus untuk Super Admin.")
            return
        render_pengaturan_bot(core, user_id)

        if is_admin:
            st.markdown("---")
            section_card(
                "Panel Super Admin",
                "Tambah & hubungkan client baru. Hanya untuk email admin.",
                icon="ti-shield-lock",
            )
            if not core.table_exists("wa_users"):
                info_pill(
                    "Tabel 'wa_users' belum ada di Supabase. Jalankan setup_laris_ai.sql di SQL Editor.",
                    "warning",
                )
            if core.table_exists("wa_users"):
                info_pill(f"Mode Admin Super aktif: {user_email}", "success")
                bw_url, catat_url = _bot_base_urls()

                section_card(
                    "Tambah Client Baru (2 Nomor WA)",
                    "Buat akun + hubungkan 2 nomor sekaligus (CS & Catat).",
                    icon="ti-user-plus",
                )
                with st.form("create_client_form"):
                    c_email = st.text_input("Email Client")
                    c_pass = st.text_input("Password Sementara", type="password")
                    c_label = st.text_input("Nama Usaha / Label")
                    c_client_id = st.text_input(
                        "Client ID BukuWarung (opsional)",
                        placeholder="toko_rafih — otomatis dari nama jika kosong",
                    )
                    c_phone_cs = st.text_input(
                        "① Nomor WA CS (Pelanggan)",
                        placeholder="0857xxxxxxxx — device Fonnte untuk CS toko",
                        help="Pelanggan chat nomor ini → balasan CS BukuWarung.",
                    )
                    c_phone_catat = st.text_input(
                        "② Nomor HP Owner (AI Catat)",
                        placeholder="0812xxxxxxxx — HP owner kirim jual/beli",
                        help="Owner kirim 'jual kopi 50rb' dari HP ini → tercatat di Buku Kas.",
                    )
                    if st.form_submit_button("Buat Client + Hubungkan 2 Nomor", type="primary"):
                        if not c_email.strip() or len(c_pass) < 6:
                            st.error("Email wajib & password minimal 6 karakter.")
                        elif not c_phone_cs.strip() or not c_phone_catat.strip():
                            st.error("Nomor WA CS dan nomor AI Catat wajib diisi.")
                        else:
                            new_id, err = core.create_client_account(c_email.strip(), c_pass)
                            if err:
                                st.error(f"Gagal membuat client: {err}")
                            else:
                                try:
                                    setup = core.setup_dual_wa_client(
                                        new_id,
                                        wa_cs=c_phone_cs.strip(),
                                        wa_catat=c_phone_catat.strip(),
                                        label=c_label.strip() or c_email.split("@")[0],
                                        client_id=c_client_id.strip() or None,
                                        email=c_email.strip(),
                                        bukuwarung_base_url=bw_url,
                                        catat_bot_base_url=catat_url,
                                    )
                                    st.success(
                                        f"Client dibuat! `user_id`: `{new_id}` · "
                                        f"`client_id`: `{setup['client_id']}`"
                                    )
                                    if setup["bukuwarung_ok"]:
                                        st.markdown(
                                            f"**Webhook Fonnte CS:** `{setup['webhook_cs']}`  \n"
                                            f"**Webhook Fonnte AI Catat:** `{setup['webhook_catat']}`"
                                        )
                                    else:
                                        st.warning(
                                            f"Akun & nomor Catat OK, tapi tabel clients gagal: "
                                            f"{setup.get('bukuwarung_error')}. "
                                            f"Jalankan `bukuwarung-ai/sql/fix_rls_bukuwarung.sql` di Supabase."
                                        )
                                    st.rerun()
                                except Exception as e:
                                    st.warning(f"Akun dibuat, setup WA gagal: {str(e)[:150]}")

                st.markdown("---")
                section_card(
                    "Update Dua Nomor WA Client",
                    "Perbarui nomor CS & Catat untuk client yang sudah ada.",
                    icon="ti-link",
                )
                with st.form("link_dual_wa_form"):
                    target_uid = st.text_input("User ID Client")
                    wa_cs = st.text_input("① Nomor WA CS (Pelanggan)", placeholder="0857xxxxxxxx")
                    wa_catat = st.text_input("② Nomor HP Owner (AI Catat)", placeholder="0812xxxxxxxx")
                    wa_label = st.text_input("Nama Usaha / Label")
                    link_client_id = st.text_input("Client ID BukuWarung (opsional)")
                    if st.form_submit_button("Simpan Dua Nomor", type="primary"):
                        if not target_uid.strip() or not wa_cs.strip() or not wa_catat.strip():
                            st.error("User ID, nomor CS, dan nomor Catat wajib diisi.")
                        else:
                            try:
                                setup = core.setup_dual_wa_client(
                                    target_uid.strip(),
                                    wa_cs=wa_cs.strip(),
                                    wa_catat=wa_catat.strip(),
                                    label=wa_label.strip() or target_uid.strip()[:8],
                                    client_id=link_client_id.strip() or None,
                                    bukuwarung_base_url=bw_url,
                                    catat_bot_base_url=catat_url,
                                )
                                st.success(
                                    f"Terhubung · CS `{setup['wa_cs']}` · Catat `{setup['wa_catat']}` · "
                                    f"client_id `{setup['client_id']}`"
                                )
                                st.code(
                                    f"Webhook CS:\n{setup['webhook_cs']}\n\n"
                                    f"Webhook AI Catat:\n{setup['webhook_catat']}",
                                    language="text",
                                )
                                if not setup["bukuwarung_ok"]:
                                    st.warning(setup.get("bukuwarung_error"))
                                st.rerun()
                            except Exception as e:
                                st.error(f"Gagal: {str(e)[:150]}")

                st.markdown("---")
                section_card(
                    "Hubungkan Nomor WA (satu nomor / legacy)",
                    "Untuk klien lama dengan satu nomor WA.",
                    icon="ti-phone",
                )
                with st.form("link_client_wa_form"):
                    target_uid = st.text_input("User ID Client", key="legacy_target_uid")
                    wa_phone = st.text_input("Nomor WhatsApp", placeholder="0812xxxxxxxx")
                    wa_label = st.text_input("Label (opsional)")
                    if st.form_submit_button("Hubungkan", type="primary"):
                        if not target_uid.strip() or not wa_phone.strip():
                            st.error("User ID & nomor WA wajib diisi.")
                        else:
                            try:
                                core.link_wa_number(target_uid.strip(), wa_phone, wa_label or None)
                                st.success(
                                    f"Nomor {core.normalize_phone(wa_phone)} "
                                    f"terhubung ke {target_uid.strip()}"
                                )
                                st.rerun()
                            except Exception as e:
                                st.error(f"Gagal menghubungkan: {str(e)[:150]}")

                st.markdown("---")
                section_card(
                    "Semua Client Terdaftar",
                    "Daftar lengkap client BukuWarung & nomor WA AI Catat.",
                    icon="ti-list-details",
                )
                admin_core = get_admin_core()
                if admin_core:
                    bw_clients = admin_core.admin_list_bukuwarung_clients()
                else:
                    info_pill(
                        "Tambahkan SUPABASE_SERVICE_KEY di secrets.toml untuk melihat semua client.",
                        "warning",
                    )
                    bw_clients = core.list_bukuwarung_clients(user_id)
                if bw_clients:
                    st.markdown("**BukuWarung CS (tabel clients)**")
                    for c in bw_clients:
                        meta = c.get("metadata") or {}
                        cs_disp = meta.get("whatsapp_cs_display") or meta.get("wa_cs") or "—"
                        catat_disp = meta.get("whatsapp_catat_display") or meta.get("wa_catat") or "—"
                        active = "✅" if c.get("is_active") else "⏸️"
                        st.markdown(
                            f"{active} **{c.get('name')}** (`{c.get('client_id')}`)  \n"
                            f"① CS: `{cs_disp}` · ② Catat: `{catat_disp}`  \n"
                            f"Webhook CS: `{meta.get('webhook_cs', '—')}`"
                        )
                    st.markdown("---")

                if admin_core:
                    numbers = admin_core.admin_list_all_wa_numbers()
                else:
                    numbers = core.list_wa_numbers(user_id)
                if numbers is None:
                    st.error("Gagal memuat data. Pastikan tabel 'wa_users' tersedia.")
                elif not numbers:
                    info_pill("Belum ada nomor AI Catat di wa_users.", "info")
                else:
                    st.markdown("**AI Catat (tabel wa_users)**")
                    for n in numbers:
                        c1, c2 = st.columns([5, 1])
                        label = f" — {n.get('label')}" if n.get("label") else ""
                        c1.write(f"📱 **{n.get('phone')}**{label}  \n`{n.get('user_id')}`")
                        if c2.button("Hapus", key=f"unlink_{n['id']}"):
                            core.unlink_wa_number(n["user_id"], n["phone"])
                            st.rerun()

    elif menu == "Tambah Gudang":
        # === KHUSUS ADMIN: form input gudang baru ===
        if not is_super_admin(user_email):
            st.error("⛔ Akses ditolak. Menu ini khusus untuk Super Admin.")
            st.info(
                "Gudang dibuat dan dikelola oleh Admin. "
                "Silakan hubungi Admin jika butuh gudang baru."
            )
            return
        _render_tambah_gudang(core, user_id)

    elif menu == "Gudang":
        # === SEMUA USER: daftar produk per client (read-only) ===
        render_daftar_produk(core, user_id, user_email)


# ============================================================
# HANDLER: Tambah Gudang (admin-only)
# ============================================================

def _render_tambah_gudang(core, user_id) -> None:
    """Halaman Tambah Gudang — khusus Super Admin.

    Berisi:
    - Form buat gudang baru
    - Daftar gudang yang sudah ada
    - Quick actions: lihat inventaris, tambah produk
    """
    section_card(
        "Tambah Gudang",
        "Buat gudang baru untuk inventaris toko. Hanya Admin yang bisa menambah.",
        icon="ti-building-warehouse",
    )

    # === Form tambah gudang ===
    with st.expander("➕ Buat Gudang Baru", expanded=True):
        with st.form("create_warehouse", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                wh_name = st.text_input("Nama Gudang *", placeholder="cth: Gudang Utama, Toko Depan, dll")
            with col2:
                wh_location = st.text_input("Lokasi (opsional)", placeholder="cth: Jakarta Selatan")

            wh_notes = st.text_area("Keterangan (opsional)", placeholder="Catatan tambahan tentang gudang ini")

            col_btn1, col_btn2, _ = st.columns([1, 1, 4])
            with col_btn1:
                submitted = st.form_submit_button("Buat Gudang", type="primary", use_container_width=True)
            with col_btn2:
                cancel = st.form_submit_button("Reset", use_container_width=True)

            if submitted:
                if not wh_name or not wh_name.strip():
                    st.error("❌ Nama gudang wajib diisi.")
                else:
                    try:
                        res = core.create_warehouse(
                            user_id,
                            wh_name.strip(),
                            wh_location.strip() or None,
                            wh_notes.strip() or None,
                        )
                        if res:
                            st.success(f"✅ Gudang '{wh_name}' berhasil dibuat!")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("❌ Gagal membuat gudang. Coba lagi.")
                    except Exception as exc:
                        logger.exception("create_warehouse failed: %s", exc)
                        st.error(f"❌ Error: {exc}")

    st.markdown("---")

    # === Daftar gudang yang sudah ada ===
    section_card(
        "Daftar Gudang Tersimpan",
        "Semua gudang yang sudah dibuat.",
        icon="ti-archive",
    )

    try:
        warehouses = core.list_warehouses(user_id)
    except Exception as exc:
        logger.error("list_warehouses: %s", exc)
        warehouses = None

    if warehouses is None:
        st.error("❌ Terjadi kesalahan saat memuat data gudang.")
        return

    if not warehouses:
        empty_state(
            "ti-building",
            "Belum ada gudang",
            "Buat gudang pertama Anda lewat form di atas.",
        )
        return

    # Tabel ringkas
    import pandas as _pd
    wh_df = _pd.DataFrame(warehouses)
    display_cols = [c for c in ["id", "name", "location", "created_at", "notes"] if c in wh_df.columns]
    if display_cols:
        st.dataframe(
            wh_df[display_cols],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.dataframe(wh_df, use_container_width=True, hide_index=True)

    # === Quick action: tambah inventaris ke gudang tertentu ===
    st.markdown("---")
    section_card(
        "Catat Barang (In/Out)",
        "Entri inventaris otomatis tersinkron ke tabel produk.",
        icon="ti-package-import",
    )

    wh_choices = {w.get("id"): w.get("name") for w in warehouses}
    with st.form("inventory_form"):
        col1, col2 = st.columns(2)
        with col1:
            wh_selected = st.selectbox(
                "Gudang",
                options=list(wh_choices.keys()),
                format_func=lambda x: wh_choices.get(x, "—"),
            )
        with col2:
            barang = st.text_input("Nama Barang", placeholder="cth: Indomie Goreng")

        col3, col4 = st.columns(2)
        with col3:
            qty_in = st.number_input("Masuk (qty)", min_value=0, step=1, value=0)
        with col4:
            qty_out = st.number_input("Keluar (qty)", min_value=0, step=1, value=0)

        keterangan = st.text_input("Keterangan (opsional)")

        if st.form_submit_button("Simpan Inventaris", type="primary"):
            if not wh_selected:
                st.error("Pilih gudang terlebih dahulu.")
            elif not barang or not barang.strip():
                st.error("Isi nama barang.")
            else:
                try:
                    res = core.add_inventory_entry(
                        user_id, wh_selected, barang.strip(), qty_in, qty_out, keterangan or None
                    )
                    st.success(f"✅ Entri inventaris '{barang}' tersimpan.")
                except Exception as exc:
                    logger.exception("add_inventory_entry failed: %s", exc)
                    st.error(f"❌ Error: {exc}")


# ============================================================
# HANDLER: Pengaturan (semua user)
# ============================================================

# Nomor WhatsApp Admin laris.AI
ADMIN_WA_NUMBER = "6282112826851"  # Format intl tanpa +
ADMIN_WA_DISPLAY = "+62 821-1282-6851"
ADMIN_WA_MESSAGE = (
    "Halo Admin laris.AI, saya pengguna dashboard dan butuh bantuan."
)


def _render_pengaturan_user(core, user_id, user_email) -> None:
    """Halaman Pengaturan untuk semua user.

    Berisi:
    - Info akun (email, user_id)
    - Tombol Chat Admin (buka WhatsApp Web)
    - Tombol Keluar (logout)
    """
    section_card(
        "Pengaturan Akun",
        "Kelola akun dan hubungi admin jika butuh bantuan.",
        icon="ti-user-circle",
    )

    # === Info Akun ===
    st.markdown(
        f"""
        <div class="laris-card" style="padding: 1rem 1.25rem; margin-bottom: 1rem;">
            <div style="font-size: 0.78rem; color: #637381; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">
                Email
            </div>
            <div style="font-size: 0.95rem; font-weight: 600; color: #1c252e; margin-bottom: 0.75rem;">
                {html.escape(user_email or "—")}
            </div>
            <div style="font-size: 0.78rem; color: #637381; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">
                User ID
            </div>
            <div style="font-size: 0.85rem; color: #1c252e; font-family: monospace; word-break: break-all;">
                {html.escape(str(user_id) if user_id else "—")}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # === Chat Admin (WhatsApp) ===
    section_card(
        "Butuh Bantuan?",
        "Hubungi Admin via WhatsApp untuk pertanyaan, masalah teknis, atau permintaan.",
        icon="ti-brand-whatsapp",
    )

    wa_url = f"https://wa.me/{ADMIN_WA_NUMBER}?text={urllib.parse.quote(ADMIN_WA_MESSAGE)}"

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(
            f"""
            <div class="laris-card" style="padding: 1rem; display: flex; align-items: center; gap: 0.75rem; background: linear-gradient(135deg, #d4f1d4 0%, #c8fad6 100%); border: 1px solid rgba(0,167,111,0.2);">
                <div style="width: 44px; height: 44px; background: #00a76f; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 1.4rem; flex-shrink: 0;">
                    📱
                </div>
                <div style="flex: 1;">
                    <div style="font-weight: 700; color: #1c252e; font-size: 0.95rem;">Admin laris.AI</div>
                    <div style="font-size: 0.8rem; color: #454f5b;">{ADMIN_WA_DISPLAY}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.link_button(
            "💬 Chat via WhatsApp",
            wa_url,
            type="primary",
            use_container_width=True,
        )

    st.caption(
        "Klik tombol di atas untuk membuka WhatsApp Web dengan pesan "
        "yang sudah disiapkan. Admin akan balas secepatnya."
    )

    st.markdown("---")

    # === Tombol Keluar ===
    section_card(
        "Keluar",
        "Keluar dari akun dan kembali ke halaman login.",
        icon="ti-logout",
    )

    col1, col2, _ = st.columns([1, 1, 4])
    with col1:
        if st.button(
            "🚪 Keluar",
            type="secondary",
            use_container_width=True,
            key="pengaturan_logout",
        ):
            from login import logout
            logout()
            st.success("Berhasil keluar. Mengalihkan ke halaman login...")
            st.rerun()


def render_daftar_produk(core, user_id, user_email) -> None:
    """Halaman khusus Daftar Produk — read-only untuk Client.

    Tabel sederhana: nama, harga, stok, kategori, status aktif.
    Sumber: tabel `products` di Supabase.

    Isolasi tenant dijamin oleh 3 lapis:
    1. Aplikasi: laris_core.list_products() filter .eq("user_id", uid)
    2. Session: user_id selalu dari session user yang login
    3. Database: RLS policy p_own_products (user_id = auth.uid())
    """
    section_card(
        "Daftar Produk",
        "Daftar produk & harga yang tersedia di toko Anda. "
        "Update otomatis dari aktivitas gudang.",
        icon="ti-box",
    )

    is_admin = is_super_admin(user_email)

    # Info untuk Client
    if not is_admin:
        st.info(
            "📋 **Info untuk Client:** Ini adalah daftar produk yang terdaftar di toko Anda. "
            "Stok dan harga dikelola dari aktivitas gudang oleh Admin."
        )
    else:
        st.info(
            "🛡️ **Mode Admin Super** — Tampilan ini di-scope ke toko yang sedang Anda "
            "buka. Data yang muncul di-filter oleh user_id toko tersebut (bukan admin)."
        )

    try:
        products = core.list_products(user_id)
    except Exception as exc:
        logger.error("list_products di Daftar Produk: %s", exc)
        products = None

    if products is None:
        st.error("Gagal memuat data produk. Pastikan tabel 'products' tersedia di Supabase.")
        return

    if not products:
        st.info("Belum ada produk terdaftar. Admin perlu menambahkan produk dari menu Gudang.")
        return

    # Banner kecil: info scope (supaya user yakin data ini HANYA untuk tokonya)
    st.caption(
        f"🔒 Menampilkan **{len(products)}** produk untuk toko ini "
        f"(user_id `{user_id[:8]}…`). Data terisolasi per-toko, tidak akan bocor "
        f"ke produk toko lain."
    )

    # Bangun dataframe sederhana
    rows = []
    for p in products:
        rows.append({
            "Nama": p.get("name", "—"),
            "Harga": f"Rp {int(p.get('price', 0)):,}".replace(",", "."),
            "Stok": p.get("stock", 0),
            "Kategori": p.get("category") or "—",
            "Status": "✅ Aktif" if p.get("is_active") else "❌ Non-aktif",
        })
    df = pd.DataFrame(rows)

    # Highlight stok menipis (kuning) dan habis (merah)
    def _highlight_stock(row):
        stock = row["Stok"]
        if stock == 0:
            return ["background-color: #f8d7da"] * len(row)  # merah
        elif stock <= 10:
            return ["background-color: #fff3cd"] * len(row)  # kuning
        else:
            return [""] * len(row)

    st.dataframe(
        df.style.apply(_highlight_stock, axis=1),
        use_container_width=True,
        hide_index=True,
    )

    # Ringkasan
    total_produk = len(df)
    stok_habis = len(df[df["Stok"] == 0])
    stok_menipis = len(df[(df["Stok"] > 0) & (df["Stok"] <= 10)])

    cols = st.columns(3)
    with cols[0]:
        st.metric("Total Produk", total_produk)
    with cols[1]:
        st.metric("Stok Habis", stok_habis, delta_color="inverse")
    with cols[2]:
        st.metric("Stok Menipis (≤10)", stok_menipis, delta_color="inverse")


def _redirect_legacy_paths() -> None:
    """Path yang sebenarnya dilayani Cloudflare Pages (www.larisai.my.id)
    tapi user/email/share-link bisa datang ke root domain (larisai.my.id).
    Streamlit tidak handle arbitrary path, jadi pakai JS redirect di awal.
    """
    LANDING = "https://www.larisai.my.id"
    # Path yang wajib di-redirect ke landing (Pages). Tambah sesuai kebutuhan.
    REDIRECT_PREFIXES = ("/artikel/", "/3d/", "/laris-3d/")

    # Pakai st.html() (Streamlit >= 1.32) — lebih cocok untuk HTML kecil
    # seperti JS redirect. st.components.v1.html deprecated per 2026-06-01.
    try:
        st.html(
            f"""
            <script>
              (function() {{
                var p = window.location.pathname || "/";
                var prefixes = {list(REDIRECT_PREFIXES)};
                for (var i = 0; i < prefixes.length; i++) {{
                  if (p.indexOf(prefixes[i]) === 0) {{
                    window.location.replace("{LANDING}" + p);
                    return;
                  }}
                }}
              }})();
            </script>
            """
        )
        return
    except AttributeError:
        pass
    # Fallback untuk Streamlit lama
    import streamlit.components.v1 as components
    components.html(
        f"""
        <script>
          (function() {{
            var p = window.location.pathname || "/";
            var prefixes = {list(REDIRECT_PREFIXES)};
            for (var i = 0; i < prefixes.length; i++) {{
              if (p.indexOf(prefixes[i]) === 0) {{
                window.location.replace("{LANDING}" + p);
                return;
              }}
            }}
          }})();
        </script>
        """,
        height=0,
    )


def main() -> None:
    page_config()
    _redirect_legacy_paths()
    render_header()

    if get_query_flag("demo"):
        st.session_state["demo_mode"] = True
        st.session_state.pop("show_login", None)

    show_login = st.session_state.get("show_login", False) or get_query_flag("login")
    if get_query_flag("login"):
        st.session_state.pop("demo_mode", None)
        st.session_state["show_login"] = True
        show_login = True

    if st.session_state.get("demo_mode"):
        render_demo_dashboard()
        return

    if show_login:
        if show_login_page():
            render_dashboard(get_core(), get_current_user())
        return

    if st.session_state.get("user"):
        if ensure_valid_session():
            render_dashboard(get_core(), get_current_user())
        else:
            st.warning("Sesi Anda telah berakhir. Silakan masuk kembali.")
            render_home()
    else:
        render_home()


if __name__ == "__main__":
    main()
