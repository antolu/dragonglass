from __future__ import annotations

from dragonglass._mod_replace import replace_modname
from dragonglass.agent.parsing import parse_tool_calls_from_text
from dragonglass.agent.runtime import VaultAgent, history_to_events, resolve_model_name
from dragonglass.agent.types import (
    AgentEvent,
    ApprovalRequestEvent,
    DoneEvent,
    MCPToolEvent,
    StatusEvent,
    TextChunk,
    ToolPhase,
    UsageEvent,
    UserMessageEvent,
)

for _sym in (  # noqa: RUF067
    VaultAgent,
    history_to_events,
    parse_tool_calls_from_text,
    resolve_model_name,
    ApprovalRequestEvent,
    DoneEvent,
    MCPToolEvent,
    StatusEvent,
    TextChunk,
    ToolPhase,
    UsageEvent,
    UserMessageEvent,
):
    replace_modname(_sym, __name__)

__all__ = [
    "AgentEvent",
    "ApprovalRequestEvent",
    "DoneEvent",
    "MCPToolEvent",
    "StatusEvent",
    "TextChunk",
    "ToolPhase",
    "UsageEvent",
    "UserMessageEvent",
    "VaultAgent",
    "history_to_events",
    "parse_tool_calls_from_text",
    "resolve_model_name",
]
