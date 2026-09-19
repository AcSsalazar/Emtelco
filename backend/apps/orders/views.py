from rest_framework import generics

from apps.accounts.utils import get_customer

from .models import Order, Warranty
from .serializers import OrderSerializer, WarrantySerializer


class CustomerOrderMixin:
    """Restrict every query to the authenticated customer's own orders."""

    def get_queryset(self):
        customer = get_customer(self.request.user)
        if customer is None:
            return Order.objects.none()
        return Order.objects.filter(customer=customer).select_related("product")


class OrderListView(CustomerOrderMixin, generics.ListAPIView):
    serializer_class = OrderSerializer


class OrderDetailView(CustomerOrderMixin, generics.RetrieveAPIView):
    serializer_class = OrderSerializer


class WarrantyListView(generics.ListAPIView):
    serializer_class = WarrantySerializer

    def get_queryset(self):
        customer = get_customer(self.request.user)
        if customer is None:
            return Warranty.objects.none()
        return Warranty.objects.filter(order__customer=customer).select_related(
            "product", "order"
        )
