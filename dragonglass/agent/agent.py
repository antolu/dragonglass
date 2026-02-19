from __future__ import annotations

import json
import typing
from collections.abc import AsyncGenerator
from contextlib import AsyncExitStack
from dataclasses import dataclass

import litellm
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent

from dragonglass.agent.prompts import load_system_prompt
from dragonglass.config import Settings
from dragonglass.mcp.omnisearch import create_omnisearch_server

JsonValue = str | int | float | bool | list["JsonValue"] | dict[str, "JsonValue"] | None


class _ToolFunction(typing.TypedDict):
    name: str
    description: str
    parameters: dict[str, JsonValue]


class _Tool(typing.TypedDict):
    type: str
    function: _ToolFunction


class _FunctionCall(typing.TypedDict):
    name: str
    arguments: str


class _ToolCallMsg(typing.TypedDict):
    id: str
    type: str
    function: _FunctionCall


class _Message(typing.TypedDict, total=False):
    role: str
    content: str
    tool_calls: list[_ToolCallMsg]
    tool_call_id: str


@dataclass
class StatusEvent:
    message: str


@dataclass
class TextChunk:
    text: str


@dataclass
class DoneEvent:
    pass


AgentEvent = StatusEvent | TextChunk | DoneEvent

_TOOL_STATUS: dict[str, str] = {
    "search_vault": "searching vault for",
    "obsidian_global_search": "searching vault for",
    "obsidian_read_note": "reading note",
    "obsidian_update_note": "updating note",
    "obsidian_search_replace": "editing note",
    "obsidian_list_notes": "listing",
    "obsidian_delete_note": "deleting note",
    "obsidian_manage_frontmatter": "updating frontmatter of",
    "obsidian_manage_tags": "updating tags of",
    "fetch": "fetching",
    "sequentialthinking": "thinking",
}

_EXTRA_MCP_SERVERS = [
    StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-sequential-thinking"],
    ),
    StdioServerParameters(
        command="uvx",
        args=["mcp-server-fetch"],
    ),
]


def _status_for_tool(name: str, args: dict[str, JsonValue]) -> str:
    prefix = _TOOL_STATUS.get(name, f"calling {name}")
    detail = (
        args.get("filePath")
        or args.get("dirPath")
        or args.get("query")
        or args.get("url")
        or ""
    )
    if detail:
        return f"{prefix} {detail}"
    return prefix


class VaultAgent:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._history: list[_Message] = []
        self._system_prompt: str | None = None
        self._litellm_tools: list[_Tool] = []
        self._stdio_sessions: list[ClientSession] = []
        self._exit_stack = AsyncExitStack()
        self._omnisearch = create_omnisearch_server(settings)

    async def initialise(self) -> None:
        self._system_prompt = await load_system_prompt(self._settings)
        await self._connect_mcp_servers()

    async def _connect_mcp_servers(self) -> None:
        obsidian_params = StdioServerParameters(
            command="npx",
            args=["obsidian-mcp-server"],
            env={
                "OBSIDIAN_API_KEY": self._settings.obsidian_api_key,
                "OBSIDIAN_BASE_URL": self._settings.obsidian_api_url,
                "OBSIDIAN_VERIFY_SSL": "false",
                "OBSIDIAN_ENABLE_CACHE": "true",
            },
        )
        for params in [obsidian_params, *_EXTRA_MCP_SERVERS]:
            try:
                session = await self._exit_stack.enter_async_context(
                    _StdioSessionContext(params)
                )
                result = await session.list_tools()
                self._stdio_sessions.append(session)
                for tool in result.tools:
                    self._litellm_tools.append(_mcp_tool_to_litellm(tool))
            except Exception:
                pass

        for tool in await self._omnisearch.list_tools():
            self._litellm_tools.append(
                _Tool(
                    type="function",
                    function=_ToolFunction(
                        name=getattr(tool, "name", ""),
                        description=getattr(tool, "description", "") or "",
                        parameters=getattr(tool, "inputSchema", {}),
                    ),
                )
            )

    async def run(self, user_message: str) -> AsyncGenerator[AgentEvent, None]:
        assert self._system_prompt is not None, "call initialise() first"
        self._history.append(_Message(role="user", content=user_message))
        messages: list[_Message] = [
            _Message(role="system", content=self._system_prompt),
            *self._history,
        ]
        gen = self._agent_loop(messages)
        try:
            async for event in gen:
                yield event
        except Exception as exc:
            yield StatusEvent(message=f"Error: {exc}")
            yield DoneEvent()
        finally:
            await gen.aclose()

    async def _agent_loop(
        self, messages: list[_Message]
    ) -> AsyncGenerator[AgentEvent, None]:
        while True:
            kwargs: dict[str, str | bool | list[_Tool] | list[_Message]] = {
                "model": self._settings.llm_model,
                "messages": messages,
                "stream": False,
            }
            if self._litellm_tools:
                kwargs["tools"] = self._litellm_tools
            if self._settings.gemini_api_key:
                kwargs["api_key"] = self._settings.gemini_api_key

            response = await litellm.acompletion(**kwargs)

            choice = response.choices[0]
            msg = choice.message
            tool_calls = getattr(msg, "tool_calls", None)

            assistant_msg = _Message(role="assistant", content=msg.content or "")
            if tool_calls:
                assistant_msg["tool_calls"] = [
                    _ToolCallMsg(
                        id=tc.id,
                        type="function",
                        function=_FunctionCall(
                            name=tc.function.name,
                            arguments=tc.function.arguments,
                        ),
                    )
                    for tc in tool_calls
                ]
            messages.append(assistant_msg)

            if not tool_calls:
                if msg.content:
                    yield TextChunk(text=msg.content)
                    self._history.append(
                        _Message(role="assistant", content=msg.content)
                    )
                yield DoneEvent()
                return

            for tc in tool_calls:
                tool_name = tc.function.name
                try:
                    args: dict[str, JsonValue] = json.loads(
                        tc.function.arguments or "{}"
                    )
                except json.JSONDecodeError:
                    args = {}

                yield StatusEvent(message=_status_for_tool(tool_name, args))
                result = await self._call_tool(tool_name, args)
                messages.append(
                    _Message(role="tool", tool_call_id=tc.id, content=result)
                )

    async def _call_tool(self, name: str, args: dict[str, JsonValue]) -> str:
        if name == "search_vault":
            try:
                omni_result = await self._omnisearch.call_tool(name, args)
                first = omni_result.content[0] if omni_result.content else None
                return first.text if isinstance(first, TextContent) else "[]"
            except Exception as exc:
                return f"Omnisearch error: {exc}"

        for session in self._stdio_sessions:
            try:
                tools = await session.list_tools()
                if any(t.name == name for t in tools.tools):
                    call_result = await session.call_tool(name, args)
                    first = call_result.content[0] if call_result.content else None
                    return first.text if isinstance(first, TextContent) else ""
            except Exception:
                continue

        return f"Tool '{name}' not found"

    async def close(self) -> None:
        await self._exit_stack.aclose()


class _StdioSessionContext:
    def __init__(self, params: StdioServerParameters) -> None:
        self._params = params
        self._inner_stack = AsyncExitStack()

    async def __aenter__(self) -> ClientSession:
        read, write = await self._inner_stack.enter_async_context(
            stdio_client(self._params)
        )
        session = ClientSession(read, write)
        await self._inner_stack.enter_async_context(session)
        await session.initialize()
        return session

    async def __aexit__(self, *args: object) -> None:
        await self._inner_stack.aclose()


def _mcp_tool_to_litellm(tool: object) -> _Tool:
    return _Tool(
        type="function",
        function=_ToolFunction(
            name=getattr(tool, "name", ""),
            description=getattr(tool, "description", "") or "",
            parameters=getattr(tool, "inputSchema", {}),
        ),
    )
