from __future__ import annotations

import asyncio
import collections.abc
import contextlib
import json
import logging

import websockets

from dragonglass.agent.agent import (
    AgentEvent,
    DoneEvent,
    MCPToolEvent,
    StatusEvent,
    TextChunk,
    UsageEvent,
)

logger = logging.getLogger(__name__)

_EVENT_MAP: dict[str, type[AgentEvent]] = {
    "StatusEvent": StatusEvent,
    "TextChunk": TextChunk,
    "UsageEvent": UsageEvent,
    "DoneEvent": DoneEvent,
    "MCPToolEvent": MCPToolEvent,
}


class AgentClient:
    def __init__(self, host: str = "localhost", port: int = 51363) -> None:
        self.uri = f"ws://{host}:{port}"
        self._websocket: websockets.WebSocketClientProtocol | None = None
        self._queue: asyncio.Queue[AgentEvent] = asyncio.Queue()
        self._receive_task: asyncio.Task[None] | None = None

    async def connect(self) -> None:
        self._websocket = await websockets.connect(self.uri)
        self._receive_task = asyncio.create_task(self._receive_loop())

    async def _receive_loop(self) -> None:
        assert self._websocket is not None
        try:
            async for message in self._websocket:
                data = json.loads(message)
                event_type = data.pop("type", None)
                cls = _EVENT_MAP.get(event_type)
                if cls:
                    field_names = {f.name for f in cls.__dataclass_fields__.values()}
                    filtered = {k: v for k, v in data.items() if k in field_names}
                    await self._queue.put(cls(**filtered))
                else:
                    logger.warning("client: unknown event type: %r", event_type)
        except websockets.exceptions.ConnectionClosed:
            logger.info("client: connection closed")
        except Exception:
            logger.exception("client: receive loop error")
        finally:
            await self._queue.put(DoneEvent())

    async def run(self, text: str) -> collections.abc.AsyncGenerator[AgentEvent]:
        if self._websocket is None or self._websocket.closed:
            try:
                await self.connect()
            except Exception:
                logger.exception("client: connection error")
                yield MCPToolEvent(
                    tool="connection",
                    phase="error",
                    message="connection",
                    detail=f"Could not connect to dragonglass server at {self.uri}",
                )
                yield DoneEvent()
                return

        while not self._queue.empty():
            self._queue.get_nowait()

        assert self._websocket is not None
        await self._websocket.send(json.dumps({"command": "chat", "text": text}))

        while True:
            event = await self._queue.get()
            yield event
            if isinstance(event, DoneEvent):
                break

    async def stop(self) -> None:
        if self._websocket is not None and not self._websocket.closed:
            await self._websocket.send(json.dumps({"command": "stop"}))

    async def close(self) -> None:
        if self._receive_task is not None:
            self._receive_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._receive_task
        if self._websocket is not None:
            await self._websocket.close()
