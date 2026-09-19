from django.contrib import admin

from .models import Customer, CustomerModeration, CustomerProfile


class CustomerProfileInline(admin.StackedInline):
    model = CustomerProfile
    can_delete = False
    extra = 0


class CustomerModerationInline(admin.StackedInline):
    model = CustomerModeration
    can_delete = False
    extra = 0


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("identification", "full_name", "phone", "email", "user")
    search_fields = ("identification", "full_name", "email")
    inlines = [CustomerProfileInline, CustomerModerationInline]


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "customer",
        "os_preference",
        "experience_level",
        "budget_max",
        "updated_at",
    )
    search_fields = ("customer__full_name", "customer__identification")


@admin.register(CustomerModeration)
class CustomerModerationAdmin(admin.ModelAdmin):
    list_display = (
        "customer",
        "permanent_blocked",
        "temporary_block_until",
        "violation_count",
        "warning_count",
        "last_violation_at",
    )
    list_filter = ("permanent_blocked",)
    search_fields = ("customer__full_name", "customer__identification")
