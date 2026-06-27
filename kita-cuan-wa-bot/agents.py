# agents.py — bridge ke laris_core (satu sumber logika bisnis)
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from laris_core import LarisCore

core = LarisCore(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_KEY"],
    os.environ["GROQ_API_KEY"],
)

supabase = core.supabase


def resolve_user_id(phone: str) -> str:
    return core.resolve_user_id_by_phone(phone)


def get_dashboard_data(user_id: str):
    return core.get_dashboard_data(user_id)


def db_insert_transaction(type_txn, category, amount, note, is_prive=False, user_id=None):
    if not user_id:
        raise ValueError("user_id wajib untuk bot WhatsApp")
    core.db_insert_transaction(user_id, type_txn, category, amount, note, is_prive=is_prive)


def db_delete_transaction(txn_id, user_id=None):
    if not user_id:
        raise ValueError("user_id wajib untuk bot WhatsApp")
    core.db_delete_transaction(user_id, txn_id)


def ai_extractor_agent(text):
    return core.ai_extractor_agent(text)


def vision_extractor_agent(b64: str):
    return core.vision_extractor_agent_from_b64(b64)


def voice_extractor_agent(audio_bytes: bytes):
    return core.voice_extractor_agent_from_bytes(audio_bytes)


def calculate_cuan_score(df):
    return LarisCore.calculate_laris_score(df)


def get_ai_advisor_insights(df):
    return core.get_ai_advisor_insights(df)
