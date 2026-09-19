"""Conceptual classification of a conversational turn.

Kept separate from moderation: an unresolved attempt is not a violation.
"""

from __future__ import annotations


class TurnOutcome:
    RESOLVED = "resolved"
    NEEDS_CLARIFICATION = "needs_clarification"
    TOOL_REQUIRED = "tool_required"
    OUT_OF_SCOPE = "out_of_scope"
    ESCALATE = "escalate"

    ALL = {RESOLVED, NEEDS_CLARIFICATION, TOOL_REQUIRED, OUT_OF_SCOPE, ESCALATE}


def normalize(value: str | None) -> str:
    if value in TurnOutcome.ALL:
        return value
    return TurnOutcome.RESOLVED
