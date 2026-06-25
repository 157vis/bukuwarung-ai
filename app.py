import streamlit as st
import pandas as pd

from brand import APP_NAME, PAGE_ICON, PAGE_TITLE, DASHBOARD_TITLE
from landing import render_landing
from login import show_login_page, get_current_user, logout
from laris_core import LarisCore


AGENT_LABELS = {"admin": "Admin AI", "logistik": "Logistik AI"}

# Hanya email ini yang boleh menambah & mengedit client baru.
SUPER_ADMIN_EMAIL = "rafihrr1@gmail.com"


def agent_label(agent_id) -> str:
    return AGENT_LABELS.get(agent_id, agent_id or "AI")


def get_core() -> LarisCore:
    return LarisCore(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"],
        st.secrets["GROQ_API_KEY"],
    )


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
            header[data-testid="stHeader"] { display: none !important; }
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
            /* Latar utama: gradient halus + aksen radial lembut */
            .stApp {
                background:
                    radial-gradient(1200px 600px at 85% -10%, rgba(124,58,237,0.18), transparent 60%),
                    radial-gradient(900px 500px at -10% 110%, rgba(30,64,175,0.18), transparent 55%),
                    linear-gradient(160deg, #0b1220 0%, #0f172a 45%, #111827 100%);
                color: #e5e7eb;
            }
            /* Sidebar glassmorphism */
            section[data-testid="stSidebar"] > div {
                background: rgba(17, 24, 39, 0.72);
                backdrop-filter: blur(10px);
                border-right: 1px solid rgba(148,163,184,0.15);
            }
            /* Heading */
            h1, h2, h3, h4 { color: #f8fafc !important; letter-spacing: 0.2px; }
            /* Metric & expander jadi kartu kaca */
            div[data-testid="stMetric"],
            div[data-testid="stExpander"],
            div[data-testid="stForm"] {
                background: rgba(255,255,255,0.04);
                border: 1px solid rgba(148,163,184,0.15);
                border-radius: 16px;
                padding: 1rem 1.1rem;
                box-shadow: 0 8px 24px rgba(0,0,0,0.25);
            }
            div[data-testid="stMetricValue"] { color: #f8fafc; }
            /* Tombol primer bergaya brand */
            .stButton > button[kind="primary"] {
                background: linear-gradient(135deg, #7c3aed, #1e40af);
                border: none; border-radius: 12px; font-weight: 700;
            }
            .stButton > button { border-radius: 12px; }
            /* Dataframe sedikit transparan */
            div[data-testid="stDataFrame"] {
                border-radius: 14px; overflow: hidden;
                border: 1px solid rgba(148,163,184,0.15);
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def get_query_flag(name: str) -> bool:
    params = getattr(st, "query_params", {}) or {}
    return params.get(name, [None])[0] == "1"


def render_home() -> None:
    # Tombol akses native Streamlit (selalu terbaca, tidak overlay, tidak di dalam iframe).
    col_brand, col_cta = st.columns([4, 1])
    with col_brand:
        st.markdown(f"### {APP_NAME}")
    with col_cta:
        if st.button("Masuk ke Dashboard", type="primary", use_container_width=True):
            st.session_state["show_login"] = True
            st.rerun()
    render_landing()


def render_dashboard(core: LarisCore, user) -> None:
    inject_dashboard_style()
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

    # Hamburger / toggle menu (restore quick access)
    if 'show_menu' not in st.session_state:
        st.session_state.show_menu = True

    col1, col2 = st.columns([1, 19])
    with col1:
        if st.button('\u2630', key='hamburger_button', help='Tampilkan atau sembunyikan menu'):
            st.session_state.show_menu = not st.session_state.show_menu
    with col2:
        pass

    warehouse_enabled = core.table_exists("warehouses")

    # Sidebar content only rendered when menu is shown.
    # "Ruang Komando" diletakkan paling depan: owner langsung disodorkan keputusan (Proactive UI).
    menu_items = ["Ruang Komando", "Ringkasan", "Catat Transaksi", "Buku Kas", "Laporan KUR"]
    if warehouse_enabled:
        menu_items.append("Gudang")
    menu_items.append("Pengaturan")

    if st.session_state.show_menu:
        st.sidebar.title(APP_NAME)
        st.sidebar.markdown(f"**{DASHBOARD_TITLE}**")
        st.sidebar.divider()
        st.sidebar.markdown(f"**Pengguna:** {user_email or 'Unknown'}  ")
        if st.sidebar.button("Logout"):
            logout()
        st.sidebar.divider()

        menu = st.sidebar.radio(
            "Menu",
            menu_items,
            index=0,
        )
    else:
        # Fallback when sidebar is hidden: show compact selector at top
        menu = st.selectbox("Menu", menu_items)

    df = core.get_dashboard_data(user_id)
    score = core.calculate_laris_score(df)

    if menu == "Ruang Komando":
        st.title("🚀 Ruang Komando")
        st.caption("Keputusan yang disodorkan tim AI Anda. Setujui atau tolak langsung di sini.")

        if not core.table_exists("approvals"):
            st.warning(
                "Tabel 'approvals' belum ada di Supabase. Jalankan `sql/create_approvals.sql` "
                "di SQL Editor Supabase untuk mengaktifkan Ruang Komando."
            )
        else:
            approvals = core.list_pending_approvals(user_id)
            if approvals is None:
                st.error("Gagal memuat data approval. Pastikan tabel 'approvals' tersedia di Supabase.")
            elif not approvals:
                st.success("✅ Tidak ada keputusan menunggu. Semua aman, Bos!")
            else:
                st.markdown(f"**{len(approvals)} keputusan menunggu persetujuan Anda:**")
                for a in approvals:
                    with st.container(border=True):
                        st.markdown(f"#### 💡 {agent_label(a.get('agent_id'))}")
                        st.write(a.get("summary", ""))
                        payload = a.get("payload") or {}
                        if payload:
                            with st.expander("Lihat detail aksi"):
                                st.json(payload)
                        c1, c2, _ = st.columns([1, 1, 4])
                        if c1.button("✅ Setujui", key=f"approve_{a['id']}", type="primary"):
                            core.update_approval_status(user_id, a["id"], "APPROVED")
                            st.success("Disetujui & diproses!")
                            st.rerun()
                        if c2.button("❌ Tolak", key=f"reject_{a['id']}"):
                            core.update_approval_status(user_id, a["id"], "REJECTED")
                            st.info("Keputusan ditolak.")
                            st.rerun()

        st.markdown("---")
        st.subheader("Aktivitas WhatsApp Terbaru")
        if not core.table_exists("wa_messages"):
            st.caption("Aktifkan log percakapan dengan menjalankan `sql/create_approvals.sql` (tabel 'wa_messages').")
        else:
            msgs = core.list_wa_messages(user_id, limit=20)
            if not msgs:
                st.caption("Belum ada percakapan WhatsApp.")
            else:
                for m in msgs:
                    if m.get("role") == "user":
                        with st.chat_message("user"):
                            st.write(m.get("content", ""))
                    else:
                        with st.chat_message("assistant"):
                            st.markdown(f"**{agent_label(m.get('agent_id'))}**")
                            st.write(m.get("content", ""))

    elif menu == "Ringkasan":
        st.title("Ringkasan Bisnis")
        col1, col2, col3, col4 = st.columns(4)
        total_income = int(df[df["type"] == "Pemasukan"]["amount"].sum()) if not df.empty else 0
        total_expense = int(df[df["type"] == "Pengeluaran"]["amount"].sum()) if not df.empty else 0
        balance = total_income - total_expense

        col1.metric("Total Pemasukan", f"Rp {total_income:,}")
        col2.metric("Total Pengeluaran", f"Rp {total_expense:,}")
        col3.metric("Saldo Bersih", f"Rp {balance:,}")
        col4.metric("Laris Score", f"{score['score']}/100")

        st.markdown("---")
        if df.empty:
            st.info("Belum ada transaksi. Silakan catat transaksi pertama Anda di menu 'Catat Transaksi'.")
        else:
            if not warehouse_enabled:
                st.warning("Fitur gudang belum tersedia. Pastikan tabel 'warehouses' di Supabase sudah dibuat untuk mengaktifkan manajemen gudang.")

            st.subheader("Statistik Ringkas")
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
                st.subheader("Top Pengeluaran")
                st.bar_chart(top_costs.head(5))

            st.subheader("Saran AI")
            if len(df) >= 5:
                st.info(core.get_ai_advisor_insights(df))
            else:
                st.warning("Catat minimal 5 transaksi agar AI dapat memberi rekomendasi lebih baik.")

            with st.expander("Tampilkan aktivitas terbaru", expanded=False):
                recent = df.sort_values(by="date", ascending=False).head(6).reset_index(drop=True)
                st.table(recent[["date", "type", "category", "amount", "note"]])

    elif menu == "Catat Transaksi":
        st.title("Catat Transaksi")
        with st.form("transaction_form"):
            type_txn = st.radio("Jenis Transaksi", ["Pemasukan", "Pengeluaran"], horizontal=True)
            category = st.text_input("Kategori", value="Penjualan")
            amount = st.number_input("Jumlah (Rp)", min_value=0, step=1000)
            note = st.text_input("Catatan", value="")
            is_prive = st.checkbox("Prive / ambil pribadi")
            submitted = st.form_submit_button("Simpan Transaksi")

            if submitted:
                if amount <= 0:
                    st.error("Masukkan jumlah transaksi yang valid.")
                else:
                    core.db_insert_transaction(user_id, type_txn, category, int(amount), note, is_prive=is_prive)
                    st.success("Transaksi berhasil dicatat.")
                    st.experimental_rerun()

        st.markdown("---")
        st.write("Gunakan form di atas untuk mencatat pemasukan atau pengeluaran baru.")

    elif menu == "Buku Kas":
        st.title("Buku Kas")
        if df.empty:
            st.info("Buku kas masih kosong. Tambahkan transaksi terlebih dahulu.")
        else:
            st.markdown("**Ringkasan buku kas terbaru**")
            summary = df.sort_values(by="date", ascending=False).reset_index(drop=True)
            st.dataframe(summary, height=320)
            if st.checkbox("Tampilkan semua entri buku kas", value=False):
                st.dataframe(df.sort_values(by="date", ascending=False).reset_index(drop=True))

            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("Unduh CSV", csv, file_name="buku_kas.csv", mime="text/csv")

            st.markdown("---")
            st.subheader("Edit atau Hapus Transaksi")
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
                    updated = st.form_submit_button("Simpan Perubahan")
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
                            st.experimental_rerun()

                if st.button("Hapus transaksi ini", key="delete_txn_button"):
                    core.db_delete_transaction(user_id, selected_txn["id"])
                    st.success("Transaksi berhasil dihapus.")
                    st.experimental_rerun()

    elif menu == "Laporan KUR":
        st.title("Laporan KUR")
        if df.empty:
            st.info("Masih belum ada data untuk laporan.")
        else:
            total_income = int(df[df["type"] == "Pemasukan"]["amount"].sum())
            total_expense = int(df[df["type"] == "Pengeluaran"]["amount"].sum())
            net_profit = total_income - total_expense
            st.metric("Pendapatan", f"Rp {total_income:,}")
            st.metric("Biaya", f"Rp {total_expense:,}")
            st.metric("Laba Bersih", f"Rp {net_profit:,}")
            st.markdown(
                f"**Insight**: {score['insight']}" 
                f"**Kesehatan**: {score['level'].capitalize()}"
            )

    elif menu == "Pengaturan":
        st.title("⚙️ Pengaturan")
        is_admin = (user_email or "").strip().lower() == SUPER_ADMIN_EMAIL

        if not is_admin:
            st.info(
                "Penambahan & pengeditan client baru hanya dilakukan oleh Admin Laris.AI "
                f"({SUPER_ADMIN_EMAIL}). Hubungi admin untuk mendaftarkan nomor WhatsApp Anda."
            )
            st.caption(f"User ID Anda (untuk referensi ke admin): `{user_id}`")
        elif not core.table_exists("wa_users"):
            st.warning(
                "Tabel 'wa_users' belum ada di Supabase. Jalankan `sql/setup_laris_ai.sql` "
                "di SQL Editor Supabase terlebih dahulu."
            )
        else:
            st.success(f"Mode Admin Super aktif: {user_email}")

            # 1) Buat client baru (akun + nomor WA sekaligus)
            st.subheader("➕ Tambah Client Baru")
            with st.form("create_client_form"):
                c_email = st.text_input("Email Client")
                c_pass = st.text_input("Password Sementara", type="password")
                c_phone = st.text_input("Nomor WhatsApp (opsional)", placeholder="0812xxxxxxxx")
                c_label = st.text_input("Nama Usaha / Label (opsional)")
                if st.form_submit_button("Buat Client"):
                    if not c_email.strip() or len(c_pass) < 6:
                        st.error("Email wajib & password minimal 6 karakter.")
                    else:
                        new_id, err = core.create_client_account(c_email.strip(), c_pass)
                        if err:
                            st.error(f"Gagal membuat client: {err}")
                        else:
                            if c_phone.strip():
                                try:
                                    core.link_wa_number(new_id, c_phone, c_label or None)
                                except Exception as e:
                                    st.warning(f"Akun dibuat, tapi gagal hubungkan WA: {str(e)[:120]}")
                            st.success(f"Client dibuat! user_id: {new_id}")
                            st.rerun()

            # 2) Hubungkan / petakan nomor WA ke client (berdasarkan user_id)
            st.markdown("---")
            st.subheader("🔗 Hubungkan Nomor WA ke Client")
            with st.form("link_client_wa_form"):
                target_uid = st.text_input("User ID Client")
                wa_phone = st.text_input("Nomor WhatsApp", placeholder="0812xxxxxxxx")
                wa_label = st.text_input("Label (opsional)")
                if st.form_submit_button("Hubungkan"):
                    if not target_uid.strip() or not wa_phone.strip():
                        st.error("User ID & nomor WA wajib diisi.")
                    else:
                        try:
                            core.link_wa_number(target_uid.strip(), wa_phone, wa_label or None)
                            st.success(f"Nomor {core.normalize_phone(wa_phone)} terhubung ke {target_uid.strip()}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Gagal menghubungkan: {str(e)[:150]}")

            # 3) Daftar semua client (mapping WA) + edit/hapus
            st.markdown("---")
            st.subheader("📋 Semua Client Terdaftar")
            numbers = core.list_all_wa_numbers()
            if numbers is None:
                st.error("Gagal memuat data. Pastikan tabel 'wa_users' tersedia.")
            elif not numbers:
                st.info("Belum ada client/nomor WA terdaftar.")
            else:
                for n in numbers:
                    c1, c2 = st.columns([5, 1])
                    label = f" — {n.get('label')}" if n.get('label') else ""
                    c1.write(f"📱 **{n.get('phone')}**{label}  \n`{n.get('user_id')}`")
                    if c2.button("Hapus", key=f"unlink_{n['id']}"):
                        core.unlink_wa_number(n["user_id"], n["phone"])
                        st.rerun()

    elif menu == "Gudang":
        st.title("Manajemen Gudang & Inventaris")
        core = get_core()
        user = user
        user_id = None
        if isinstance(user, dict):
            user_id = user.get("id")
        else:
            user_id = getattr(user, "id", None)

        # Warehouse creation
        with st.expander("Tambah Gudang", expanded=False):
            with st.form("create_warehouse"):
                wh_name = st.text_input("Nama Gudang")
                wh_location = st.text_input("Lokasi (opsional)")
                wh_notes = st.text_area("Keterangan (opsional)")
                if st.form_submit_button("Buat Gudang"):
                    if not wh_name:
                        st.error("Nama gudang wajib.")
                    else:
                        res = core.create_warehouse(user_id, wh_name, wh_location or None, wh_notes or None)
                        st.success("Gudang dibuat.")

        # List warehouses
        try:
            warehouses = core.list_warehouses(user_id)
        except BaseException as exc:
            print("ERROR app.render_dashboard list_warehouses:", exc)
            warehouses = None

        st.subheader("Daftar Gudang")
        if warehouses is None:
            st.error("Terjadi kesalahan saat memuat data gudang. Pastikan tabel 'warehouses' tersedia di Supabase.")
            st.stop()

        if not warehouses:
            st.info("Belum ada gudang. Buat gudang baru di atas.")
        else:
            options = {str(w.get('id')): w for w in warehouses}
            cols = st.columns([3, 1])
            with cols[0]:
                sel = st.selectbox("Pilih Gudang", [f"{w.get('name')} (id:{w.get('id')})" for w in warehouses])
                selected_id = None
                if sel:
                    # extract id from selection
                    try:
                        selected_id = int(sel.split("id:")[-1].strip(')'))
                    except Exception:
                        selected_id = warehouses[0].get('id')
            with cols[1]:
                if st.button("Segarkan Gudang"):
                    st.experimental_rerun()

            # Inventory entry form
            st.markdown("---")
            st.subheader("Catat Barang (In/Out)")
            with st.form("inventory_form"):
                if warehouses:
                    wh_choices = {w.get('id'): w.get('name') for w in warehouses}
                    wh_selected = st.selectbox("Gudang", options=list(wh_choices.keys()), format_func=lambda x: wh_choices.get(x))
                else:
                    st.warning("Buat minimal satu gudang terlebih dahulu.")
                    wh_selected = None

                barang = st.text_input("Nama Barang")
                qty_in = st.number_input("Masuk (qty)", min_value=0, step=1, value=0)
                qty_out = st.number_input("Keluar (qty)", min_value=0, step=1, value=0)
                keterangan = st.text_input("Keterangan")
                if st.form_submit_button("Simpan Inventaris"):
                    if not wh_selected:
                        st.error("Pilih gudang terlebih dahulu.")
                    elif not barang:
                        st.error("Isi nama barang.")
                    else:
                        res = core.add_inventory_entry(user_id, wh_selected, barang, qty_in, qty_out, keterangan or None)
                        st.success("Entri inventaris tersimpan.")

            # Show recent inventory
            st.markdown("---")
            st.subheader("Aktivitas Inventaris Terakhir")
            inv = core.list_inventory(user_id, warehouse_id=selected_id if 'selected_id' in locals() else None)
            if not inv:
                st.info("Belum ada aktivitas inventaris.")
            else:
                import pandas as _pd

                inv_df = _pd.DataFrame(inv)
                if not inv_df.empty and 'date' in inv_df.columns:
                    inv_df['date'] = pd.to_datetime(inv_df['date'])
                st.dataframe(inv_df.head(30))


def main() -> None:
    page_config()
    render_header()

    show_login = st.session_state.get("show_login", False) or get_query_flag("login")
    if get_query_flag("login"):
        st.session_state["show_login"] = True
        show_login = True

    if show_login:
        if show_login_page():
            render_dashboard(get_core(), get_current_user())
        return

    if st.session_state.get("user"):
        render_dashboard(get_core(), get_current_user())
    else:
        render_home()


if __name__ == "__main__":
    main()
