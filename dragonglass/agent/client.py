from __future__ import annotations

import collections.abc
import json
import logging

import websockets

from dragonglass.agent.agent import (
    AgentEvent,
    DoneEvent,
    FileAccessEvent,
    StatusEvent,
    TextChunk,
    ToolErrorEvent,
    UsageEvent,
)

logger = logging.getLogger(__name__)

_EVENT_MAP: dict[str, type[AgentEvent]] = {
    "StatusEvent": StatusEvent,
    "ToolErrorEvent": ToolErrorEvent,
    "TextChunk": TextChunk,
    "UsageEvent": UsageEvent,
    "DoneEvent": DoneEvent,
    "FileAccessEvent": FileAccessEvent,
}


class AgentClient:
    def __init__(self, host: str = "localhost", port: int = 51363) -> None:
        self.uri = f"ws://{host}:{port}"

    async def run(self, text: str) -> collections.abc.AsyncGenerator[AgentEvent]:
        try:
            async with websockets.connect(self.uri) as websocket:
                await websocket.send(json.dumps({"command": "chat", "text": text}))
                async for message in websocket:
                    data = json.loads(message)
                    event_type = data.pop("type", None)
                    cls = _EVENT_MAP.get(event_type)
                    if cls:
                        # Construct dataclass from dict, ignoring unknown fields
                        field_names = {
                            f.name for f in cls.__dataclass_fields__.values()
                        }
                        filtered = {k: v for k, v in data.items() if k in field_names}
                        event = cls(**filtered)
                        yield event
                        if isinstance(event, DoneEvent):
                            break
                    else:
                        logger.warning("client: unknown event type: %r", event_type)
        except Exception:
            logger.exception("client: connection error")
            yield ToolErrorEvent(
                tool="connection",
                error=f"Could not connect to dragonglass server at {self.uri}",
            )
            yield DoneEvent()
