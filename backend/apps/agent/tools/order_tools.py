"""Order tools: status, delivery estimate and address updates.

Orders are identified by their customer-facing guide number (``GUI-XXXXXX``),
never by an internal database id.
"""

from __future__ import annotations

import re
from typing import Any

from apps.orders.models import Order

from .registry import ToolContext, ToolError, register_tool

MAX_ORDERS = 20


def _order_summary(order: Order) -> dict[str, Any]:
    return {
        "number": order.number,
        "product": order.product.name,
        "product_sku": order.product.sku,
        "brand": order.product.brand,
        "quantity": order.quantity,
        "total": float(order.total),
        "status": order.status,
        "status_label": order.get_status_display(),
        "tracking_number": order.tracking_number or None,
        "shipping_address": order.shipping_address,
        "estimated_delivery": (
            order.estimated_delivery.isoformat() if order.estimated_delivery else None
        ),
    }


def _order_brief(order: Order) -> dict[str, Any]:
    """Compact order reference: no address, tracking or dates."""
    return {
        "number": order.number,
        "product": order.product.name,
        "status_label": order.get_status_display(),
    }


def _order_blob(order: Order) -> str:
    product = order.product
    specs = " ".join(str(value) for value in (product.specifications or {}).values())
    return " ".join(
        [
            product.name,
            product.brand,
            product.description,
            product.get_category_display(),
            product.category,
            specs,
        ]
    ).lower()


def _terms(text: str) -> list[str]:
    words = re.findall(r"[a-záéíóúüñ0-9]+", (text or "").lower())
    return [word for word in words if len(word) >= 3]


def _customer_orders(
    context: ToolContext,
    order_number: str = "",
    product_query: str = "",
) -> list[Order]:
    qs = (
        Order.objects.filter(customer=context.customer)
        .select_related("product")
        .order_by("-created_at")
    )
    if order_number:
        return list(qs.filter(number__iexact=order_number.strip()))

    orders = list(qs)
    terms = _terms(product_query)
    if not terms:
        return orders

    # Prefer orders that match every term; fall back to any term.
    full = [order for order in orders if all(term in _order_blob(order) for term in terms)]
    if full:
        return full
    return [order for order in orders if any(term in _order_blob(order) for term in terms)]


def _single_order(
    context: ToolContext,
    order_number: str = "",
    product_query: str = "",
) -> Order:
    orders = _customer_orders(context, order_number, product_query)
    if not orders:
        if product_query:
            raise ToolError("No encontré un pedido tuyo con ese producto.")
        raise ToolError("No encontré ese número de guía en tu cuenta.")
    return orders[0]


def _not_found_with_available(context: ToolContext, message: str) -> dict[str, Any]:
    """Help the agent recover from a wrong code with a compact list of orders."""
    available = _customer_orders(context)[:MAX_ORDERS]
    result: dict[str, Any] = {"found": False, "message": message}
    if available:
        result["available_orders"] = [_order_brief(order) for order in available]
    return result


STATUS_PARAMS = {
    "type": "object",
    "properties": {
        "order_number": {
            "type": "string",
            "description": (
                "Número de guía del pedido (formato GUI-XXXXXX). Úsalo cuando el "
                "cliente te lo dé. Nunca lo inventes."
            ),
        },
        "product_query": {
            "type": "string",
            "description": (
                "Texto para localizar el pedido por el producto (ej. 'televisor', "
                "'la marca') cuando el cliente no tiene el número de guía."
            ),
        },
    },
    "required": [],
}


@register_tool(
    name="get_order_status",
    description=(
        "Consulta el estado de un pedido del cliente autenticado. Localízalo por "
        "order_number (GUI-XXXXXX) o por product_query. Si no indicas nada, "
        "devuelve TODOS los pedidos del cliente para que identifiques cuál quiere. "
        "No inventes un número de guía. Solo pedidos propios."
    ),
    parameters=STATUS_PARAMS,
)
def get_order_status(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    order_number = str(args.get("order_number") or "").strip()
    product_query = str(args.get("product_query") or "").strip()

    if order_number:
        orders = _customer_orders(context, order_number=order_number)
        if not orders:
            return _not_found_with_available(
                context, "No encontré ese número de guía en tu cuenta."
            )
        return {"found": True, "order": _order_summary(orders[0])}

    orders = _customer_orders(context, product_query=product_query)[:MAX_ORDERS]
    if not orders:
        if product_query:
            return {
                "found": False,
                "message": "No encontré un pedido tuyo con ese producto.",
            }
        return {"found": False, "message": "No encontré pedidos asociados a tu cuenta."}
    if len(orders) == 1:
        return {"found": True, "order": _order_summary(orders[0])}
    return {
        "found": True,
        "multiple": True,
        "orders": [_order_brief(order) for order in orders],
        "message": "El cliente tiene varios pedidos; pídele que indique el número de guía.",
    }


DELIVERY_PARAMS = {
    "type": "object",
    "properties": {
        "order_number": {
            "type": "string",
            "description": "Número de guía del pedido (GUI-XXXXXX).",
        },
        "product_query": {
            "type": "string",
            "description": "Producto, marca o categoría para localizar el pedido.",
        },
    },
    "required": [],
}


@register_tool(
    name="get_delivery_estimate",
    description=(
        "Devuelve la fecha estimada de entrega de un pedido del cliente "
        "autenticado."
    ),
    parameters=DELIVERY_PARAMS,
)
def get_delivery_estimate(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    order_number = str(args.get("order_number") or "").strip()
    product_query = str(args.get("product_query") or "").strip()
    orders = _customer_orders(context, order_number, product_query)
    if not orders:
        if order_number or product_query:
            return _not_found_with_available(
                context, "No encontré ese pedido en tu cuenta."
            )
        raise ToolError("No encontré pedidos asociados a tu cuenta.")

    order = orders[0]
    return {
        "found": True,
        "order_number": order.number,
        "status": order.status,
        "status_label": order.get_status_display(),
        "estimated_delivery": (
            order.estimated_delivery.isoformat() if order.estimated_delivery else None
        ),
        "product_shipping_days": order.product.shipping_days,
    }


UPDATE_ADDRESS_PARAMS = {
    "type": "object",
    "properties": {
        "order_number": {
            "type": "string",
            "description": "Número de guía del pedido a actualizar (GUI-XXXXXX).",
        },
        "new_address": {
            "type": "string",
            "description": "Nueva dirección de entrega completa.",
        },
    },
    "required": ["order_number", "new_address"],
}


@register_tool(
    name="update_delivery_address",
    description=(
        "Actualiza la dirección de entrega de un pedido propio que aún no ha "
        "sido entregado ni cancelado. Requiere el número de guía."
    ),
    parameters=UPDATE_ADDRESS_PARAMS,
)
def update_delivery_address(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    order = _single_order(context, str(args["order_number"]).strip())
    new_address = str(args["new_address"]).strip()
    if len(new_address) < 5:
        raise ToolError("La nueva dirección no parece válida. ¿Puedes darme la dirección completa?")

    if order.status in {Order.Status.DELIVERED, Order.Status.CANCELLED}:
        raise ToolError(
            "Ese pedido ya fue entregado o cancelado, así que no puedo cambiar la dirección."
        )

    previous = order.shipping_address
    order.shipping_address = new_address
    order.save(update_fields=["shipping_address", "updated_at"])

    return {
        "updated": True,
        "order_number": order.number,
        "previous_address": previous,
        "shipping_address": order.shipping_address,
        "status_label": order.get_status_display(),
    }
