from datetime import timedelta

import pytest
from django.utils import timezone

from apps.agent.tools.registry import ToolContext, execute_tool
from apps.orders.models import Warranty
from apps.support.models import SupportTicket

pytestmark = pytest.mark.django_db


def ctx(customer):
    return ToolContext(customer=customer, conversation=None)


def make_warranty(order, coverage_status, days_from_now):
    return Warranty.objects.create(
        order=order,
        product=order.product,
        coverage_status=coverage_status,
        expiration_date=timezone.now().date() + timedelta(days=days_from_now),
        conditions="Cubre defectos de fábrica.",
    )


def test_warranty_and_ticket_get_codes(customer_a, products, order_factory):
    order = order_factory(customer_a, products["tv"], status="delivered")
    warranty = make_warranty(order, Warranty.CoverageStatus.ACTIVE, 100)
    assert warranty.number.startswith("GAR-")

    ticket = SupportTicket.objects.create(customer=customer_a, subject="Prueba")
    assert ticket.number.startswith("TCK-")


def test_check_warranty_active(customer_a, products, order_factory):
    order = order_factory(customer_a, products["tv"], status="delivered")
    make_warranty(order, Warranty.CoverageStatus.ACTIVE, 100)
    result = execute_tool(
        "check_warranty", {"order_number": order.number}, ctx(customer_a)
    )
    assert result["found"] is True
    assert result["warranties"][0]["is_active"] is True
    assert result["warranties"][0]["number"].startswith("GAR-")


def test_check_warranty_by_warranty_number(customer_a, products, order_factory):
    order = order_factory(customer_a, products["tv"], status="delivered")
    warranty = make_warranty(order, Warranty.CoverageStatus.ACTIVE, 100)
    result = execute_tool(
        "check_warranty", {"warranty_number": warranty.number}, ctx(customer_a)
    )
    assert result["found"] is True
    assert result["warranties"][0]["number"] == warranty.number


def test_check_warranty_expired(customer_a, products, order_factory):
    order = order_factory(customer_a, products["tv"], status="delivered")
    make_warranty(order, Warranty.CoverageStatus.EXPIRED, -30)
    result = execute_tool(
        "check_warranty", {"order_number": order.number}, ctx(customer_a)
    )
    assert result["found"] is True
    assert result["warranties"][0]["is_active"] is False


def test_check_warranty_not_found(customer_a, products, order_factory):
    order = order_factory(customer_a, products["phone"], status="delivered")
    result = execute_tool(
        "check_warranty", {"order_number": order.number}, ctx(customer_a)
    )
    assert result["found"] is False


def test_check_warranty_rejects_foreign_order(customer_a, customer_b, products, order_factory):
    order = order_factory(customer_b, products["tv"], status="delivered")
    make_warranty(order, Warranty.CoverageStatus.ACTIVE, 100)
    result = execute_tool(
        "check_warranty", {"order_number": order.number}, ctx(customer_a)
    )
    assert result["found"] is False


def test_create_warranty_request_creates_ticket(customer_a, products, order_factory):
    order = order_factory(customer_a, products["tv"], status="delivered")
    make_warranty(order, Warranty.CoverageStatus.ACTIVE, 100)
    result = execute_tool(
        "create_warranty_request",
        {"order_number": order.number, "description": "El televisor no enciende"},
        ctx(customer_a),
    )
    assert result["created"] is True
    assert result["ticket_number"].startswith("TCK-")
    ticket = SupportTicket.objects.get(number=result["ticket_number"])
    assert ticket.source == SupportTicket.Source.WARRANTY
    assert ticket.warranty_id is not None


def test_create_warranty_request_rejects_foreign_order(customer_a, customer_b, products, order_factory):
    order = order_factory(customer_b, products["tv"], status="delivered")
    result = execute_tool(
        "create_warranty_request",
        {"order_number": order.number, "description": "El televisor no enciende"},
        ctx(customer_a),
    )
    assert "error" in result
    assert SupportTicket.objects.count() == 0


def test_create_support_ticket(customer_a):
    result = execute_tool(
        "create_support_ticket",
        {"subject": "Consulta de facturación", "description": "Necesito revisar un cobro"},
        ctx(customer_a),
    )
    assert result["created"] is True
    assert SupportTicket.objects.filter(number=result["ticket_number"]).exists()


def test_check_warranty_without_args_lists_all(customer_a, products, order_factory):
    tv_order = order_factory(customer_a, products["tv"], status="delivered")
    laptop_order = order_factory(customer_a, products["laptop_gpu"], status="delivered")
    make_warranty(tv_order, Warranty.CoverageStatus.ACTIVE, 100)
    make_warranty(laptop_order, Warranty.CoverageStatus.ACTIVE, 200)

    result = execute_tool("check_warranty", {}, ctx(customer_a))
    assert result["found"] is True
    assert result["count"] == 2


def test_check_warranty_bad_filter_returns_available(customer_a, products, order_factory):
    order = order_factory(customer_a, products["tv"], status="delivered")
    make_warranty(order, Warranty.CoverageStatus.ACTIVE, 100)

    result = execute_tool(
        "check_warranty", {"order_number": "GUI-NOPE00"}, ctx(customer_a)
    )
    assert result["found"] is False
    assert len(result["available_warranties"]) == 1
