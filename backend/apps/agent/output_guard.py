"""Deterministic backstop for the agent's own output.

The primary control is the agent policy (section 12), which instructs the model
to stay respectful. This module is a cheap safety net: if the generated reply
contains a blocked term, it is replaced with a safe, on-domain message before
it is stored or shown.
"""

from __future__ import annotations

import logging
import re

from django.conf import settings

logger = logging.getLogger(__name__)

_DEFAULT_TERMS = [
    "hijueputa",
    "gonorrea",
    "pendejo",
    "imbecil",
    "estupido",
    "cabron",
    "marica",
    "verga",
    "puta",
    "puto",
    "mierda",
    "joder",
    "coño",
    "fuck",
    "shit",
    "bitch",
]

_SAFE_REPLY = (
    "Prefiero mantener un lenguaje respetuoso. ¿En qué más te puedo ayudar con "
    "productos, pedidos, entregas, garantías o soporte?"
)


def _pattern():
    terms = getattr(settings, "AGENT_BLOCKED_OUTPUT_TERMS", _DEFAULT_TERMS)
    terms = [str(term).strip() for term in terms if str(term).strip()]
    if not terms:
        return None
    return re.compile("|".join(re.escape(term) for term in terms), re.IGNORECASE)


def sanitize_reply(text: str) -> str:
    pattern = _pattern()
    if pattern and text and pattern.search(text):
        logger.warning("Agent output blocked by safety backstop")
        return _SAFE_REPLY
    return text
