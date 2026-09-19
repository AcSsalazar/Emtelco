"""Reusable validators for customer data.

These rules mirror the technical test specification:

* identification: 4-11 numeric digits
* full_name: 1-100 chars, letters, spaces, accents and ñ only
* phone: exactly 10 digits, starting with 3 or 6
* email: valid email format
"""

import re

from django.core.exceptions import ValidationError

IDENTIFICATION_RE = re.compile(r"^\d{4,11}$")
PHONE_RE = re.compile(r"^[36]\d{9}$")
FULL_NAME_RE = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ\s]+$")


def validate_identification(value: str) -> None:
    if not IDENTIFICATION_RE.match(str(value or "")):
        raise ValidationError(
            "La identificación debe tener entre 4 y 11 dígitos numéricos.",
            code="invalid_identification",
        )


def validate_full_name(value: str) -> None:
    value = str(value or "").strip()
    if not (1 <= len(value) <= 100) or not FULL_NAME_RE.match(value):
        raise ValidationError(
            "El nombre solo puede contener letras, espacios, tildes y ñ (1-100 caracteres).",
            code="invalid_full_name",
        )


def validate_phone(value: str) -> None:
    if not PHONE_RE.match(str(value or "")):
        raise ValidationError(
            "El teléfono debe tener exactamente 10 dígitos y comenzar por 3 o 6.",
            code="invalid_phone",
        )
