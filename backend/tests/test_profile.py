import pytest

from apps.accounts.models import CustomerProfile
from apps.agent.orchestrator import run_agent
from apps.agent.tools.registry import ToolContext, execute_tool
from apps.conversations.models import Conversation
from tests.fake_provider import guard_response, outcome_response, text_response

pytestmark = pytest.mark.django_db


def ctx(customer):
    return ToolContext(customer=customer, conversation=None)


def test_save_customer_preference_tool(customer_a):
    result = execute_tool(
        "save_customer_preference",
        {"use_cases": ["edición de video"], "software": ["DaVinci Resolve"]},
        ctx(customer_a),
    )
    assert result["saved"] is True
    profile = CustomerProfile.objects.get(customer=customer_a)
    assert "edición de video" in profile.use_cases
    assert "DaVinci Resolve" in profile.software


def test_save_customer_preference_dedupes(customer_a):
    for _ in range(2):
        execute_tool(
            "save_customer_preference",
            {"preferred_brands": ["Apple"]},
            ctx(customer_a),
        )
    profile = CustomerProfile.objects.get(customer=customer_a)
    assert profile.preferred_brands == ["Apple"]


def test_save_customer_preference_requires_data(customer_a):
    result = execute_tool("save_customer_preference", {}, ctx(customer_a))
    assert "error" in result


def test_guard_profile_updates_are_merged(customer_a, fake_llm):
    conversation = Conversation.objects.create(customer=customer_a)
    fake_llm.queue(
        guard_response(
            in_scope=True,
            profile={"use_cases": ["gaming"], "os_preference": "windows"},
        ),
        text_response("Claro, te ayudo con eso."),
        outcome_response("resolved"),
    )
    run_agent(conversation, "Quiero un portátil para gaming, uso Windows")

    profile = CustomerProfile.objects.get(customer=customer_a)
    assert "gaming" in profile.use_cases
    assert profile.os_preference == "windows"


def test_profile_persists_across_conversations(customer_a):
    execute_tool(
        "save_customer_preference",
        {"software": ["Illustrator"], "experience_level": "intermediate"},
        ctx(customer_a),
    )
    other_conversation = Conversation.objects.create(customer=customer_a)
    profile = CustomerProfile.objects.get(customer=customer_a)
    assert "Illustrator" in profile.software
    assert other_conversation.customer_id == customer_a.id


def test_profile_endpoint_get_and_patch(auth_client, customer_a):
    response = auth_client.get("/api/profile")
    assert response.status_code == 200
    assert response.data["use_cases"] == []

    patched = auth_client.patch(
        "/api/profile",
        {"use_cases": ["diseño gráfico"], "budget_max": "5000000"},
        format="json",
    )
    assert patched.status_code == 200
    assert patched.data["use_cases"] == ["diseño gráfico"]
    assert float(patched.data["budget_max"]) == 5000000


def test_profile_isolation(auth_client, other_client, customer_a, customer_b):
    other_client.patch(
        "/api/profile", {"software": ["DaVinci Resolve"]}, format="json"
    )
    profile_a = auth_client.get("/api/profile").data
    assert profile_a["software"] == []

    profile_b = other_client.get("/api/profile").data
    assert profile_b["software"] == ["DaVinci Resolve"]


def test_profile_endpoint_requires_auth(api_client):
    assert api_client.get("/api/profile").status_code == 401


def test_agent_output_backstop(customer_a, fake_llm):
    conversation = Conversation.objects.create(customer=customer_a)
    fake_llm.queue(
        guard_response(in_scope=True),
        text_response("Eso es una mierda de producto."),
        outcome_response("resolved"),
    )
    result = run_agent(conversation, "dime algo")
    assert "lenguaje respetuoso" in result.reply
