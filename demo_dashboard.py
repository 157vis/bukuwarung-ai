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
    from ui.dasher_assets import inject_dasher_styles
    from ui.components import (
        empty_state,
        hero_welcome,
        info_pill,
        section_card,
        sidebar_brand,
        stat_card_row,
    )

    inject_dasher_styles(login=False)
    sidebar_brand()

    st.sidebar.markdown(
        '<div class="px-3 mt-2 mb-3"><span class="laris-page-badge" '
        'style="background:var(--ds-primary-bg-subtle);color:var(--ds-primary-text-emphasis);">Demo Publik</span></div>',
        unsafe_allow_html=True,
    )
    st.sidebar.caption("Calon pengguna & presentasi")
    st.sidebar.divider()

    if st.sidebar.button("Masuk dengan Akun Real", type="primary", use_container_width=True):
        _clear_demo_mode()
        st.session_state["show_login"] = True
        st.rerun()
    st.sidebar.markdown(
        f'<a href="{WA_BASE_URL}?text=Halo%20laris.AI%2C%20saya%20tertarik%20minta%20demo" '
        'style="display:block;text-align:center;background:#22c55e;color:#fff;padding:0.65rem 1rem;'
        'border-radius:.5rem;text-decoration:none;font-weight:700;margin:0.35rem 0;">💬 Chat WhatsApp</a>',
        unsafe_allow_html=True,
    )
    if st.sidebar.button("Kembali ke Landing", use_container_width=True):
        _clear_demo_mode()
        st.rerun()
    st.sidebar.divider()
    st.sidebar.markdown(
        '<div class="px-3 mb-2"><small class="text-muted">Pengguna</small><br>'
        '<span class="fw-semibold">demo@laris.ai</span></div>',
        unsafe_allow_html=True,
    )

    df = _demo_transactions()
    score = LarisCore.calculate_laris_score(df)
    approvals = _demo_approvals()
    messages = _demo_messages()
    warehouses = _demo_warehouses()
    inventory_df = _demo_inventory()

    menu_items = ["Ruang Komando", "Ringkasan", "Catat Transaksi", "Buku Kas", "Laporan KUR", "Gudang", "Pengaturan"]
    menu = st.sidebar.radio("Menu Demo", menu_items, index=0, label_visibility="collapsed")

    # Topbar
    st.markdown(
        f"""
        <div class="laris-dasher-topbar d-flex align-items-center justify-content-between flex-wrap gap-3">
            <div class="d-flex align-items-center gap-3">
                <span class="laris-page-badge">Demo</span>
                <div>
                    <h2 class="mb-0">{APP_NAME}</h2>
                    <small class="text-muted">Dashboard contoh untuk publik</small>
                </div>
            </div>
            <div class="laris-user-chip d-none d-md-flex align-items-center gap-2">
                <i class="ti ti-user-circle fs-3 text-primary"></i>
                <div class="lh-sm">
                    <small class="d-block text-muted">Pengguna</small>
                    <strong>demo@laris.ai</strong>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if menu == "Ruang Komando":
        section_card(
            "🚀 Ruang Komando Demo",
            "Contoh keputusan yang biasanya disodorkan AI ke owner.",
            icon="ti-layout-dashboard",
        )
        st.markdown(
            f'<p class="text-muted mb-3">{len(approvals)} keputusan contoh menunggu persetujuan:</p>',
            unsafe_allow_html=True,
        )
        for approval in approvals:
            agent_name = approval["agent_id"].capitalize()
            with st.container(border=True):
                col_h, col_a = st.columns([7, 3])
                with col_h:
                    st.markdown(
                        f'<span class="laris-page-badge"><i class="ti ti-robot"></i> {agent_name} AI</span>',
                        unsafe_allow_html=True,
                    )
                    st.write(approval["summary"])
                with col_a:
                    c1, c2 = st.columns(2)
                    if c1.button(
                        "✅ Setujui",
                        key=f"demo_approve_{approval['id']}",
                        type="primary",
                        use_container_width=True,
                    ):
                        st.info("Mode demo publik tidak menyimpan aksi. Login untuk workflow asli.")
                    if c2.button(
                        "❌ Tolak",
                        key=f"demo_reject_{approval['id']}",
                        use_container_width=True,
                    ):
                        st.info("Mode demo publik tidak menyimpan aksi. Login untuk workflow asli.")
                with st.expander("Lihat detail aksi"):
                    st.json(approval["payload"])

        st.markdown("---")
        section_card(
            "Aktivitas WhatsApp Contoh",
            "Cuplikan percakapan antara pelanggan, owner, dan AI.",
            icon="ti-brand-whatsapp",
        )
        for message in messages:
            with st.chat_message(message["role"]):
                if message["role"] == "assistant":
                    st.markdown(f"**{message['agent_id'].capitalize()} AI**")
                st.write(message["content"])

    elif menu == "Ringkasan":
        hero_welcome(user_name="demo@laris.ai", subtitle="Dashboard contoh UMKM Indonesia")
        total_income = int(df[df["type"] == "Pemasukan"]["amount"].sum())
        total_expense = int(df[df["type"] == "Pengeluaran"]["amount"].sum())
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
                "5 kategori terbesar.",
                icon="ti-arrows-down",
            )
            st.bar_chart(top_costs.head(5))

        section_card(
            "Saran Demo",
            "Insight dari AI berdasarkan data contoh.",
            icon="ti-sparkles",
        )
        st.markdown(
            f'<div class="alert alert-info mb-0" role="alert">{_demo_advisor(df)}</div>',
            unsafe_allow_html=True,
        )
        with st.expander("Tampilkan aktivitas terbaru", expanded=False):
            recent = df.sort_values(by="date", ascending=False).head(6).reset_index(drop=True)
            st.table(recent[["date", "type", "category", "amount", "note"]])

    elif menu == "Catat Transaksi":
        section_card(
            "Catat Transaksi Demo",
            "Form ini dibuat untuk menunjukkan alur input. Data tidak akan disimpan.",
            icon="ti-pencil-plus",
        )
        with st.form("demo_transaction_form"):
            c1, c2 = st.columns(2)
            with c1:
                type_txn = st.radio("Jenis Transaksi", ["Pemasukan", "Pengeluaran"], horizontal=True)
                category = st.text_input("Kategori", value="Penjualan")
            with c2:
                amount = st.number_input("Jumlah (Rp)", min_value=0, step=1000, value=150000)
                is_prive = st.checkbox("Prive / ambil pribadi")
            note = st.text_input("Catatan", value="Contoh transaksi demo")
            submitted = st.form_submit_button("Coba Simpan", type="primary", use_container_width=True)
            if submitted:
                if amount <= 0:
                    st.error("Masukkan jumlah transaksi yang valid.")
                else:
                    st.success(
                        f"Demo berhasil menampilkan alur simpan untuk {type_txn.lower()} "
                        f"Rp {int(amount):,} di kategori {category}."
                    )
                    st.info("Mode demo publik tidak menyimpan perubahan. Login untuk memakai data asli.")
        info_pill(
            "💡 Atau kirim lewat WhatsApp ke nomor AI Catat — contoh: 'jual kopi 50rb'.",
            "info",
        )

    elif menu == "Buku Kas":
        section_card(
            "Buku Kas Demo",
            "Daftar transaksi contoh. Data ini publik dan tidak terkait toko nyata.",
            icon="ti-cash",
        )
        summary = df.sort_values(by="date", ascending=False).reset_index(drop=True)
        st.dataframe(summary, height=320)
        if st.checkbox("Tampilkan semua entri buku kas demo", value=False):
            st.dataframe(summary)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Unduh CSV Demo",
            csv,
            file_name="buku_kas_demo.csv",
            mime="text/csv",
            type="primary",
        )
        st.caption("Data di atas adalah contoh agar publik bisa melihat bentuk laporan tanpa membuka data pelanggan nyata.")

    elif menu == "Laporan KUR":
        section_card(
            "Laporan KUR Demo",
            "Ringkasan otomatis untuk pengajuan Kredit Usaha Rakyat.",
            icon="ti-report-analytics",
        )
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
                <h5 class="mb-1"><i class="ti ti-bulb text-warning me-2"></i>Insight Demo</h5>
                <p class="mb-1"><strong>Insight:</strong> {score['insight']}</p>
                <p class="mb-0"><strong>Kesehatan:</strong> {score['level'].capitalize()}</p>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.info(
            "Mode demo ini memperlihatkan bagaimana data transaksi bisa dibaca ulang sebagai "
            "ringkasan usaha yang lebih siap untuk evaluasi atau kebutuhan pembiayaan."
        )

    elif menu == "Gudang":
        section_card(
            "Gudang & Inventaris Demo",
            "Pantau stok per gudang dan produk terkoneksi.",
            icon="ti-building-warehouse",
        )
        labels = {warehouse["id"]: warehouse["name"] for warehouse in warehouses}
        selected = st.selectbox("Pilih Gudang", options=list(labels.keys()), format_func=lambda x: labels[x])
        selected_name = labels[selected]
        section_card(
            f"Ringkasan {selected_name}",
            "Aktivitas inventaris gudang demo.",
            icon="ti-archive",
        )
        filtered = inventory_df[inventory_df["warehouse"] == selected_name]
        if filtered.empty:
            empty_state("ti-tray", "Belum ada aktivitas inventaris", "")
        else:
            st.dataframe(filtered.reset_index(drop=True), height=280)
        with st.expander("Lihat saran restock demo", expanded=True):
            st.write(
                "- Mie Instan: stok aman 2 hari, pertimbangkan restock sebelum akhir pekan.\n"
                "- Teh Botol: perputaran cepat, cocok diprioritaskan saat belanja berikutnya.\n"
                "- Beras 5kg: margin masih sehat, bisa dipakai untuk paket bundling."
            )

    elif menu == "Pengaturan":
        section_card(
            "⚙️ Pengaturan Demo",
            "Mode demo publik tidak membuka pengaturan akun asli.",
            icon="ti-settings",
        )
        info_pill(
            "Mode demo publik tidak membuka pengaturan akun asli atau data pelanggan.",
            "info",
        )
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
