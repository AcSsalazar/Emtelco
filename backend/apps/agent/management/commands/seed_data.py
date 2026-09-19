"""Populate the database with demo data for the required scenarios.

Usage:
    python manage.py seed_data
    python manage.py seed_data --reset
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Customer, CustomerModeration
from apps.catalog.models import Product
from apps.orders.models import Order, Warranty

from apps.agent.demo_data import (
    CUSTOMERS,
    DEMO_PASSWORD,
    ORDERS,
    PRODUCTS,
)


class Command(BaseCommand):
    help = "Load demo products, customers, orders and warranties."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete previously seeded demo data before loading it again.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            self._reset()

        products = self._seed_products()
        customers = self._seed_customers()
        customer_by_id = {c.identification: c for c in customers}
        self._seed_orders(products, customer_by_id)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete: {len(products)} products, "
                f"{len(customers)} customers, {len(ORDERS)} orders."
            )
        )

    # -- helpers ----------------------------------------------------------
    def _seed_products(self) -> dict[str, Product]:
        products: dict[str, Product] = {}
        for data in PRODUCTS:
            payload = dict(data)
            sku = payload.pop("sku")
            payload["price"] = Decimal(str(payload["price"]))
            product, _ = Product.objects.update_or_create(
                sku=sku,
                defaults=payload,
            )
            products[sku] = product
        return products

    def _seed_customers(self) -> list[Customer]:
        User = get_user_model()
        customers = []
        for data in CUSTOMERS:
            identification = data["identification"]
            payload = {
                "full_name": data["full_name"],
                "phone": data["phone"],
                "email": data["email"],
            }
            customer, _ = Customer.objects.update_or_create(
                identification=identification,
                defaults=payload,
            )
            CustomerModeration.objects.get_or_create(customer=customer)

            if data.get("with_user"):
                user = User.objects.filter(username=data["email"]).first()
                if user is None:
                    user = User.objects.create_user(
                        username=data["email"],
                        email=data["email"],
                        password=DEMO_PASSWORD,
                        first_name=data["full_name"].split(" ")[0],
                    )
                if customer.user_id != user.id:
                    customer.user = user
                    customer.save(update_fields=["user"])
            customers.append(customer)
        return customers

    def _seed_orders(
        self,
        products: dict[str, Product],
        customers: dict[str, Customer],
    ) -> None:
        today = timezone.now().date()
        for data in ORDERS:
            customer = customers[data["customer"]]
            product = products[data["sku"]]
            total = Decimal(str(product.price)) * data["quantity"]
            estimated = (
                today + timedelta(days=data["days_from_now"])
                if data["days_from_now"] is not None
                else None
            )
            defaults = {
                "product": product,
                "quantity": data["quantity"],
                "total": total,
                "status": data["status"],
                "shipping_address": data["shipping_address"],
                "estimated_delivery": estimated,
            }
            if data["tracking_number"]:
                lookup = {
                    "customer": customer,
                    "tracking_number": data["tracking_number"],
                }
            else:
                lookup = {
                    "customer": customer,
                    "product": product,
                    "status": data["status"],
                }
            order, _ = Order.objects.update_or_create(defaults=defaults, **lookup)

            warranty = data.get("warranty")
            if warranty:
                Warranty.objects.update_or_create(
                    order=order,
                    product=product,
                    defaults={
                        "coverage_status": warranty["coverage_status"],
                        "expiration_date": today
                        + timedelta(days=warranty["expiration_days_from_now"]),
                        "conditions": warranty["conditions"],
                    },
                )

    def _reset(self) -> None:
        identifications = [c["identification"] for c in CUSTOMERS]
        emails = [c["email"] for c in CUSTOMERS if c.get("with_user")]
        User = get_user_model()

        Customer.objects.filter(identification__in=identifications).delete()
        User.objects.filter(username__in=emails).delete()
        for data in PRODUCTS:
            Product.objects.filter(sku=data["sku"]).delete()
        self.stdout.write(self.style.WARNING("Previous demo data removed."))
