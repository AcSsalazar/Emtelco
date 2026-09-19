from datetime import timedelta

import pytest
from django.utils import timezone

from apps.agent.tools.registry import ToolContext, execute_tool

pytestmark = pytest.mark.django_db


def ctx(customer):
    return ToolContext(customer=customer, conversation=None)


def test_order_list_only_own(auth_client, customer_a, customer_b, products, order_factory):
    order_factory(customer_a, products["laptop_gpu"], status="shipped")
    order_factory(customer_b, products["tv"], status="delivered")

    response = auth_client.get("/api/orders")
    assert response.status_code == 200
    assert response.data["count"] == 1


def test_cannot_read_other_customer_order(auth_client, customer_b, products, order_factory):
    foreign = order_factory(customer_b, products["tv"], status="shipped")
    response = auth_client.get(f"/api/orders/{foreign.id}")
    assert response.status_code == 404


def test_orders_get_a_guide_number(customer_a, products, order_factory):
    order = order_factory(customer_a, products["laptop_gpu"], status="processing")
    assert order.number.startswith("GUI-")
    assert len(order.number) == 10


def test_get_order_status_by_number(customer_a, products, order_factory):
    order = order_factory(customer_a, products["laptop_gpu"], status="out_for_delivery")
    result = execute_tool(
        "get_order_status", {"order_number": order.number}, ctx(customer_a)
    )
    assert result["found"] is True
    assert result["order"]["number"] == order.number
    assert result["order"]["status"] == "out_for_delivery"


def test_get_order_status_rejects_foreign_order(customer_a, customer_b, products, order_factory):
    foreign = order_factory(customer_b, products["tv"])
    result = execute_tool(
        "get_order_status", {"order_number": foreign.number}, ctx(customer_a)
    )
    assert result["found"] is False


def test_get_order_status_lists_multiple(customer_a, products, order_factory):
    order_factory(customer_a, products["laptop_gpu"], status="shipped")
    order_factory(customer_a, products["tv"], status="processing")
    result = execute_tool("get_order_status", {}, ctx(customer_a))
    assert result["multiple"] is True
    assert len(result["orders"]) == 2
    assert all(order["number"].startswith("GUI-") for order in result["orders"])


def test_get_order_status_lists_all_orders(customer_a, products, order_factory):
    for _ in range(7):
        order_factory(customer_a, products["tv"], status="shipped")
    result = execute_tool("get_order_status", {}, ctx(customer_a))
    assert result["multiple"] is True
    assert len(result["orders"]) == 7


def test_get_order_status_filters_by_product(customer_a, products, order_factory):
    order_factory(customer_a, products["laptop_gpu"], status="delivered")
    order_factory(customer_a, products["tv"], status="out_for_delivery")
    result = execute_tool("get_order_status", {"product_query": "Samsung"}, ctx(customer_a))
    assert result["found"] is True
    assert result["order"]["product"] == products["tv"].name


def test_get_order_status_filters_by_phrase(customer_a, products, order_factory):
    order_factory(customer_a, products["laptop_gpu"], status="delivered")
    order_factory(customer_a, products["tv"], status="out_for_delivery")
    result = execute_tool(
        "get_order_status", {"product_query": "televisor Samsung"}, ctx(customer_a)
    )
    assert result["found"] is True
    assert result["order"]["product"] == products["tv"].name


def test_get_order_status_phrase_without_match(customer_a, products, order_factory):
    order_factory(customer_a, products["laptop_gpu"], status="delivered")
    result = execute_tool(
        "get_order_status", {"product_query": "televisor Samsung"}, ctx(customer_a)
    )
    assert result["found"] is False


def test_get_order_status_wrong_code_returns_available(customer_a, products, order_factory):
    order_factory(customer_a, products["tv"], status="out_for_delivery")
    result = execute_tool(
        "get_order_status", {"order_number": "GUI-NOPE00"}, ctx(customer_a)
    )
    assert result["found"] is False
    assert len(result["available_orders"]) == 1
    # Minimal disclosure: no address, tracking or dates.
    assert "shipping_address" not in result["available_orders"][0]
    assert "tracking_number" not in result["available_orders"][0]


def test_multi_order_listing_is_compact(customer_a, products, order_factory):
    order_factory(customer_a, products["tv"], status="shipped", tracking_number="EMT-1")
    order_factory(customer_a, products["laptop_gpu"], status="delivered")
    result = execute_tool("get_order_status", {}, ctx(customer_a))
    assert result["multiple"] is True
    for order in result["orders"]:
        assert set(order.keys()) == {"number", "product", "status_label"}


def test_single_order_has_full_detail(customer_a, products, order_factory):
    order = order_factory(
        customer_a, products["tv"], status="shipped", tracking_number="EMT-1"
    )
    result = execute_tool(
        "get_order_status", {"order_number": order.number}, ctx(customer_a)
    )
    assert result["found"] is True
    assert result["order"]["shipping_address"]
    assert result["order"]["tracking_number"] == "EMT-1"


def test_get_delivery_estimate_tool(customer_a, products, order_factory):
    estimated = timezone.now().date() + timedelta(days=2)
    order = order_factory(
        customer_a, products["tv"], status="shipped", estimated_delivery=estimated
    )
    result = execute_tool(
        "get_delivery_estimate", {"order_number": order.number}, ctx(customer_a)
    )
    assert result["found"] is True
    assert result["estimated_delivery"] == estimated.isoformat()


def test_update_delivery_address_valid(customer_a, products, order_factory):
    order = order_factory(customer_a, products["tv"], status="processing")
    result = execute_tool(
        "update_delivery_address",
        {"order_number": order.number, "new_address": "Cra 10 # 20-30, Medellín"},
        ctx(customer_a),
    )
    assert result["updated"] is True
    order.refresh_from_db()
    assert order.shipping_address == "Cra 10 # 20-30, Medellín"


def test_update_delivery_address_invalid(customer_a, products, order_factory):
    order = order_factory(customer_a, products["tv"], status="processing")
    result = execute_tool(
        "update_delivery_address",
        {"order_number": order.number, "new_address": "x"},
        ctx(customer_a),
    )
    assert "error" in result


def test_update_delivery_address_rejects_delivered(customer_a, products, order_factory):
    order = order_factory(customer_a, products["tv"], status="delivered")
    result = execute_tool(
        "update_delivery_address",
        {"order_number": order.number, "new_address": "Cra 10 # 20-30, Medellín"},
        ctx(customer_a),
    )
    assert "error" in result
    order.refresh_from_db()
    assert order.shipping_address != "Cra 10 # 20-30, Medellín"


def test_cannot_update_other_customer_order(customer_a, customer_b, products, order_factory):
    foreign = order_factory(customer_b, products["tv"], status="processing")
    result = execute_tool(
        "update_delivery_address",
        {"order_number": foreign.number, "new_address": "Cra 10 # 20-30, Medellín"},
        ctx(customer_a),
    )
    assert "error" in result
    foreign.refresh_from_db()
    assert foreign.shipping_address != "Cra 10 # 20-30, Medellín"
