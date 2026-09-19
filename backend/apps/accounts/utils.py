"""Small helpers shared across apps."""

from typing import Optional

from .models import Customer


def get_customer(user) -> Optional[Customer]:
    """Return the customer profile for a user, or ``None``.

    The reverse one-to-one descriptor raises ``RelatedObjectDoesNotExist``
    (an ``AttributeError`` subclass), so ``getattr`` with a default is safe.
    """
    return getattr(user, "customer", None)
