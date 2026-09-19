from django.contrib import admin

from .models import Conversation, ConversationMemory, Message


def _excerpt(obj) -> str:
    text = (obj.content or "").replace("\n", " ")
    return text[:80] + ("…" if len(text) > 80 else "")


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    can_delete = False
    fields = ("role", "tool_name", "excerpt", "created_at")
    readonly_fields = ("role", "tool_name", "excerpt", "created_at")

    @admin.display(description="Contenido")
    def excerpt(self, obj):
        return _excerpt(obj)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "title", "escalated", "updated_at")
    list_filter = ("escalated",)
    search_fields = ("customer__full_name", "customer__identification", "title")
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "role", "tool_name", "excerpt", "created_at")
    list_filter = ("role", "tool_name")
    search_fields = ("content",)

    @admin.display(description="Contenido")
    def excerpt(self, obj):
        return _excerpt(obj)


@admin.register(ConversationMemory)
class ConversationMemoryAdmin(admin.ModelAdmin):
    list_display = (
        "conversation",
        "customer_name",
        "budget",
        "last_order_number",
        "unresolved_attempts",
    )
