"""Builds the message list sent to the LLM: system prompt + relevant history."""

from __future__ import annotations

from django.conf import settings

from apps.conversations.models import Message

from .policy import build_context_prompt, build_stable_prompt


def build_messages(conversation, memory, profile=None, hints=None) -> list[dict]:
    # The stable policy goes first so it can be cached together with the tool
    # schemas; the volatile context follows in a separate system message.
    messages: list[dict] = [
        {"role": "system", "content": build_stable_prompt()},
        {"role": "system", "content": build_context_prompt(memory, profile, hints)},
    ]

    limit = settings.AGENT_MAX_CONTEXT_MESSAGES
    history = list(
        Message.objects.filter(conversation=conversation)
        .exclude(role=Message.Role.TOOL)
        .exclude(role=Message.Role.SYSTEM)
        .order_by("-created_at")[:limit]
    )
    history.reverse()

    for message in history:
        if message.role == Message.Role.USER:
            messages.append({"role": "user", "content": message.content})
        elif message.role == Message.Role.ASSISTANT and message.content:
            messages.append({"role": "assistant", "content": message.content})
    return messages
