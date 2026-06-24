import streamlit as st
import pandas as pd

from brand import APP_NAME, PAGE_ICON, PAGE_TITLE, DASHBOARD_TITLE, LOGIN_QUERY
from landing import render_landing
from login import show_login_page, get_current_user, logout
from laris_core import LarisCore


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


def get_query_flag(name: str) -> bool:
    params = getattr(st, "query_params", {}) or {}
    return params.get(name, [None])[0] == "1"


def render_home() -> None:
    st.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
            <div>
                <h1 style="margin:0; font-size:2.5rem;">{APP_NAME}</h1>
                <p style="margin:0.25rem 0 0; color:#475569; font-size:1.05rem;">AI Multi-Agent untuk UMKM Indonesia</p>
            </div>
            <div>
                <a class="app-link-button" href="{LOGIN_QUERY}">Masuk ke Dashboard</a>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_landing()


def render_dashboard(core: LarisCore, user) -> None:
    user_id = None
    if isinstance(user, dict):
        user_id = user.get("id") or user.get("user", {}).get("id")
    else:
        user_id = getattr(user, "id", None)
        nested = getattr(user, "user", None)
        if not user_id and nested is not None:
            user_id = getattr(nested, "id", None)

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

    # Sidebar content only rendered when menu is shown
    if st.session_state.show_menu:
        st.sidebar.title(APP_NAME)
        st.sidebar.markdown(f"**{DASHBOARD_TITLE}**")
        st.sidebar.divider()
        st.sidebar.markdown(f"**Pengguna:** {getattr(user, 'email', None) or user.get('email', 'Unknown')}  ")
        if st.sidebar.button("Logout"):
            logout()
        st.sidebar.divider()

        menu = st.sidebar.radio(
            "Menu",
            ["Ringkasan", "Catat Transaksi", "Buku Kas", "Laporan KUR", "Gudang"],
            index=0,
        )
    else:
        # Fallback when sidebar is hidden: show compact selector at top
        menu = st.selectbox("Menu", ["Ringkasan", "Catat Transaksi", "Buku Kas", "Laporan KUR", "Gudang"]) 

    df = core.get_dashboard_data(user_id)
    score = core.calculate_laris_score(df)

    if menu == "Ringkasan":
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
            summary = df.sort_values(by="date", ascending=False).head(8).reset_index(drop=True)
            st.dataframe(summary, height=320)
            if st.checkbox("Tampilkan semua entri buku kas", value=False):
                st.dataframe(df.sort_values(by="date", ascending=False).reset_index(drop=True))

            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("Unduh CSV", csv, file_name="buku_kas.csv", mime="text/csv")

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
        warehouses = core.list_warehouses(user_id)
        st.subheader("Daftar Gudang")
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
