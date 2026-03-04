from __future__ import annotations

import collections.abc
import contextlib
import dataclasses
import json
import logging
import os
import re
import typing

import litellm
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent

from dragonglass.agent.prompts import load_system_prompt
from dragonglass.config import Settings, get_settings
from dragonglass.mcp.search import create_search_server

logger = logging.getLogger(__name__)

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


@dataclasses.dataclass
class StatusEvent:
    message: str


@dataclasses.dataclass
class ToolErrorEvent:
    tool: str
    error: str


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
class FileAccessEvent:
    path: str
    operation: str  # "read" | "write" | "delete"


@dataclasses.dataclass
class UserMessageEvent:
    message: str


@dataclasses.dataclass
class ConversationsListEvent:
    conversations: list[dict[str, typing.Any]]


@dataclasses.dataclass
class ConversationLoadedEvent:
    id: str
    history: list[AgentEvent]


AgentEvent = (
    StatusEvent
    | ToolErrorEvent
    | TextChunk
    | UsageEvent
    | DoneEvent
    | FileAccessEvent
    | ConversationsListEvent
    | ConversationLoadedEvent
    | UserMessageEvent
)


def history_to_events(history: list[_Message]) -> list[AgentEvent]:
    events: list[AgentEvent] = []
    for msg in history:
        role = msg.get("role")
        content = str(msg.get("content") or "")
        if role == "user":
            events.append(UserMessageEvent(message=content))
        elif role == "assistant" and content:
            events.append(TextChunk(text=content))
        # Tool messages and tool_calls are currently omitted from UI history
        # as they are intermediate steps.
    return events


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


def _is_error_result(result: str) -> bool:
    if result.startswith(("Search server error:", "Tool '")):
        return True
    try:
        data = json.loads(result)
        return isinstance(data, dict) and "error" in data
    except json.JSONDecodeError:
        return False


_TOOL_STATUS: dict[str, str] = {
    "fetch": "fetching",
    "sequentialthinking": "thinking",
    "open_note": "opening",
    "run_command": "running command",
}


def _fmt_args(args: dict[str, JsonValue]) -> str:
    return ", ".join(f"{k}={json.dumps(v)}" for k, v in args.items())


def _extract_tool_errors(msg: str) -> str | None:
    """Extract descriptive error messages from FastMCP/Pydantic validation errors."""
    lines = msg.splitlines()
    for i, line in enumerate(lines):
        lowered = line.lower()
        # 1. Handle "missing required argument: 'path'" (same line)
        # 2. "['path'] argument is required" (same line)
        rx_same_line = re.compile(
            r"(?:missing|required) (?:argument|parameter)[:\s]+['\"]?([a-zA-Z0-9_]+)['\"]?|"
            r"['\"]?([a-zA-Z0-9_]+)['\"]? (?:argument|parameter)?\s*(?:is|missing) required",
            re.IGNORECASE,
        )
        matches = [m for group in rx_same_line.findall(line) for m in group if m]
        if matches:
            return f"Missing required parameter(s): {', '.join(matches)}"

        # 3. Handle Pydantic multi-line errors:
        # queries
        #   Input should be a valid list [type=list_type, input_value='...', input_type=str]
        if (
            any(
                kw in lowered
                for kw in ("input should be", "missing required", "field required")
            )
            and i > 0
            and (param := lines[i - 1].strip())
            and " " not in param
            and not param.endswith("]")
        ):
            if "missing" in lowered or ("required" in lowered and "field" in lowered):
                return f"Missing required parameter: '{param}'"
            return f"Parameter '{param}' is invalid: {line.strip()}"

    return None


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


def resolve_model_name(model_override: str | None, default_model: str) -> str:
    if model_override is None:
        return default_model

    override = model_override.strip()
    if not override:
        return default_model
    if "/" in override:
        return override

    if "/" in default_model:
        provider, _ = default_model.split("/", 1)
        return f"{provider}/{override}"
    return override


_SEARCH_TOOLS = frozenset({
    "new_search_session",
    "keyword_search",
    "vector_search",
    "open_note",
    "obsidian_list_notes",
    "obsidian_global_search",
    "read_note_with_hash",
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
    "read_note_with_hash",
    "patch_note_lines",
})

_FILE_READ_TOOLS = frozenset({
    "obsidian_list_notes",
    "obsidian_global_search",
    "read_note_with_hash",
})
_FILE_WRITE_TOOLS = frozenset({
    "obsidian_update_note",
    "obsidian_search_replace",
    "obsidian_manage_frontmatter",
    "obsidian_manage_tags",
    "patch_note_lines",
})
_FILE_DELETE_TOOLS = frozenset({"obsidian_delete_note"})


def _get_mcp_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    if extra:
        env.update(extra)

    # Augment PATH to include common locations for npx, uvx, etc.
    paths = env.get("PATH", "").split(os.pathsep)
    new_paths = [
        "/usr/local/bin",
        "/opt/homebrew/bin",
        "/opt/homebrew/sbin",
        os.path.expanduser("~/.local/bin"),
    ]
    # Add existing paths, avoiding duplicates
    for p in paths:
        if p and p not in new_paths:
            new_paths.append(p)

    env["PATH"] = os.pathsep.join(new_paths)
    return env


_THINKING_SERVER = StdioServerParameters(
    command="npx",
    args=["@modelcontextprotocol/server-sequential-thinking"],
    env=_get_mcp_env(),
)

_EXTRA_MCP_SERVERS = [
    StdioServerParameters(
        command="uvx",
        args=["mcp-server-fetch"],
        env=_get_mcp_env(),
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
        or args.get("path")
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
        self._exit_stack = contextlib.AsyncExitStack()
        self._search = create_search_server(get_settings())
        self.agents_note_found: bool = False
        self._total_tokens: int = 0

    async def initialise(self) -> None:
        self._system_prompt, self.agents_note_found = await load_system_prompt(
            get_settings()
        )
        await self._connect_mcp_servers()

    def clear_history(self) -> None:
        self._history = []
        self._total_tokens = 0

    def get_history(self) -> list[_Message]:
        return list(self._history)

    def set_history(self, history: list[_Message]) -> None:
        self._history = list(history)
        # We don't necessarily know the total tokens from loaded history,
        # but we can reset or approximate if we had it. For now just reset.
        self._total_tokens = 0

    async def _connect_mcp_servers(self) -> None:
        settings = get_settings()
        obsidian_params = StdioServerParameters(
            command="npx",
            args=["obsidian-mcp-server"],
            env=_get_mcp_env({
                "OBSIDIAN_API_KEY": settings.obsidian_api_key,
                "OBSIDIAN_BASE_URL": settings.obsidian_api_url,
                "OBSIDIAN_VERIFY_SSL": "false",
                "OBSIDIAN_ENABLE_CACHE": "true",
            }),
        )
        for params in [obsidian_params, *_EXTRA_MCP_SERVERS]:
            try:
                session = await self._exit_stack.enter_async_context(
                    _StdioSessionContext(params)
                )
                result = await session.list_tools()
                self._stdio_sessions.append(session)
                for tool in result.tools:
                    if tool.name == "obsidian_read_note":
                        continue
                    lt_tool = _mcp_tool_to_litellm(tool)
                    self._litellm_tools.append(lt_tool)
                    self._base_tools.append(lt_tool)
            except Exception:
                logger.warning(
                    "failed to connect MCP server %s %s",
                    params.command,
                    params.args,
                    exc_info=True,
                )

        try:
            think_session = await self._exit_stack.enter_async_context(
                _StdioSessionContext(_THINKING_SERVER)
            )
            result = await think_session.list_tools()
            self._stdio_sessions.append(think_session)
            for tool in result.tools:
                self._litellm_tools.append(_mcp_tool_to_litellm(tool))
        except Exception:
            logger.warning("failed to connect thinking MCP server", exc_info=True)

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

    async def run(
        self, user_message: str, model_override: str | None = None
    ) -> collections.abc.AsyncGenerator[AgentEvent]:
        assert self._system_prompt is not None, "call initialise() first"
        history_len_before = len(self._history)
        self._history.append(_Message(role="user", content=user_message))
        messages: list[_Message] = [
            _Message(role="system", content=self._system_prompt),
            *self._history,
        ]
        is_complex = _is_complex(user_message)
        gen = self._agent_loop(
            messages, use_full_tools=is_complex, model_override=model_override
        )
        try:
            async for event in gen:
                yield typing.cast(AgentEvent, event)
        except Exception as exc:
            logger.exception("agent loop error")
            yield StatusEvent(message=f"Error: {exc}")
            yield DoneEvent()
        except BaseException:
            del self._history[history_len_before:]
            raise
        finally:
            await gen.aclose()

        new_messages = messages[1 + history_len_before :]
        self._history.extend(new_messages)

    async def _agent_loop(  # noqa: PLR0912, PLR0914, PLR0915
        self,
        messages: list[_Message],
        use_full_tools: bool = True,
        model_override: str | None = None,
    ) -> collections.abc.AsyncGenerator[AgentEvent]:
        seen_calls: dict[tuple[str, str], str] = {}
        max_iterations = 20
        iterations = 0

        while iterations < max_iterations:
            iterations += 1
            settings = get_settings()
            litellm.drop_params = True
            model_name = resolve_model_name(model_override, settings.llm_model)
            kwargs: dict[str, typing.Any] = {
                "model": model_name,
                "messages": messages,
                "stream": False,
                "temperature": settings.llm_temperature,
                "top_p": settings.llm_top_p,
                "top_k": settings.llm_top_k,
                "topK": settings.llm_top_k,  # Gemini mapping
                "min_p": settings.llm_min_p,
                "presence_penalty": settings.llm_presence_penalty,
                "repetition_penalty": settings.llm_repetition_penalty,
                "api_base": settings.ollama_url,
            }
            raw_tools = self._litellm_tools if use_full_tools else self._base_tools
            tools = raw_tools

            if tools:
                kwargs["tools"] = tools

            logger.debug(
                "LLM request  model=%s  tools=%s  messages=%d  iter=%d",
                model_name,
                [t["function"]["name"] for t in tools],
                len(messages),
                iterations,
            )
            for i, m in enumerate(messages):
                role = m.get("role", "?")
                content = m.get("content", "")
                tcs = m.get("tool_calls")
                if tcs:
                    logger.debug(
                        "  msg[%d] %s  tool_calls=%s",
                        i,
                        role,
                        [tc["function"]["name"] for tc in tcs],
                    )
                else:
                    logger.debug("  msg[%d] %s  %s", i, role, str(content)[:2000])

            response = await litellm.acompletion(**kwargs)
            logger.debug("LLM raw response: %s", response.model_dump_json(indent=2))

            # Log the full assistant response to make it easier to follow the chain
            choice = response.choices[0]
            msg = choice.message
            if msg.content:
                logger.debug("Assistant response content: %s", msg.content)

            usage = getattr(response, "usage", None)
            if usage:
                pt = getattr(usage, "prompt_tokens", 0) or 0
                ct = getattr(usage, "completion_tokens", 0) or 0
                self._total_tokens += pt + ct
                yield UsageEvent(
                    prompt_tokens=pt,
                    completion_tokens=ct,
                    total_tokens=pt + ct,
                    session_total=self._total_tokens,
                )

            choice = response.choices[0]
            msg = choice.message
            tool_calls = getattr(msg, "tool_calls", None)
            logger.debug(
                "LLM response  tool_calls=%s  content=%s",
                [tc.function.name for tc in tool_calls] if tool_calls else None,
                msg.content,
            )

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
                return

            for tc in tool_calls:
                tool_name = tc.function.name
                try:
                    args: dict[str, JsonValue] = json.loads(
                        tc.function.arguments or "{}"
                    )
                except json.JSONDecodeError:
                    logger.warning(
                        "could not parse tool call arguments for %r: %r",
                        tool_name,
                        tc.function.arguments,
                    )
                    args = {}

                status = _status_for_tool(tool_name, args)
                if status:
                    yield StatusEvent(message=status)

                if tool_name in {"keyword_search", "vector_search"}:
                    queries = args.get("queries")
                    detail = (
                        ", ".join(str(q) for q in queries)
                        if isinstance(queries, list) and queries
                        else args.get("query")
                    )
                    if detail:
                        yield FileAccessEvent(path=str(detail), operation="search")

                file_path = str(
                    args.get("filePath")
                    or args.get("dirPath")
                    or args.get("path")
                    or ""
                )
                if file_path and tool_name in _FILE_READ_TOOLS:
                    yield FileAccessEvent(path=file_path, operation="read")
                elif file_path and tool_name in _FILE_WRITE_TOOLS:
                    yield FileAccessEvent(path=file_path, operation="write")
                elif file_path and tool_name in _FILE_DELETE_TOOLS:
                    yield FileAccessEvent(path=file_path, operation="delete")

                call_key = (tool_name, json.dumps(args, sort_keys=True))
                if call_key in seen_calls:
                    result = seen_calls[call_key]
                    logger.debug(
                        "tool %r  deduplicated — returning cached result", tool_name
                    )
                else:
                    result = await self._call_tool(tool_name, args)
                    if not _is_error_result(result):
                        seen_calls[call_key] = result
                    logger.debug(
                        "tool %r  args=%s  result=%s", tool_name, args, result[:300]
                    )
                if result.startswith(("Search server error:", "Tool '")):
                    yield ToolErrorEvent(tool=tool_name, error=result)

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
            "read_note_with_hash",
            "patch_note_lines",
        }
        if name in search_tools:
            try:
                result = await self._search.call_tool(name, args)
                first = result.content[0] if result.content else None
                text = first.text if isinstance(first, TextContent) else "[]"
                return _truncate_result(text)
            except Exception as exc:
                msg = str(exc)
                logger.warning("search server error calling %r: %s", name, msg)

                error_hint = _extract_tool_errors(msg)
                if error_hint:
                    return (
                        f"Tool '{name}' called with wrong arguments. {error_hint}. "
                        "Check the tool schema and use the exact parameter names and types."
                    )
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
                logger.warning(
                    "tool call %r failed on a session, trying next", name, exc_info=True
                )
                continue

        return f"Tool '{name}' not found"

    async def close(self) -> None:
        await self._exit_stack.aclose()


class _StdioSessionContext:
    def __init__(self, params: StdioServerParameters) -> None:
        self._params = params
        self._inner_stack = contextlib.AsyncExitStack()

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
