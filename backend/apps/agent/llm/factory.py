"""Provider factory.

Only OpenAI is implemented for the MVP, but the rest of the system resolves
the provider through this factory. Tests inject a fake provider with
``set_llm_provider`` without touching production code.
"""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .base import LLMProvider

_override: LLMProvider | None = None


def set_llm_provider(provider: LLMProvider | None) -> None:
    """Override the provider (used by tests)."""
    global _override
    _override = provider


def reset_llm_provider() -> None:
    set_llm_provider(None)


def get_llm_provider() -> LLMProvider:
    if _override is not None:
        return _override

    name = (settings.LLM_PROVIDER or "openai").lower()
    if name == "openai":
        from .openai_provider import OpenAIProvider

        return OpenAIProvider()

    raise ImproperlyConfigured(f"Proveedor LLM no soportado: {name}")
