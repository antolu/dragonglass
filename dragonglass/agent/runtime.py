from __future__ import annotations

import asyncio
import collections.abc
import contextlib
import json
import logging
import typing
import uuid

import litellm
from mcp import ClientSession
from mcp.types import TextContent
from opencode_ai import AsyncOpencode
from pydantic import JsonValue

from dragonglass.agent.approval import DragonglassTool, needs_approval
from dragonglass.agent.mcp import (
    _EXCLUDED_MCP_TOOLS,
    _EXTRA_MCP_SERVERS,
    _check_node_version,
    _get_mcp_env,
    _StdioSessionContext,
    mcp_tool_to_litellm,
)
from dragonglass.agent.opencode import run_opencode_turn
from dragonglass.agent.parsing import (
    _extract_tool_errors,
    _is_error_result,
    _is_validation_error_result,
    _truncate_result,
    parse_tool_calls_from_text,
)
from dragonglass.agent.prompts import load_system_prompt
from dragonglass.agent.types import (
    AgentEvent,
    ApprovalRequestEvent,
    DoneEvent,
    MCPToolEvent,
    Message,
    StatusEvent,
    TextChunk,
    UsageEvent,
    UserMessageEvent,
    _FallbackFunction,
    _FallbackToolCall,
    _FunctionCall,
    _Tool,
    _ToolCallMsg,
)
from dragonglass.config import LLMBackend, Settings, get_settings
from dragonglass.mcp import ToolPhase, compute_diff, create_search_server

logger = logging.getLogger(__name__)

_TOOL_STATUS: dict[str, str] = {
    "fetch": "fetching",
    "sequentialthinking": "thinking",
    DragonglassTool.OPEN_NOTE: "opening",
    DragonglassTool.RUN_COMMAND: "running command",
    DragonglassTool.MANAGE_FRONTMATTER: "updating frontmatter",
    DragonglassTool.MANAGE_TAGS: "updating tags",
}

_SEARCH_TOOLS: frozenset[str] = frozenset({
    DragonglassTool.NEW_SEARCH_SESSION,
    DragonglassTool.KEYWORD_SEARCH,
    DragonglassTool.VECTOR_SEARCH,
    DragonglassTool.RUN_COMMAND,
    DragonglassTool.READ_NOTE_WITH_HASH,
    DragonglassTool.REPLACE_LINES,
    DragonglassTool.INSERT_AFTER_LINE,
    DragonglassTool.DELETE_LINES,
    DragonglassTool.MANAGE_FRONTMATTER,
    DragonglassTool.MANAGE_TAGS,
})


class CompletionKwargs(typing.TypedDict, total=False):
    model: str
    messages: list[Message]
    stream: bool
    temperature: float | None
    top_p: float | None
    top_k: int | None
    topK: int | None
    min_p: float | None
    presence_penalty: float | None
    repetition_penalty: float | None
    api_base: str
    tools: list[_Tool]


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


def history_to_events(history: list[Message]) -> list[AgentEvent]:
    tool_results: dict[str, str] = {
        msg["tool_call_id"]: str(msg.get("content") or "")
        for msg in history
        if msg.get("role") == "tool" and msg.get("tool_call_id")
    }

    events: list[AgentEvent] = []
    for msg in history:
        role = msg.get("role")
        content = str(msg.get("content") or "")
        if role == "user":
            events.append(UserMessageEvent(message=content))
        elif role == "assistant":
            if content:
                events.append(TextChunk(text=content))
            for tc in msg.get("tool_calls") or []:
                fn = tc.get("function") or {}
                tool_name = str(fn.get("name") or "tool")
                raw_args = str(fn.get("arguments") or "")
                result = tool_results.get(tc.get("id") or "", "")
                try:
                    parsed = json.loads(raw_args)
                except json.JSONDecodeError:
                    parsed = {}
                if tool_name == DragonglassTool.READ_NOTE_WITH_HASH and parsed.get(
                    "path"
                ):
                    message = f"Reading: {parsed['path']}"
                else:
                    message = raw_args
                events.append(
                    MCPToolEvent(
                        tool=tool_name,
                        phase=ToolPhase.DONE,
                        message=message,
                        detail=result,
                    )
                )
    return events


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


def _coerce_json_map(value: JsonValue) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, JsonValue] = {
        key: item for key, item in value.items() if isinstance(key, str)
    }
    return result


class VaultAgent:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._history: list[Message] = []
        self._system_prompt: str | None = None
        self._litellm_tools: list[_Tool] = []
        self._stdio_sessions: list[ClientSession] = []
        self._exit_stack = contextlib.AsyncExitStack()
        self._search = create_search_server(get_settings())
        self.agents_note_found: bool = False
        self._total_tokens: int = 0
        self._opencode_session_id: str | None = None
        self._approval_gates: dict[str, asyncio.Event] = {}
        self._approval_results: dict[str, bool] = {}
        self._session_approved: set[str] = set()

    async def initialise(self) -> None:
        settings = get_settings()
        logger.info(
            "agent initialise backend=%s model=%s vector_search=%s",
            settings.llm_backend,
            settings.llm_model,
            settings.vector_search_url,
        )
        self._system_prompt, self.agents_note_found = await load_system_prompt(
            settings, opencode=settings.llm_backend == LLMBackend.opencode
        )
        await self._connect_mcp_servers()
        logger.info(
            "agent ready tools=%d stdio_sessions=%d agents_note_found=%s",
            len(self._litellm_tools),
            len(self._stdio_sessions),
            self.agents_note_found,
        )

    def clear_history(self) -> None:
        self._history = []
        self._total_tokens = 0
        self._opencode_session_id = None
        self._session_approved.clear()

    def get_history(self) -> list[Message]:
        return list(self._history)

    def set_history(self, history: list[Message]) -> None:
        self._history = list(history)
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
                    self._litellm_tools.append(mcp_tool_to_litellm(tool))
                logger.info(
                    "connected MCP server command=%s args=%s tools=%d",
                    params.command,
                    params.args,
                    len(result.tools),
                )
            except Exception:
                logger.warning(
                    "failed to connect MCP server %s %s",
                    params.command,
                    params.args,
                    exc_info=True,
                )

        if not self._stdio_sessions:
            logger.warning("no MCP servers connected; agent will run without tools")

        logger.debug("sequential thinking MCP server disabled")

        for tool in await self._search.list_tools():
            self._litellm_tools.append(mcp_tool_to_litellm(tool))
        logger.info("registered search tools total=%d", len(self._litellm_tools))

    async def run(
        self, user_message: str, model_override: str | None = None
    ) -> collections.abc.AsyncGenerator[AgentEvent]:
        assert self._system_prompt is not None, "call initialise() first"
        logger.info(
            "agent run start message_len=%d model_override=%s history_len=%d",
            len(user_message),
            model_override,
            len(self._history),
        )
        history_len_before = len(self._history)
        self._history.append(Message(role="user", content=user_message))
        messages: list[Message] = [
            Message(role="system", content=self._system_prompt),
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
        logger.info(
            "agent run done history_added=%d history_total=%d",
            len(new_messages),
            len(self._history),
        )

    def resolve_approval(
        self,
        request_id: str,
        approved: bool,
        session: bool = False,
        permission: str | None = None,
    ) -> None:
        self._approval_results[request_id] = approved
        if session and permission and approved:
            self._session_approved.add(permission)
        gate = self._approval_gates.get(request_id)
        if gate:
            gate.set()
        else:
            logger.warning("resolve_approval: no pending gate for %r", request_id)

    async def _agent_loop(  # noqa: PLR0912, PLR0914, PLR0915
        self,
        messages: list[Message],
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

            if settings.llm_backend == LLMBackend.opencode:
                if not self._opencode_session_id:
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
                    messages[-1]["content"],
                    model_id,
                    provider_id,
                    settings,
                    system_prompt=self._system_prompt,
                    agent="dragonglass",
                ):
                    yield event
                return

            if model_name.startswith("ollama/"):
                model_name = "ollama_chat/" + model_name[len("ollama/") :]

            kwargs: CompletionKwargs = {
                "model": model_name,
                "messages": messages,
                "stream": True,
                "temperature": settings.llm_temperature,
                "top_p": settings.llm_top_p,
                "top_k": settings.llm_top_k,
                "topK": settings.llm_top_k,
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

            stream = await litellm.acompletion(**kwargs)
            full_text = ""
            accumulated_tool_calls: dict[str, _ToolCallMsg] = {}
            usage_emitted = False
            final_reasoning = ""

            async for chunk in stream:
                usage = getattr(chunk, "usage", None)
                if usage and not usage_emitted:
                    pt = getattr(usage, "prompt_tokens", 0) or 0
                    ct = getattr(usage, "completion_tokens", 0) or 0
                    self._total_tokens += pt + ct
                    yield UsageEvent(
                        prompt_tokens=pt,
                        completion_tokens=ct,
                        total_tokens=pt + ct,
                        session_total=self._total_tokens,
                    )
                    usage_emitted = True

                choices = getattr(chunk, "choices", None) or []
                if not choices:
                    continue

                delta = getattr(choices[0], "delta", None)
                if delta is None:
                    continue

                content_delta = getattr(delta, "content", None)
                if isinstance(content_delta, str) and content_delta:
                    full_text += content_delta
                    yield TextChunk(text=content_delta)

                reasoning_delta = getattr(delta, "reasoning_content", None)
                if isinstance(reasoning_delta, str) and reasoning_delta:
                    final_reasoning += reasoning_delta

                chunk_tool_calls = getattr(delta, "tool_calls", None) or []
                for tc in chunk_tool_calls:
                    tc_id = getattr(tc, "id", None)
                    if not isinstance(tc_id, str) or not tc_id:
                        continue
                    function = getattr(tc, "function", None)
                    name_delta = getattr(function, "name", None) if function else None
                    args_delta = (
                        getattr(function, "arguments", None) if function else None
                    )

                    existing = accumulated_tool_calls.get(tc_id)
                    if existing is None:
                        accumulated_tool_calls[tc_id] = _ToolCallMsg(
                            id=tc_id,
                            type="function",
                            function=_FunctionCall(
                                name=name_delta or "",
                                arguments=args_delta or "",
                            ),
                        )
                    else:
                        if isinstance(name_delta, str) and name_delta:
                            existing["function"]["name"] = (
                                existing["function"].get("name", "") + name_delta
                            )
                        if isinstance(args_delta, str) and args_delta:
                            existing["function"]["arguments"] = (
                                existing["function"].get("arguments", "") + args_delta
                            )

            msg_content = full_text
            tool_calls = [
                _FallbackToolCall(
                    id=tc["id"],
                    function=_FallbackFunction(
                        name=tc["function"].get("name", ""),
                        arguments=tc["function"].get("arguments", ""),
                    ),
                )
                for tc in accumulated_tool_calls.values()
            ]

            if not tool_calls:
                fallback = parse_tool_calls_from_text(final_reasoning)
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
                msg_content,
            )

            assistant_msg = Message(role="assistant", content=msg_content)
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
                yield DoneEvent()
                return

            for tc in tool_calls:
                tool_name = tc.function.name
                try:
                    raw_args = typing.cast(
                        JsonValue,
                        json.loads(tc.function.arguments or "{}"),
                    )
                    args = _coerce_json_map(raw_args)
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

                perm = needs_approval(tool_name, args, settings, self._session_approved)
                if perm is not None:
                    request_id = uuid.uuid4().hex
                    path, diff_text, description = await compute_diff(
                        tool_name, args, settings.vector_search_url
                    )
                    gate = asyncio.Event()
                    self._approval_gates[request_id] = gate
                    yield ApprovalRequestEvent(
                        request_id=request_id,
                        tool=tool_name,
                        permission=perm,
                        path=path,
                        diff=diff_text,
                        description=description,
                    )
                    try:
                        await asyncio.wait_for(gate.wait(), timeout=120.0)
                    except TimeoutError:
                        self._approval_gates.pop(request_id, None)
                        yield StatusEvent(message="Approval timed out — edit cancelled")
                        yield DoneEvent()
                        return
                    finally:
                        self._approval_gates.pop(request_id, None)
                    if not self._approval_results.pop(request_id, False):
                        yield StatusEvent(message="Edit rejected")
                        yield DoneEvent()
                        return

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
                if _is_validation_error_result(result):
                    yield MCPToolEvent(
                        tool=tool_name,
                        phase=ToolPhase.VALIDATION_ERROR,
                        message=tool_name,
                        detail=result,
                    )
                elif _is_error_result(result):
                    yield MCPToolEvent(
                        tool=tool_name,
                        phase=ToolPhase.ERROR,
                        message=tool_name,
                        detail=result,
                    )

                messages.append(
                    Message(role="tool", tool_call_id=tc.id, content=result)
                )

    async def _call_tool(self, name: str, args: dict[str, JsonValue]) -> str:
        if name in _SEARCH_TOOLS:
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
