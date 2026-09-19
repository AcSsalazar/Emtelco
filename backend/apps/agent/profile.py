"""Persistent customer profile service.

The profile holds durable preferences that travel with the customer across
conversations (use cases, software, brands, OS, budget, experience). It is
merged from two sources: the per-turn classifier and the agent's
``save_customer_preference`` tool.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from apps.accounts.models import Customer, CustomerProfile

MAX_ITEMS = 8

_LIST_FIELDS = ("use_cases", "software", "preferred_brands")
_CHOICE_FIELDS = {
    "os_preference": CustomerProfile.OS.values,
    "experience_level": CustomerProfile.Experience.values,
}
_BUDGET_FIELDS = ("budget_min", "budget_max")


def get_or_create_profile(customer: Customer) -> CustomerProfile:
    profile, _ = CustomerProfile.objects.get_or_create(customer=customer)
    return profile


def merge_profile(customer: Customer, updates: dict | None) -> CustomerProfile:
    profile = get_or_create_profile(customer)
    if not updates:
        return profile

    changed = False

    for field in _LIST_FIELDS:
        values = updates.get(field)
        if not values:
            continue
        if isinstance(values, str):
            values = [values]
        current = list(getattr(profile, field) or [])
        for value in values:
            value = str(value).strip()
            if value and value not in current:
                current.append(value)
        current = current[-MAX_ITEMS:]
        if current != (getattr(profile, field) or []):
            setattr(profile, field, current)
            changed = True

    for field, allowed in _CHOICE_FIELDS.items():
        value = updates.get(field)
        if not value:
            continue
        value = str(value).strip().lower()
        if value in allowed and getattr(profile, field) != value:
            setattr(profile, field, value)
            changed = True

    for field in _BUDGET_FIELDS:
        value = updates.get(field)
        if value in (None, ""):
            continue
        try:
            amount = Decimal(str(value)).quantize(Decimal("1"))
        except (InvalidOperation, ValueError):
            continue
        if getattr(profile, field) != amount:
            setattr(profile, field, amount)
            changed = True

    notes = updates.get("notes")
    if notes:
        notes = str(notes).strip()
        if notes and notes != profile.notes:
            profile.notes = notes[:500]
            changed = True

    if changed:
        profile.save()
    return profile


def render_profile(profile: CustomerProfile | None) -> str:
    if profile is None:
        return "- Sin preferencias registradas todavía."

    lines = []
    if profile.use_cases:
        lines.append(f"- Usos/objetivos: {', '.join(profile.use_cases)}")
    if profile.software:
        lines.append(f"- Software que usa: {', '.join(profile.software)}")
    if profile.preferred_brands:
        lines.append(f"- Marcas preferidas: {', '.join(profile.preferred_brands)}")
    if profile.os_preference:
        lines.append(f"- Sistema preferido: {profile.get_os_preference_display()}")
    if profile.budget_min is not None or profile.budget_max is not None:
        low = int(profile.budget_min) if profile.budget_min is not None else None
        high = int(profile.budget_max) if profile.budget_max is not None else None
        lines.append(f"- Rango de presupuesto: {low or 'sin mínimo'} - {high or 'sin máximo'} COP")
    if profile.experience_level:
        lines.append(
            f"- Nivel de experiencia: {profile.get_experience_level_display()}"
        )
    if profile.notes:
        lines.append(f"- Notas: {profile.notes}")
    return "\n".join(lines) if lines else "- Sin preferencias registradas todavía."
