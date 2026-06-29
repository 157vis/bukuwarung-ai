"""Dashboard demo publik untuk laris.AI."""

from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from brand import APP_NAME, DASHBOARD_TITLE, WA_BASE_URL
from laris_core import LarisCore


def _inject_demo_style() -> None:
    st.markdown(
        """
        <style>
            .stApp {
                background:
                    radial-gradient(1200px 600px at 85% -10%, rgba(124,58,237,0.18), transparent 60%),
                    radial-gradient(900px 500px at -10% 110%, rgba(30,64,175,0.18), transparent 55%),
                    linear-gradient(160deg, #0b1220 0%, #0f172a 45%, #111827 100%);
                color: #e5e7eb;
            }
            section[data-testid="stSidebar"] > div {
                background: rgba(17, 24, 39, 0.72);
                backdrop-filter: blur(10px);
                border-right: 1px solid rgba(148,163,184,0.15);
            }
            h1, h2, h3, h4 { color: #f8fafc !important; letter-spacing: 0.2px; }
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
            .stButton > button[kind="primary"] {
                background: linear-gradient(135deg, #7c3aed, #1e40af);
                border: none; border-radius: 12px; font-weight: 700;
            }
            .stButton > button { border-radius: 12px; }
            div[data-testid="stDataFrame"] {
                border-radius: 14px; overflow: hidden;
                border: 1px solid rgba(148,163,184,0.15);
            }
            .demo-pill {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                background: rgba(34,197,94,0.14);
                color: #bbf7d0;
                border: 1px solid rgba(34,197,94,0.28);
                border-radius: 999px;
                padding: 8px 14px;
                font-weight: 700;
                margin-bottom: 8px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _demo_transactions() -> pd.DataFrame:
    now = datetime.now()
    rows = [
        ((now - timedelta(days=14)).strftime("%Y-%m-%d 08:15"), "Pemasukan", "Penjualan Warung", 780000, "Penjualan harian awal pekan", False),
        ((now - timedelta(days=13)).strftime("%Y-%m-%d 12:10"), "Pengeluaran", "Belanja Stok", 320000, "Belanja mie, telur, dan minuman", False),
        ((now - timedelta(days=12)).strftime("%Y-%m-%d 10:25"), "Pemasukan", "Penjualan Warung", 845000, "Penjualan rame jam makan siang", False),
        ((now - timedelta(days=11)).strftime("%Y-%m-%d 18:05"), "Pengeluaran", "Operasional", 85000, "Gas, plastik, dan es batu", False),
        ((now - timedelta(days=9)).strftime("%Y-%m-%d 08:40"), "Pemasukan", "Penjualan Warung", 910000, "Repeat order katering kantor", False),
        ((now - timedelta(days=8)).strftime("%Y-%m-%d 15:20"), "Pengeluaran", "Belanja Stok", 410000, "Restock sembako dan saus", False),
        ((now - timedelta(days=7)).strftime("%Y-%m-%d 20:10"), "Pemasukan", "Penjualan Warung", 995000, "Akhir pekan lebih ramai", False),
        ((now - timedelta(days=6)).strftime("%Y-%m-%d 16:40"), "Pengeluaran", "Piutang / Kasbon", 70000, "Kasbon pelanggan langganan", False),
        ((now - timedelta(days=4)).strftime("%Y-%m-%d 09:05"), "Pemasukan", "Penjualan Warung", 1025000, "Penjualan + pesanan WhatsApp", False),
        ((now - timedelta(days=3)).strftime("%Y-%m-%d 17:00"), "Pengeluaran", "Belanja Stok", 365000, "Restock minuman dan snack", False),
        ((now - timedelta(days=2)).strftime("%Y-%m-%d 11:15"), "Pemasukan", "Penjualan Warung", 1110000, "Penjualan lunch box", False),
        ((now - timedelta(days=1)).strftime("%Y-%m-%d 21:00"), "Pengeluaran", "Prive", 150000, "Ambil pribadi untuk kebutuhan rumah", True),
    ]
    running_balance = 0
    data = []
    for idx, (date, tx_type, category, amount, note, is_prive) in enumerate(rows, start=1):
        running_balance += amount if tx_type == "Pemasukan" else -amount
        data.append(
            {
                "id": idx,
                "date": date,
                "type": tx_type,
                "category": category,
                "amount": amount,
                "note": note,
                "is_prive": is_prive,
                "running_balance": running_balance,
            }
        )
    return pd.DataFrame(data)


def _demo_approvals() -> list[dict]:
    return [
        {
            "id": 1,
            "agent_id": "admin",
            "summary": "Harga es teh manis naik 1.000 karena biaya gula meningkat. Simulasi: margin tetap aman.",
            "payload": {"aksi": "update_harga", "produk": "Es Teh Manis", "harga_lama": 4000, "harga_baru": 5000},
        },
        {
            "id": 2,
            "agent_id": "logistik",
            "summary": "Stok mie instan tinggal 18 pcs. Rekomendasi restock 6 dus untuk 7 hari ke depan.",
            "payload": {"aksi": "restock", "produk": "Mie Instan", "stok_sekarang": 18, "saran_order": 72},
        },
    ]


def _demo_messages() -> list[dict]:
    return [
        {"role": "user", "content": "Hari ini penjualan agak ramai, stok mie aman tidak?"},
        {"role": "assistant", "agent_id": "logistik", "content": "Stok mie tinggal 18 pcs. Sebaiknya restock 6 dus sebelum akhir pekan."},
        {"role": "user", "content": "Kalau harga es teh dinaikkan, kira-kira aman?"},
        {"role": "assistant", "agent_id": "admin", "content": "Aman. Kenaikan 1.000 masih menjaga margin dan tidak terlalu jauh dari harga pasar sekitar."},
    ]


def _demo_warehouses() -> list[dict]:
    return [
        {"id": 1, "name": "Gudang Utama", "location": "Belakang Warung"},
        {"id": 2, "name": "Freezer Minuman", "location": "Area Kasir"},
    ]


def _demo_inventory() -> pd.DataFrame:
    now = datetime.now()
    rows = [
        {"date": (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M"), "warehouse": "Gudang Utama", "barang": "Mie Instan", "qty_in": 24, "qty_out": 12, "note": "Penjualan harian"},
        {"date": (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M"), "warehouse": "Gudang Utama", "barang": "Telur", "qty_in": 60, "qty_out": 34, "note": "Masuk dari supplier"},
        {"date": (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M"), "warehouse": "Freezer Minuman", "barang": "Teh Botol", "qty_in": 48, "qty_out": 19, "note": "Restock sore"},
        {"date": now.strftime("%Y-%m-%d %H:%M"), "warehouse": "Gudang Utama", "barang": "Beras 5kg", "qty_in": 10, "qty_out": 4, "note": "Penjualan paket bulanan"},
    ]
    return pd.DataFrame(rows)


def _demo_advisor(df: pd.DataFrame) -> str:
    income = int(df[df["type"] == "Pemasukan"]["amount"].sum())
    expense = int(df[df["type"] == "Pengeluaran"]["amount"].sum())
    profit = income - expense
    return (
        f"Demo insight: omzet contoh ada di Rp {income:,} dengan laba bersih sekitar Rp {profit:,}. "
        "Pola terbaiknya: jaga restock produk paling cepat laku dan batasi prive agar arus kas tetap sehat."
    )


def _clear_demo_mode() -> None:
    st.session_state.pop("demo_mode", None)
    try:
        st.query_params.clear()
    except (AttributeError, TypeError, KeyError):
        pass


def render_demo_dashboard() -> None:
    _inject_demo_style()

    df = _demo_transactions()
    score = LarisCore.calculate_laris_score(df)
    approvals = _demo_approvals()
    messages = _demo_messages()
    warehouses = _demo_warehouses()
    inventory_df = _demo_inventory()

    if "show_menu" not in st.session_state:
        st.session_state.show_menu = True

    col1, col2 = st.columns([1, 19])
    with col1:
        if st.button("☰", key="demo_hamburger_button", help="Tampilkan atau sembunyikan menu"):
            st.session_state.show_menu = not st.session_state.show_menu
    with col2:
        st.markdown('<div class="demo-pill">Mode Demo Publik — data contoh, aman untuk publik</div>', unsafe_allow_html=True)

    menu_items = ["Ruang Komando", "Ringkasan", "Catat Transaksi", "Buku Kas", "Laporan KUR", "Gudang", "Pengaturan"]
    if st.session_state.show_menu:
        st.sidebar.title(APP_NAME)
        st.sidebar.markdown(f"**{DASHBOARD_TITLE}**")
        st.sidebar.caption("Demo publik untuk calon pengguna dan presentasi.")
        st.sidebar.divider()
        st.sidebar.markdown("**Pengguna Demo:** demo@laris.ai")
        if st.sidebar.button("Masuk dengan Akun Real", type="primary", use_container_width=True):
            _clear_demo_mode()
            st.session_state["show_login"] = True
            st.rerun()
        st.sidebar.markdown(
            f'<a href="{WA_BASE_URL}?text=Halo%20laris.AI%2C%20saya%20tertarik%20minta%20demo" '
            'style="display:block;text-align:center;background:#22c55e;color:#fff;padding:0.75rem 1rem;'
            'border-radius:12px;text-decoration:none;font-weight:700;margin-top:0.5rem;">Chat WhatsApp</a>',
            unsafe_allow_html=True,
        )
        if st.sidebar.button("Kembali ke Landing", use_container_width=True):
            _clear_demo_mode()
            st.rerun()
        st.sidebar.divider()
        menu = st.sidebar.radio("Menu Demo", menu_items, index=0)
    else:
        menu = st.selectbox("Menu Demo", menu_items)

    if menu == "Ruang Komando":
        st.title("🚀 Ruang Komando Demo")
        st.caption("Contoh keputusan yang biasanya disodorkan AI ke owner.")
        st.markdown(f"**{len(approvals)} keputusan contoh menunggu persetujuan:**")
        for approval in approvals:
            with st.container(border=True):
                st.markdown(f"#### 💡 {approval['agent_id'].capitalize()} AI")
                st.write(approval["summary"])
                with st.expander("Lihat detail aksi"):
                    st.json(approval["payload"])
                c1, c2, _ = st.columns([1, 1, 4])
                if c1.button("✅ Setujui", key=f"demo_approve_{approval['id']}", type="primary"):
                    st.info("Mode demo publik tidak menyimpan aksi. Login untuk mencoba workflow asli.")
                if c2.button("❌ Tolak", key=f"demo_reject_{approval['id']}"):
                    st.info("Mode demo publik tidak menyimpan aksi. Login untuk mencoba workflow asli.")

        st.markdown("---")
        st.subheader("Aktivitas WhatsApp Contoh")
        for message in messages:
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.write(message["content"])
            else:
                with st.chat_message("assistant"):
                    st.markdown(f"**{message['agent_id'].capitalize()} AI**")
                    st.write(message["content"])

    elif menu == "Ringkasan":
        st.title("Ringkasan Bisnis Demo")
        col1, col2, col3, col4 = st.columns(4)
        total_income = int(df[df["type"] == "Pemasukan"]["amount"].sum())
        total_expense = int(df[df["type"] == "Pengeluaran"]["amount"].sum())
        balance = total_income - total_expense
        col1.metric("Total Pemasukan", f"Rp {total_income:,}")
        col2.metric("Total Pengeluaran", f"Rp {total_expense:,}")
        col3.metric("Saldo Bersih", f"Rp {balance:,}")
        col4.metric("Laris Score", f"{score['score']}/100")

        st.markdown("---")
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

        st.subheader("Saran Demo")
        st.info(_demo_advisor(df))
        with st.expander("Tampilkan aktivitas terbaru", expanded=False):
            recent = df.sort_values(by="date", ascending=False).head(6).reset_index(drop=True)
            st.table(recent[["date", "type", "category", "amount", "note"]])

    elif menu == "Catat Transaksi":
        st.title("Catat Transaksi Demo")
        st.caption("Form ini dibuat untuk menunjukkan alur input. Data tidak akan disimpan.")
        with st.form("demo_transaction_form"):
            type_txn = st.radio("Jenis Transaksi", ["Pemasukan", "Pengeluaran"], horizontal=True)
            category = st.text_input("Kategori", value="Penjualan")
            amount = st.number_input("Jumlah (Rp)", min_value=0, step=1000, value=150000)
            note = st.text_input("Catatan", value="Contoh transaksi demo")
            is_prive = st.checkbox("Prive / ambil pribadi")
            submitted = st.form_submit_button("Coba Simpan")
            if submitted:
                if amount <= 0:
                    st.error("Masukkan jumlah transaksi yang valid.")
                else:
                    st.success(
                        f"Demo berhasil menampilkan alur simpan untuk {type_txn.lower()} "
                        f"Rp {int(amount):,} di kategori {category}."
                    )
                    st.info("Mode demo publik tidak menyimpan perubahan. Login untuk memakai data asli.")
        st.markdown("---")
        st.write("Contoh ini menunjukkan betapa ringan alur input transaksi untuk owner atau admin.")

    elif menu == "Buku Kas":
        st.title("Buku Kas Demo")
        st.markdown("**Ringkasan buku kas terbaru**")
        summary = df.sort_values(by="date", ascending=False).reset_index(drop=True)
        st.dataframe(summary, height=320)
        if st.checkbox("Tampilkan semua entri buku kas demo", value=False):
            st.dataframe(summary)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Unduh CSV Demo", csv, file_name="buku_kas_demo.csv", mime="text/csv")
        st.caption("Data di atas adalah contoh agar publik bisa melihat bentuk laporan tanpa membuka data pelanggan nyata.")

    elif menu == "Laporan KUR":
        st.title("Laporan KUR Demo")
        total_income = int(df[df["type"] == "Pemasukan"]["amount"].sum())
        total_expense = int(df[df["type"] == "Pengeluaran"]["amount"].sum())
        net_profit = total_income - total_expense
        c1, c2, c3 = st.columns(3)
        c1.metric("Pendapatan", f"Rp {total_income:,}")
        c2.metric("Biaya", f"Rp {total_expense:,}")
        c3.metric("Laba Bersih", f"Rp {net_profit:,}")
        st.markdown(
            f"**Insight Demo:** {score['insight']}  \n"
            f"**Kesehatan Usaha:** {score['level'].capitalize()}"
        )
        st.info(
            "Mode demo ini memperlihatkan bagaimana data transaksi bisa dibaca ulang sebagai "
            "ringkasan usaha yang lebih siap untuk evaluasi atau kebutuhan pembiayaan."
        )

    elif menu == "Gudang":
        st.title("Gudang & Inventaris Demo")
        labels = {warehouse["id"]: warehouse["name"] for warehouse in warehouses}
        selected = st.selectbox("Pilih Gudang", options=list(labels.keys()), format_func=lambda x: labels[x])
        selected_name = labels[selected]
        st.subheader(f"Ringkasan {selected_name}")
        filtered = inventory_df[inventory_df["warehouse"] == selected_name]
        if filtered.empty:
            st.info("Belum ada aktivitas inventaris pada gudang demo ini.")
        else:
            st.dataframe(filtered.reset_index(drop=True), height=280)
        with st.expander("Lihat saran restock demo", expanded=True):
            st.write(
                "- Mie Instan: stok aman 2 hari, pertimbangkan restock sebelum akhir pekan.\n"
                "- Teh Botol: perputaran cepat, cocok diprioritaskan saat belanja berikutnya.\n"
                "- Beras 5kg: margin masih sehat, bisa dipakai untuk paket bundling."
            )

    elif menu == "Pengaturan":
        st.title("⚙️ Pengaturan Demo")
        st.info("Mode demo publik tidak membuka pengaturan akun asli atau data pelanggan.")
        st.markdown(
            """
            **Yang biasanya bisa dilihat setelah login:**
            - Tambah client baru oleh admin
            - Hubungkan nomor WhatsApp ke akun
            - Kelola mapping client dan akses dashboard

            **Yang bisa dilakukan publik di demo ini:**
            - lihat contoh dashboard,
            - cek buku kas dan laporan,
            - pahami alur produk sebelum mendaftar.
            """
        )
