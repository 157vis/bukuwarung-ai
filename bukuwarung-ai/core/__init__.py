"""Core system — Otak AI, Personality, Router."""
from core.otak_ai import OtakAI, MemoryRecord
from core.personality import PERSONALITY_PROFILES, PersonalityEngine
from core.semantic_router import RouteResult, SemanticRouter
from core.client_registry import ClientConfig, get_client_registry
from core.tenant_bridge import get_tenant_core
from core.tenant_data import TenantContext, build_tenant_context, fetch_client_settings, fetch_products

__all__ = [
    "OtakAI",
    "MemoryRecord",
    "PersonalityEngine",
    "PERSONALITY_PROFILES",
    "SemanticRouter",
    "RouteResult",
    "ClientConfig",
    "get_client_registry",
    "get_tenant_core",
    "TenantContext",
    "build_tenant_context",
    "fetch_client_settings",
    "fetch_products",
]