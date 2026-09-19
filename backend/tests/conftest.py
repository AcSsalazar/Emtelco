import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.accounts.models import Customer, CustomerModeration
from apps.agent.llm.factory import reset_llm_provider, set_llm_provider
from apps.agent.tools import registry as tool_registry
from tests.fake_provider import FakeLLMProvider

User = get_user_model()


@pytest.fixture(autouse=True)
def _load_tools():
    tool_registry._load_tools()
    yield


@pytest.fixture
def create_customer(db):
    def _create(
        identification="1000000001",
        full_name="Andrés Felipe Ríos",
        phone="3101234567",
        email="andres@example.com",
        password="Secret12345",
        with_user=True,
    ):
        customer = Customer.objects.create(
            identification=identification,
            full_name=full_name,
            phone=phone,
            email=email,
        )
        CustomerModeration.objects.get_or_create(customer=customer)
        if with_user:
            user = User.objects.create_user(
                username=email, email=email, password=password
            )
            customer.user = user
            customer.save(update_fields=["user"])
        return customer

    return _create


@pytest.fixture
def customer_a(create_customer):
    return create_customer()


@pytest.fixture
def customer_b(create_customer):
    return create_customer(
        identification="1000000002",
        full_name="María José Ñáñez",
        phone="6012345678",
        email="maria@example.com",
    )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(customer_a):
    client = APIClient()
    client.force_authenticate(user=customer_a.user)
    return client


@pytest.fixture
def other_client(customer_b):
    client = APIClient()
    client.force_authenticate(user=customer_b.user)
    return client


@pytest.fixture
def products(db):
    from apps.catalog.models import Product

    return {
        "laptop_gpu": Product.objects.create(
            sku="LAP-GPU",
            name="Lenovo LOQ 15IRH8",
            brand="Lenovo",
            category="laptop",
            price=4799900,
            stock=5,
            specifications={"gpu": "NVIDIA GeForce RTX 3050 6GB", "ram_gb": 16},
            warranty_months=12,
            shipping_days=3,
        ),
        "laptop_plain": Product.objects.create(
            sku="LAP-PLAIN",
            name="Acer Aspire 3",
            brand="Acer",
            category="laptop",
            price=2199900,
            stock=10,
            specifications={"gpu": "Intel UHD Graphics", "ram_gb": 8},
            warranty_months=12,
            shipping_days=3,
        ),
        "tv": Product.objects.create(
            sku="TV-55",
            name='Samsung 55" DU7000',
            brand="Samsung",
            category="tv",
            price=2399900,
            stock=10,
            specifications={"resolucion": "4K UHD", "pantalla_pulgadas": 55},
            warranty_months=12,
            shipping_days=4,
        ),
        "phone": Product.objects.create(
            sku="PHN-1",
            name="Samsung Galaxy S24",
            brand="Samsung",
            category="phone",
            price=3799900,
            stock=0,
            specifications={"red": "5G", "ram_gb": 8},
            warranty_months=12,
            shipping_days=2,
        ),
    }


@pytest.fixture
def order_factory(db):
    from apps.orders.models import Order

    def _create(customer, product, status="processing", **overrides):
        defaults = {
            "quantity": 1,
            "total": product.price,
            "shipping_address": "Calle 1 # 2-3, Bogotá",
            "tracking_number": "",
        }
        defaults.update(overrides)
        return Order.objects.create(customer=customer, product=product, status=status, **defaults)

    return _create


@pytest.fixture
def fake_llm():
    provider = FakeLLMProvider()
    set_llm_provider(provider)
    yield provider
    reset_llm_provider()


@pytest.fixture
def seeded(db):
    call_command("seed_data")
    return Customer.objects.get(identification="1023456789")
