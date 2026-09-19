from django.urls import path

from .views import OrderDetailView, OrderListView, WarrantyListView

urlpatterns = [
    path("orders", OrderListView.as_view(), name="order-list"),
    path("orders/<int:pk>", OrderDetailView.as_view(), name="order-detail"),
    path("warranties", WarrantyListView.as_view(), name="warranty-list"),
]
