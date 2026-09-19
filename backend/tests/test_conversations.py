import pytest

from apps.conversations.models import Conversation, Message
from apps.conversations.serializers import MESSAGE_LIMIT
from tests.fake_provider import guard_response, outcome_response, text_response

pytestmark = pytest.mark.django_db


def test_conversation_list_includes_message_count(auth_client, customer_a):
    conversation = Conversation.objects.create(customer=customer_a, title="Prueba")
    Message.objects.create(conversation=conversation, role=Message.Role.USER, content="hola")
    Message.objects.create(
        conversation=conversation, role=Message.Role.ASSISTANT, content="hola"
    )

    response = auth_client.get("/api/conversations")
    item = response.data["results"][0]
    assert item["message_count"] == 2


def test_conversation_detail_limits_history(auth_client, customer_a):
    conversation = Conversation.objects.create(customer=customer_a)
    for index in range(MESSAGE_LIMIT + 5):
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER if index % 2 == 0 else Message.Role.ASSISTANT,
            content=f"mensaje {index}",
        )

    response = auth_client.get(f"/api/conversations/{conversation.id}")
    assert response.data["message_count"] == MESSAGE_LIMIT + 5
    assert len(response.data["messages"]) == MESSAGE_LIMIT
    # The most recent message must be present.
    assert response.data["messages"][-1]["content"] == f"mensaje {MESSAGE_LIMIT + 4}"


def test_title_set_from_first_message(auth_client, customer_a, fake_llm):
    created = auth_client.post("/api/conversations", {}, format="json").data
    conversation = Conversation.objects.get(id=created["id"])

    fake_llm.queue(
        guard_response(in_scope=True),
        text_response("Claro, te ayudo."),
        outcome_response("resolved"),
    )
    auth_client.post(
        f"/api/conversations/{conversation.id}/messages",
        {"content": "Necesito un portátil para diseño gráfico"},
        format="json",
    )

    conversation.refresh_from_db()
    assert conversation.title == "Necesito un portátil para diseño gráfico"


def test_retry_regenerates_reply_without_duplicating(auth_client, customer_a, fake_llm):
    conversation = Conversation.objects.create(customer=customer_a)
    Message.objects.create(
        conversation=conversation, role=Message.Role.USER, content="¿Dónde está mi pedido?"
    )

    fake_llm.queue(
        guard_response(in_scope=True),
        text_response("Estoy revisando tu pedido."),
        outcome_response("resolved"),
    )
    response = auth_client.post(
        f"/api/conversations/{conversation.id}/messages",
        {"retry": True},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["reply"] == "Estoy revisando tu pedido."
    assert conversation.messages.filter(role=Message.Role.USER).count() == 1
    assert conversation.messages.filter(role=Message.Role.ASSISTANT).count() == 1


def test_retry_when_already_answered_returns_existing(auth_client, customer_a):
    conversation = Conversation.objects.create(customer=customer_a)
    Message.objects.create(conversation=conversation, role=Message.Role.USER, content="hola")
    Message.objects.create(
        conversation=conversation, role=Message.Role.ASSISTANT, content="ya respondido"
    )

    response = auth_client.post(
        f"/api/conversations/{conversation.id}/messages",
        {"retry": True},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["already_answered"] is True
    assert response.data["reply"] == "ya respondido"
