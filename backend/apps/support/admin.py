from django.contrib import admin

from .models import SupportTicket


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "customer",
        "subject",
        "status",
        "priority",
        "source",
        "created_at",
    )
    list_filter = ("status", "priority", "source")
    search_fields = (
        "number",
        "subject",
        "customer__full_name",
        "customer__identification",
    )
    readonly_fields = ("number", "created_at", "updated_at")
