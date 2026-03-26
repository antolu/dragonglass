from __future__ import annotations

import dataclasses
import queue
import time


@dataclasses.dataclass
class MCPToolTelemetryEvent:
    tool: str
    phase: str
    message: str
    detail: str
    ts: float


_QUEUE: queue.Queue[MCPToolTelemetryEvent] = queue.Queue()


def emit_tool_event(tool: str, phase: str, message: str, detail: str = "") -> None:
    _QUEUE.put(
        MCPToolTelemetryEvent(
            tool=tool,
            phase=phase,
            message=message,
            detail=detail,
            ts=time.time(),
        )
    )


def drain_tool_events() -> list[MCPToolTelemetryEvent]:
    events: list[MCPToolTelemetryEvent] = []
    while True:
        try:
            events.append(_QUEUE.get_nowait())
        except queue.Empty:
            break
    return events
