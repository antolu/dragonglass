from __future__ import annotations

import asyncio
import collections.abc
import contextlib
import json
import logging
import time
import tomllib
import typing
import urllib.parse
import uuid
from http import HTTPStatus

import httpx
import tomli_w
import websockets.exceptions
from opencode_ai import AsyncOpencode

from dragonglass import paths
from dragonglass._version import version
from dragonglass.agent.agent import AgentEvent, DoneEvent, MCPToolEvent, VaultAgent
from dragonglass.agent.types import JsonValue, StatusEvent, _Message
from dragonglass.config import LLMBackend, get_settings, invalidate_settings
from dragonglass.log_context import bind_request_id
from dragonglass.mcp.telemetry import drain_tool_events
from dragonglass.server.conversations import ConversationStore
from dragonglass.server.models import (
    Command,
    parse_ollama_models,
    parse_opencode_models,
    resolve_chat_model,
    serialize_event,
)
from dragonglass.server.opencode import OpenCodeManager

logger = logging.getLogger(__name__)

MCP_READY_TIMEOUT_SECONDS = 10.0
MCP_READY_POLL_INTERVAL_SECONDS = 0.1
MCP_HEALTHCHECK_TIMEOUT_SECONDS = 0.5

OLLAMA_LIST_MODELS_TIMEOUT_SECONDS = 5.0
OPEN_NOTE_TIMEOUT_SECONDS = 5.0
EVENT_QUEUE_POLL_TIMEOUT_SECONDS = 0.1
DEFAULT_OLLAMA_PORT = 11434


class WebSocketConnection(typing.Protocol):
    async def send(self, message: str) -> None: ...

    def __aiter__(self) -> collections.abc.AsyncIterator[str | bytes]: ...


def _parse_payload(message: str | bytes) -> dict[str, JsonValue] | None:
    try:
        parsed = json.loads(message)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    payload: dict[str, JsonValue] = {}
    for key, value in parsed.items():
        if isinstance(key, str):
            payload[key] = typing.cast(JsonValue, value)
    return payload


def _coerce_json_map(value: JsonValue) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, JsonValue] = {
        key: item for key, item in value.items() if isinstance(key, str)
    }
    return result


class ConnectionHandler:
    def __init__(
        self,
        agent: VaultAgent,
        opencode: OpenCodeManager,
        conversations: ConversationStore,
    ) -> None:
        self._agent = agent
        self._opencode = opencode
        self._conversations = conversations
        self._chat_task: asyncio.Task[None] | None = None
        self.agent_ready: bool = False

    async def handle_client(self, websocket: WebSocketConnection) -> None:  # noqa: PLR0912, PLR0915
        logger.info("server: client connected")
        try:
            async for message in websocket:
                data = _parse_payload(message)
                if data is None:
                    logger.warning("server: received malformed JSON: %r", message[:200])
                    await websocket.send(
                        json.dumps({"type": "error", "error": "malformed JSON"})
                    )
                    continue
                raw_command = data.get("command")
                try:
                    command = Command(
                        str(raw_command) if raw_command is not None else ""
                    )
                except ValueError:
                    logger.warning("server: unknown command %r", data.get("command"))
                    continue
                logger.info(
                    "server: command=%s payload_keys=%s",
                    command.value,
                    sorted(data.keys()),
                )
                match command:
                    case Command.CHAT:
                        if self._chat_task and not self._chat_task.done():
                            self._chat_task.cancel()
                        self._chat_task = asyncio.create_task(
                            self._run_chat_task(websocket, data)
                        )
                    case Command.STOP:
                        if self._chat_task and not self._chat_task.done():
                            self._chat_task.cancel()
                    case Command.APPROVE | Command.REJECT | Command.APPROVE_SESSION:
                        request_id = str(data.get("request_id", ""))
                        permission = str(data.get("permission", ""))
                        if not request_id:
                            continue
                        self._agent.resolve_approval(
                            request_id=request_id,
                            approved=command
                            in {Command.APPROVE, Command.APPROVE_SESSION},
                            session=(command == Command.APPROVE_SESSION),
                            permission=permission or None,
                        )
                    case Command.PING:
                        await websocket.send(json.dumps({"type": "pong"}))
                    case Command.GET_CONFIG:
                        await self._handle_get_config(websocket)
                    case Command.SET_CONFIG:
                        await self._handle_set_config(websocket, data)
                    case Command.LIST_MODELS:
                        await self._handle_list_models(websocket)
                    case Command.SAVE_MODEL:
                        await self._handle_save_model(websocket, data)
                    case Command.GET_VERSION:
                        await websocket.send(
                            json.dumps({"type": "version", "version": version})
                        )
                    case Command.NEW_CHAT:
                        self._agent.clear_history()
                        self._conversations.current_id = None
                        await websocket.send(
                            json.dumps({
                                "type": "status",
                                "message": "Started new chat",
                            })
                        )
                    case Command.LIST_CONVERSATIONS:
                        await websocket.send(
                            serialize_event(self._conversations.build_list_event())
                        )
                    case Command.LOAD_CONVERSATION:
                        await self._handle_load_conversation(websocket, data)
                    case Command.DELETE_CONVERSATION:
                        await self._handle_delete_conversation(websocket, data)
                    case Command.OPEN_NOTE:
                        await self._handle_open_note(websocket, data)
        except websockets.exceptions.ConnectionClosed:
            logger.info("server: client disconnected")
        except Exception:
            logger.exception("server: error handling client")
        finally:
            logger.info("server: request done")

    async def _run_chat_task(
        self, websocket: WebSocketConnection, data: dict[str, JsonValue]
    ) -> None:
        request_id = uuid.uuid4().hex[:10]
        with bind_request_id(request_id):
            await self._run_chat_task_with_context(websocket, data)

    async def _run_chat_task_with_context(  # noqa: PLR0915
        self, websocket: WebSocketConnection, data: dict[str, JsonValue]
    ) -> None:
        text = str(data.get("text", ""))
        settings = get_settings()
        raw_model = data.get("model")
        model_override = resolve_chat_model(
            raw_model if isinstance(raw_model, str) else None,
            settings.selected_model,
        )
        logger.info(
            "server: chat message received chars=%d model=%s conversation_id=%s",
            len(text),
            model_override,
            self._conversations.current_id,
        )

        provisional_history: list[_Message] | None = None
        if text:
            if not self._conversations.current_id:
                self._conversations.current_id = str(uuid.uuid4())
            provisional_history = [
                *self._agent.get_history(),
                {"role": "user", "content": text},
            ]
            self._conversations.save(
                self._conversations.current_id, provisional_history
            )

        def persist_history() -> None:
            if not self._conversations.current_id:
                return
            latest_history = self._agent.get_history()
            if provisional_history is not None and len(latest_history) < len(
                provisional_history
            ):
                self._conversations.save(
                    self._conversations.current_id,
                    provisional_history,
                )
                return
            self._conversations.save(self._conversations.current_id, latest_history)

        try:
            if not self.agent_ready:
                await websocket.send(
                    serialize_event(
                        StatusEvent(
                            message="Backend is still starting up, please wait a moment."
                        )
                    )
                )
                await websocket.send(serialize_event(DoneEvent()))
                return

            async def flush_mcp_telemetry() -> None:
                for telemetry_event in drain_tool_events():
                    await websocket.send(
                        serialize_event(
                            MCPToolEvent(
                                tool=telemetry_event.tool,
                                phase=telemetry_event.phase,
                                message=telemetry_event.message,
                                detail=telemetry_event.detail,
                            )
                        )
                    )

            await flush_mcp_telemetry()

            event_queue: asyncio.Queue[AgentEvent | None] = asyncio.Queue()
            agent = self._agent

            async def _feed_queue() -> None:
                try:
                    async for ev in agent.run(text, model_override=model_override):
                        await event_queue.put(ev)
                finally:
                    await event_queue.put(None)

            feed_task = asyncio.create_task(_feed_queue())
            try:
                while True:
                    try:
                        event = await asyncio.wait_for(
                            event_queue.get(),
                            timeout=EVENT_QUEUE_POLL_TIMEOUT_SECONDS,
                        )
                    except TimeoutError:
                        await flush_mcp_telemetry()
                        continue
                    if event is None:
                        break
                    await websocket.send(serialize_event(event))
                    await flush_mcp_telemetry()
            finally:
                if not feed_task.done():
                    feed_task.cancel()
                    with contextlib.suppress(Exception):
                        await feed_task

            await flush_mcp_telemetry()
            persist_history()
        except asyncio.CancelledError:
            logger.info("server: chat task cancelled")
            persist_history()
            with contextlib.suppress(Exception):
                await websocket.send(serialize_event(DoneEvent()))

    async def _handle_get_config(self, websocket: WebSocketConnection) -> None:
        settings = get_settings()
        extra_models = []
        if paths.EXTRA_MODELS_FILE.exists():
            try:
                with open(paths.EXTRA_MODELS_FILE, encoding="utf-8") as f:
                    extra_models = json.load(f)
            except Exception:
                logger.warning("failed to load extra models", exc_info=True)

        await websocket.send(
            json.dumps({
                "type": "config",
                **settings.model_dump(),
                "extra_models": extra_models,
                "opencode_available": (
                    self._opencode.resolve_executable() is not None
                    and self._opencode.start_error is None
                ),
                "opencode_disabled_reason": self._opencode.start_error,
            })
        )

    async def _handle_list_models(self, websocket: WebSocketConnection) -> None:
        settings = get_settings()
        models: list[str] = []
        base_urls = settings.ollama_probe_urls()
        if not base_urls:
            parsed_ollama = urllib.parse.urlparse(settings.ollama_url)
            fallback_host = (
                parsed_ollama.hostname
                or urllib.parse.urlparse(settings.opencode_url).hostname
            )
            if fallback_host:
                base_urls = [
                    settings.build_http_url(fallback_host, DEFAULT_OLLAMA_PORT)
                ]

        for base_url in dict.fromkeys(base_urls):
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        f"{base_url}/api/tags",
                        timeout=OLLAMA_LIST_MODELS_TIMEOUT_SECONDS,
                    )
                    if resp.status_code != HTTPStatus.OK:
                        continue
                    data = resp.json()
                    parsed_models = parse_ollama_models(data.get("models"))
                    if parsed_models:
                        models = parsed_models
                        break
            except Exception:
                logger.debug("ollama unreachable at %s", base_url, exc_info=True)

        if settings.llm_backend == LLMBackend.opencode:
            if self._opencode.start_error:
                await websocket.send(
                    serialize_event(StatusEvent(message=self._opencode.start_error))
                )
            try:
                opencode_client = AsyncOpencode(base_url=settings.opencode_url)
                providers = await opencode_client.app.providers()
                opencode_models = parse_opencode_models(providers)
                models = opencode_models
            except Exception:
                logger.exception("failed to fetch opencode models")

        await websocket.send(json.dumps({"type": "models_list", "models": models}))

    @staticmethod
    async def _handle_save_model(
        websocket: WebSocketConnection, data: dict[str, JsonValue]
    ) -> None:
        model_name = data.get("name")
        if not isinstance(model_name, str) or not model_name:
            return

        extra_models = []
        if paths.EXTRA_MODELS_FILE.exists():
            try:
                with open(paths.EXTRA_MODELS_FILE, encoding="utf-8") as f:
                    extra_models = json.load(f)
            except Exception:
                logger.warning("failed to read extra models file", exc_info=True)

        if model_name not in extra_models:
            extra_models.append(model_name)
            try:
                with open(paths.EXTRA_MODELS_FILE, "w", encoding="utf-8") as f:
                    json.dump(extra_models, f)
            except Exception:
                logger.exception("failed to save extra models")

    async def _handle_set_config(
        self, websocket: WebSocketConnection, data: dict[str, JsonValue]
    ) -> None:
        new_config = data.get("config")
        if not isinstance(new_config, dict):
            logger.warning("server: invalid config update payload")
            return
        logger.info(
            "server: config update requested keys=%s", sorted(new_config.keys())
        )

        current_toml: dict[str, JsonValue] = {}
        try:
            with open(paths.CONFIG_FILE, "rb") as f:
                loaded = tomllib.load(f)
            current_toml = _coerce_json_map(typing.cast(JsonValue, loaded))
        except FileNotFoundError:
            pass
        except Exception:
            logger.exception("server: failed to read config file %s", paths.CONFIG_FILE)
            await websocket.send(
                json.dumps({"type": "error", "error": "failed to read config file"})
            )
            return
        new_config_map = _coerce_json_map(new_config)

        old_settings = get_settings()

        new_config_map.pop("opencode_available", None)
        new_config_map.pop("opencode_disabled_reason", None)
        backend_changed = (
            "llm_backend" in new_config_map
            and new_config_map["llm_backend"] != old_settings.llm_backend
        )
        if backend_changed:
            logger.info(
                "server: llm backend transition %s -> %s",
                old_settings.llm_backend,
                new_config_map["llm_backend"],
            )
            current_toml[f"selected_model_{old_settings.llm_backend}"] = (
                old_settings.selected_model
            )
        current_toml.update(new_config_map)
        if backend_changed:
            new_backend = str(new_config_map["llm_backend"])
            current_toml["selected_model"] = current_toml.get(
                f"selected_model_{new_backend}", ""
            )

        paths.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

        with open(paths.CONFIG_FILE, "wb") as f:
            tomli_w.dump(current_toml, f)

        invalidate_settings()
        settings = get_settings()

        old_active = self._opencode.is_active(old_settings)
        new_active = self._opencode.is_active(settings)
        should_restart_opencode = (not old_active and new_active) or (
            old_active
            and new_active
            and settings.llm_model != self._opencode.last_model
        )
        logger.info(
            "server: opencode state old_active=%s new_active=%s restart=%s old_model=%s new_model=%s",
            old_active,
            new_active,
            should_restart_opencode,
            self._opencode.last_model,
            settings.llm_model,
        )

        if old_active and not new_active:
            await self._opencode.stop()
        elif should_restart_opencode and await self._opencode.restart(
            settings.llm_model
        ):
            pass  # last_model updated inside restart()

        logger.info(
            "server: config updated and settings invalidated for file %s",
            paths.CONFIG_FILE,
        )
        await websocket.send(json.dumps({"type": "config_ack"}))
        await self._handle_get_config(websocket)
        if "llm_backend" in new_config_map:
            await self._handle_list_models(websocket)

    async def _handle_load_conversation(
        self, websocket: WebSocketConnection, data: dict[str, JsonValue]
    ) -> None:
        conv_id = data.get("id")
        if not isinstance(conv_id, str):
            return

        path = self._conversations.get_path(conv_id)
        if not path.exists():
            await websocket.send(
                json.dumps({"type": "error", "error": "Conversation not found"})
            )
            return

        try:
            event = self._conversations.load(conv_id)
            if event is None:
                await websocket.send(
                    json.dumps({"type": "error", "error": "Conversation not found"})
                )
                return
            history = self._conversations.get_history(conv_id)
            if history is not None:
                self._agent.set_history(history)
            await websocket.send(serialize_event(event))
        except Exception as e:
            logger.exception("failed to load conversation %s", conv_id)
            await websocket.send(json.dumps({"type": "error", "error": str(e)}))

    async def _handle_delete_conversation(
        self, websocket: WebSocketConnection, data: dict[str, JsonValue]
    ) -> None:
        conv_id = data.get("id")
        if not isinstance(conv_id, str):
            return

        was_current = self._conversations.current_id == conv_id
        self._conversations.delete(conv_id)
        if was_current:
            self._agent.clear_history()

        await websocket.send(serialize_event(self._conversations.build_list_event()))

    @staticmethod
    async def _handle_open_note(
        websocket: WebSocketConnection, data: dict[str, JsonValue]
    ) -> None:
        path = data.get("path")
        if not isinstance(path, str) or not path:
            await websocket.send(
                json.dumps({"type": "open_note_ack", "error": "missing path"})
            )
            return
        settings = get_settings()
        encoded = urllib.parse.quote(path, safe="")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{settings.vector_search_url}/open/{encoded}",
                    timeout=OPEN_NOTE_TIMEOUT_SECONDS,
                )
            if resp.status_code in {204, 200}:
                await websocket.send(json.dumps({"type": "open_note_ack"}))
            else:
                await websocket.send(
                    json.dumps({
                        "type": "open_note_ack",
                        "error": f"HTTP {resp.status_code}",
                    })
                )
        except Exception as exc:
            logger.warning("open_note failed for %r: %s", path, exc)
            await websocket.send(
                json.dumps({"type": "open_note_ack", "error": str(exc)})
            )

    async def check_mcp_server(self, port: int) -> bool:  # noqa: PLR6301
        settings = get_settings()
        async with httpx.AsyncClient(timeout=MCP_HEALTHCHECK_TIMEOUT_SECONDS) as client:
            for url in settings.mcp_probe_urls(port):
                resp = await client.get(url)
                if resp.status_code in {
                    HTTPStatus.OK,
                    HTTPStatus.BAD_REQUEST,
                    HTTPStatus.UNAUTHORIZED,
                    HTTPStatus.METHOD_NOT_ALLOWED,
                    HTTPStatus.NOT_ACCEPTABLE,
                }:
                    return True
        return False

    async def wait_for_mcp_server(
        self, port: int, mcp_task: asyncio.Task[None] | None
    ) -> None:
        deadline = time.monotonic() + MCP_READY_TIMEOUT_SECONDS
        last_error: Exception | None = None
        attempts = 0

        while time.monotonic() < deadline:
            attempts += 1
            if mcp_task and mcp_task.done():
                task_exc = mcp_task.exception()
                if task_exc is not None:
                    if await self.check_mcp_server(port):
                        logger.warning(
                            "server: MCP task failed but endpoint is already available on port %d; using existing server",
                            port,
                        )
                        return
                    raise RuntimeError("MCP server task failed to start") from task_exc

            try:
                if await self.check_mcp_server(port):
                    logger.info(
                        "server: MCP health check passed port=%d attempts=%d",
                        port,
                        attempts,
                    )
                    return
            except Exception as exc:
                last_error = exc
                logger.debug(
                    "server: MCP health check failed port=%d attempt=%d error=%s",
                    port,
                    attempts,
                    type(exc).__name__,
                )

            await asyncio.sleep(MCP_READY_POLL_INTERVAL_SECONDS)

        if mcp_task and mcp_task.done():
            task_exc = mcp_task.exception()
            if task_exc is not None:
                if await self.check_mcp_server(port):
                    logger.warning(
                        "server: MCP task failed but endpoint is already available on port %d; using existing server",
                        port,
                    )
                    return
                raise RuntimeError("MCP server task failed to start") from task_exc

        raise RuntimeError(
            f"Timed out waiting for MCP server on port {port}"
        ) from last_error
