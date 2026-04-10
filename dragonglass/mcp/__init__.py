from __future__ import annotations

from dragonglass._mod_replace import replace_modname
from dragonglass.mcp.preview import compute_diff
from dragonglass.mcp.search import create_search_server
from dragonglass.mcp.telemetry import (
    MCPToolTelemetryEvent,
    ToolPhase,
    drain_tool_events,
    emit_tool_event,
)

for _sym in (  # noqa: RUF067
    compute_diff,
    create_search_server,
    MCPToolTelemetryEvent,
    ToolPhase,
    drain_tool_events,
    emit_tool_event,
):
    replace_modname(_sym, __name__)

__all__ = [
    "MCPToolTelemetryEvent",
    "ToolPhase",
    "compute_diff",
    "create_search_server",
    "drain_tool_events",
    "emit_tool_event",
]
