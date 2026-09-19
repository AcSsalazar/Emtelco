"""Persistent structured memory for a conversation.

Combined with the message history, this is what the Context Builder renders
into the system prompt. No embeddings or vector stores are used.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from apps.conversations.models import Conversation, ConversationMemory

MAX_PRODUCTS = 12
MAX_PREFERENCES = 10


def get_or_create_memory(conversation: Conversation) -> ConversationMemory:
    memory, _ = ConversationMemory.objects.get_or_create(
        conversation=conversation,
        defaults={"customer_name": conversation.customer.full_name},
    )
    return memory


def extract_budget(text: str) -> Decimal | None:
    """Best-effort extraction of a budget mentioned in COP."""
    if not text:
        return None
    lowered = text.lower().replace("$", " ").replace("cop", " ")

    millions = re.search(r"(\d+(?:[.,]\d+)?)\s*(millones|millon|millón|mm)\b", lowered)
    if millions:
        try:
            value = Decimal(millions.group(1).replace(",", "."))
        except InvalidOperation:
            return None
        return (value * Decimal(1_000_000)).quantize(Decimal("1"))

    for match in re.finditer(r"\d[\d.,]*", lowered):
        digits = re.sub(r"[.,]", "", match.group(0))
        if len(digits) >= 6:
            return Decimal(digits)
    return None


def set_customer_name(memory: ConversationMemory, name: str) -> None:
    if name and memory.customer_name != name:
        memory.customer_name = name
        memory.save(update_fields=["customer_name", "updated_at"])


def set_budget(memory: ConversationMemory, budget: Decimal | None) -> None:
    if budget is not None and memory.budget != budget:
        memory.budget = budget
        memory.save(update_fields=["budget", "updated_at"])


def set_intent(memory: ConversationMemory, intent: str) -> None:
    intent = (intent or "").strip()[:40]
    if intent and memory.last_intent != intent:
        memory.last_intent = intent
        memory.save(update_fields=["last_intent", "updated_at"])


def set_last_order_number(memory: ConversationMemory, number: str) -> None:
    number = (number or "").strip()[:16]
    if number and memory.last_order_number != number:
        memory.last_order_number = number
        memory.save(update_fields=["last_order_number", "updated_at"])


def set_last_product_sku(memory: ConversationMemory, sku: str) -> None:
    sku = (sku or "").strip()[:40]
    if sku and memory.last_product_sku != sku:
        memory.last_product_sku = sku
        memory.save(update_fields=["last_product_sku", "updated_at"])


def record_products(memory: ConversationMemory, products: list[dict[str, Any]]) -> None:
    if not products:
        return
    current = list(memory.products_consulted or [])
    seen = {item.get("id") for item in current}
    for product in products:
        if not isinstance(product, dict) or product.get("id") is None:
            continue
        if product["id"] in seen:
            continue
        current.append({"id": product["id"], "name": product.get("name", "")})
        seen.add(product["id"])
    current = current[-MAX_PRODUCTS:]
    if current != (memory.products_consulted or []):
        memory.products_consulted = current
        memory.save(update_fields=["products_consulted", "updated_at"])


def record_preferences(memory: ConversationMemory, preferences: list[str]) -> None:
    if not preferences:
        return
    current = list(memory.preferences or [])
    for preference in preferences:
        preference = preference.strip()
        if preference and preference not in current:
            current.append(preference)
    current = current[-MAX_PREFERENCES:]
    if current != (memory.preferences or []):
        memory.preferences = current
        memory.save(update_fields=["preferences", "updated_at"])


def increment_unresolved(memory: ConversationMemory) -> int:
    memory.unresolved_attempts += 1
    memory.save(update_fields=["unresolved_attempts", "updated_at"])
    return memory.unresolved_attempts


def reset_unresolved(memory: ConversationMemory) -> None:
    if memory.unresolved_attempts:
        memory.unresolved_attempts = 0
        memory.save(update_fields=["unresolved_attempts", "updated_at"])


def render_memory(memory: ConversationMemory) -> str:
    """Render memory as a compact block for the system prompt."""
    lines = []
    if memory.customer_name:
        lines.append(f"- Nombre del cliente: {memory.customer_name}")
    if memory.budget is not None:
        lines.append(f"- Presupuesto mencionado: {int(memory.budget)} COP")
    if memory.products_consulted:
        products = ", ".join(
            f"{item.get('name')} (id {item.get('id')})"
            for item in memory.products_consulted
        )
        lines.append(f"- Productos consultados: {products}")
    if memory.preferences:
        lines.append(f"- Preferencias: {', '.join(memory.preferences)}")
    if memory.last_order_number:
        lines.append(f"- Último pedido consultado: {memory.last_order_number}")
    if memory.last_product_sku:
        lines.append(f"- Último producto relevante (SKU): {memory.last_product_sku}")
    if memory.last_intent:
        lines.append(f"- Intención reciente: {memory.last_intent}")
    return "\n".join(lines) if lines else "- Sin datos previos relevantes."
