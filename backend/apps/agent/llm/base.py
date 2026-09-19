"""Provider-agnostic LLM interface.

The rest of the agent only depends on the types and the ``LLMProvider``
contract defined here, so swapping OpenAI for another vendor later does not
touch tools, memory, business models or the API layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"
    usage: dict[str, Any] | None = None


# Internal, provider-neutral message format.
#   {"role": "system", "content": str}
#   {"role": "user", "content": str}
#   {"role": "assistant", "content": str, "tool_calls": [ToolCall]}
#   {"role": "tool", "tool_call_id": str, "name": str, "content": str}
Message = dict[str, Any]


class LLMProviderError(Exception):
    """Raised when the provider cannot fulfil a request."""


class LLMProvider(ABC):
    @abstractmethod
    def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        """Return the model response for the given conversation."""
