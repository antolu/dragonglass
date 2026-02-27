from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
import signal
import tomllib
from http import HTTPStatus

import httpx
import tomli_w
import websockets

from dragonglass import paths
from dragonglass._version import version
from dragonglass.agent.agent import AgentEvent, VaultAgent
from dragonglass.config import get_settings, invalidate_settings

logger = logging.getLogger(__name__)


def serialize_event(event: AgentEvent) -> str:
    data = dataclasses.asdict(event)
    data["type"] = event.__class__.__name__
    return json.dumps(data)


class DragonglassServer:
    def __init__(self, host: str = "localhost", port: int = 51363) -> None:
        self.host = host
        self.port = port
        self.agent: VaultAgent | None = None
        self._stop_event = asyncio.Event()

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

    async def _handle_client(
        self, websocket: websockets.WebSocketServerProtocol
    ) -> None:
        logger.info("server: client connected")
        try:
            async for message in websocket:
                data = json.loads(message)
                command = data.get("command")
                if command == "chat":
                    await self._handle_chat(websocket, data)
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
        except websockets.exceptions.ConnectionClosed:
            logger.info("server: client disconnected")
        except Exception:
            logger.exception("server: error handling client")
        finally:
            logger.info("server: request done")

    async def _handle_chat(
        self, websocket: websockets.WebSocketServerProtocol, data: dict[str, object]
    ) -> None:
        text = str(data.get("text", ""))
        model_override = data.get("model")
        if not isinstance(model_override, str):
            model_override = None

        logger.info("server: chat message: %r (model=%s)", text, model_override)
        if self.agent:
            async for event in self.agent.run(text, model_override=model_override):
                await websocket.send(serialize_event(event))

    @staticmethod
    async def _handle_get_config(websocket: websockets.WebSocketServerProtocol) -> None:
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
        websocket: websockets.WebSocketServerProtocol,
    ) -> None:
        settings = get_settings()
        models = []
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{settings.ollama_url}/api/tags", timeout=2.0)
                if resp.status_code == HTTPStatus.OK:
                    data = resp.json()
                    models = [m["name"] for m in data.get("models", [])]
        except Exception:
            logger.debug("ollama unreachable", exc_info=True)

        await websocket.send(json.dumps({"type": "models_list", "models": models}))

    @staticmethod
    async def _handle_save_model(
        websocket: websockets.WebSocketServerProtocol, data: dict[str, object]
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
        websocket: websockets.WebSocketServerProtocol, data: dict[str, object]
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

    @staticmethod
    async def _handle_get_version(
        websocket: websockets.WebSocketServerProtocol,
    ) -> None:
        await websocket.send(json.dumps({"type": "version", "version": version}))


async def main() -> None:
    server = DragonglassServer()
    await server.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
