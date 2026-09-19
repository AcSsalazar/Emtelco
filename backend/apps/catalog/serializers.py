from rest_framework import serializers

from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    in_stock = serializers.BooleanField(read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "sku",
            "name",
            "brand",
            "category",
            "category_label",
            "description",
            "image_url",
            "price",
            "stock",
            "in_stock",
            "specifications",
            "warranty_months",
            "shipping_days",
            "active",
        ]

    def get_image_url(self, obj):
        if not obj.image:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.image.url) if request else obj.image.url
