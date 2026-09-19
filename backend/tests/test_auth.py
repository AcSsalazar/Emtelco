import pytest
from rest_framework import status

from apps.accounts.models import Customer

pytestmark = pytest.mark.django_db

REGISTER_URL = "/api/auth/register"
LOGIN_URL = "/api/auth/login"


def payload(**overrides):
    data = {
        "identification": "1234567890",
        "full_name": "Juan Pérez",
        "phone": "3101234567",
        "email": "juan@example.com",
        "password": "Secret12345",
    }
    data.update(overrides)
    return data


def test_register_valid(api_client):
    response = api_client.post(REGISTER_URL, payload(), format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert "access" in response.data and "refresh" in response.data
    assert response.data["user"]["customer"]["identification"] == "1234567890"


@pytest.mark.parametrize("identification", ["123", "123456789012", "abc12345", ""])
def test_register_invalid_identification(api_client, identification):
    response = api_client.post(
        REGISTER_URL, payload(identification=identification), format="json"
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_register_duplicate_identification(create_customer, api_client):
    create_customer(identification="1234567890", email="first@example.com")
    response = api_client.post(
        REGISTER_URL, payload(email="second@example.com"), format="json"
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "identification" in response.data


@pytest.mark.parametrize("phone", ["2101234567", "31012345", "31012345678", "310123456a"])
def test_register_invalid_phone(api_client, phone):
    response = api_client.post(REGISTER_URL, payload(phone=phone), format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_register_invalid_name(api_client):
    response = api_client.post(
        REGISTER_URL, payload(full_name="Juan 123"), format="json"
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_register_invalid_email(api_client):
    response = api_client.post(
        REGISTER_URL, payload(email="not-an-email"), format="json"
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_register_claims_existing_customer_without_user(seeded, api_client):
    response = api_client.post(
        REGISTER_URL,
        payload(
            identification="1122334455",
            full_name="Carlos Andrés Pérez",
            phone="3159876543",
            email="carlos.perez@example.com",
        ),
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    customer = Customer.objects.get(identification="1122334455")
    assert customer.user is not None
    # Orders from the seeded profile are preserved.
    assert customer.orders.exists()


def test_register_existing_identification_with_user_rejected(seeded, api_client):
    response = api_client.post(
        REGISTER_URL,
        payload(identification="1023456789", email="other@example.com"),
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_login_correct(create_customer, api_client):
    create_customer(email="login@example.com", password="Secret12345")
    response = api_client.post(
        LOGIN_URL,
        {"email": "login@example.com", "password": "Secret12345"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data and "refresh" in response.data


def test_login_incorrect(create_customer, api_client):
    create_customer(email="login@example.com", password="Secret12345")
    response = api_client.post(
        LOGIN_URL,
        {"email": "login@example.com", "password": "wrong-password"},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_login_with_identification(create_customer, api_client):
    create_customer(
        identification="1023456789",
        email="frecuente@example.com",
        password="Secret12345",
    )
    response = api_client.post(
        LOGIN_URL,
        {"identifier": "1023456789", "password": "Secret12345"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data


def test_login_with_unknown_identification(api_client):
    response = api_client.post(
        LOGIN_URL,
        {"identifier": "9999999999", "password": "Secret12345"},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_protected_endpoint_without_jwt(api_client):
    response = api_client.get("/api/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_me_endpoint_returns_customer(auth_client, customer_a):
    response = auth_client.get("/api/auth/me")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["customer"]["identification"] == customer_a.identification
