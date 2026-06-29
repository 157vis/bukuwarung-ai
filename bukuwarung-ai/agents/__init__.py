"""Registry 6 agent spesialis."""

from __future__ import annotations

from typing import TYPE_CHECKING

from agents.admin_agent import AdminAgent
from agents.base_agent import BaseAgent
from agents.cs_agent import CSAgent
from agents.data_access import OrderStore
from agents.order_agent import OrderAgent
from agents.payment_agent import PaymentAgent
from agents.sales_agent import SalesAgent
from agents.support_agent import SupportAgent

if TYPE_CHECKING:
    from core.otak_ai import OtakAI
    from core.personality import PersonalityEngine
    from utils.openrouter import OpenRouterClient

AGENT_CLASSES: dict[str, type[BaseAgent]] = {
    "cs": CSAgent,
    "sales": SalesAgent,
    "order": OrderAgent,
    "payment": PaymentAgent,
    "support": SupportAgent,
    "admin": AdminAgent,
}


def build_agents(
    otak: OtakAI,
    personality: PersonalityEngine,
    llm: OpenRouterClient,
) -> dict[str, BaseAgent]:
    """Instansiasi semua agent dengan DI + OrderStore bersama."""
    store = OrderStore()
    agents: dict[str, BaseAgent] = {
        "cs": CSAgent(otak, personality, llm),
        "sales": SalesAgent(otak, personality, llm),
        "order": OrderAgent(otak, personality, llm, store),
        "payment": PaymentAgent(otak, personality, llm, store),
        "support": SupportAgent(otak, personality, llm),
        "admin": AdminAgent(otak, personality, llm, store),
    }
    agents["greeting"] = agents["cs"]
    return agents


__all__ = [
    "BaseAgent",
    "CSAgent",
    "SalesAgent",
    "OrderAgent",
    "PaymentAgent",
    "SupportAgent",
    "AdminAgent",
    "build_agents",
    "AGENT_CLASSES",
]
