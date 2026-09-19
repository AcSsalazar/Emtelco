from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "brand", "category", "price", "stock", "active")
    list_filter = ("category", "active")
    search_fields = ("sku", "name", "brand")
    readonly_fields = ("created_at", "updated_at")
