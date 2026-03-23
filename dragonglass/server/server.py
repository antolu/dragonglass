from __future__ import annotations

import asyncio
import collections.abc
import contextlib
import dataclasses
import json
import logging
import os
import pathlib
import signal
import time
import tomllib
import typing
import urllib.parse
import uuid
from http import HTTPStatus

import httpx
import tomli_w
import websockets
from opencode_ai import AsyncOpencode
from uvicorn import Config, Server

from dragonglass import paths
from dragonglass._version import version
from dragonglass.agent.agent import (
    AgentEvent,
    DoneEvent,
    MCPToolEvent,
    VaultAgent,
    history_to_events,
)
from dragonglass.agent.types import (
    ConversationLoadedEvent,
    ConversationsListEvent,
)
from dragonglass.config import Settings, get_settings, invalidate_settings
from dragonglass.mcp.search import create_search_server
from dragonglass.mcp.telemetry import drain_tool_events
from dragonglass.paths import OPENCODE_CONFIG_FILE

logger = logging.getLogger(__name__)

MAX_TITLE_LENGTH = 40

_OPENCODE_CONFIG_TEMPLATE: dict[str, typing.Any] = {
    "$schema": "https://opencode.ai/config.json",
    "mcp": {
        "dragonglass": {
            "type": "remote",
            "enabled": True,
        }
    },
    "agent": {
        "dragonglass": {
            "mode": "primary",
            "tools": {
                "dragonglass_*": True,
            },
        }
    },
}


def serialize_event(event: AgentEvent) -> str:
    def _encode(obj: typing.Any) -> typing.Any:
        if dataclasses.is_dataclass(obj):
            # We don't use asdict() here because it's recursive and
            # doesn't allow us to inject the 'type' field into nested objects easily.
            result = {"type": obj.__class__.__name__}
            for field in dataclasses.fields(obj):
                value = getattr(obj, field.name)
                result[field.name] = _encode(value)
            return result
        if isinstance(obj, list):
            return [_encode(item) for item in obj]
        if isinstance(obj, dict):
            return {k: _encode(v) for k, v in obj.items()}
        return obj

    return json.dumps(_encode(event))


def resolve_chat_model(raw_model_override: object, selected_model: str) -> str | None:
    model_override: str | None = None
    if isinstance(raw_model_override, str):
        stripped = raw_model_override.strip()
        if stripped:
            model_override = stripped
    if model_override is not None:
        return model_override
    selected = selected_model.strip()
    if selected:
        return selected
    return None


def format_ollama_chat_model_name(model_name: str) -> str:
    stripped = model_name.strip()
    if not stripped:
        return stripped
    if "/" in stripped:
        return stripped
    return f"ollama_chat/{stripped}"


def is_embedding_model(model_name: str) -> bool:
    lowered = model_name.lower()
    return "embed" in lowered or "embedding" in lowered


def parse_ollama_models(raw_models: object) -> list[str]:
    if not isinstance(raw_models, list):
        return []

    parsed_models: list[str] = []
    for model in raw_models:
        name: str | None = None
        if isinstance(model, str):
            name = model
        elif isinstance(model, dict):
            value = model.get("name") or model.get("model")
            if isinstance(value, str):
                name = value
        if not name:
            continue

        formatted_name = format_ollama_chat_model_name(name)
        if not is_embedding_model(formatted_name):
            parsed_models.append(formatted_name)

    return parsed_models


def parse_opencode_models(raw_providers: object) -> list[str]:
    if not isinstance(raw_providers, list):
        return []

    parsed_models: list[str] = []
    for provider in raw_providers:
        if not isinstance(provider, dict):
            continue
        provider_id = provider.get("id")
        models = provider.get("models")
        if not isinstance(provider_id, str) or not isinstance(models, list):
            continue
        for model in models:
            model_id = None
            if isinstance(model, str):
                model_id = model
            elif isinstance(model, dict):
                model_id = model.get("id") or model.get("name")
            if isinstance(model_id, str):
                parsed_models.append(f"{provider_id}/{model_id}")

    return parsed_models


class DragonglassServer:
    def __init__(self, host: str = "localhost", port: int = 51363) -> None:
        self.host = host
        self.port = port
        self.agent: VaultAgent | None = None
        self._stop_event = asyncio.Event()
        self._chat_task: asyncio.Task[None] | None = None
        self._current_conversation_id: str | None = None
        self._opencode_process: asyncio.subprocess.Process | None = None
        self._mcp_task: asyncio.Task[None] | None = None
        self._last_opencode_model: str | None = None

    @staticmethod
    def _get_conversation_path(conversation_id: str) -> pathlib.Path:
        return paths.CONVERSATIONS_DIR / f"{conversation_id}.json"

    def _save_conversation(
        self, conversation_id: str, history: list[typing.Any]
    ) -> None:
        path = self._get_conversation_path(conversation_id)
        # Simple title extraction: first user message
        title = "New Chat"
        for msg in history:
            if msg.get("role") == "user" and msg.get("content"):
                content = str(msg["content"])
                title = content[:MAX_TITLE_LENGTH] + (
                    "..." if len(content) > MAX_TITLE_LENGTH else ""
                )
                break

        data = {
            "id": conversation_id,
            "title": title,
            "updated_at": time.time(),
            "history": history,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    async def run(self) -> None:
        settings = get_settings()
        self.agent = VaultAgent(settings)

        # Start OpenCode and MCP servers if needed
        await self._start_managed_services(settings)

        logger.info("server: connecting to vault")
        try:
            await self.agent.initialise()
        except Exception:
            logger.exception("server: failed to connect to vault")
            return

        logger.info("server: starting websocket server on %s:%d", self.host, self.port)

        # Signal handling for graceful shutdown
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._stop_event.set)

        async with websockets.serve(self._handle_client, self.host, self.port):
            await self._stop_event.wait()

        logger.info("server: shutting down")
        if self._chat_task:
            self._chat_task.cancel()
        if self._mcp_task:
            self._mcp_task.cancel()
        if self._opencode_process:
            logger.info("server: stopping opencode process")
            self._opencode_process.terminate()
            with contextlib.suppress(Exception):
                await asyncio.wait_for(self._opencode_process.wait(), timeout=5.0)

        await self.agent.close()

    async def _start_managed_services(self, settings: Settings) -> None:
        # Start MCP HTTP/SSE server
        mcp_server = create_search_server(settings)

        def run_uvicorn() -> None:
            config = Config(
                app=mcp_server.http_app(path="/mcp"),
                host="localhost",
                port=settings.mcp_http_port,
                log_level="warning",
            )
            server = Server(config)
            server.run()

        self._mcp_task = asyncio.create_task(asyncio.to_thread(run_uvicorn))
        await self._wait_for_mcp_server(settings.mcp_http_port)
        logger.info(
            "server: MCP HTTP/SSE server ready on port %d", settings.mcp_http_port
        )

        # Start OpenCode server
        if settings.llm_backend == "opencode" and settings.spawn_opencode:
            port = self._opencode_port(settings.opencode_url)
            logger.info("server: starting OpenCode server on port %d", port)
            await self._restart_opencode(settings.llm_model)
            self._last_opencode_model = settings.llm_model

    async def _wait_for_mcp_server(self, port: int) -> None:
        deadline = time.monotonic() + 10.0
        last_error: Exception | None = None

        while time.monotonic() < deadline:
            if self._mcp_task and self._mcp_task.done():
                task_exc = self._mcp_task.exception()
                if task_exc is not None:
                    if await self._check_mcp_server(port):
                        logger.warning(
                            "server: MCP task failed but endpoint is already available on port %d; using existing server",
                            port,
                        )
                        return
                    raise RuntimeError("MCP server task failed to start") from task_exc

            try:
                if await self._check_mcp_server(port):
                    return
            except Exception as exc:
                last_error = exc

            await asyncio.sleep(0.1)

        if self._mcp_task and self._mcp_task.done():
            task_exc = self._mcp_task.exception()
            if task_exc is not None:
                if await self._check_mcp_server(port):
                    logger.warning(
                        "server: MCP task failed but endpoint is already available on port %d; using existing server",
                        port,
                    )
                    return
                raise RuntimeError("MCP server task failed to start") from task_exc

        raise RuntimeError(
            f"Timed out waiting for MCP server on port {port}"
        ) from last_error

    @staticmethod
    async def _check_mcp_server(port: int) -> bool:
        async with httpx.AsyncClient(timeout=0.5) as client:
            resp = await client.get(f"http://127.0.0.1:{port}/mcp")
        return resp.status_code in {
            HTTPStatus.OK,
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.UNAUTHORIZED,
            HTTPStatus.METHOD_NOT_ALLOWED,
        }

    @staticmethod
    def _opencode_port(opencode_url: str) -> int:
        port = 4096
        try:
            parsed = urllib.parse.urlparse(opencode_url)
            if parsed.port:
                port = parsed.port
        except Exception:
            logger.warning("server: failed to parse OpenCode URL %s", opencode_url)
        return port

    @staticmethod
    def _load_json_file(path: pathlib.Path) -> dict[str, typing.Any]:
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                logger.info("server: loaded OpenCode config source %s", path)
                return data
            logger.warning("server: ignoring non-object config file %s", path)
        except FileNotFoundError:
            return {}
        except Exception:
            logger.warning("server: failed reading config file %s", path, exc_info=True)
        return {}

    @staticmethod
    def _merge_config_dicts(
        base: dict[str, typing.Any], incoming: dict[str, typing.Any]
    ) -> dict[str, typing.Any]:
        for key, value in incoming.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                DragonglassServer._merge_config_dicts(
                    typing.cast(dict[str, typing.Any], base[key]), value
                )
            else:
                base[key] = value
        return base

    def _build_opencode_config(self, model_id: str) -> dict[str, typing.Any]:
        settings = get_settings()
        merged: dict[str, typing.Any] = self._merge_config_dicts(
            {},
            _OPENCODE_CONFIG_TEMPLATE,
        )

        local_config = self._load_json_file(OPENCODE_CONFIG_FILE)
        if local_config:
            merged = self._merge_config_dicts(merged, local_config)

        mcp_config = merged.setdefault("mcp", {}).setdefault("dragonglass", {})
        mcp_config["type"] = "remote"
        mcp_config["url"] = f"http://127.0.0.1:{settings.mcp_http_port}/mcp"
        mcp_config["enabled"] = True

        agent_config = merged.setdefault("agent", {}).setdefault("dragonglass", {})
        agent_config["mode"] = "primary"
        agent_tools = agent_config.setdefault("tools", {})
        agent_tools["dragonglass_*"] = True
        if model_id.strip():
            agent_config["model"] = model_id

        return merged

    def _write_opencode_config(self, model_id: str) -> None:
        OPENCODE_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        config = self._build_opencode_config(model_id)
        with open(OPENCODE_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        logger.info(
            "server: wrote OpenCode config to %s (model=%s)",
            OPENCODE_CONFIG_FILE,
            model_id,
        )

    async def _wait_for_opencode_server(self, opencode_url: str) -> None:
        deadline = time.monotonic() + 15.0
        last_error: Exception | None = None
        url = opencode_url.rstrip("/") + "/"

        while time.monotonic() < deadline:
            if self._opencode_process and self._opencode_process.returncode is not None:
                raise RuntimeError(
                    "OpenCode process exited early with code "
                    f"{self._opencode_process.returncode}"
                )

            try:
                async with httpx.AsyncClient(timeout=0.5) as client:
                    resp = await client.get(url)
                    if resp.status_code < HTTPStatus.INTERNAL_SERVER_ERROR:
                        logger.info(
                            "server: OpenCode health check status=%d url=%s",
                            resp.status_code,
                            url,
                        )
                        return
            except Exception as exc:
                last_error = exc

            await asyncio.sleep(0.1)

        raise RuntimeError(
            f"Timed out waiting for OpenCode at {opencode_url}"
        ) from last_error

    async def _restart_opencode(self, model_id: str) -> None:
        """Kills existing OpenCode server and restarts."""
        settings = get_settings()
        if not settings.spawn_opencode:
            return

        # 1. Kill existing
        if self._opencode_process and self._opencode_process.returncode is None:
            logger.info(
                "server: terminating existing OpenCode server (pid %d)",
                self._opencode_process.pid,
            )
            self._opencode_process.terminate()
            try:
                await asyncio.wait_for(self._opencode_process.wait(), timeout=8.0)
            except TimeoutError:
                logger.warning(
                    "server: OpenCode process did not terminate in time; killing pid %d",
                    self._opencode_process.pid,
                )
                self._opencode_process.kill()
                await self._opencode_process.wait()
            self._opencode_process = None

        # 2. Update OpenCode config
        try:
            self._write_opencode_config(model_id)
        except Exception:
            logger.warning("server: failed to update OpenCode config", exc_info=True)

        # 3. Start new process
        port = self._opencode_port(settings.opencode_url)

        try:
            env = os.environ.copy()
            env["OPENCODE_CONFIG"] = str(OPENCODE_CONFIG_FILE)
            logger.info(
                "server: launching OpenCode process port=%d config=%s",
                port,
                OPENCODE_CONFIG_FILE,
            )
            self._opencode_process = await asyncio.create_subprocess_exec(
                "opencode",
                "serve",
                "--port",
                str(port),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
                env=env,
            )
            await self._wait_for_opencode_server(settings.opencode_url)
            logger.info(
                "server: OpenCode server started with model %s (pid %d)",
                model_id,
                self._opencode_process.pid,
            )
        except Exception:
            logger.exception("server: failed to restart OpenCode")

    async def _handle_client(  # noqa: PLR0912
        self, websocket: typing.Any
    ) -> None:
        logger.info("server: client connected")
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    logger.warning("server: received malformed JSON: %r", message[:200])
                    await websocket.send(
                        json.dumps({"type": "error", "error": "malformed JSON"})
                    )
                    continue
                command = data.get("command")
                if command == "chat":
                    if self._chat_task and not self._chat_task.done():
                        self._chat_task.cancel()
                    self._chat_task = asyncio.create_task(
                        self._run_chat_task(websocket, data)
                    )
                elif command == "stop":
                    if self._chat_task and not self._chat_task.done():
                        self._chat_task.cancel()
                elif command == "ping":
                    await websocket.send(json.dumps({"type": "pong"}))
                elif command == "get_config":
                    await self._handle_get_config(websocket)
                elif command == "set_config":
                    await self._handle_set_config(websocket, data)
                elif command == "list_models":
                    await self._handle_list_models(websocket)
                elif command == "save_model":
                    await self._handle_save_model(websocket, data)
                elif command == "get_version":
                    await self._handle_get_version(websocket)
                elif command == "new_chat":
                    await self._handle_new_chat(websocket)
                elif command == "list_conversations":
                    await self._handle_list_conversations(websocket)
                elif command == "load_conversation":
                    await self._handle_load_conversation(websocket, data)
                elif command == "delete_conversation":
                    await self._handle_delete_conversation(websocket, data)
        except websockets.exceptions.ConnectionClosed:
            logger.info("server: client disconnected")
        except Exception:
            logger.exception("server: error handling client")
        finally:
            logger.info("server: request done")

    async def _run_chat_task(
        self, websocket: typing.Any, data: dict[str, object]
    ) -> None:
        text = str(data.get("text", ""))
        settings = get_settings()
        model_override = resolve_chat_model(data.get("model"), settings.selected_model)

        logger.info("server: chat message: %r (model=%s)", text, model_override)

        # Check if we need to restart OpenCode for a different model
        if (
            settings.llm_backend == "opencode"
            and model_override
            and model_override != self._last_opencode_model
        ):
            logger.info(
                "server: model changed from %s to %s, restarting OpenCode",
                self._last_opencode_model,
                model_override,
            )
            await self._restart_opencode(model_override)
            self._last_opencode_model = model_override

        try:
            if self.agent:
                if not self._current_conversation_id:
                    self._current_conversation_id = str(uuid.uuid4())

                async def flush_mcp_telemetry() -> None:
                    for telemetry_event in drain_tool_events():
                        await websocket.send(
                            serialize_event(
                                MCPToolEvent(
                                    tool=telemetry_event.tool,
                                    phase=telemetry_event.phase,
                                    message=telemetry_event.message,
                                )
                            )
                        )

                await flush_mcp_telemetry()

                agent_stream: collections.abc.AsyncIterator[AgentEvent] = (
                    self.agent.run(
                        text,
                        model_override=model_override,
                    )
                )
                while True:
                    try:
                        event = await asyncio.wait_for(
                            anext(agent_stream),
                            timeout=0.1,
                        )
                    except TimeoutError:
                        await flush_mcp_telemetry()
                        continue
                    except StopAsyncIteration:
                        break

                    await websocket.send(serialize_event(event))
                    await flush_mcp_telemetry()

                await flush_mcp_telemetry()

                # Auto-save after response
                self._save_conversation(
                    self._current_conversation_id, self.agent.get_history()
                )  # type: ignore
        except asyncio.CancelledError:
            logger.info("server: chat task cancelled")
            with contextlib.suppress(Exception):
                await websocket.send(serialize_event(DoneEvent()))

    @staticmethod
    async def _handle_get_config(websocket: typing.Any) -> None:
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
            })
        )

    @staticmethod
    async def _handle_list_models(
        websocket: typing.Any,
    ) -> None:
        settings = get_settings()
        models: list[str] = []
        base_urls = [
            settings.ollama_url.rstrip("/"),
            "http://127.0.0.1:11434",
            "http://[::1]:11434",
            "http://localhost:11434",
        ]

        for base_url in dict.fromkeys(base_urls):
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(f"{base_url}/api/tags", timeout=5.0)
                    if resp.status_code != HTTPStatus.OK:
                        continue
                    data = resp.json()
                    parsed_models = parse_ollama_models(data.get("models"))
                    if parsed_models:
                        models = parsed_models
                        break
            except Exception:
                logger.debug("ollama unreachable at %s", base_url, exc_info=True)

        if settings.llm_backend == "opencode":
            try:
                client = AsyncOpencode(base_url=settings.opencode_url)
                providers = await client.app.providers()
                opencode_models = parse_opencode_models(providers)
                if opencode_models:
                    models = opencode_models
            except Exception:
                logger.exception("failed to fetch opencode models")

        await websocket.send(json.dumps({"type": "models_list", "models": models}))

    @staticmethod
    async def _handle_save_model(
        websocket: typing.Any, data: dict[str, object]
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
        self, websocket: typing.Any, data: dict[str, object]
    ) -> None:
        new_config = data.get("config")
        if not isinstance(new_config, dict):
            logger.warning("server: invalid config update payload")
            return

        try:
            with open(paths.CONFIG_FILE, "rb") as f:
                current_toml = tomllib.load(f)
        except FileNotFoundError:
            current_toml = {}
        except Exception:
            logger.exception("server: failed to read config file %s", paths.CONFIG_FILE)
            await websocket.send(
                json.dumps({"type": "error", "error": "failed to read config file"})
            )
            return

        # Merge new config into current TOML
        # We assume keys coming from Swift are already snake_case via CodingKeys
        current_toml.update(new_config)

        # Ensure the config directory exists before writing
        paths.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

        with open(paths.CONFIG_FILE, "wb") as f:
            tomli_w.dump(current_toml, f)

        invalidate_settings()
        settings = get_settings()

        # Restart OpenCode if model or backend changed
        if (
            settings.llm_backend == "opencode"
            and settings.llm_model != self._last_opencode_model
        ):
            await self._restart_opencode(settings.llm_model)
            self._last_opencode_model = settings.llm_model

        logger.info(
            "server: config updated and settings invalidated for file %s",
            paths.CONFIG_FILE,
        )
        await websocket.send(json.dumps({"type": "config_ack"}))
        await self._handle_get_config(websocket)

    @staticmethod
    async def _handle_get_version(
        websocket: typing.Any,
    ) -> None:
        await websocket.send(json.dumps({"type": "version", "version": version}))

    async def _handle_new_chat(self, websocket: typing.Any) -> None:
        if self.agent:
            self.agent.clear_history()
        self._current_conversation_id = None
        await websocket.send(
            json.dumps({"type": "status", "message": "Started new chat"})
        )

    @staticmethod
    async def _handle_list_conversations(websocket: typing.Any) -> None:
        conversations = []
        for path in paths.CONVERSATIONS_DIR.glob("*.json"):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                    conversations.append({
                        "id": data["id"],
                        "title": data["title"],
                        "updated_at": data.get("updated_at", 0),
                    })
            except Exception:
                logger.warning(
                    "failed to load conversation metadata from %s", path, exc_info=True
                )

        # Sort by updated_at descending
        conversations.sort(key=lambda x: x["updated_at"], reverse=True)
        await websocket.send(
            serialize_event(ConversationsListEvent(conversations=conversations))
        )

    async def _handle_load_conversation(
        self, websocket: typing.Any, data: dict[str, object]
    ) -> None:
        conv_id = data.get("id")
        if not isinstance(conv_id, str):
            return

        path = self._get_conversation_path(conv_id)
        if not path.exists():
            await websocket.send(
                json.dumps({"type": "error", "error": "Conversation not found"})
            )
            return

        try:
            with open(path, encoding="utf-8") as f:
                conv_data = json.load(f)
                if self.agent:
                    self.agent.set_history(conv_data["history"])
                self._current_conversation_id = conv_id

                # Send history back to client as events
                events = history_to_events(conv_data["history"])
                await websocket.send(
                    serialize_event(
                        ConversationLoadedEvent(
                            id=conv_id,
                            history=events,
                        )
                    )
                )
        except Exception as e:
            logger.exception("failed to load conversation %s", conv_id)
            await websocket.send(json.dumps({"type": "error", "error": str(e)}))

    async def _handle_delete_conversation(
        self, websocket: typing.Any, data: dict[str, object]
    ) -> None:
        conv_id = data.get("id")
        if not isinstance(conv_id, str):
            return

        path = self._get_conversation_path(conv_id)
        if path.exists():
            path.unlink()

        if self._current_conversation_id == conv_id:
            self._current_conversation_id = None
            if self.agent:
                self.agent.clear_history()

        await self._handle_list_conversations(websocket)


async def main() -> None:
    server = DragonglassServer()
    await server.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
