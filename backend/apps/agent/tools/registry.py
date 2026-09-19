"""Tool registry.

Tools are plain Python functions with a name, a natural-language description
and a JSON-schema for their parameters. The orchestrator exposes them to the
LLM and executes them against the Django ORM.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

logger = logging.getLogger(__name__)


class ToolError(Exception):
    """A controlled, user-safe tool failure."""


@dataclass
class ToolContext:
    customer: Any
    conversation: Any


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[[ToolContext, dict[str, Any]], dict[str, Any]]


_REGISTRY: dict[str, Tool] = {}


def register_tool(
    name: str,
    description: str,
    parameters: dict[str, Any],
) -> Callable:
    def decorator(func: Callable[[ToolContext, dict[str, Any]], dict[str, Any]]):
        _REGISTRY[name] = Tool(
            name=name,
            description=description,
            parameters=parameters,
            handler=func,
        )
        return func

    return decorator


def get_registry() -> dict[str, Tool]:
    return _REGISTRY


def get_tool_schemas() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
        for tool in _REGISTRY.values()
    ]


def execute_tool(
    name: str,
    arguments: dict[str, Any] | None,
    context: ToolContext,
) -> dict[str, Any]:
    tool = _REGISTRY.get(name)
    if tool is None:
        logger.warning("Unknown tool requested: %s", name)
        return {"error": f"La herramienta '{name}' no está disponible."}

    arguments = arguments or {}
    logger.info("Tool call: %s(%s)", name, arguments)
    missing = [
        param
        for param in tool.parameters.get("required", [])
        if param not in arguments or arguments[param] in (None, "")
    ]
    if missing:
        return {"error": f"Faltan parámetros obligatorios: {', '.join(missing)}."}

    try:
        return tool.handler(context, arguments)
    except ToolError as exc:
        return {"error": str(exc)}
    except Exception:  # noqa: BLE001 - never leak internals to the model/user
        logger.exception("Tool '%s' failed", name)
        return {"error": "No fue posible completar la operación solicitada."}


def _load_tools() -> None:
    """Import tool modules so their decorators run."""
    from . import catalog_tools, order_tools, profile_tools, support_tools  # noqa: F401
