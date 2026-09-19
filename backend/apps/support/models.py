from django.db import models

from apps.accounts.models import Customer
from apps.common.codes import TICKET_PREFIX, unique_code
from apps.conversations.models import Conversation
from apps.orders.models import Warranty


class SupportTicket(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Abierto"
        IN_PROGRESS = "in_progress", "En proceso"
        ESCALATED = "escalated", "Escalado"
        RESOLVED = "resolved", "Resuelto"
        CLOSED = "closed", "Cerrado"

    class Priority(models.TextChoices):
        LOW = "low", "Baja"
        MEDIUM = "medium", "Media"
        HIGH = "high", "Alta"
        URGENT = "urgent", "Urgente"

    class Source(models.TextChoices):
        AGENT = "agent", "Agente"
        WARRANTY = "warranty", "Garantía"
        ESCALATION = "escalation", "Escalamiento"
        CUSTOMER = "customer", "Cliente"

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="support_tickets",
    )
    number = models.CharField(max_length=16, unique=True, blank=True)
    warranty = models.ForeignKey(
        Warranty,
        on_delete=models.SET_NULL,
        related_name="support_tickets",
        null=True,
        blank=True,
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.SET_NULL,
        related_name="support_tickets",
        null=True,
        blank=True,
    )
    subject = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.AGENT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Ticket {self.number} - {self.subject}"

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = unique_code(TICKET_PREFIX, SupportTicket)
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = list(set(update_fields) | {"number"})
        super().save(*args, **kwargs)
