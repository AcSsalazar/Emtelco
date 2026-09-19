"""OpenAI implementation of the LLM provider contract."""

from __future__ import annotations

import json
import logging
from typing import Any

from django.conf import settings
from openai import OpenAI, OpenAIError

from .base import LLMProvider, LLMProviderError, LLMResponse, Message, ToolCall

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_MODEL
        if not self.api_key:
            raise LLMProviderError(
                "El servicio de lenguaje no está configurado (falta OPENAI_API_KEY)."
            )
        self._client = OpenAI(api_key=self.api_key)

    def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        payload = [self._to_openai_message(message) for message in messages]
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": payload,
            "temperature": 0.3,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            completion = self._client.chat.completions.create(**kwargs)
        except OpenAIError as exc:
            logger.error("OpenAI request failed: %s", exc, exc_info=True)
            raise LLMProviderError(
                "El proveedor de lenguaje no está disponible en este momento."
            ) from exc

        choice = completion.choices[0]
        message = choice.message
        tool_calls = []
        for call in message.tool_calls or []:
            try:
                arguments = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                logger.warning("Invalid tool arguments for %s", call.function.name)
                arguments = {}
            tool_calls.append(
                ToolCall(id=call.id, name=call.function.name, arguments=arguments)
            )

        usage = self._usage(completion)
        if usage:
            logger.info(
                "LLM usage: prompt=%s cached=%s completion=%s",
                usage["prompt_tokens"],
                usage["cached_tokens"],
                usage["completion_tokens"],
            )

        return LLMResponse(
            content=message.content or "",
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
            usage=usage,
        )

    @staticmethod
    def _usage(completion) -> dict[str, Any] | None:
        usage = getattr(completion, "usage", None)
        if usage is None:
            return None
        details = getattr(usage, "prompt_tokens_details", None)
        return {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "cached_tokens": getattr(details, "cached_tokens", 0) if details else 0,
        }

    @staticmethod
    def _to_openai_message(message: Message) -> dict[str, Any]:
        role = message["role"]
        tool_calls = message.get("tool_calls")
        if role == "assistant" and tool_calls:
            return {
                "role": "assistant",
                "content": message.get("content") or None,
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.name,
                            "arguments": json.dumps(call.arguments, ensure_ascii=False),
                        },
                    }
                    for call in tool_calls
                ],
            }
        if role == "tool":
            return {
                "role": "tool",
                "tool_call_id": message["tool_call_id"],
                "content": message.get("content", ""),
            }
        return {"role": role, "content": message.get("content", "")}
