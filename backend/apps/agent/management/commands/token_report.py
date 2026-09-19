"""Report token usage of the agent prompt using the real tokenizer.

Usage:
    python manage.py token_report
    python manage.py token_report --conversation 12
    python manage.py token_report --history 6
"""

from __future__ import annotations

import json

import tiktoken
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.agent.guard import _CLASSIFIER_PROMPT
from apps.agent.orchestrator import _OUTCOME_PROMPT
from apps.agent.policy import build_context_prompt, build_stable_prompt
from apps.agent.tools import registry
from apps.agent.tools.catalog_tools import _brief, _card
from apps.agent.tools.registry import get_tool_schemas
from apps.catalog.models import Product
from apps.conversations.models import Conversation, Message

MESSAGE_OVERHEAD = 4  # approximate per-message role/format overhead


def _encoding():
    try:
        return tiktoken.encoding_for_model(settings.OPENAI_MODEL)
    except Exception:  # noqa: BLE001 - fall back to the current OpenAI encoding
        return tiktoken.get_encoding("o200k_base")


class Command(BaseCommand):
    help = "Report token usage of the agent prompt (real tokenizer)."

    def add_arguments(self, parser):
        parser.add_argument("--conversation", type=int, help="Conversation id to measure.")
        parser.add_argument(
            "--history",
            type=int,
            default=10,
            help="Number of history messages to simulate (default 10).",
        )

    def handle(self, *args, **options):
        self.enc = _encoding()
        registry._load_tools()

        policy = self.count(build_stable_prompt())
        tools = self.count(json.dumps(get_tool_schemas(), ensure_ascii=False))
        classifier = self.count(_CLASSIFIER_PROMPT)
        outcome = self.count(_OUTCOME_PROMPT)

        self.stdout.write(self.style.MIGRATE_HEADING("Componentes estáticos"))
        self.stdout.write(f"  Política (system estable): {policy} tokens")
        self.stdout.write(f"  Esquemas de {len(get_tool_schemas())} tools: {tools} tokens")
        self.stdout.write(f"  Prompt del Guard: {classifier} tokens")
        self.stdout.write(f"  Prompt de resultado: {outcome} tokens")
        self.stdout.write(
            self.style.SUCCESS(f"  Prefijo cacheable (tools+política): {tools + policy} tokens")
        )

        avg_message, avg_tool = self._averages()
        self.stdout.write("\n" + self.style.MIGRATE_HEADING("Promedios medidos en BD"))
        self.stdout.write(f"  Mensaje (user/assistant): {avg_message} tokens")
        self.stdout.write(f"  Resultado de tool: {avg_tool} tokens")

        self._tool_payload_savings()
        self._simulate(policy, tools, classifier, outcome, avg_message, avg_tool, options)

    # -- helpers ---------------------------------------------------------
    def count(self, text: str) -> int:
        return len(self.enc.encode(text))

    def _averages(self) -> tuple[int, int]:
        messages = [m.content for m in Message.objects.exclude(role=Message.Role.TOOL)]
        tools = [m.content for m in Message.objects.filter(role=Message.Role.TOOL)]
        avg_message = (
            round(sum(self.count(m) for m in messages) / len(messages))
            if messages
            else 70
        )
        avg_tool = (
            round(sum(self.count(t) for t in tools) / len(tools)) if tools else 660
        )
        return avg_message, avg_tool

    def _tool_payload_savings(self) -> None:
        products = list(Product.objects.filter(active=True, category="laptop")[:5])
        if not products:
            return
        full = self.count(json.dumps([_brief(p) for p in products], ensure_ascii=False, default=str))
        compact = self.count(
            json.dumps([_card(p) for p in products], ensure_ascii=False, default=str)
        )
        pct = round((1 - compact / full) * 100) if full else 0
        self.stdout.write("\n" + self.style.MIGRATE_HEADING("Tarjetas de producto (5 portátiles)"))
        self.stdout.write(f"  Antes (ficha completa): {full} tokens")
        self.stdout.write(f"  Ahora (compacta):       {compact} tokens")
        self.stdout.write(self.style.SUCCESS(f"  Ahorro: {pct}%"))

    def _simulate(self, policy, tools, classifier, outcome, avg_message, avg_tool, options):
        history_n = options["history"]
        history = avg_message * history_n

        guard = classifier + history + avg_message
        agent_base = policy + tools + history + avg_message + 120  # + profile/memory
        agent_with_tool = agent_base + avg_tool + 120  # + tool result and tool_calls
        outcome_call = outcome + avg_message + 250 + 20

        no_tool = guard + agent_base + outcome_call
        one_tool = guard + agent_base + agent_with_tool + outcome_call
        two_tools = guard + agent_base + (agent_with_tool + avg_tool + 40) + outcome_call

        self.stdout.write("\n" + self.style.MIGRATE_HEADING(
            f"Turno simulado (historial de {history_n} mensajes)"
        ))
        self.stdout.write(f"  Guard:            {guard} tokens")
        self.stdout.write(f"  Agente (1.ª vez): {agent_base} tokens")
        self.stdout.write(f"  Resultado:        {outcome_call} tokens")
        self.stdout.write(f"  -- Sin tools:       {no_tool} tokens de entrada")
        self.stdout.write(f"  -- Con 1 tool:      {one_tool} tokens de entrada")
        self.stdout.write(f"  -- Con 2 tools:     {two_tools} tokens de entrada")

        conversation_id = options.get("conversation")
        if conversation_id:
            self._measure_real(conversation_id)

    def _measure_real(self, conversation_id: int) -> None:
        conversation = (
            Conversation.objects.filter(id=conversation_id)
            .select_related("customer")
            .first()
        )
        if conversation is None:
            self.stderr.write(f"No existe la conversación {conversation_id}.")
            return
        from apps.agent.memory import get_or_create_memory
        from apps.agent.profile import get_or_create_profile
        from apps.agent.context_builder import build_messages

        memory = get_or_create_memory(conversation)
        profile = get_or_create_profile(conversation.customer)
        messages = build_messages(conversation, memory, profile)
        total = sum(
            self.count(m.get("content") or "") + MESSAGE_OVERHEAD for m in messages
        )
        self.stdout.write(
            "\n" + self.style.MIGRATE_HEADING(f"Conversación real #{conversation_id}")
        )
        self.stdout.write(f"  Mensajes en el prompt: {len(messages)}")
        self.stdout.write(f"  Tokens (sin tools): {total}")
        self.stdout.write(f"  Tokens con tools:   {total + self.count(json.dumps(get_tool_schemas(), ensure_ascii=False))}")
