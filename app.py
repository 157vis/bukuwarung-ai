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

        # === Plan / Tier Banner (Free vs Pro) ===
        _render_plan_banner(core, user_id, user_email)

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
                "Tambah toko baru, update nomor existing, lihat semua tenant. Hanya untuk email admin.",
                icon="ti-shield-lock",
            )

            # Ambil base URL bot SEBELUM tabs (dipakai oleh semua form)
            bw_url, catat_url = _bot_base_urls()

            # === Tab separation supaya tidak bingung ===
            tab_daftar, tab_update, tab_list = st.tabs([
                "➕ Tambah Toko Baru",
                "✏️ Update Toko Existing",
                "📋 Daftar Semua Toko",
            ])

            with tab_daftar:
                _render_schema_health_check(core)
                _render_form_tambah_client(core, bw_url, catat_url, user_email)

            with tab_update:
                _render_form_update_client(core, bw_url, catat_url, user_id, user_email)

            with tab_list:
                _render_clients_admin_list(core)

    elif menu == "Tambah Gudang":
        # === KHUSUS ADMIN: form input gudang baru ===
        if not is_super_admin(user_email):
            st.error("⛔ Akses ditolak. Menu ini khusus untuk Super Admin.")
            st.info(
                "Gudang dibuat dan dikelola oleh Admin. "
                "Silakan hubungi Admin jika butuh gudang baru."
            )
            return
        _render_tambah_gudang(core, user_id, user_email)

    elif menu == "Gudang":
        # === SEMUA USER: daftar produk per client (read-only) ===
        render_daftar_produk(core, user_id, user_email)


# ============================================================
# HANDLER: Tambah Gudang (admin-only)
# ============================================================

def _render_tambah_gudang(core, user_id, user_email: str | None = None) -> None:
    """Halaman Tambah Gudang — khusus Super Admin.

    Berisi:
    - Form buat gudang baru
    - Daftar gudang yang sudah ada
    - Quick actions: lihat inventaris, tambah produk
    - Tambah produk ke gudang client (dengan pemilihan client untuk multi-tenant)
    """
    section_card(
        "Tambah Gudang",
        "Buat gudang baru & kelola inventaris toko client. Hanya Admin.",
        icon="ti-building-warehouse",
    )

    # Inisialisasi admin_core di awal (dipakai oleh section "Semua Gudang" di bawah)
    admin_core = None
    try:
        admin_core = get_admin_core()
    except Exception:
        admin_core = None

    # === Banner info utama — supaya user tahu ada section Tambah Produk di bawah ===
    st.info(
        "📋 **Halaman ini punya 3 section utama:**\n"
        "1. **➕ Tambah Produk ke Gudang Client** (atas — untuk daftarkan produk baru)\n"
        "2. **➕ Buat Gudang Baru** (tengah — untuk gudang fisik)\n"
        "3. **Catat Barang (In/Out)** + **Daftar Gudang & Produk** (bawah — operasional harian)"
    )

    # === SECTION 1: Tambah Produk ke Gudang Client (PINDAH KE ATAS!) ===
    _render_tambah_produk_section(core, user_id, user_email)

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
        st.warning("⚠️ Tabel 'warehouses' belum tersedia atau RLS memblokir akses. Section inventaris di bawah dilewati.")
        warehouses = []

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

    # === ADMIN VIEW: Semua Gudang Lintas-Tenant ===
    # Karena "Daftar Gudang Tersimpan" di atas hanya menampilkan gudang
    # milik user_id admin sendiri (kosong untuk admin), kita tambah section
    # khusus yang menampilkan SEMUA gudang dari semua toko client.
    try:
        st.markdown("---")
        section_card(
            "Semua Gudang (Admin View)",
            "Daftar gudang dari semua toko client. Hanya Super Admin yang melihat ini.",
            icon="ti-server-2",
        )
    except Exception as exc:
        logger.error("admin view header: %s", exc)
        st.warning(f"⚠️ Tidak bisa render admin view header: {exc}")

    all_warehouses = []
    if admin_core:
        try:
            all_warehouses = admin_core.get_all_warehouses_for_admin()
        except Exception as exc:
            logger.error("get_all_warehouses_for_admin in admin view: %s", exc)
            all_warehouses = []

    if not admin_core:
        st.caption(
            "🔒 **Mode Terbatas** — Set `SUPABASE_SERVICE_KEY` di secrets.toml untuk "
            "melihat semua gudang lintas-tenant. Tanpa itu, hanya gudang admin sendiri yang tampil."
        )
    elif not all_warehouses:
        st.info("Belum ada gudang yang dibuat oleh client manapun.")
    else:
        # Group by user_id supaya admin tahu gudang mana milik toko mana
        wh_by_user: dict[str, list[dict]] = {}
        for wh in all_warehouses:
            uid = wh.get("user_id", "—")
            wh_by_user.setdefault(uid, []).append(wh)

        st.caption(
            f"📦 Total **{len(all_warehouses)} gudang** untuk **{len(wh_by_user)} toko** client. "
            f"Klik UUID untuk copy ke clipboard."
        )

        import pandas as _pd3
        rows = []
        for uid, whs in wh_by_user.items():
            for wh in whs:
                rows.append({
                    "ID": wh.get("id"),
                    "UUID Toko": uid,
                    "Nama Gudang": wh.get("name", "—"),
                    "Lokasi": wh.get("location") or "—",
                    "Catatan": wh.get("notes") or "—",
                    "Created": wh.get("created_at", "—"),
                })
        st.dataframe(
            _pd3.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )

        # Expander untuk lihat per-toko
        with st.expander("🔍 Lihat detail gudang per toko", expanded=False):
            for uid, whs in wh_by_user.items():
                st.markdown(
                    f"**Toko UUID:** `{uid}` &nbsp;&nbsp; "
                    f"({len(whs)} gudang)"
                )
                for wh in whs:
                    st.markdown(
                        f"- **{wh.get('name', '?')}** "
                        f"_(lokasi: {wh.get('location') or '—'}, "
                        f"catatan: {wh.get('notes') or '—'})_"
                    )
                st.markdown("---")

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

    # === SECTION 1 SUDAH DI ATAS (lihat _render_tambah_produk_section) ===
    # Section ini dipanggil di awal _render_tambah_gudang agar langsung
    # terlihat di atas, tidak perlu scroll jauh.

    # Daftar produk existing di toko admin (read-only, di paling bawah)
    st.markdown("---")
    section_card(
        "Produk Aktif di Toko Admin",
        f"Daftar produk untuk user_id `{user_id[:8]}…` (toko admin sendiri).",
        icon="ti-list",
    )
    try:
        products = core.list_products(user_id)
    except Exception as exc:
        logger.error("list_products in tambah_gudang: %s", exc)
        products = None
    if products is None:
        st.error("❌ Gagal memuat data produk.")
    elif not products:
        empty_state(
            "ti-package",
            "Belum ada produk",
            "Tambah produk pertama lewat form di bagian ATAS halaman ini.",
        )
    else:
        import pandas as _pd2
        rows = []
        for p in products:
            rows.append({
                "ID": p.get("id"),
                "Nama": p.get("name", "—"),
                "Harga": f"Rp {int(p.get('price', 0)):,}".replace(",", "."),
                "Stok": p.get("stock", 0),
                "Kategori": p.get("category") or "—",
                "Status": "✅ Aktif" if p.get("is_active") else "❌ Non-aktif",
            })
        st.caption(f"Total: **{len(products)}** produk")
        st.dataframe(
            _pd2.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# HANDLER: Tambah Produk ke Gudang Client (helper, admin-only)
# ============================================================

def _render_tambah_produk_section(core, user_id, user_email: str | None = None) -> None:
    """Section 'Tambah Produk ke Gudang Client' — dipanggil di ATAS halaman.

    Form lengkap: nama, kategori, harga, stok, status aktif, deskripsi.
    Untuk admin dengan service_role: ada dropdown pilih toko client.
    Untuk non-admin / tanpa service_role: tambah ke toko sendiri saja.
    """
    st.markdown("---")
    section_card(
        "Tambah Produk ke Gudang Client",
        "Daftarkan produk baru ke inventaris toko. Produk akan otomatis muncul "
        "di menu Gudang milik client tersebut.",
        icon="ti-box",
    )

    # Pilih client target: kalau admin punya service_role, tampilkan dropdown
    # semua client. Kalau tidak, ada input manual UUID + auto-detect dari gudang.
    target_user_id = user_id
    target_label = "toko ini (admin)"
    admin_core = None
    try:
        admin_core = get_admin_core()
    except Exception:
        admin_core = None

    # === Mode 1: Service role aktif → dropdown toko client ===
    clients = []
    if admin_core:
        try:
            clients = admin_core.get_clients_for_admin()
        except Exception as exc:
            logger.error("get_clients_for_admin: %s", exc)
            clients = []

    if admin_core and clients:
        # Bangun map user_id → dict client
        client_map: dict[str, dict] = {c.get("user_id"): c for c in clients if c.get("user_id")}

        def _format_client(uid: str) -> str:
            if uid == "__self__":
                return "— Toko sendiri (admin) —"
            c = client_map.get(uid, {})
            name = c.get("business_name") or c.get("name") or uid[:8]
            wa = c.get("wa_cs") or c.get("wa_catat") or ""
            if wa:
                return f"🏪 {name} (WA {wa})"
            return f"🏪 {name}"

        client_options = list(client_map.keys()) + ["__self__"]
        chosen = st.selectbox(
            "Pilih toko client",
            options=client_options,
            format_func=_format_client,
            key="tambah_produk_target_client",
        )
        if chosen != "__self__":
            target_user_id = chosen
            cn = client_map.get(chosen, {})
            target_label = f"toko {cn.get('business_name') or chosen[:8]}"
        else:
            target_label = "toko admin sendiri"

    # === Mode 2: Tanpa service_role → input manual UUID + auto-detect gudang ===
    else:
        # Coba ambil semua warehouse lintas-tenant via service_role (kalau ada)
        all_warehouses = []
        if admin_core:
            try:
                all_warehouses = admin_core.get_all_warehouses_for_admin()
            except Exception as exc:
                logger.error("get_all_warehouses_for_admin: %s", exc)

        if all_warehouses:
            # Group by user_id supaya admin tahu UUID mana yang punya gudang
            wh_by_user: dict[str, list[dict]] = {}
            for wh in all_warehouses:
                uid = wh.get("user_id")
                if uid:
                    wh_by_user.setdefault(uid, []).append(wh)

            st.caption(
                f"📦 **{len(all_warehouses)} gudang** terdaftar untuk "
                f"**{len(wh_by_user)} user**. Pilih UUID di bawah untuk target toko."
            )
            # Build selectbox options
            wh_options = []
            wh_option_labels = []
            for uid, whs in wh_by_user.items():
                wh_names = ", ".join(w.get("name", "?") for w in whs)
                wh_options.append(uid)
                wh_option_labels.append(f"🏪 {wh_names} — UUID {uid[:8]}…")
            wh_options.append("__self__")
            wh_option_labels.append("— Toko sendiri (admin) —")
            wh_map = dict(zip(wh_options, wh_option_labels))
            chosen = st.selectbox(
                "Pilih toko berdasarkan gudang",
                options=wh_options,
                format_func=lambda k: wh_map.get(k, k),
                key="tambah_produk_target_warehouse",
            )
            if chosen != "__self__":
                target_user_id = chosen
                target_label = f"toko UUID {chosen[:8]}… ({wh_by_user[chosen][0].get('name', '?')})"
            else:
                target_label = "toko admin sendiri"
        else:
            # Mode 3: input manual UUID
            st.caption(
                "ℹ️ Service role belum aktif. **Input manual UUID toko target** di bawah ini, "
                "atau tambahkan `SUPABASE_SERVICE_KEY` di secrets.toml untuk dropdown otomatis."
            )
            uuid_input = st.text_input(
                "UUID Toko Target",
                value=user_id,
                placeholder="1eaa9645-eb0d-4b85-aab8-3c6b514fa59b",
                help="UUID toko tempat produk akan ditambahkan. Default = UUID admin sendiri.",
                key="tambah_produk_target_uuid",
            ).strip()
            if uuid_input:
                target_user_id = uuid_input
                target_label = f"UUID {uuid_input[:8]}…"

    # === Form tambah produk ===
    with st.expander("➕ Tambah Produk Baru", expanded=True):
        with st.form("tambah_produk_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                prod_name = st.text_input(
                    "Nama Produk *",
                    placeholder="cth: Indomie Goreng, Minyak Goreng 1L",
                )
            with col2:
                prod_category = st.text_input(
                    "Kategori (opsional)",
                    placeholder="cth: Sembako, Minuman, Snack",
                )

            col3, col4, col5 = st.columns(3)
            with col3:
                prod_price = st.number_input(
                    "Harga Jual (Rp) *",
                    min_value=0,
                    step=500,
                    value=0,
                )
            with col4:
                prod_stock = st.number_input(
                    "Stok Awal",
                    min_value=0,
                    step=1,
                    value=0,
                )
            with col5:
                prod_active = st.checkbox("Aktif", value=True)

            prod_description = st.text_area(
                "Deskripsi (opsional)",
                placeholder="Catatan produk: variant, supplier, dll.",
                height=70,
            )

            submitted = st.form_submit_button(
                "Simpan Produk",
                type="primary",
                use_container_width=True,
            )

            if submitted:
                if not prod_name or not prod_name.strip():
                    st.error("❌ Nama produk wajib diisi.")
                else:
                    try:
                        runner = admin_core if (admin_core and target_user_id != user_id) else core
                        result = runner.create_product(
                            target_user_id,
                            prod_name.strip(),
                            price=prod_price,
                            stock=prod_stock,
                            category=prod_category,
                            description=prod_description,
                            is_active=prod_active,
                        )
                        if result:
                            st.success(
                                f"✅ Produk **{prod_name}** berhasil ditambahkan ke "
                                f"{target_label} (user_id `{target_user_id[:8]}…`)."
                            )
                            st.balloons()
                        else:
                            st.error("❌ Gagal menambah produk. Cek log server.")
                    except Exception as exc:
                        logger.exception("create_product failed: %s", exc)
                        st.error(f"❌ Error: {exc}")


    # === Daftar produk existing di target toko ===
    st.markdown("---")
    section_card(
        f"Produk Aktif di {target_label}",
        f"Daftar produk yang sudah terdaftar untuk user_id `{target_user_id[:8]}…`. "
        f"Gunakan untuk verifikasi setelah menambah produk baru.",
        icon="ti-list",
    )

    try:
        runner = admin_core if (admin_core and target_user_id != user_id) else core
        products = runner.list_products(target_user_id)
    except Exception as exc:
        logger.error("list_products in tambah_gudang: %s", exc)
        products = None

    if products is None:
        st.error("❌ Gagal memuat data produk. Pastikan tabel 'products' ada di Supabase.")
    elif not products:
        empty_state(
            "ti-package",
            "Belum ada produk",
            "Tambah produk pertama lewat form di atas.",
        )
    else:
        import pandas as _pd2
        rows = []
        for p in products:
            rows.append({
                "ID": p.get("id"),
                "Nama": p.get("name", "—"),
                "Harga": f"Rp {int(p.get('price', 0)):,}".replace(",", "."),
                "Stok": p.get("stock", 0),
                "Kategori": p.get("category") or "—",
                "Status": "✅ Aktif" if p.get("is_active") else "❌ Non-aktif",
            })
        _prod_df = _pd2.DataFrame(rows)
        st.caption(f"Total: **{len(products)}** produk")
        st.dataframe(
            _prod_df,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# HANDLER: Pengaturan (semua user)
# ============================================================

# Nomor WhatsApp Admin laris.AI
ADMIN_WA_NUMBER = "6282112826851"  # Format intl tanpa +
ADMIN_WA_DISPLAY = "+62 821-1282-6851"
ADMIN_WA_MESSAGE = (
    "Halo Admin laris.AI, saya pengguna dashboard dan butuh bantuan."
)


def _render_form_tambah_client(core, bw_url: str, catat_url: str, admin_email: str) -> None:
    """Form A: Tambah Toko Baru (3 tabel: auth.users, clients, wa_users).

    Dipakai oleh Super Admin untuk onboard toko baru.
    """
    section_card(
        "➕ Form Tambah Toko Baru",
        "Pakai form ini untuk daftarkan toko UMKM baru ke sistem laris.AI. "
        "Akan insert ke 3 tabel: `auth.users` (akun login) + `clients` (multi-tenant registry) + `wa_users` (nomor owner).",
        icon="ti-user-plus",
    )

    # Info box: tabel mana yang akan ter-update
    st.info(
        "📋 **Yang akan terjadi setelah klik Submit:**\n\n"
        "| Tabel | Apa yang di-insert |\n"
        "|-------|--------------------|\n"
        "| `auth.users` | Akun login owner (email + password) |\n"
        "| `clients` | Toko, nomor, Fonnte token, metadata JSONB |\n"
        "| `wa_users` | Nomor owner → UUID mapping (untuk routing) |\n",
        icon="📝",
    )

    with st.form("create_client_form_v2"):
        st.markdown("**🧑 Akun Login Owner**")
        c_email = st.text_input("Email Owner (untuk login Streamlit)", placeholder="owner@tokomu.com")
        c_pass = st.text_input("Password Sementara", type="password", placeholder="min 6 karakter")

        st.markdown("---")
        st.markdown("**🏪 Data Toko**")
        c_label = st.text_input("Nama Usaha", placeholder="Toko Sumber Rezeki")
        c_client_id = st.text_input(
            "Client ID (slug)",
            placeholder="toko_sumber_rezeki — otomatis dari nama jika kosong",
            help="Huruf kecil + angka + underscore. Contoh: toko_rezeki, warung_berkah",
        )

        st.markdown("---")
        st.markdown("**📱 2 Nomor WhatsApp**")
        c_phone_cs = st.text_input(
            "① Nomor WA CS (Pelanggan chat ke sini)",
            placeholder="0857xxxxxxxx",
            help="Nomor device Fonnte toko. Pelanggan chat ke nomor ini.",
        )
        c_phone_catat = st.text_input(
            "② Nomor HP Owner (untuk catat transaksi)",
            placeholder="0812xxxxxxxx",
            help="HP owner. Kirim 'jual kopi 50rb' dari nomor ini → tercatat.",
        )

        st.markdown("---")
        st.markdown("**🔑 Token Fonnte**")
        c_fonnte_token = st.text_input(
            "Token Fonnte (device CS)",
            type="password",
            placeholder="Token dari dashboard Fonnte",
            help="WAJIB. Min 10 karakter. Ambil dari https://fonnte.com → device CS → Token.",
        )

        # === Preview schema sebelum submit ===
        with st.expander("🔍 Preview schema yang akan di-insert", expanded=False):
            from core.client_registration import (
                normalize_phone_to_e164,
                normalize_phone_to_display,
                slugify_client_id,
            )
            preview_cid = c_client_id.strip() or slugify_client_id(
                c_label.strip() or (c_email.split("@")[0] if c_email else "toko")
            )
            preview_cs = normalize_phone_to_e164(c_phone_cs.strip())
            preview_catat = normalize_phone_to_e164(c_phone_catat.strip())
            st.code(
                f"┌─ Tabel: clients\n"
                f"│  client_id       = '{preview_cid}'\n"
                f"│  name            = '{c_label.strip() or preview_cid}'\n"
                f"│  fonnte_token    = '***hidden***' (len={len(c_fonnte_token.strip())})\n"
                f"│  owner_phones    = ['{preview_catat}']\n"
                f"│  is_active       = true\n"
                f"│  plan_tier       = 'free'\n"
                f"│  metadata        = {{\n"
                f"│    'user_id': '<UUID dari auth.users>',\n"
                f"│    'wa_cs': '{preview_cs}',\n"
                f"│    'wa_catat': '{preview_catat}',\n"
                f"│    'whatsapp_display': '{normalize_phone_to_display(preview_cs)}',\n"
                f"│    'pattern': 'multitenant_v1',\n"
                f"│  }}\n"
                f"└─\n\n"
                f"┌─ Tabel: wa_users\n"
                f"│  phone     = '{preview_catat}'\n"
                f"│  user_id   = '<UUID dari auth.users>'\n"
                f"│  label     = 'Owner {c_label.strip() or preview_cid}'\n"
                f"└─",
                language="yaml",
            )

        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            submitted = st.form_submit_button("✅ Buat Toko", type="primary", use_container_width=True)
        with col2:
            cancelled = st.form_submit_button("❌ Reset", use_container_width=True)
        if cancelled:
            st.rerun()

    if submitted:
        # === Validasi ===
        errors = []
        if not c_email.strip():
            errors.append("❌ Email Owner wajib diisi")
        elif "@" not in c_email:
            errors.append("❌ Format email tidak valid")
        if not c_pass or len(c_pass) < 6:
            errors.append("❌ Password minimal 6 karakter")
        if not c_label.strip():
            errors.append("❌ Nama Usaha wajib diisi")
        if not c_phone_cs.strip():
            errors.append("❌ Nomor WA CS wajib diisi")
        if not c_phone_catat.strip():
            errors.append("❌ Nomor HP Owner wajib diisi")
        if not c_fonnte_token.strip() or len(c_fonnte_token.strip()) < 10:
            errors.append("❌ Token Fonnte wajib diisi (min 10 karakter)")

        if errors:
            for e in errors:
                st.error(e)
            st.stop()

        # === Submit ===
        try:
            new_id, err = core.create_client_account(c_email.strip(), c_pass)
            if err:
                st.error(f"❌ Gagal membuat akun: {err}")
                st.stop()

            setup = core.setup_dual_wa_client(
                new_id,
                wa_cs=c_phone_cs.strip(),
                wa_catat=c_phone_catat.strip(),
                label=c_label.strip() or c_email.split("@")[0],
                client_id=c_client_id.strip() or None,
                email=c_email.strip(),
                bukuwarung_base_url=bw_url,
                catat_bot_base_url=catat_url,
                fonnte_token=c_fonnte_token.strip(),
            )

            st.success(f"✅ Toko berhasil didaftarkan!")
            st.markdown(
                f"**Detail toko baru:**\n"
                f"- **User ID**: `{new_id}`\n"
                f"- **Client ID**: `{setup['client_id']}`\n"
                f"- **Nama**: {c_label.strip()}\n"
                f"- **Plan**: 🆓 Free (default, bisa di-upgrade nanti)\n\n"
                f"**📋 Tabel yang ter-update:**\n"
                f"- ✅ `auth.users` — akun login\n"
                f"- ✅ `clients` — multi-tenant registry\n"
                f"- ✅ `wa_users` — owner phone mapping\n"
            )

            if setup["bukuwarung_ok"]:
                st.markdown("### 🔗 Webhook untuk Fonnte Dashboard")
                st.markdown(
                    f"Copy-paste URL ini ke **Fonnte → Device CS → Webhook URL**:\n\n"
                    f"```\n{setup['webhook_cs']}\n```\n\n"
                    f"Untuk **Device Owner (catat)**: pakai URL di menu Pengaturan Bisnis toko baru."
                )
            else:
                st.warning(f"Tabel clients gagal update: {setup.get('bukuwarung_error')}")

            st.info(
                "**📝 Langkah selanjutnya:**\n"
                "1. Buka dashboard Fonnte → set webhook URL di atas\n"
                "2. Owner login & coba catat transaksi via WA\n"
                "3. Test customer chat dari HP lain ke nomor CS"
            )
        except Exception as e:
            st.error(f"❌ Error: {str(e)[:200]}")


def _render_form_update_client(core, bw_url: str, catat_url: str, current_user_id: str, admin_email: str) -> None:
    """Form B: Update Toko Existing (1 tabel: clients via upsert)."""
    section_card(
        "✏️ Form Update Toko Existing",
        "Pakai form ini untuk update nomor / token toko yang sudah terdaftar. "
        "Hanya update 1 tabel: `clients` (via upsert on `client_id`).",
        icon="ti-edit",
    )

    st.info(
        "📋 **Yang terjadi setelah klik Submit:**\n\n"
        "| Tabel | Aksi |\n"
        "|-------|------|\n"
        "| `clients` | UPDATE row by `client_id` (nomor, token, plan_tier) |\n"
        "| `wa_users` | Optional — re-link nomor owner kalau berubah |\n",
        icon="📝",
    )

    # === Ambil list client existing untuk dropdown ===
    from core.client_registration import list_all_clients
    try:
        clients = list_all_clients(core)
    except Exception:
        clients = []

    if not clients:
        st.warning("Belum ada client yang terdaftar. Pindah ke tab 'Tambah Toko Baru' dulu.")
        return

    client_options = {f"{c['name']} ({c['client_id']})": c for c in clients}

    with st.form("update_client_form_v2"):
        selected = st.selectbox(
            "Pilih Toko",
            options=list(client_options.keys()),
            help="Pilih toko yang mau di-update",
        )
        if not selected:
            st.stop()
        current = client_options[selected]
        current_meta = current.get("metadata") or {}

        st.markdown("---")
        st.markdown("**📱 Update Nomor (kosongkan jika tidak berubah)**")

        # Tampilkan nilai saat ini sebagai info
        st.caption(
            f"ℹ️ **Nilai saat ini**: CS=`{current_meta.get('wa_cs', '—')}` · "
            f"Catat=`{current_meta.get('wa_catat', '—')}`"
        )

        new_phone_cs = st.text_input(
            "① Nomor WA CS baru",
            placeholder="0857xxxxxxxx (kosongkan jika tidak berubah)",
        )
        new_phone_catat = st.text_input(
            "② Nomor HP Owner baru",
            placeholder="0812xxxxxxxx (kosongkan jika tidak berubah)",
        )

        st.markdown("---")
        st.markdown("**🔑 Update Token (kosongkan jika tidak berubah)**")
        new_token = st.text_input(
            "Token Fonnte baru",
            type="password",
            placeholder="Token baru (kosongkan jika tidak berubah)",
        )

        submitted = st.form_submit_button("💾 Simpan Perubahan", type="primary")

    if submitted:
        try:
            user_id = current_meta.get("user_id") or current.get("client_id", "")
            label = current.get("name", "")

            # Bangun payload update — hanya field yang diisi
            update_kwargs = dict(
                client_id=current["client_id"],
                name=label,
                wa_cs=new_phone_cs.strip() or current_meta.get("wa_cs", ""),
                wa_catat=new_phone_catat.strip() or current_meta.get("wa_catat", ""),
                user_id=user_id,
                bukuwarung_base_url=bw_url,
                catat_bot_base_url=catat_url,
            )
            if new_token.strip():
                update_kwargs["fonnte_token"] = new_token.strip()

            ok, err = core.upsert_bukuwarung_client(**update_kwargs)
            if ok:
                st.success(f"✅ Toko `{current['client_id']}` berhasil di-update!")
            else:
                st.error(f"❌ Gagal: {err}")
        except Exception as e:
            st.error(f"❌ Error: {str(e)[:200]}")


def _render_schema_health_check(core) -> None:
    """Tampilkan status tabel Supabase yang relevan untuk pendaftaran client.

    Ditampilkan di menu Pengaturan Bot → Panel Super Admin agar admin
    tahu tabel mana yang aktif dan mana yang perlu dibuat dulu.
    """
    section_card(
        "Schema Health Check",
        "Status tabel Supabase yang berpengaruh saat pendaftaran client baru.",
        icon="ti-database",
    )

    from core.client_registration import detect_required_tables
    tables = detect_required_tables(core)

    rows = []
    rows.append(("`clients`", "WAJIB — multi-tenant registry", tables.get("clients", False)))
    rows.append(("`auth.users`", "WAJIB — login owner", True))  # selalu ada di Supabase
    rows.append(("`wa_users`", "Owner → UUID mapping (legacy)", tables.get("wa_users", False)))
    rows.append(("`warehouses`", "Auto-create Gudang Utama", tables.get("warehouses", False)))
    rows.append(("`products`", "Daftar produk per toko", tables.get("products", False)))
    rows.append(("`client_settings`", "Settings per tenant", tables.get("client_settings", False)))

    cols = st.columns([1, 3, 1])
    cols[0].markdown("**Tabel**")
    cols[1].markdown("**Fungsi**")
    cols[2].markdown("**Status**")
    for t, desc, ok in rows:
        c1, c2, c3 = st.columns([1, 3, 1])
        c1.code(t)
        c2.markdown(desc)
        if ok:
            c3.success("✅ Aktif")
        else:
            c3.error("❌ Belum ada")


def _render_clients_admin_list(core) -> None:
    """Tampilkan daftar semua client (admin view lintas-tenant)."""
    from core.client_registration import list_all_clients
    section_card(
        "Daftar Semua Client",
        "Monitoring toko yang sudah terdaftar. Hanya Super Admin.",
        icon="ti-list",
    )

    try:
        clients = list_all_clients(core)
    except Exception as exc:
        st.warning(f"Tidak bisa akses `clients` lintas-tenant. Perlu SUPABASE_SERVICE_KEY. ({exc})")
        return

    if not clients:
        info_pill("Belum ada client yang terdaftar.", "info")
        return

    import pandas as pd
    df = pd.DataFrame(clients)
    # Format display
    if "owner_phones" in df.columns:
        df["owner_phones"] = df["owner_phones"].apply(
            lambda x: ", ".join(x) if isinstance(x, list) else str(x)
        )
    # Pilih kolom yang relevan
    show_cols = ["client_id", "name", "is_active", "plan_tier", "owner_phones", "created_at"]
    show_cols = [c for c in show_cols if c in df.columns]
    df_show = df[show_cols].copy()

    st.dataframe(
        df_show,
        use_container_width=True,
        hide_index=True,
        column_config={
            "is_active": st.column_config.CheckboxColumn("Aktif"),
            "plan_tier": st.column_config.TextColumn("Plan"),
        },
    )
    st.caption(f"Total: **{len(clients)}** client terdaftar")


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


def _render_plan_banner(core, user_id, user_email) -> None:
    """Tampilkan banner Free Tier + tombol Upgrade Pro.

    Ditampilkan di Ruang Komando untuk SEMUA user (admin & client).
    - Free: banner kuning + counter "X / 100 transaksi bulan ini" + tombol "⬆️ Upgrade ke Pro"
    - Pro/Bisnis: badge tier + "Sisa X hari lagi"
    - Kemitraan: badge special (no banner)
    """
    client_id = user_id  # Asumsi 1:1 mapping user_id → client_id
    try:
        plan_limits = core.get_plan_limits(client_id)
        quota = core.check_tx_quota(client_id)
    except Exception as exc:
        logger.debug("render_plan_banner error: %s", exc)
        return

    tier = plan_limits["tier"]
    tier_label = {
        "free":      "🆓 Free",
        "pro":       "⭐ Pro",
        "bisnis":    "🏢 Bisnis",
        "kemitraan": "🤝 Kemitraan",
    }.get(tier, tier.title())

    # === KEMITRAAN: badge gold, no banner ===
    if tier == "kemitraan":
        st.markdown(
            "<div style='text-align:right;'>"
            "<span style='background:linear-gradient(135deg,#FFD700,#FFA500);"
            "color:#000;padding:.25rem .75rem;border-radius:1rem;"
            "font-size:.85rem;font-weight:600;'>"
            "🤝 Kemitraan — Akses Penuh</span></div>",
            unsafe_allow_html=True,
        )
        return

    # === FREE TIER BANNER ===
    if tier == "free":
        cols = st.columns([3, 1])
        with cols[0]:
            tx_count = quota.get("current", 0)
            tx_limit = quota.get("limit", 100)
            pct = min(100, int(tx_count / tx_limit * 100)) if tx_limit else 0
            warn_color = "#ef4444" if pct >= 80 else "#f59e0b"
            st.markdown(
                f"<div class='laris-plan-banner' style='background:rgba(245,158,11,.08);"
                f"border:1px solid {warn_color};border-radius:.75rem;padding:1rem 1.25rem;"
                f"margin-bottom:1rem;'>"
                f"<div style='display:flex;align-items:center;gap:.5rem;margin-bottom:.5rem;'>"
                f"<span style='background:#f59e0b;color:#fff;padding:.2rem .6rem;"
                f"border-radius:1rem;font-size:.75rem;font-weight:700;'>🆓 FREE</span>"
                f"<strong>Upgrade ke Pro</strong> — transaksi tanpa batas & AI CS 24/7"
                f"</div>"
                f"<div style='background:rgba(0,0,0,.06);border-radius:.5rem;height:.5rem;"
                f"overflow:hidden;margin-bottom:.25rem;'>"
                f"<div style='background:{warn_color};height:100%;width:{pct}%;'></div></div>"
                f"<small style='color:#6b7280;'>📊 {tx_count} / {tx_limit} transaksi bulan ini</small>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with cols[1]:
            if st.button("⬆️ Upgrade Pro", key="upgrade_pro_top", type="primary", use_container_width=True):
                _show_upgrade_dialog()

    # === PRO / BISNIS: badge kecil ===
    else:
        try:
            resp = (
                core.supabase.table("clients")
                .select("plan_expires_at")
                .eq("client_id", client_id)
                .limit(1)
                .execute()
            )
            rows = resp.data or []
            expires_at = rows[0].get("plan_expires_at") if rows else None
        except Exception:
            expires_at = None

        days_left = ""
        if expires_at:
            try:
                from datetime import datetime, timezone
                exp_str = expires_at.replace("Z", "+00:00")
                exp_dt = datetime.fromisoformat(exp_str)
                now = datetime.now(timezone.utc)
                if exp_dt.tzinfo is None:
                    exp_dt = exp_dt.replace(tzinfo=timezone.utc)
                days = max(0, (exp_dt - now).days)
                days_left = f" · ⏰ {days} hari lagi"
            except Exception:
                pass

        st.markdown(
            f"<div style='text-align:right;'>"
            f"<span style='background:linear-gradient(135deg,#3b82f6,#8b5cf6);"
            f"color:#fff;padding:.25rem .75rem;border-radius:1rem;"
            f"font-size:.8rem;font-weight:600;'>{tier_label}{days_left}</span></div>",
            unsafe_allow_html=True,
        )


def _show_upgrade_dialog() -> None:
    """Dialog instruksi upgrade Pro (manual transfer)."""
    st.info(
        "**Cara Upgrade ke Pro (Rp 149.000/bulan):**\n\n"
        "1. Transfer **Rp 149.000** ke salah satu rekening:\n"
        "   • BCA: 123-456-7890 a/n Rafih R\n"
        "   • GoPay/OVO/DANA: 0812-3456-7890\n\n"
        "2. Kirim bukti transfer via WhatsApp ke **0857-8997-4981**\n\n"
        "3. Admin akan aktifkan Pro dalam 1x24 jam\n\n"
        "✅ **Pro** (Rp 149k/bln): 1.000 transaksi/bulan + AI CS 24/7 + 5 gudang\n"
        "✅ **Bisnis** (Rp 299k/bln): 10.000 transaksi/bulan + unlimited AI CS + 20 gudang\n"
        "✅ **Kemitraan**: Custom — hubungi admin untuk penawaran",
        icon="💎",
    )


def render_daftar_produk(core, user_id, user_email) -> None:
    """Halaman khusus Daftar Produk — read-only + form input untuk SEMUA user.

    Tabel sederhana: nama, harga, stok, kategori, status aktif.
    Sumber: tabel `products` di Supabase.

    Isolasi tenant dijamin oleh 3 lapis:
    1. Aplikasi: laris_core.list_products() filter .eq("user_id", uid)
    2. Session: user_id selalu dari session user yang login
    3. Database: RLS policy p_own_products (user_id = auth.uid())

    SEMUA user (admin & client) bisa tambah produk ke gudang mereka sendiri.
    Admin dengan service_role bisa juga pilih toko client (lihat _render_tambah_produk_section).
    """
    section_card(
        "Daftar Produk",
        "Daftar produk & harga yang tersedia di toko Anda. "
        "Tambah produk baru lewat form di bawah.",
        icon="ti-box",
    )

    is_admin = is_super_admin(user_email)

    # Info untuk Client
    if not is_admin:
        st.info(
            "📋 **Info untuk Client:** Ini adalah daftar produk yang terdaftar di toko Anda. "
            "Gunakan form di bawah untuk tambah produk baru ke gudang Anda."
        )
    else:
        st.info(
            "🛡️ **Mode Admin Super** — Tampilan ini di-scope ke toko yang sedang Anda "
            "buka. Produk yang ditambah lewat form di bawah akan masuk ke toko Anda. "
            "Untuk menambah produk ke toko client, gunakan menu 'Tambah Gudang' di atas."
        )

    # === Form tambah produk (SEMUA user bisa akses — produk masuk ke toko sendiri) ===
    with st.expander("➕ Tambah Produk ke Gudang Saya", expanded=False):
        with st.form("tambah_produk_client_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                cp_name = st.text_input(
                    "Nama Produk *",
                    placeholder="cth: Indomie Goreng, Minyak Goreng 1L",
                    key="cp_name",
                )
            with col2:
                cp_category = st.text_input(
                    "Kategori (opsional)",
                    placeholder="cth: Sembako, Minuman, Snack",
                    key="cp_category",
                )

            col3, col4 = st.columns(2)
            with col3:
                cp_price = st.number_input(
                    "Harga Jual (Rp) *",
                    min_value=0,
                    step=500,
                    value=0,
                    key="cp_price",
                )
            with col4:
                cp_stock = st.number_input(
                    "Stok Awal",
                    min_value=0,
                    step=1,
                    value=0,
                    key="cp_stock",
                )

            cp_active = st.checkbox("Aktif", value=True, key="cp_active")

            cp_submitted = st.form_submit_button(
                "Simpan ke Gudang Saya",
                type="primary",
                use_container_width=True,
            )

            if cp_submitted:
                if not cp_name or not cp_name.strip():
                    st.error("❌ Nama produk wajib diisi.")
                else:
                    try:
                        result = core.create_product(
                            user_id,
                            cp_name.strip(),
                            price=cp_price,
                            stock=cp_stock,
                            category=cp_category,
                            is_active=cp_active,
                        )
                        if result:
                            st.success(
                                f"✅ Produk **{cp_name}** berhasil ditambahkan ke gudang Anda. "
                                f"Refresh halaman untuk melihat di tabel."
                            )
                            st.balloons()
                        else:
                            st.error("❌ Gagal menambah produk. Cek log server.")
                    except Exception as exc:
                        logger.exception("create_product (client) failed: %s", exc)
                        st.error(f"❌ Error: {exc}")

    # === Tabel produk existing ===
    try:
        products = core.list_products(user_id)
    except Exception as exc:
        logger.error("list_products di Daftar Produk: %s", exc)
        products = None

    if products is None:
        st.error("Gagal memuat data produk. Pastikan tabel 'products' tersedia di Supabase.")
        return

    if not products:
        st.info("Belum ada produk terdaftar. Tambah produk pertama lewat form di atas.")
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
