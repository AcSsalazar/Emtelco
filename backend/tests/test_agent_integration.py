import pytest
from django.conf import settings

from apps.agent.llm import factory as llm_factory
from apps.agent.orchestrator import run_agent
from apps.conversations.models import Conversation, Message
from tests.fake_provider import (
    guard_response,
    outcome_response,
    text_response,
    tool_call,
    tool_response,
)

pytestmark = pytest.mark.django_db


def test_create_and_list_conversations(auth_client, customer_a):
    response = auth_client.post("/api/conversations", {}, format="json")
    assert response.status_code == 201

    listing = auth_client.get("/api/conversations")
    assert listing.status_code == 200
    assert listing.data["count"] == 1


def test_messages_require_authentication(api_client, customer_a):
    conversation = Conversation.objects.create(customer=customer_a)
    response = api_client.post(
        f"/api/conversations/{conversation.id}/messages",
        {"content": "hola"},
        format="json",
    )
    assert response.status_code == 401


def test_conversation_isolation(auth_client, customer_b):
    foreign = Conversation.objects.create(customer=customer_b)
    assert auth_client.get(f"/api/conversations/{foreign.id}").status_code == 404
    assert (
        auth_client.post(
            f"/api/conversations/{foreign.id}/messages",
            {"content": "hola"},
            format="json",
        ).status_code
        == 404
    )


def test_chat_flow_request_to_tool_to_database(
    auth_client, customer_a, products, order_factory, fake_llm
):
    order = order_factory(customer_a, products["tv"], status="out_for_delivery")
    conversation = Conversation.objects.create(customer=customer_a)

    fake_llm.queue(
        guard_response(in_scope=True),
        tool_response(tool_call("get_order_status", {"order_id": order.id})),
        text_response("Tu pedido está en reparto y la entrega está prevista para hoy."),
        outcome_response("resolved"),
    )

    response = auth_client.post(
        f"/api/conversations/{conversation.id}/messages",
        {"content": "¿Dónde está mi pedido?"},
        format="json",
    )

    assert response.status_code == 200
    assert "reparto" in response.data["reply"]
    assert conversation.messages.filter(role=Message.Role.USER).count() == 1
    assert conversation.messages.filter(
        role=Message.Role.TOOL, tool_name="get_order_status"
    ).exists()
    assert conversation.messages.filter(role=Message.Role.ASSISTANT).exists()


def test_chat_returns_503_when_provider_not_configured(
    auth_client, customer_a, monkeypatch
):
    llm_factory.reset_llm_provider()
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    conversation = Conversation.objects.create(customer=customer_a)

    response = auth_client.post(
        f"/api/conversations/{conversation.id}/messages",
        {"content": "hola"},
        format="json",
    )
    assert response.status_code == 503


def test_empty_message_rejected(auth_client, customer_a, fake_llm):
    conversation = Conversation.objects.create(customer=customer_a)
    response = auth_client.post(
        f"/api/conversations/{conversation.id}/messages",
        {"content": ""},
        format="json",
    )
    assert response.status_code == 400


def test_system_prompt_is_split_for_caching(customer_a, fake_llm):
    conversation = Conversation.objects.create(customer=customer_a)
    fake_llm.queue(
        guard_response(in_scope=True),
        text_response("ok"),
        outcome_response("resolved"),
    )
    run_agent(conversation, "hola")

    agent_request = fake_llm.requests[1]
    systems = [m for m in agent_request["messages"] if m["role"] == "system"]
    assert len(systems) == 2
    assert "Política del agente" in systems[0]["content"]
    assert "Perfil del cliente" in systems[1]["content"]


def test_assistant_message_includes_product_cards(
    auth_client, customer_a, products, fake_llm
):
    conversation = Conversation.objects.create(customer=customer_a)
    fake_llm.queue(
        guard_response(in_scope=True),
        tool_response(tool_call("search_products", {"category": "laptop"})),
        text_response("Encontré estas opciones para ti."),
        outcome_response("resolved"),
    )

    auth_client.post(
        f"/api/conversations/{conversation.id}/messages",
        {"content": "muéstrame portátiles"},
        format="json",
    )

    assistant = conversation.messages.filter(role=Message.Role.ASSISTANT).last()
    cards = (assistant.metadata or {}).get("products")
    assert cards
    assert {"id", "name", "price", "image_url"} <= set(cards[0])

    detail = auth_client.get(f"/api/conversations/{conversation.id}")
    last_message = detail.data["messages"][-1]
    assert last_message["metadata"]["products"][0]["name"]
