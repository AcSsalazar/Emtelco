"""Deterministic moderation state machine.

All decisions about warnings, temporary blocks and permanent blocks live here,
in the backend. The LLM only classifies a message; it never decides the
penalty.
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.accounts.models import Customer, CustomerModeration


class ModerationAction:
    NONE = "none"
    WARNING_1 = "warning_1"
    WARNING_2 = "warning_2"
    TEMP_BLOCK = "temp_block"
    PERMANENT = "permanent"


def get_or_create_moderation(customer: Customer) -> CustomerModeration:
    moderation, _ = CustomerModeration.objects.get_or_create(customer=customer)
    return moderation


def active_block(customer: Customer) -> str | None:
    """Return 'permanent', 'temporary' or None for the current state."""
    moderation = get_or_create_moderation(customer)
    if moderation.permanent_blocked:
        return "permanent"
    if moderation.temporary_block_until and moderation.temporary_block_until > timezone.now():
        return "temporary"
    return None


def register_violation(customer: Customer, severity: str) -> str:
    """Apply the penalty ladder and return the resulting action.

    Aligned with the product requirement: a first offense is never a permanent
    block. Mild violations (``low``) escalate through warnings and a temporary
    suspension; severe ones (``high``) start at a temporary suspension. A
    permanent block requires recurrence.
    """
    moderation = get_or_create_moderation(customer)
    now = timezone.now()
    moderation.violation_count += 1
    moderation.warning_count += 1
    moderation.last_violation_at = now
    count = moderation.violation_count
    threshold = settings.AGENT_PERMANENT_BLOCK_AFTER

    if count >= threshold:
        moderation.permanent_blocked = True
        action = ModerationAction.PERMANENT
    elif severity == "high":
        if count >= 2:
            moderation.permanent_blocked = True
            action = ModerationAction.PERMANENT
        else:
            moderation.temporary_block_until = now + timedelta(
                minutes=settings.AGENT_TEMPORARY_BLOCK_MINUTES
            )
            action = ModerationAction.TEMP_BLOCK
    elif count == 1:
        action = ModerationAction.WARNING_1
    elif count == 2:
        action = ModerationAction.WARNING_2
    elif count == 3:
        moderation.temporary_block_until = now + timedelta(
            minutes=settings.AGENT_TEMPORARY_BLOCK_MINUTES
        )
        action = ModerationAction.TEMP_BLOCK
    else:
        moderation.permanent_blocked = True
        action = ModerationAction.PERMANENT

    moderation.save()
    return action


def unblock(customer: Customer) -> CustomerModeration:
    """Clear a customer's blocks and counters (used by the moderation command)."""
    moderation = get_or_create_moderation(customer)
    moderation.permanent_blocked = False
    moderation.temporary_block_until = None
    moderation.warning_count = 0
    moderation.violation_count = 0
    moderation.save()
    return moderation


def block_permanently(customer: Customer) -> CustomerModeration:
    moderation = get_or_create_moderation(customer)
    moderation.permanent_blocked = True
    moderation.save()
    return moderation
