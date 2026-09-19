"""Deterministic LLM provider used in tests.

It returns pre-scripted responses in order, so tests never hit the real
provider, and records the requests it received for assertions.
"""

from __future__ import annotations

import json

from apps.agent.llm.base import LLMProvider, LLMResponse, ToolCall


class FakeLLMProvider(LLMProvider):
    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.requests: list[dict] = []

    def queue(self, *responses) -> "FakeLLMProvider":
        self.responses.extend(responses)
        return self

    def chat(self, messages, tools=None):
        self.requests.append({"messages": messages, "tools": tools})
        if not self.responses:
            raise AssertionError("FakeLLMProvider ran out of scripted responses")
        item = self.responses.pop(0)
        if callable(item):
            return item(messages, tools)
        return item


def guard_response(
    in_scope=True,
    violation=False,
    severity="none",
    category="ok",
    intent="consulta",
    preferences=None,
    profile=None,
):
    return LLMResponse(
        content=json.dumps(
            {
                "in_scope": in_scope,
                "violation": violation,
                "severity": severity,
                "category": category,
                "intent": intent,
                "preferences": preferences or [],
                "profile": profile or {},
            }
        )
    )


def outcome_response(outcome):
    return LLMResponse(content=json.dumps({"outcome": outcome}))


def text_response(content):
    return LLMResponse(content=content)


def tool_call(name, arguments=None, call_id="call-1"):
    return ToolCall(id=call_id, name=name, arguments=arguments or {})


def tool_response(*calls):
    return LLMResponse(content="", tool_calls=list(calls))
