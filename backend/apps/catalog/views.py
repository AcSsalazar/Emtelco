from rest_framework import generics

from .models import Product
from .serializers import ProductSerializer


class ProductListView(generics.ListAPIView):
    serializer_class = ProductSerializer

    def get_queryset(self):
        qs = Product.objects.filter(active=True)
        params = self.request.query_params

        category = params.get("category")
        if category:
            qs = qs.filter(category=category)

        brand = params.get("brand")
        if brand:
            qs = qs.filter(brand__iexact=brand)

        q = params.get("q")
        if q:
            qs = qs.filter(name__icontains=q)

        max_price = params.get("max_price")
        if max_price:
            qs = qs.filter(price__lte=max_price)

        min_price = params.get("min_price")
        if min_price:
            qs = qs.filter(price__gte=min_price)

        if params.get("in_stock") in {"1", "true", "True"}:
            qs = qs.filter(stock__gt=0)

        return qs


class ProductDetailView(generics.RetrieveAPIView):
    serializer_class = ProductSerializer
    queryset = Product.objects.filter(active=True)
