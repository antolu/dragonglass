from __future__ import annotations

import json
import re
import typing
from collections.abc import AsyncGenerator
from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import Literal

import litellm
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent

from dragonglass.agent.prompts import load_system_prompt
from dragonglass.config import Settings
from dragonglass.mcp.search import create_search_server

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


@dataclass
class UsageEvent:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    session_total: int


AgentEvent = StatusEvent | TextChunk | UsageEvent | DoneEvent

_EVENT_TUPLE_LEN = 2
_COMPLEX_WORD_THRESHOLD = 15
_MAX_TOOL_RESULT_CHARS = 4000


def _truncate_result(text: str) -> str:
    if len(text) <= _MAX_TOOL_RESULT_CHARS:
        return text
    return (
        text[:_MAX_TOOL_RESULT_CHARS]
        + f"\n[truncated — {len(text) - _MAX_TOOL_RESULT_CHARS} chars omitted]"
    )


_TOOL_STATUS: dict[str, str] = {
    "keyword_search": "keyword searching vault",
    "vector_search": "semantic searching vault for",
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
    "open_note": "opening",
    "run_command": "running command",
}


def _fmt_args(args: dict[str, JsonValue]) -> str:
    return ", ".join(f"{k}={json.dumps(v)}" for k, v in args.items())


def _summarize_turn(
    tool_calls_made: list[tuple[str, dict[str, JsonValue], str]],
) -> str:
    if not tool_calls_made:
        return ""
    lines = []
    for name, args, result in tool_calls_made:
        preview = result[:120].replace("\n", " ").strip()
        lines.append(f"- {name}({_fmt_args(args)}) → {preview}")
    return "Actions taken:\n" + "\n".join(lines)


_COMPLEX_SIGNALS = re.compile(
    r"\b(compare|summarize|analyse|analyze|relate|find all|list all|how many|across|between|both)\b",
    re.IGNORECASE,
)


def _is_complex(text: str) -> bool:
    return len(text.split()) > _COMPLEX_WORD_THRESHOLD or bool(
        _COMPLEX_SIGNALS.search(text)
    )


_SEARCH_TOOLS = frozenset({
    "new_search_session",
    "keyword_search",
    "vector_search",
    "open_note",
    "obsidian_read_note",
    "obsidian_list_notes",
    "obsidian_global_search",
    "fetch",
    "sequentialthinking",
})
_EDIT_TOOLS = frozenset({
    "obsidian_update_note",
    "obsidian_search_replace",
    "obsidian_delete_note",
    "obsidian_manage_frontmatter",
    "obsidian_manage_tags",
    "run_command",
})


_THINKING_SERVER = StdioServerParameters(
    command="npx",
    args=["@modelcontextprotocol/server-sequential-thinking"],
)

_EXTRA_MCP_SERVERS = [
    StdioServerParameters(
        command="uvx",
        args=["mcp-server-fetch"],
    ),
]


def _status_for_tool(name: str, args: dict[str, JsonValue]) -> str:
    prefix = _TOOL_STATUS.get(name, "")
    if not prefix:
        return ""
    queries = args.get("queries")
    detail = (
        args.get("filePath")
        or args.get("dirPath")
        or (
            ", ".join(str(q) for q in queries)
            if isinstance(queries, list) and queries
            else None
        )
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
        self._base_tools: list[_Tool] = []
        self._stdio_sessions: list[ClientSession] = []
        self._exit_stack = AsyncExitStack()
        self._search = create_search_server(settings)
        self.agents_note_found: bool = False
        self._total_tokens: int = 0

    async def initialise(self) -> None:
        self._system_prompt, self.agents_note_found = await load_system_prompt(
            self._settings
        )
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
                    lt_tool = _mcp_tool_to_litellm(tool)
                    self._litellm_tools.append(lt_tool)
                    self._base_tools.append(lt_tool)
            except Exception:
                pass

        try:
            think_session = await self._exit_stack.enter_async_context(
                _StdioSessionContext(_THINKING_SERVER)
            )
            result = await think_session.list_tools()
            self._stdio_sessions.append(think_session)
            for tool in result.tools:
                self._litellm_tools.append(_mcp_tool_to_litellm(tool))
        except Exception:
            pass

        for tool in await self._search.list_tools():
            lt_tool = _Tool(
                type="function",
                function=_ToolFunction(
                    name=getattr(tool, "name", ""),
                    description=getattr(tool, "description", "") or "",
                    parameters=getattr(tool, "inputSchema", {}),
                ),
            )
            self._litellm_tools.append(lt_tool)
            self._base_tools.append(lt_tool)

    async def run(self, user_message: str) -> AsyncGenerator[AgentEvent]:
        assert self._system_prompt is not None, "call initialise() first"
        self._history.append(_Message(role="user", content=user_message))
        messages: list[_Message] = [
            _Message(role="system", content=self._system_prompt),
            *self._history,
        ]
        is_complex = _is_complex(user_message)
        gen = self._agent_loop(messages, use_full_tools=is_complex)
        summary = ""
        final_answer = ""
        try:
            async for event in gen:
                if isinstance(event, tuple) and len(event) == _EVENT_TUPLE_LEN:
                    summary, final_answer = event
                    continue
                yield typing.cast(AgentEvent, event)
        except Exception as exc:
            yield StatusEvent(message=f"Error: {exc}")
            yield DoneEvent()
        finally:
            await gen.aclose()

        if summary:
            # We compress: [summary of tools] followed by [final answer]
            # to replace the whole chain in history.
            self._history.append(_Message(role="assistant", content=summary))
        if final_answer:
            self._history.append(_Message(role="assistant", content=final_answer))

    async def _agent_loop(  # noqa: PLR0914
        self, messages: list[_Message], use_full_tools: bool = True
    ) -> AsyncGenerator[AgentEvent | tuple[str, str]]:
        phase: Literal["search", "edit"] = "search"
        tool_log: list[tuple[str, dict[str, JsonValue], str]] = []

        while True:
            kwargs: dict[str, typing.Any] = {
                "model": self._settings.llm_model,
                "messages": messages,
                "stream": False,
            }
            raw_tools = self._litellm_tools if use_full_tools else self._base_tools
            # Filter tools by phase
            allowed = _SEARCH_TOOLS if phase == "search" else _EDIT_TOOLS
            tools = [t for t in raw_tools if t["function"]["name"] in allowed]

            if tools:
                kwargs["tools"] = tools

            response = await litellm.acompletion(**kwargs)

            usage = getattr(response, "usage", None)
            if usage:
                usage_info = {
                    "pt": getattr(usage, "prompt_tokens", 0),
                    "ct": getattr(usage, "completion_tokens", 0),
                    "tt": getattr(usage, "total_tokens", 0),
                }
                self._total_tokens += usage_info["tt"]
                yield UsageEvent(
                    prompt_tokens=usage_info["pt"],
                    completion_tokens=usage_info["ct"],
                    total_tokens=usage_info["tt"],
                    session_total=self._total_tokens,
                )

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
                yield DoneEvent()
                yield _summarize_turn(tool_log), msg.content or ""
                return

            for tc in tool_calls:
                tool_name = tc.function.name
                try:
                    args: dict[str, JsonValue] = json.loads(
                        tc.function.arguments or "{}"
                    )
                except json.JSONDecodeError:
                    args = {}

                status = _status_for_tool(tool_name, args)
                if status:
                    yield StatusEvent(message=status)

                if tool_name in _EDIT_TOOLS:
                    phase = "edit"

                result = await self._call_tool(tool_name, args)
                tool_log.append((tool_name, args, result))

                messages.append(
                    _Message(role="tool", tool_call_id=tc.id, content=result)
                )

    async def _call_tool(self, name: str, args: dict[str, JsonValue]) -> str:
        search_tools = {
            "new_search_session",
            "keyword_search",
            "vector_search",
            "open_note",
            "run_command",
        }
        if name in search_tools:
            try:
                result = await self._search.call_tool(name, args)
                first = result.content[0] if result.content else None
                text = first.text if isinstance(first, TextContent) else "[]"
                return _truncate_result(text)
            except Exception as exc:
                return f"Search server error: {exc}"

        for session in self._stdio_sessions:
            try:
                tools = await session.list_tools()
                if any(t.name == name for t in tools.tools):
                    call_result = await session.call_tool(name, args)
                    first = call_result.content[0] if call_result.content else None
                    text = first.text if isinstance(first, TextContent) else ""
                    return _truncate_result(text)
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
