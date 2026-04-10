from __future__ import annotations

from dragonglass._mod_replace import replace_modname
from dragonglass.mcp.search import (
    create_search_server,
    delete_frontmatter_key_lines,
    rebuild_note_with_frontmatter,
    remove_inline_tags,
    set_frontmatter_key_lines,
    split_frontmatter_block,
)
from dragonglass.mcp.telemetry import (
    MCPToolTelemetryEvent,
    ToolPhase,
    drain_tool_events,
    emit_tool_event,
)

for _sym in (  # noqa: RUF067
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
    "create_search_server",
    "delete_frontmatter_key_lines",
    "drain_tool_events",
    "emit_tool_event",
    "rebuild_note_with_frontmatter",
    "remove_inline_tags",
    "set_frontmatter_key_lines",
    "split_frontmatter_block",
]
