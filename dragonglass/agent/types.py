from __future__ import annotations

import dataclasses
import typing

JsonValue = str | int | float | bool | list["JsonValue"] | dict[str, "JsonValue"] | None


class _ToolFunction(typing.TypedDict):
    name: str
    description: str
    parameters: dict[str, JsonValue]


class _Tool(typing.TypedDict):  # noqa: PYI049
    type: str
    function: _ToolFunction


class _FunctionCall(typing.TypedDict):
    name: str
    arguments: str


@dataclasses.dataclass
class _FallbackFunction:
    name: str
    arguments: str


@dataclasses.dataclass
class _FallbackToolCall:
    id: str
    function: _FallbackFunction


class _ToolCallMsg(typing.TypedDict):
    id: str
    type: str
    function: _FunctionCall


class _Message(typing.TypedDict, total=False):  # noqa: PYI049
    role: str
    content: str
    tool_calls: list[_ToolCallMsg]
    tool_call_id: str


@dataclasses.dataclass
class StatusEvent:
    message: str


@dataclasses.dataclass
class TextChunk:
    text: str


@dataclasses.dataclass
class DoneEvent:
    pass


@dataclasses.dataclass
class UsageEvent:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    session_total: int


@dataclasses.dataclass
class UserMessageEvent:
    message: str


@dataclasses.dataclass
class MCPToolEvent:
    tool: str
    phase: str
    message: str
    detail: str = ""


@dataclasses.dataclass
class ApprovalRequestEvent:
    request_id: str
    tool: str
    permission: str
    path: str
    diff: str
    description: str


@dataclasses.dataclass
class ConversationsListEvent:
    conversations: list[dict[str, typing.Any]]


@dataclasses.dataclass
class ConversationLoadedEvent:
    id: str
    history: list[AgentEvent]


AgentEvent = (
    StatusEvent
    | TextChunk
    | UsageEvent
    | DoneEvent
    | MCPToolEvent
    | ConversationsListEvent
    | ConversationLoadedEvent
    | UserMessageEvent
    | ApprovalRequestEvent
)
