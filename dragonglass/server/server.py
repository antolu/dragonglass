from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
import signal

import websockets

from dragonglass.agent.agent import AgentEvent, VaultAgent
from dragonglass.config import get_settings

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
                if data.get("command") == "chat":
                    text = data.get("text", "")
                    logger.info("server: chat message: %r", text)
                    if self.agent:
                        async for event in self.agent.run(text):
                            await websocket.send(serialize_event(event))
                elif data.get("command") == "ping":
                    await websocket.send(json.dumps({"type": "pong"}))
        except websockets.exceptions.ConnectionClosed:
            logger.info("server: client disconnected")
        except Exception:
            logger.exception("server: error handling client")
        finally:
            logger.info("server: request done")


async def main() -> None:
    server = DragonglassServer()
    await server.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
