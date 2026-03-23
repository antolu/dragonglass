from __future__ import annotations

import collections.abc
import contextlib
import json
import logging
import os
import re
import subprocess
import typing
import uuid

import litellm
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent
from opencode_ai import AsyncOpencode

from dragonglass.agent.opencode import run_opencode_turn
from dragonglass.agent.prompts import load_system_prompt
from dragonglass.agent.types import (
    AgentEvent,
    DoneEvent,
    FileAccessEvent,
    JsonValue,
    StatusEvent,
    TextChunk,
    ToolErrorEvent,
    UsageEvent,
    UserMessageEvent,
    _FallbackFunction,
    _FallbackToolCall,
    _FunctionCall,
    _Message,
    _Tool,
    _ToolCallMsg,
    _ToolFunction,
)
from dragonglass.config import Settings, get_settings
from dragonglass.mcp.search import create_search_server

logger = logging.getLogger(__name__)


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
    "dragonglass_open_note": "opening",
    "dragonglass_run_command": "running command",
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


def parse_tool_calls_from_text(
    text: str,
) -> list[tuple[str, dict[str, JsonValue]]]:
    """Parse Qwen3-style XML tool calls from free text.

    Handles the case where the model emits tool calls inside its <think> block
    (reasoning_content) rather than as structured tool_calls. Format:

        <tool_call>
        <function=name>
        <parameter=key>value</parameter>
        </function>
        </tool_call>
    """
    results: list[tuple[str, dict[str, JsonValue]]] = []
    for block in re.findall(r"<tool_call>(.*?)</tool_call>", text, re.DOTALL):
        fn_match = re.search(r"<function=([^>]+)>", block)
        if not fn_match:
            continue
        name = fn_match.group(1).strip()
        params: dict[str, JsonValue] = {}
        for pm in re.finditer(
            r"<parameter=([^>]+)>(.*?)</parameter>", block, re.DOTALL
        ):
            key = pm.group(1).strip()
            val_raw = pm.group(2).strip()
            try:
                params[key] = json.loads(val_raw)
            except json.JSONDecodeError:
                params[key] = val_raw
        results.append((name, params))
    return results


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


_EXCLUDED_MCP_TOOLS = frozenset({
    "obsidian_read_note",
    "obsidian_global_search",
    "obsidian_search_replace",
})

_FILE_READ_TOOLS = frozenset({
    "dragonglass_read_note_with_hash",
    "obsidian_list_notes",
    "obsidian_global_search",
})

_FILE_WRITE_TOOLS = frozenset({
    "obsidian_update_note",
    "obsidian_search_replace",
    "obsidian_manage_frontmatter",
    "obsidian_manage_tags",
    "dragonglass_patch_note_lines",
})
_FILE_DELETE_TOOLS: frozenset[str] = frozenset()


def _get_mcp_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    if extra:
        env.update(extra)

    # Augment PATH to include common locations for npx, uvx, etc.
    # Homebrew paths come before /usr/local/bin to prefer newer binaries
    # (e.g. /usr/local/bin/node may be an old legacy install on Apple Silicon macs).
    paths = env.get("PATH", "").split(os.pathsep)
    new_paths = [
        "/opt/homebrew/bin",
        "/opt/homebrew/sbin",
        os.path.expanduser("~/.local/bin"),
        "/usr/local/bin",
    ]
    # Add existing paths, avoiding duplicates
    for p in paths:
        if p and p not in new_paths:
            new_paths.append(p)

    env["PATH"] = os.pathsep.join(new_paths)
    return env


# @hono/node-server (a dependency of obsidian-mcp-server) requires Node >= 18.14.1.
_MIN_NODE_MAJOR = 18


def _check_node_version(env: dict[str, str]) -> None:
    """Raise RuntimeError if node is missing or below _MIN_NODE_MAJOR."""
    try:
        result = subprocess.run(
            ["node", "--version"],
            env=env,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"node not found in PATH; install Node.js >= {_MIN_NODE_MAJOR}"
        ) from exc

    raw = result.stdout.strip()
    if not raw.startswith("v"):
        raise RuntimeError(f"unexpected output from node --version: {raw!r}")

    try:
        major = int(raw[1:].split(".")[0])
    except (ValueError, IndexError) as exc:
        raise RuntimeError(f"could not parse node version: {raw!r}") from exc

    if major < _MIN_NODE_MAJOR:
        raise RuntimeError(
            f"node {raw[1:]} is too old; "
            f"dragonglass requires node >= {_MIN_NODE_MAJOR} "
            f"(obsidian-mcp-server dependency @hono/node-server requires >= 18.14.1)"
        )

    logger.debug("node %s OK (>= %d required)", raw, _MIN_NODE_MAJOR)


# Sequential thinking MCP server disabled: the module is complex and
# caused runtime issues when launched from the macOS app. Keep the
# config here for reference; to re-enable, restore the block below and
# the connection attempt in _connect_mcp_servers().
# _THINKING_SERVER = StdioServerParameters(
#     command="npx",
#     args=["@modelcontextprotocol/server-sequential-thinking"],
#     env=_get_mcp_env(),
# )

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
        self._stdio_sessions: list[ClientSession] = []
        self._exit_stack = contextlib.AsyncExitStack()
        self._search = create_search_server(get_settings())
        self.agents_note_found: bool = False
        self._total_tokens: int = 0
        self._opencode_session_id: str | None = None

    async def initialise(self) -> None:
        self._system_prompt, self.agents_note_found = await load_system_prompt(
            get_settings()
        )
        await self._connect_mcp_servers()

    def clear_history(self) -> None:
        self._history = []
        self._total_tokens = 0
        self._opencode_session_id = None

    def get_history(self) -> list[_Message]:
        return list(self._history)

    def set_history(self, history: list[_Message]) -> None:
        self._history = list(history)
        # We don't necessarily know the total tokens from loaded history,
        # but we can reset or approximate if we had it. For now just reset.
        self._total_tokens = 0

    async def _connect_mcp_servers(self) -> None:
        _check_node_version(_get_mcp_env())
        for params in _EXTRA_MCP_SERVERS:
            try:
                session = await self._exit_stack.enter_async_context(
                    _StdioSessionContext(params)
                )
                result = await session.list_tools()
                self._stdio_sessions.append(session)
                for tool in result.tools:
                    if tool.name in _EXCLUDED_MCP_TOOLS:
                        continue
                    lt_tool = _mcp_tool_to_litellm(tool)
                    self._litellm_tools.append(lt_tool)
            except Exception:
                logger.warning(
                    "failed to connect MCP server %s %s",
                    params.command,
                    params.args,
                    exc_info=True,
                )

        if not self._stdio_sessions:
            logger.warning("no MCP servers connected; agent will run without tools")

        # Sequential thinking MCP server currently disabled to avoid
        # launching complex external dependencies at runtime. If you need
        # it later, re-enable the _THINKING_SERVER definition above and
        # restore the connection logic here.
        logger.debug("sequential thinking MCP server disabled")

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
        gen = self._agent_loop(messages, model_override=model_override)
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

        new_messages = messages[2 + history_len_before :]
        self._history.extend(new_messages)

    async def _agent_loop(  # noqa: PLR0912, PLR0914, PLR0915
        self,
        messages: list[_Message],
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

            if settings.llm_backend == "opencode":
                if not self._opencode_session_id:
                    # We create session lazily on first turn
                    client = AsyncOpencode(base_url=settings.opencode_url)
                    try:
                        model_name_for_session = resolve_model_name(
                            model_override, settings.llm_model
                        )
                        session_provider_id = "copilot"
                        session_model_id = model_name_for_session
                        if "/" in model_name_for_session:
                            session_provider_id, session_model_id = (
                                model_name_for_session.split("/", 1)
                            )

                        session = await client.session.create(
                            extra_body={
                                "agent": "dragonglass",
                                "model": {
                                    "providerID": session_provider_id,
                                    "modelID": session_model_id,
                                },
                            }
                        )
                        logger.info(
                            "created OpenCode session id=%s provider=%s model=%s",
                            session.id,
                            session_provider_id,
                            session_model_id,
                        )
                        self._opencode_session_id = session.id
                    except Exception:
                        logger.exception("failed to create OpenCode session")
                        yield StatusEvent(message="Failed to connect to OpenCode")
                        yield DoneEvent()
                        return

                provider_id = "copilot"
                model_id = model_name
                if "/" in model_name:
                    provider_id, model_id = model_name.split("/", 1)

                logger.debug(
                    "Switching to OpenCode backend  session=%s  provider=%s  model=%s",
                    self._opencode_session_id,
                    provider_id,
                    model_id,
                )
                async for event in run_opencode_turn(
                    self._opencode_session_id,
                    messages[-1]["content"],  # Raw user message
                    model_id,
                    provider_id,
                    settings,
                    system_prompt=self._system_prompt,
                    agent="dragonglass",
                ):
                    yield event
                return

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
            tools = self._litellm_tools

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
            logger.debug(
                "LLM raw response: %s",
                json.dumps(response.model_dump(), indent=2, default=str),
            )

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

            if not tool_calls:
                reasoning = getattr(msg, "reasoning_content", None) or ""
                fallback = parse_tool_calls_from_text(reasoning)
                if fallback:
                    logger.warning(
                        "tool calls found in reasoning_content, not in tool_calls — "
                        "model emitted tool call inside <think> block; extracting %d call(s)",
                        len(fallback),
                    )
                    tool_calls = [
                        _FallbackToolCall(
                            id=f"call_{uuid.uuid4().hex[:8]}",
                            function=_FallbackFunction(
                                name=name,
                                arguments=json.dumps(args),
                            ),
                        )
                        for name, args in fallback
                    ]

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

                if tool_name in {
                    "dragonglass_keyword_search",
                    "dragonglass_vector_search",
                }:
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
            "dragonglass_new_search_session",
            "dragonglass_keyword_search",
            "dragonglass_vector_search",
            "dragonglass_open_note",
            "dragonglass_run_command",
            "dragonglass_read_note_with_hash",
            "dragonglass_patch_note_lines",
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

        exhausted = True
        for session in self._stdio_sessions:
            try:
                tools = await session.list_tools()
                if any(t.name == name for t in tools.tools):
                    exhausted = False
                    call_result = await session.call_tool(name, args)
                    first = call_result.content[0] if call_result.content else None
                    text = first.text if isinstance(first, TextContent) else ""
                    return _truncate_result(text)
            except Exception:
                logger.warning(
                    "tool call %r failed on a session, trying next", name, exc_info=True
                )
                continue

        if exhausted:
            return f"Tool '{name}' not found"
        return f"Tool '{name}' failed on all available sessions"

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
