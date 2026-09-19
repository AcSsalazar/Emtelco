from io import StringIO

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.accounts.models import Customer, CustomerModeration, CustomerProfile
from apps.catalog.models import Product
from apps.conversations.models import Conversation, ConversationMemory, Message
from apps.orders.models import Order, Warranty
from apps.support.models import SupportTicket

pytestmark = pytest.mark.django_db


def test_admin_registers_key_models():
    models = [
        Customer,
        CustomerProfile,
        CustomerModeration,
        Product,
        Order,
        Warranty,
        Conversation,
        Message,
        ConversationMemory,
        SupportTicket,
    ]
    for model in models:
        assert admin.site.is_registered(model), f"{model.__name__} no está en el admin"


def test_admin_pages_load_with_superuser(client, seeded):
    User = get_user_model()
    superuser = User.objects.create_superuser(
        username="admin@test.com", email="admin@test.com", password="Secret12345"
    )
    client.force_login(superuser)

    paths = [
        "/admin/",
        "/admin/accounts/customer/",
        "/admin/catalog/product/",
        "/admin/orders/order/",
        "/admin/orders/warranty/",
        "/admin/support/supportticket/",
        "/admin/conversations/conversation/",
        "/admin/conversations/message/",
    ]
    for path in paths:
        assert client.get(path).status_code == 200, path


def test_verify_scenario3_persists(seeded):
    output = StringIO()
    call_command("verify_scenario3", stdout=output)
    text = output.getvalue()

    assert "check_warranty" in text
    assert "create_warranty_request" in text
    assert "escalate_conversation" in text

    warranty_ticket = SupportTicket.objects.filter(
        source=SupportTicket.Source.WARRANTY
    ).first()
    assert warranty_ticket is not None
    assert warranty_ticket.number.startswith("TCK-")
    assert warranty_ticket.warranty is not None
    assert warranty_ticket.conversation_id is not None

    conversation = Conversation.objects.filter(customer=seeded).first()
    assert conversation is not None
    assert conversation.escalated is True
    assert SupportTicket.objects.filter(
        source=SupportTicket.Source.ESCALATION, conversation=conversation
    ).exists()


def test_verify_scenario3_cleanup_removes_data(seeded):
    call_command("verify_scenario3", "--cleanup", stdout=StringIO())
    assert not SupportTicket.objects.filter(source=SupportTicket.Source.WARRANTY).exists()
    assert not Conversation.objects.filter(customer=seeded, escalated=True).exists()
