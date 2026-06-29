"""Utilities — embeddings, database, WhatsApp."""

from utils.embeddings import GroqEmbeddingClient, cosine_similarity

__all__ = ["GroqEmbeddingClient", "cosine_similarity", "get_supabase_client"]


def __getattr__(name: str):
    if name == "get_supabase_client":
        from utils.supabase import get_supabase_client
        return get_supabase_client
    if name == "OpenRouterClient":
        from utils.openrouter import OpenRouterClient
        return OpenRouterClient
    if name == "send_whatsapp_message":
        from utils.whatsapp import send_whatsapp_message
        return send_whatsapp_message
    raise AttributeError(name)
