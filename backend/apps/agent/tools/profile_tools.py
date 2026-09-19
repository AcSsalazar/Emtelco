"""Profile tools: let the agent persist durable customer preferences."""

from __future__ import annotations

from typing import Any

from apps.agent import profile as profile_service

from .registry import ToolContext, ToolError, register_tool

PROFILE_PARAMS = {
    "type": "object",
    "properties": {
        "use_cases": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Objetivos o usos del cliente (ej. 'diseño gráfico', 'edición de video').",
        },
        "software": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Programas que usa (ej. 'DaVinci Resolve', 'Illustrator').",
        },
        "preferred_brands": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Marcas que prefiere.",
        },
        "os_preference": {
            "type": "string",
            "enum": ["windows", "macos", "linux", "any"],
            "description": "Sistema operativo preferido.",
        },
        "experience_level": {
            "type": "string",
            "enum": ["basic", "intermediate", "advanced"],
            "description": "Nivel de experiencia del cliente.",
        },
        "budget_min": {
            "type": "number",
            "description": "Presupuesto mínimo en pesos colombianos.",
        },
        "budget_max": {
            "type": "number",
            "description": "Presupuesto máximo en pesos colombianos.",
        },
        "notes": {
            "type": "string",
            "description": "Otra preferencia o dato relevante del cliente.",
        },
    },
    "required": [],
}


@register_tool(
    name="save_customer_preference",
    description=(
        "Guarda preferencias o datos de perfil del cliente para futuras "
        "recomendaciones (usos, software, marcas, sistema, presupuesto, "
        "experiencia). Úsala cuando el cliente exprese una preferencia."
    ),
    parameters=PROFILE_PARAMS,
)
def save_customer_preference(
    context: ToolContext, args: dict[str, Any]
) -> dict[str, Any]:
    cleaned = {key: value for key, value in (args or {}).items() if value not in (None, "", [])}
    if not cleaned:
        raise ToolError("No recibí ninguna preferencia para guardar.")

    profile = profile_service.merge_profile(context.customer, cleaned)
    return {
        "saved": True,
        "profile": {
            "use_cases": profile.use_cases,
            "software": profile.software,
            "preferred_brands": profile.preferred_brands,
            "os_preference": profile.os_preference,
            "experience_level": profile.experience_level,
            "budget_min": float(profile.budget_min) if profile.budget_min else None,
            "budget_max": float(profile.budget_max) if profile.budget_max else None,
        },
    }
