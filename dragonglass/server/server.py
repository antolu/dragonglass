from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
import signal
import tomllib

import tomli_w
import websockets

from dragonglass import paths
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
        logger.info("server: chat message: %r", text)
        if self.agent:
            async for event in self.agent.run(text):
                await websocket.send(serialize_event(event))

    @staticmethod
    async def _handle_get_config(websocket: websockets.WebSocketServerProtocol) -> None:
        settings = get_settings()
        await websocket.send(json.dumps({"type": "config", **settings.model_dump()}))

    @staticmethod
    async def _handle_set_config(
        websocket: websockets.WebSocketServerProtocol, data: dict[str, object]
    ) -> None:
        new_config = data.get("config")
        if not isinstance(new_config, dict):
            return

        try:
            with open(paths.CONFIG_FILE, "rb") as f:
                current_toml = tomllib.load(f)
        except FileNotFoundError:
            current_toml = {}

        current_toml.update(new_config)
        with open(paths.CONFIG_FILE, "wb") as f:
            tomli_w.dump(current_toml, f)

        invalidate_settings()
        logger.info("server: config updated: %r", new_config)
        await websocket.send(json.dumps({"type": "config_ack"}))


async def main() -> None:
    server = DragonglassServer()
    await server.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
