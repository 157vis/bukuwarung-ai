import streamlit as st
import pandas as pd
from datetime import datetime
import re
import json
import base64
import io
import streamlit as st # Pastikan import st ada di atas
from supabase import create_client, Client
from groq import Groq

# ==========================================
# 1. KONFIGURASI KUNCI RAHASIA
# ==========================================
# Mengambil kunci rahasia dari Brankas Streamlit Cloud

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]


@st.cache_resource
def init_clients():
    supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    groq_client = Groq(api_key=GROQ_API_KEY)
    return supabase_client, groq_client

supabase, groq_client = init_clients()

# ==========================================
# 2. DATABASE AGENT (SUPABASE)
# ==========================================
def db_insert_transaction(type_txn, category, amount, note):
    data = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "type": type_txn,
        "category": category,
        "amount": amount,
        "note": note
    }
    supabase.table("transactions").insert(data).execute()

def get_dashboard_data():
    response = supabase.table("transactions").select("*").order("id", desc=True).execute()
    return pd.DataFrame(response.data)

# ==========================================
# 3. TEXT EXTRACTOR AGENT (NLP)
# ==========================================
def clean_json_response(response_text):
    match = re.search(r'```(?:json)?\n(.*?)\n```', response_text, re.DOTALL)
    if match: return match.group(1)
    if not response_text.strip().startswith('['): return f"[{response_text}]"
    return response_text

def ai_extractor_agent(text):
    prompt = f"""
    Anda adalah AI Akuntan ahli untuk UMKM di Indonesia. 
    Analisis teks berikut dan ekstrak menjadi array JSON. Pahami bahasa gaul, singkatan, dan konteks utang/piutang.
    Teks User: "{text}"
    Aturan: 'type' (Pemasukan/Pengeluaran), 'amount' (angka saja), 'category', 'note'.
    HANYA kembalikan format JSON array yang valid.
    """
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="openai/gpt-oss-120b",
            temperature=0.1, response_format={"type": "json_object"}
        )
        return json.loads(clean_json_response(chat_completion.choices[0].message.content))
    except Exception as e:
        st.error(f"Text AI Error: {e}")
        return []

# ==========================================
# 4. VISION EXTRACTOR AGENT (SCAN STRUK) 📸
# ==========================================
def encode_image_to_base64(uploaded_file):
    return base64.b64encode(uploaded_file.getvalue()).decode('utf-8')

def vision_extractor_agent(uploaded_file):
    base64_image = encode_image_to_base64(uploaded_file)
    
    prompt = """
    Anda adalah AI Akuntan yang ahli membaca struk belanja UMKM.
    Analisis gambar struk ini. Cari GRAND TOTAL (Total Keseluruhan) yang harus dibayar.
    Aturan Output JSON: 'type': Selalu "Pengeluaran", 'amount': Angka Grand Total saja, 'category': Tebak dari isi struk, 'note': Ringkasan singkat.
    HANYA kembalikan format JSON array.
    """
    
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            model="openai/gpt-oss-120b",
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        return json.loads(clean_json_response(chat_completion.choices[0].message.content))
    except Exception as e:
        st.error(f"Vision AI Error: {e}")
        return []

# ==========================================
# 5. VOICE EXTRACTOR AGENT (WHISPER) 🎙️
# ==========================================
def voice_extractor_agent(audio_file):
    """
    Agent 1: Whisper AI - Mengubah suara menjadi teks
    Agent 2: GPT-OSS - Memahami teks dan mengekstrak transaksi
    """
    # Langkah 1: Speech-to-Text menggunakan Whisper
    try:
        transcription = groq_client.audio.transcriptions.create(
            file=(audio_file.name, audio_file.read()),
            model="whisper-large-v3-turbo",  # Model Whisper tercepat & akurat
            language="id",  # Optimalkan untuk Bahasa Indonesia
            response_format="text"
        )
        st.info(f"🗣️ *Hasil Transkripsi: \"{transcription}\"*")
        
        # Langkah 2: Proses teks hasil transkripsi dengan AI Extractor
        return ai_extractor_agent(transcription)
        
    except Exception as e:
        st.error(f"Voice AI Error: {e}")
        return []

# ==========================================
# 6. CFO ANALYST AGENT
# ==========================================
def cfo_analyst_agent(df):
    if df.empty: return "Selamat datang! Silakan catat transaksi pertama Anda."
    income = df[df['type'] == 'Pemasukan']['amount'].sum()
    expense = df[df['type'] == 'Pengeluaran']['amount'].sum()
    profit = income - expense
    insight = f"📊 **Analisis CFO:** Total Laba Bersih Anda saat ini adalah **Rp {profit:,.0f}**. "
    if expense > income * 0.7: insight += "⚠️ *Peringatan:* Pengeluaran Anda sudah lebih dari 70% pemasukan."
    else: insight += "✅ *Kesehatan arus kas sangat baik.*"
    return insight

# ==========================================
# 7. DASHBOARD STREAMLIT (UI)
# ==========================================
st.set_page_config(page_title="BukuWarung AI (Full Multimodal)", layout="wide")
st.title("🎙️👁️ BukuWarung AI (Full Multimodal)")
st.caption("Ketik, Foto, atau Ngomong - AI yang kerjakan semuanya!")

tab1, tab2, tab3 = st.tabs(["💬 Chat / Ketik Manual", "📸 Scan Foto Struk", "🎙️ Voice Note (Rekam Suara)"])

# --- TAB 1: TEXT INPUT ---
with tab1:
    with st.form(key="chat_form", clear_on_submit=True):
        user_input = st.text_input("Ceritakan transaksi Anda...", placeholder="Contoh: Jual nasi 50rb, beli gas 20rb")
        submit_text = st.form_submit_button("Proses Teks")
        
    if submit_text and user_input:
        with st.spinner("🤖 AI sedang membedah teks..."):
            parsed_data = ai_extractor_agent(user_input)
            if parsed_data:
                for data in parsed_data:
                    db_insert_transaction(data.get('type'), data.get('category'), data.get('amount'), data.get('note'))
                st.success(f"✅ {len(parsed_data)} Transaksi dari teks berhasil disimpan!")

# --- TAB 2: VISION INPUT ---
with tab2:
    uploaded_file = st.file_uploader("Upload foto struk belanja di sini...", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        st.image(uploaded_file, caption="Struk yang akan dipindai", width=300)
        if st.button("🔍 Proses Struk dengan Vision AI"):
            with st.spinner("👁️ Vision AI sedang membaca struk..."):
                parsed_data = vision_extractor_agent(uploaded_file)
                if parsed_data:
                    for data in parsed_data:
                        db_insert_transaction(data.get('type'), data.get('category'), data.get('amount'), data.get('note'))
                    st.success(f"✅ Struk berhasil dibaca! Total pengeluaran tercatat otomatis.")
                else:
                    st.warning("AI tidak dapat membaca struk. Pastikan foto jelas dan terang.")

# --- TAB 3: VOICE INPUT 🎙️ ---
with tab3:
    st.info("💡 Tips: Tekan tombol rekam, ucapkan transaksi dengan jelas dalam Bahasa Indonesia.")
    
    # Streamlit audio_input (fitur native untuk rekam suara)
    audio_value = st.audio_input("Rekam suara Anda di sini...")
    
    if audio_value is not None:
        st.audio(audio_value, format="audio/wav")
        if st.button("🎧 Proses Voice Note dengan Whisper AI"):
            with st.spinner("🎙️ Whisper AI sedang transkripsi suara Anda..."):
                # Buat objek file-like dari audio_value untuk Groq
                audio_file = io.BytesIO(audio_value.getvalue())
                audio_file.name = "recording.wav"
                
                parsed_data = voice_extractor_agent(audio_file)
                if parsed_data:
                    for data in parsed_data:
                        db_insert_transaction(data.get('type'), data.get('category'), data.get('amount'), data.get('note'))
                    st.success(f"✅ Suara berhasil diubah menjadi {len(parsed_data)} transaksi!")
                else:
                    st.warning("AI tidak dapat memproses suara. Pastikan audio jelas dan tidak terlalu berisik.")

# ==========================================
# 8. VISUALISASI DASHBOARD
# ==========================================
st.divider()
df = get_dashboard_data()

if not df.empty:
    col1, col2, col3 = st.columns(3)
    income = df[df['type'] == 'Pemasukan']['amount'].sum()
    expense = df[df['type'] == 'Pengeluaran']['amount'].sum()
    
    col1.metric("Total Pemasukan", f"Rp {income:,.0f}")
    col2.metric("Total Pengeluaran", f"Rp {expense:,.0f}")
    col3.metric("Laba Bersih", f"Rp {income - expense:,.0f}")

    st.subheader("📈 Arus Kas Harian")
    df['date'] = pd.to_datetime(df['date'])
    chart_data = df.groupby([df['date'].dt.date, 'type'])['amount'].sum().unstack(fill_value=0)
    st.bar_chart(chart_data)
    
    st.info(cfo_analyst_agent(df))
    
    with st.expander("📋 Lihat Buku Kas"):
        st.dataframe(df)
else:
    st.warning("Database masih kosong. Mulai dengan Ketik, Foto, atau Rekam Suara!")