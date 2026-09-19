from django.db import models


class Product(models.Model):
    class Category(models.TextChoices):
        LAPTOP = "laptop", "Portátil"
        PHONE = "phone", "Celular"
        TV = "tv", "Televisor"
        ACCESSORY = "accessory", "Accesorio"

    sku = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=150)
    brand = models.CharField(max_length=80)
    category = models.CharField(max_length=20, choices=Category.choices, db_index=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    specifications = models.JSONField(default=dict, blank=True)
    warranty_months = models.PositiveIntegerField(default=0)
    shipping_days = models.PositiveIntegerField(default=1)
    active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "brand", "name"]
        indexes = [models.Index(fields=["category", "active"])]

    def __str__(self) -> str:
        return f"{self.name} ({self.sku})"

    @property
    def in_stock(self) -> bool:
        return self.stock > 0
