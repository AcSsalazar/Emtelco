"""Warranty and support tools.

Warranties and tickets are identified by their customer-facing codes
(``GAR-XXXXXX`` and ``TCK-XXXXXX``); orders by their guide number
(``GUI-XXXXXX``) and products by SKU.
"""

from __future__ import annotations

from typing import Any

from django.utils import timezone

from apps.orders.models import Order, Warranty
from apps.support.models import SupportTicket

from .registry import ToolContext, ToolError, register_tool


def _warranty_summary(warranty: Warranty) -> dict[str, Any]:
    today = timezone.now().date()
    is_active = (
        warranty.coverage_status == Warranty.CoverageStatus.ACTIVE
        and warranty.expiration_date >= today
    )
    return {
        "number": warranty.number,
        "order_number": warranty.order.number,
        "product": warranty.product.name,
        "product_sku": warranty.product.sku,
        "coverage_status": warranty.coverage_status,
        "coverage_label": warranty.get_coverage_status_display(),
        "is_active": is_active,
        "expiration_date": warranty.expiration_date.isoformat(),
        "conditions": warranty.conditions,
    }


CHECK_PARAMS = {
    "type": "object",
    "properties": {
        "warranty_number": {
            "type": "string",
            "description": "Código de garantía (GAR-XXXXXX), si el cliente lo tiene.",
        },
        "order_number": {
            "type": "string",
            "description": "Número de guía del pedido (GUI-XXXXXX).",
        },
        "sku": {
            "type": "string",
            "description": "SKU del producto (ej. TV-MARCA-MODELO).",
        },
    },
    "required": [],
}


@register_tool(
    name="check_warranty",
    description=(
        "Consulta el estado de la garantía de un producto o pedido del cliente "
        "autenticado: cobertura, fecha de vencimiento y condiciones. Puedes "
        "filtrar por warranty_number (GAR-XXXXXX), order_number (GUI-XXXXXX) o "
        "sku. Llama SIN parámetros cuando el cliente mencione un producto pero no "
        "te dé un código: así obtienes todas las garantías del cliente. No "
        "inventes códigos."
    ),
    parameters=CHECK_PARAMS,
)
def check_warranty(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    qs = Warranty.objects.filter(order__customer=context.customer).select_related(
        "product", "order"
    )
    filtered = bool(
        args.get("warranty_number") or args.get("order_number") or args.get("sku")
    )
    if args.get("warranty_number"):
        qs = qs.filter(number__iexact=str(args["warranty_number"]).strip())
    if args.get("order_number"):
        qs = qs.filter(order__number__iexact=str(args["order_number"]).strip())
    if args.get("sku"):
        qs = qs.filter(product__sku__iexact=str(args["sku"]).strip())

    warranties = list(qs)
    if not warranties:
        if filtered:
            available = list(
                Warranty.objects.filter(order__customer=context.customer).select_related(
                    "product", "order"
                )
            )
            if available:
                return {
                    "found": False,
                    "message": "No encontré garantía para ese criterio.",
                    "available_warranties": [
                        _warranty_summary(warranty) for warranty in available
                    ],
                }
        return {
            "found": False,
            "message": "No encontré una garantía registrada para ese producto o pedido.",
        }
    return {
        "found": True,
        "count": len(warranties),
        "warranties": [_warranty_summary(warranty) for warranty in warranties],
    }


CREATE_WARRANTY_PARAMS = {
    "type": "object",
    "properties": {
        "order_number": {
            "type": "string",
            "description": "Número de guía del pedido con garantía (GUI-XXXXXX).",
        },
        "description": {
            "type": "string",
            "description": "Descripción del problema reportado por el cliente.",
        },
    },
    "required": ["order_number", "description"],
}


@register_tool(
    name="create_warranty_request",
    description=(
        "Registra una solicitud de garantía para un pedido del cliente y crea "
        "un ticket de soporte técnico asociado."
    ),
    parameters=CREATE_WARRANTY_PARAMS,
)
def create_warranty_request(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    order = (
        Order.objects.filter(
            number__iexact=str(args["order_number"]).strip(),
            customer=context.customer,
        )
        .select_related("product")
        .first()
    )
    if order is None:
        raise ToolError("No encontré ese número de guía en tu cuenta.")

    warranty = Warranty.objects.filter(order=order).first()
    summary = _warranty_summary(warranty) if warranty is not None else None

    ticket = SupportTicket.objects.create(
        customer=context.customer,
        warranty=warranty,
        conversation=getattr(context, "conversation", None),
        subject=f"Solicitud de garantía: {order.product.name}",
        description=str(args["description"]).strip(),
        priority=SupportTicket.Priority.HIGH,
        source=SupportTicket.Source.WARRANTY,
    )

    return {
        "created": True,
        "ticket_number": ticket.number,
        "ticket_status": ticket.get_status_display(),
        "order_number": order.number,
        "warranty": summary,
    }


TICKET_PARAMS = {
    "type": "object",
    "properties": {
        "subject": {"type": "string", "description": "Asunto del ticket."},
        "description": {"type": "string", "description": "Detalle del caso."},
        "priority": {
            "type": "string",
            "enum": ["low", "medium", "high", "urgent"],
            "description": "Prioridad del ticket.",
        },
        "order_number": {
            "type": "string",
            "description": "Número de guía del pedido relacionado, si aplica.",
        },
    },
    "required": ["subject", "description"],
}


@register_tool(
    name="create_support_ticket",
    description=(
        "Crea un ticket de soporte para casos que requieren seguimiento de una "
        "persona del equipo."
    ),
    parameters=TICKET_PARAMS,
)
def create_support_ticket(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    order = None
    if args.get("order_number"):
        order = Order.objects.filter(
            number__iexact=str(args["order_number"]).strip(),
            customer=context.customer,
        ).first()
        if order is None:
            raise ToolError("No encontré ese número de guía en tu cuenta.")

    priority = args.get("priority") or SupportTicket.Priority.MEDIUM
    if priority not in SupportTicket.Priority.values:
        priority = SupportTicket.Priority.MEDIUM

    ticket = SupportTicket.objects.create(
        customer=context.customer,
        warranty=Warranty.objects.filter(order=order).first() if order else None,
        conversation=getattr(context, "conversation", None),
        subject=str(args["subject"]).strip()[:150],
        description=str(args["description"]).strip(),
        priority=priority,
        source=SupportTicket.Source.AGENT,
    )
    return {
        "created": True,
        "ticket_number": ticket.number,
        "subject": ticket.subject,
        "priority": ticket.get_priority_display(),
        "status": ticket.get_status_display(),
    }
