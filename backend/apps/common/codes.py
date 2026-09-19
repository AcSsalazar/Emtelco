"""Short, unambiguous customer-facing codes.

Codes are used as the public reference the customer can read out loud to the
agent (for example an order guide ``GUI-7K3M9A``). The alphabet excludes
characters that are easy to confuse when spoken or typed: 0/O and 1/I/L.
"""

from __future__ import annotations

import secrets
from typing import Type

ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
LENGTH = 6

ORDER_PREFIX = "GUI"
WARRANTY_PREFIX = "GAR"
TICKET_PREFIX = "TCK"


def generate_code(prefix: str) -> str:
    body = "".join(secrets.choice(ALPHABET) for _ in range(LENGTH))
    return f"{prefix}-{body}"


def unique_code(prefix: str, model: Type, field: str = "number", attempts: int = 12) -> str:
    """Generate a code that does not collide with existing rows."""
    for _ in range(attempts):
        code = generate_code(prefix)
        if not model.objects.filter(**{field: code}).exists():
            return code
    raise RuntimeError(f"No se pudo generar un código único para {model.__name__}.")
