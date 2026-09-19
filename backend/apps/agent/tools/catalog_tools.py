"""Catalog tools: search, details, comparison and recommendation candidates.

These are *data-access primitives*: they return real catalog information. The
agent is responsible for interpreting, comparing and justifying; the tools do
not encode business heuristics about specific use cases.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from apps.catalog.models import Product

from .registry import ToolContext, ToolError, register_tool

MAX_RESULTS = 10

_STOPWORDS = {
    "para",
    "con",
    "por",
    "una",
    "uno",
    "los",
    "las",
    "del",
    "que",
    "como",
    "mas",
    "más",
    "sin",
    "sobre",
    "entre",
    "muy",
    "buen",
    "buena",
    "necesito",
    "quiero",
    "busco",
    "tengo",
}


def _brief(product: Product) -> dict[str, Any]:
    return {
        "id": product.id,
        "sku": product.sku,
        "name": product.name,
        "brand": product.brand,
        "category": product.category,
        "price": float(product.price),
        "stock": product.stock,
        "in_stock": product.stock > 0,
        "image_url": product.image.url if product.image else None,
        "warranty_months": product.warranty_months,
        "shipping_days": product.shipping_days,
        "specifications": product.specifications,
        "description": product.description,
    }


# Key specifications are reserved for get_product_details and compare_products,
# so list results stay small and the agent does not dump specs into the chat.


def _card(product: Product) -> dict[str, Any]:
    """Compact product representation for search and recommendation results.

    Deliberately excludes specifications: the agent must fetch a product's
    details only when it actually needs them.
    """
    return {
        "id": product.id,
        "sku": product.sku,
        "name": product.name,
        "brand": product.brand,
        "category": product.category,
        "price": float(product.price),
        "stock": product.stock,
        "in_stock": product.stock > 0,
        "image_url": product.image.url if product.image else None,
    }


def _searchable_text(product: Product) -> str:
    specs = product.specifications or {}
    spec_text = " ".join(f"{key} {value}" for key, value in specs.items())
    return " ".join(
        [
            product.name,
            product.brand,
            product.category,
            product.description,
            spec_text,
        ]
    ).lower()


def _keywords(text: str) -> list[str]:
    words = re.findall(r"[a-záéíóúüñ0-9]+", (text or "").lower())
    return [word for word in words if len(word) >= 3 and word not in _STOPWORDS]


SEARCH_PARAMS = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Texto libre para buscar en nombre, marca o descripción.",
        },
        "category": {
            "type": "string",
            "enum": ["laptop", "phone", "tv", "accessory"],
            "description": "Categoría del producto.",
        },
        "brand": {"type": "string", "description": "Marca del producto."},
        "max_price": {
            "type": "number",
            "description": "Precio máximo en pesos colombianos.",
        },
        "min_price": {
            "type": "number",
            "description": "Precio mínimo en pesos colombianos.",
        },
        "in_stock_only": {
            "type": "boolean",
            "description": "Si es true, solo devuelve productos con stock disponible.",
        },
        "limit": {"type": "integer", "description": "Máximo de resultados (1-10)."},
    },
    "required": [],
}


@register_tool(
    name="search_products",
    description=(
        "Busca productos del catálogo por texto, categoría, marca o rango de "
        "precio. Devuelve productos reales con su precio, stock y especificaciones."
    ),
    parameters=SEARCH_PARAMS,
)
def search_products(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    qs = Product.objects.filter(active=True)

    if args.get("category"):
        qs = qs.filter(category=args["category"])
    if args.get("brand"):
        qs = qs.filter(brand__iexact=args["brand"])
    if args.get("query"):
        query = args["query"]
        qs = qs.filter(name__icontains=query)
    if args.get("max_price") is not None:
        qs = qs.filter(price__lte=Decimal(str(args["max_price"])))
    if args.get("min_price") is not None:
        qs = qs.filter(price__gte=Decimal(str(args["min_price"])))
    if args.get("in_stock_only"):
        qs = qs.filter(stock__gt=0)

    limit = int(args.get("limit") or 5)
    limit = max(1, min(limit, MAX_RESULTS))
    products = list(qs.order_by("price")[:limit])

    return {
        "found": bool(products),
        "count": len(products),
        "products": [_card(product) for product in products],
    }


DETAILS_PARAMS = {
    "type": "object",
    "properties": {
        "sku": {"type": "string", "description": "SKU del producto (ej. LAP-MARCA-MODELO)."},
    },
    "required": ["sku"],
}


@register_tool(
    name="get_product_details",
    description=(
        "Devuelve los detalles completos y las especificaciones de un producto "
        "por su SKU."
    ),
    parameters=DETAILS_PARAMS,
)
def get_product_details(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    sku = str(args.get("sku") or "").strip()
    product = Product.objects.filter(sku__iexact=sku, active=True).first()
    if product is None:
        return {"found": False, "message": "No encontré ese producto en nuestro catálogo."}
    return {"found": True, "product": _brief(product)}


COMPARE_PARAMS = {
    "type": "object",
    "properties": {
        "skus": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Lista de SKUs a comparar (2 a 4).",
        }
    },
    "required": ["skus"],
}


@register_tool(
    name="compare_products",
    description=(
        "Compara dos o más productos y devuelve sus especificaciones lado a "
        "lado para que puedas analizarlos con el cliente."
    ),
    parameters=COMPARE_PARAMS,
)
def compare_products(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    skus = args.get("skus") or []
    if not isinstance(skus, list) or len(skus) < 2:
        raise ToolError("Necesito al menos dos productos para compararlos.")

    normalized = [str(sku).strip().upper() for sku in skus]
    products = list(Product.objects.filter(sku__in=normalized, active=True))
    if len(products) < 2:
        return {
            "found": False,
            "message": "No encontré suficientes productos válidos para comparar.",
        }

    spec_keys: list[str] = []
    for product in products:
        for key in (product.specifications or {}):
            if key not in spec_keys:
                spec_keys.append(key)

    comparison = []
    for product in products:
        comparison.append(
            {
                "id": product.id,
                "name": product.name,
                "brand": product.brand,
                "price": float(product.price),
                "specifications": product.specifications,
            }
        )

    return {"found": True, "attributes": spec_keys, "products": comparison}


RECOMMEND_PARAMS = {
    "type": "object",
    "properties": {
        "need": {
            "type": "string",
            "description": (
                "Necesidad del cliente en palabras suyas, por ejemplo "
                "'portátil para diseño gráfico y edición de video'."
            ),
        },
        "category": {
            "type": "string",
            "enum": ["laptop", "phone", "tv", "accessory"],
            "description": "Categoría preferida, si el cliente la mencionó.",
        },
        "budget": {
            "type": "number",
            "description": "Presupuesto máximo en pesos colombianos.",
        },
        "limit": {
            "type": "integer",
            "description": "Máximo de candidatos a devolver (1-5).",
        },
    },
    "required": ["need"],
}


@register_tool(
    name="recommend_products",
    description=(
        "Devuelve productos candidatos del catálogo para una necesidad del "
        "cliente (texto libre) y, opcionalmente, una categoría y un presupuesto. "
        "Incluye especificaciones reales para que tú analices y justifiques la "
        "recomendación. No emite una opinión por sí misma."
    ),
    parameters=RECOMMEND_PARAMS,
)
def recommend_products(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    need = str(args.get("need") or "").strip()
    if not need:
        raise ToolError("Necesito saber para qué quiere el cliente el producto.")

    qs = Product.objects.filter(active=True)
    if args.get("category"):
        qs = qs.filter(category=args["category"])
    if args.get("budget") is not None:
        qs = qs.filter(price__lte=Decimal(str(args["budget"])))

    candidates = list(qs)
    if not candidates:
        return {
            "found": False,
            "message": "No encontré opciones que cumplan con ese presupuesto.",
        }

    keywords = _keywords(need)
    if keywords:
        scored = []
        for product in candidates:
            blob = _searchable_text(product)
            score = sum(blob.count(keyword) for keyword in keywords)
            if score:
                scored.append((score, product))
        if scored:
            scored.sort(key=lambda item: (-item[0], not item[1].in_stock, float(item[1].price)))
            candidates = [product for _, product in scored]
        else:
            candidates.sort(key=lambda product: (not product.in_stock, float(product.price)))
    else:
        candidates.sort(key=lambda product: (not product.in_stock, float(product.price)))

    limit = int(args.get("limit") or 3)
    limit = max(1, min(limit, 5))

    return {
        "found": True,
        "need": need,
        "budget": args.get("budget"),
        "count": len(candidates[:limit]),
        "candidates": [_card(product) for product in candidates[:limit]],
    }
