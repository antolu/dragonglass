from __future__ import annotations

from dragonglass._mod_replace import replace_modname
from dragonglass.mcp.search.tools import create_search_server

replace_modname(create_search_server, __name__)  # noqa: RUF067

__all__ = [
    "create_search_server",
]
