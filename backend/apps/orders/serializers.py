from rest_framework import serializers

from apps.catalog.serializers import ProductSerializer

from .models import Order, Warranty


class OrderSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "product",
            "quantity",
            "total",
            "status",
            "status_label",
            "tracking_number",
            "shipping_address",
            "estimated_delivery",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class WarrantySerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    coverage_label = serializers.CharField(
        source="get_coverage_status_display", read_only=True
    )

    class Meta:
        model = Warranty
        fields = [
            "id",
            "order",
            "product",
            "coverage_status",
            "coverage_label",
            "expiration_date",
            "conditions",
        ]
        read_only_fields = fields
