from django.db import models

from apps.accounts.models import Customer
from apps.catalog.models import Product
from apps.common.codes import ORDER_PREFIX, WARRANTY_PREFIX, unique_code


class Order(models.Model):
    class Status(models.TextChoices):
        PROCESSING = "processing", "En preparación"
        SHIPPED = "shipped", "Enviado"
        OUT_FOR_DELIVERY = "out_for_delivery", "En reparto"
        DELIVERED = "delivered", "Entregado"
        DELAYED = "delayed", "Retrasado"
        CANCELLED = "cancelled", "Cancelado"

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="orders")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="orders")
    number = models.CharField(max_length=16, unique=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PROCESSING,
        db_index=True,
    )
    tracking_number = models.CharField(max_length=40, blank=True)
    shipping_address = models.CharField(max_length=255)
    estimated_delivery = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Order {self.number} - {self.product.name} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = unique_code(ORDER_PREFIX, Order)
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = list(set(update_fields) | {"number"})
        super().save(*args, **kwargs)


class Warranty(models.Model):
    class CoverageStatus(models.TextChoices):
        ACTIVE = "active", "Vigente"
        EXPIRED = "expired", "Vencida"
        VOID = "void", "No cubierta"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="warranties")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="warranties")
    number = models.CharField(max_length=16, unique=True, blank=True)
    coverage_status = models.CharField(
        max_length=20,
        choices=CoverageStatus.choices,
        default=CoverageStatus.ACTIVE,
    )
    expiration_date = models.DateField()
    conditions = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-expiration_date"]

    def __str__(self) -> str:
        return f"Warranty {self.number} order {self.order.number} ({self.get_coverage_status_display()})"

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = unique_code(WARRANTY_PREFIX, Warranty)
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = list(set(update_fields) | {"number"})
        super().save(*args, **kwargs)
