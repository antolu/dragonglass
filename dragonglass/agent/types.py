from __future__ import annotations

import dataclasses
import typing

from pydantic import JsonValue


class ToolFunction(typing.TypedDict):
    name: str
    description: str
    parameters: dict[str, JsonValue]


class Tool(typing.TypedDict):
    type: str
    function: ToolFunction


class FunctionCall(typing.TypedDict):
    name: str
    arguments: str


@dataclasses.dataclass
class FallbackFunction:
    name: str
    arguments: str


@dataclasses.dataclass
class FallbackToolCall:
    id: str
    function: FallbackFunction


class ToolCallMsg(typing.TypedDict):
    id: str
    type: str
    function: FunctionCall


class Message(typing.TypedDict, total=False):
    role: str
    content: str
    tool_calls: list[ToolCallMsg]
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
