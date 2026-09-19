"""Agent orchestrator: guard -> context -> LLM <-> tools -> response.

Keeps the conversation loop, tool execution, memory updates and escalation
decisions in one place.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.utils import timezone

from apps.conversations.models import Message
from apps.support.models import SupportTicket

from . import memory as memory_service
from . import profile as profile_service
from .context_builder import build_messages
from .guard import Guard, parse_json
from .llm.base import LLMProvider, LLMProviderError
from .llm.factory import get_llm_provider
from .outcomes import TurnOutcome, normalize
from .output_guard import sanitize_reply
from .tools import registry as tool_registry
from .tools.registry import ToolContext, execute_tool, get_tool_schemas

logger = logging.getLogger(__name__)

_PROVIDER_ERROR_REPLY = (
    "En este momento no puedo consultar la información del sistema. "
    "Intenta nuevamente en unos minutos, por favor."
)
_ESCALATION_NOTE = (
    " Creo que este caso necesita la revisión de una persona del equipo para darte "
    "una respuesta correcta. Voy a dejar registrada la solicitud para que puedan "
    "continuar desde aquí."
)

_OUTCOME_PROMPT = """\
Clasifica el resultado de este turno de atención entre estas opciones:
- "resolved": el cliente obtuvo una respuesta o acción útil.
- "needs_clarification": el agente pidió al cliente un dato que falta (no es un fallo).
- "out_of_scope": el tema está fuera del dominio de la tienda.
- "escalate": el agente no pudo resolver el caso y necesita apoyo humano.

Responde ÚNICAMENTE con JSON: {"outcome": "..."}.
"""


@dataclass
class AgentResult:
    reply: str
    outcome: str
    guard_action: str = "allow"
    escalated: bool = False


def run_agent(
    conversation,
    user_message: str,
    persist_user_message: bool = True,
) -> AgentResult:
    tool_registry._load_tools()
    provider = get_llm_provider()
    memory = memory_service.get_or_create_memory(conversation)
    profile = profile_service.get_or_create_profile(conversation.customer)

    memory_service.set_customer_name(memory, conversation.customer.full_name)
    budget = memory_service.extract_budget(user_message)
    memory_service.set_budget(memory, budget)
    if budget is not None:
        profile_service.merge_profile(conversation.customer, {"budget_max": budget})

    if persist_user_message:
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content=user_message,
        )

    # --- Guard ----------------------------------------------------------
    guard_result = Guard(provider).evaluate(
        conversation.customer, user_message, conversation=conversation
    )
    if not guard_result.allowed:
        _persist_assistant(conversation, guard_result.reply)
        if guard_result.intent:
            memory_service.set_intent(memory, guard_result.intent)
        return AgentResult(
            reply=guard_result.reply,
            outcome=TurnOutcome.ESCALATE,
            guard_action=guard_result.action,
        )

    if guard_result.intent:
        memory_service.set_intent(memory, guard_result.intent)
    memory_service.record_preferences(memory, guard_result.preferences)
    profile_service.merge_profile(conversation.customer, guard_result.profile_updates)

    # Scope and prompt-injection are signals for the agent, never blocks: the
    # agent resolves them with the full conversation context.
    hints: dict[str, Any] = {}
    if guard_result.scope == "out_of_scope":
        hints["scope"] = "out_of_scope"
    if guard_result.category == "prompt_injection":
        hints["category"] = "prompt_injection"

    # --- Agent loop -----------------------------------------------------
    messages = build_messages(conversation, memory, profile, hints)
    tool_context = ToolContext(customer=conversation.customer, conversation=conversation)
    tools = get_tool_schemas()

    used_tools = False
    tool_failed = False
    state: dict[str, Any] = {"products": [], "order_number": "", "product_sku": ""}
    final_reply = ""

    for _ in range(settings.AGENT_MAX_TOOL_ITERATIONS):
        try:
            response = provider.chat(messages, tools)
        except LLMProviderError:
            logger.error("LLM provider error during agent loop", exc_info=True)
            _persist_assistant(conversation, _PROVIDER_ERROR_REPLY)
            return AgentResult(
                reply=_PROVIDER_ERROR_REPLY,
                outcome=TurnOutcome.ESCALATE,
                guard_action=guard_result.action,
            )

        if response.tool_calls:
            used_tools = True
            messages.append(
                {
                    "role": "assistant",
                    "content": response.content or "",
                    "tool_calls": response.tool_calls,
                }
            )
            for call in response.tool_calls:
                result = execute_tool(call.name, call.arguments, tool_context)
                payload = json.dumps(result, ensure_ascii=False, default=str)
                Message.objects.create(
                    conversation=conversation,
                    role=Message.Role.TOOL,
                    content=payload,
                    tool_name=call.name,
                )
                if result.get("error") or result.get("found") is False:
                    tool_failed = True
                _harvest(result, state)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "name": call.name,
                        "content": payload,
                    }
                )
            continue

        final_reply = (response.content or "").strip()
        if final_reply:
            break

    if not final_reply:
        final_reply = _force_final_answer(provider, messages) or _PROVIDER_ERROR_REPLY

    # --- Memory updates -------------------------------------------------
    memory_service.record_products(memory, state["products"])
    memory_service.set_last_order_number(memory, state["order_number"])
    memory_service.set_last_product_sku(memory, state["product_sku"])

    product_cards = _product_cards(state["products"])

    # --- Outcome, unresolved attempts and escalation --------------------
    outcome = _classify_outcome(provider, user_message, final_reply, used_tools, tool_failed)
    escalated = False

    if outcome == TurnOutcome.RESOLVED:
        memory_service.reset_unresolved(memory)
    elif outcome in {TurnOutcome.NEEDS_CLARIFICATION, TurnOutcome.OUT_OF_SCOPE}:
        pass
    else:  # escalate
        attempts = memory_service.increment_unresolved(memory)
        if attempts >= settings.AGENT_UNRESOLVED_ATTEMPTS_THRESHOLD:
            escalated = _escalate(conversation)
            if _ESCALATION_NOTE.strip() not in final_reply:
                final_reply = final_reply.rstrip() + _ESCALATION_NOTE

    metadata = {"products": product_cards} if product_cards else {}
    final_reply = sanitize_reply(final_reply)
    _persist_assistant(conversation, final_reply, metadata=metadata)
    return AgentResult(
        reply=final_reply,
        outcome=outcome,
        guard_action=guard_result.action,
        escalated=escalated,
    )


def _force_final_answer(provider: LLMProvider, messages: list[dict]) -> str:
    try:
        response = provider.chat(
            messages
            + [
                {
                    "role": "system",
                    "content": "Resume ahora una respuesta final para el cliente, sin usar herramientas.",
                }
            ],
            tools=None,
        )
        return (response.content or "").strip()
    except LLMProviderError:
        logger.error("Could not force a final answer", exc_info=True)
        return ""


def _classify_outcome(
    provider: LLMProvider,
    user_message: str,
    assistant_reply: str,
    used_tools: bool,
    tool_failed: bool,
) -> str:
    try:
        response = provider.chat(
            [
                {"role": "system", "content": _OUTCOME_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Mensaje del cliente: {user_message}\n"
                        f"Respuesta del agente: {assistant_reply}\n"
                        f"¿Usó herramientas?: {used_tools}\n"
                        f"¿Alguna herramienta falló o no encontró datos?: {tool_failed}"
                    ),
                },
            ]
        )
    except LLMProviderError:
        logger.warning("Outcome classification failed", exc_info=True)
        return TurnOutcome.RESOLVED

    parsed = parse_json(response.content)
    if not isinstance(parsed, dict):
        return TurnOutcome.RESOLVED
    return normalize(parsed.get("outcome"))


def _escalate(conversation) -> bool:
    if not conversation.escalated:
        conversation.escalated = True
        conversation.save(update_fields=["escalated", "updated_at"])
    SupportTicket.objects.create(
        customer=conversation.customer,
        conversation=conversation,
        subject="Escalamiento a atención humana",
        description="El agente no logró resolver el caso tras varios intentos.",
        priority=SupportTicket.Priority.HIGH,
        source=SupportTicket.Source.ESCALATION,
    )
    return True


def _persist_assistant(conversation, content: str, metadata: dict | None = None) -> None:
    Message.objects.create(
        conversation=conversation,
        role=Message.Role.ASSISTANT,
        content=content,
        metadata=metadata or {},
    )
    conversation.save(update_fields=["updated_at"])


def _product_cards(products: list[dict]) -> list[dict]:
    """Build deduplicated product cards for the frontend, capped at six."""
    cards: list[dict] = []
    seen: set = set()
    for product in products:
        product_id = product.get("id")
        if product_id is None or product_id in seen:
            continue
        seen.add(product_id)
        cards.append(
            {
                "id": product_id,
                "sku": product.get("sku", ""),
                "name": product.get("name", ""),
                "brand": product.get("brand", ""),
                "category": product.get("category", ""),
                "price": product.get("price"),
                "image_url": product.get("image_url"),
                "in_stock": product.get("in_stock"),
            }
        )
    return cards[:6]


def _harvest(result: dict, state: dict) -> None:
    """Collect products, order numbers and SKUs from tool results for memory."""
    for key in ("products", "recommendations", "candidates", "warranties"):
        for item in result.get(key) or []:
            if isinstance(item, dict) and item.get("id") is not None and "name" in item:
                state["products"].append(item)

    product = result.get("product")
    if isinstance(product, dict) and product.get("id") is not None:
        state["products"].append(product)
        if product.get("sku"):
            state["product_sku"] = product["sku"]

    if result.get("sku"):
        state["product_sku"] = result["sku"]

    order = result.get("order")
    if isinstance(order, dict) and order.get("number"):
        state["order_number"] = order["number"]

    if result.get("order_number"):
        state["order_number"] = result["order_number"]


def touch_conversation(conversation) -> None:
    conversation.save(update_fields=["updated_at"])


__all__ = ["AgentResult", "run_agent", "touch_conversation"]
