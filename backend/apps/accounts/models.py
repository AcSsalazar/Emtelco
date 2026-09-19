from django.conf import settings
from django.db import models

from .validators import validate_full_name, validate_identification, validate_phone


class Customer(models.Model):
    """Business profile attached to a Django ``User``.

    A customer can exist before a user account is created (seed data), which
    lets a returning customer "claim" their profile by identification when they
    register.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="customer",
        null=True,
        blank=True,
    )
    identification = models.CharField(
        max_length=11,
        unique=True,
        validators=[validate_identification],
    )
    full_name = models.CharField(max_length=100, validators=[validate_full_name])
    phone = models.CharField(max_length=10, validators=[validate_phone])
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.identification})"

    @property
    def first_name(self) -> str:
        return self.full_name.split(" ")[0]


class CustomerProfile(models.Model):
    """Durable, structured preferences for a customer.

    Unlike ``ConversationMemory`` (scoped to a single conversation), this
    profile travels with the customer across conversations and lets the agent
    adapt its tone and recommendations.
    """

    class OS(models.TextChoices):
        WINDOWS = "windows", "Windows"
        MACOS = "macos", "macOS"
        LINUX = "linux", "Linux"
        ANY = "any", "Indiferente"

    class Experience(models.TextChoices):
        BASIC = "basic", "Básico"
        INTERMEDIATE = "intermediate", "Intermedio"
        ADVANCED = "advanced", "Avanzado"

    customer = models.OneToOneField(
        Customer,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    use_cases = models.JSONField(default=list, blank=True)
    software = models.JSONField(default=list, blank=True)
    preferred_brands = models.JSONField(default=list, blank=True)
    os_preference = models.CharField(max_length=20, choices=OS.choices, blank=True)
    budget_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    budget_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    experience_level = models.CharField(
        max_length=20, choices=Experience.choices, blank=True
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Profile<{self.customer.identification}>"


class CustomerModeration(models.Model):
    """Deterministic moderation state for a customer.

    Internal counters are never exposed to the customer in the chat; they only
    drive the warning / temporary-block / permanent-block behaviour.
    """

    customer = models.OneToOneField(
        Customer,
        on_delete=models.CASCADE,
        related_name="moderation",
    )
    warning_count = models.PositiveIntegerField(default=0)
    violation_count = models.PositiveIntegerField(default=0)
    temporary_block_until = models.DateTimeField(null=True, blank=True)
    permanent_blocked = models.BooleanField(default=False)
    last_violation_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Moderation<{self.customer.identification}>"
