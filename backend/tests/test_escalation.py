import pytest
from django.conf import settings

from apps.agent.memory import get_or_create_memory
from apps.agent.orchestrator import run_agent
from apps.conversations.models import Conversation, ConversationMemory
from apps.support.models import SupportTicket
from tests.fake_provider import guard_response, outcome_response, text_response

pytestmark = pytest.mark.django_db


def make_conversation(customer):
    return Conversation.objects.create(customer=customer)


def fresh_memory(conversation):
    return ConversationMemory.objects.get(conversation=conversation)


def test_three_unresolved_attempts_escalate(customer_a, fake_llm):
    conversation = make_conversation(customer_a)
    threshold = settings.AGENT_UNRESOLVED_ATTEMPTS_THRESHOLD

    for _ in range(threshold):
        fake_llm.queue(
            guard_response(in_scope=True),
            text_response("No pude encontrar la información que necesitas."),
            outcome_response("escalate"),
        )
        result = run_agent(conversation, "necesito ayuda con un caso complejo")

    assert fresh_memory(conversation).unresolved_attempts >= threshold
    assert result.escalated is True
    conversation.refresh_from_db()
    assert conversation.escalated is True
    assert SupportTicket.objects.filter(
        conversation=conversation, source=SupportTicket.Source.ESCALATION
    ).exists()


def test_clarification_does_not_increment(customer_a, fake_llm):
    conversation = make_conversation(customer_a)
    fake_llm.queue(
        guard_response(in_scope=True),
        text_response("¿Puedes indicarme el número del pedido?"),
        outcome_response("needs_clarification"),
    )
    run_agent(conversation, "quiero revisar un pedido")
    assert fresh_memory(conversation).unresolved_attempts == 0


def test_resolved_resets_counter(customer_a, fake_llm):
    conversation = make_conversation(customer_a)
    memory = get_or_create_memory(conversation)
    memory.unresolved_attempts = 2
    memory.save()

    fake_llm.queue(
        guard_response(in_scope=True),
        text_response("Listo, ya quedó todo claro."),
        outcome_response("resolved"),
    )
    run_agent(conversation, "gracias, era eso")
    assert fresh_memory(conversation).unresolved_attempts == 0
