from __future__ import annotations

from dragonglass._mod_replace import replace_modname
from dragonglass.server.main import DEFAULT_PORT, run, start_server_daemon

for _sym in (run, start_server_daemon):  # noqa: RUF067
    replace_modname(_sym, __name__)

__all__ = [
    "DEFAULT_PORT",
    "run",
    "start_server_daemon",
]
