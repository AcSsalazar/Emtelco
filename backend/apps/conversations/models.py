from django.db import models

from apps.accounts.models import Customer


class Conversation(models.Model):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    title = models.CharField(max_length=120, blank=True)
    escalated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"Conversation #{self.pk} - {self.customer.full_name}"


class Message(models.Model):
    class Role(models.TextChoices):
        USER = "user", "Usuario"
        ASSISTANT = "assistant", "Asistente"
        SYSTEM = "system", "Sistema"
        TOOL = "tool", "Herramienta"

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField(blank=True)
    # Optional structured payload (e.g. product cards with thumbnails) used by
    # the frontend to render rich attachments under the message.
    metadata = models.JSONField(default=dict, blank=True)
    # Kept for traceability of tool results; never shown raw to the customer.
    tool_name = models.CharField(max_length=60, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        return f"[{self.role}] {self.content[:40]}"


class ConversationMemory(models.Model):
    """Structured, persistent memory for a conversation.

    This is intentionally *not* a vector store: it is a small set of typed
    fields the Context Builder can render into the system prompt.
    """

    conversation = models.OneToOneField(
        Conversation,
        on_delete=models.CASCADE,
        related_name="memory",
    )
    customer_name = models.CharField(max_length=100, blank=True)
    budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    products_consulted = models.JSONField(default=list, blank=True)
    preferences = models.JSONField(default=list, blank=True)
    last_order_number = models.CharField(max_length=16, blank=True)
    last_product_sku = models.CharField(max_length=40, blank=True)
    last_intent = models.CharField(max_length=40, blank=True)
    unresolved_attempts = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Memory<conversation {self.conversation_id}>"
