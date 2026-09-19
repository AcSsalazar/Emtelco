import pytest

from apps.agent.tools.registry import ToolContext, execute_tool
from apps.catalog.models import Product

pytestmark = pytest.mark.django_db


def ctx(customer):
    return ToolContext(customer=customer, conversation=None)


def test_product_list_endpoint(auth_client, products):
    response = auth_client.get("/api/products")
    assert response.status_code == 200
    assert response.data["count"] == 4


def test_product_list_filters_by_budget(auth_client, products):
    response = auth_client.get("/api/products", {"category": "laptop", "max_price": "3000000"})
    assert response.status_code == 200
    results = response.data["results"]
    assert len(results) == 1
    assert float(results[0]["price"]) <= 3000000


def test_search_products_tool(seeded):
    result = execute_tool("search_products", {"category": "laptop"}, ctx(seeded))
    assert result["found"] is True
    assert result["count"] > 0


def test_search_products_respects_budget(seeded):
    result = execute_tool(
        "search_products",
        {"category": "laptop", "max_price": 5000000, "in_stock_only": True},
        ctx(seeded),
    )
    assert result["found"] is True
    assert all(product["price"] <= 5000000 for product in result["products"])


def test_get_product_details_not_found(seeded):
    result = execute_tool("get_product_details", {"sku": "NOPE-0000"}, ctx(seeded))
    assert result["found"] is False


def test_compare_products_tool(seeded):
    skus = list(
        Product.objects.filter(category="laptop")[:2].values_list("sku", flat=True)
    )
    result = execute_tool("compare_products", {"skus": skus}, ctx(seeded))
    assert result["found"] is True
    assert len(result["products"]) == 2
    assert "gpu" in result["attributes"]


def test_compare_requires_two_products(seeded):
    result = execute_tool("compare_products", {"skus": ["LAP-HP-VICTUS15"]}, ctx(seeded))
    assert "error" in result


def test_recommend_products_returns_candidates_with_specs(seeded):
    result = execute_tool(
        "recommend_products",
        {"need": "portátil para diseño gráfico", "category": "laptop", "budget": 5000000},
        ctx(seeded),
    )
    assert result["found"] is True
    candidates = result["candidates"]
    assert candidates
    assert all(product["price"] <= 5000000 for product in candidates)
    # Lists stay compact: specs are only returned by get_product_details.
    assert all("highlights" not in product for product in candidates)
    assert all("sku" in product for product in candidates)
    assert len(candidates) <= 3


def test_get_product_details_returns_full_specifications(seeded):
    product = Product.objects.filter(category="laptop").first()
    result = execute_tool("get_product_details", {"sku": product.sku}, ctx(seeded))
    assert result["found"] is True
    assert result["product"]["specifications"]
    assert result["product"]["sku"] == product.sku
