from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import json
import logging
import pathlib
import signal
import time
import tomllib
import typing
import uuid
from http import HTTPStatus

import httpx
import tomli_w
import websockets

from dragonglass import paths
from dragonglass._version import version
from dragonglass.agent.agent import (
    AgentEvent,
    ConversationLoadedEvent,
    ConversationsListEvent,
    DoneEvent,
    VaultAgent,
    history_to_events,
)
from dragonglass.config import get_settings, invalidate_settings

logger = logging.getLogger(__name__)

MAX_TITLE_LENGTH = 40


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


class DragonglassServer:
    def __init__(self, host: str = "localhost", port: int = 51363) -> None:
        self.host = host
        self.port = port
        self.agent: VaultAgent | None = None
        self._stop_event = asyncio.Event()
        self._chat_task: asyncio.Task[None] | None = None
        self._current_conversation_id: str | None = None

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
        await self.agent.close()

    async def _handle_client(  # noqa: PLR0912
        self, websocket: typing.Any
    ) -> None:
        logger.info("server: client connected")
        try:
            async for message in websocket:
                data = json.loads(message)
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
        try:
            if self.agent:
                if not self._current_conversation_id:
                    self._current_conversation_id = str(uuid.uuid4())

                async for event in self.agent.run(text, model_override=model_override):
                    await websocket.send(serialize_event(event))

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
                pass

        if model_name not in extra_models:
            extra_models.append(model_name)
            try:
                with open(paths.EXTRA_MODELS_FILE, "w", encoding="utf-8") as f:
                    json.dump(extra_models, f)
            except Exception:
                logger.exception("failed to save extra models")

    @staticmethod
    async def _handle_set_config(
        websocket: typing.Any, data: dict[str, object]
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

        # Merge new config into current TOML
        # We assume keys coming from Swift are already snake_case via CodingKeys
        current_toml.update(new_config)

        # Ensure the config directory exists before writing
        paths.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

        with open(paths.CONFIG_FILE, "wb") as f:
            tomli_w.dump(current_toml, f)

        invalidate_settings()
        logger.info(
            "server: config updated and settings invalidated for file %s",
            paths.CONFIG_FILE,
        )
        await websocket.send(json.dumps({"type": "config_ack"}))
        await DragonglassServer._handle_get_config(websocket)

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
                logger.warning("failed to load conversation metadata from %s", path)

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
