from django.contrib import admin

from .models import Order, Warranty


class WarrantyInline(admin.TabularInline):
    model = Warranty
    extra = 0
    readonly_fields = ("number",)
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "customer",
        "product",
        "status",
        "estimated_delivery",
        "tracking_number",
    )
    list_filter = ("status",)
    search_fields = (
        "number",
        "customer__full_name",
        "customer__identification",
        "product__name",
    )
    readonly_fields = ("number", "created_at", "updated_at")
    inlines = [WarrantyInline]


@admin.register(Warranty)
class WarrantyAdmin(admin.ModelAdmin):
    list_display = ("number", "order", "product", "coverage_status", "expiration_date")
    list_filter = ("coverage_status",)
    search_fields = ("number", "order__number", "product__name")
    readonly_fields = ("number", "created_at", "updated_at")
