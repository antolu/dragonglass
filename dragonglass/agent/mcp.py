from __future__ import annotations

import contextlib
import logging
import os
import subprocess
import types
import typing

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import JsonValue

from dragonglass.agent.types import Tool, ToolFunction
from dragonglass.config import Settings
from dragonglass.system_paths import resolve_tool_paths

logger = logging.getLogger(__name__)

_MIN_NODE_MAJOR = 18

_EXCLUDED_MCP_TOOLS: frozenset[str] = frozenset()


def _get_mcp_env(
    extra: dict[str, str] | None = None,
    settings: Settings | None = None,
) -> dict[str, str]:
    env = dict(os.environ)
    if extra:
        env.update({key: value for key, value in extra.items() if key != "PATH"})
    env["PATH"] = os.pathsep.join(resolve_tool_paths(settings=settings, extra=extra))
    return env


def _check_node_version(env: dict[str, str]) -> None:
    """Raise RuntimeError if node is missing or below _MIN_NODE_MAJOR."""
    try:
        result = subprocess.run(
            ["node", "--version"],
            env=env,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"node not found in PATH; install Node.js >= {_MIN_NODE_MAJOR}"
        ) from exc

    raw = result.stdout.strip()
    if not raw.startswith("v"):
        raise RuntimeError(f"unexpected output from node --version: {raw!r}")

    try:
        major = int(raw[1:].split(".")[0])
    except (ValueError, IndexError) as exc:
        raise RuntimeError(f"could not parse node version: {raw!r}") from exc

    if major < _MIN_NODE_MAJOR:
        raise RuntimeError(
            f"node {raw[1:]} is too old; "
            f"dragonglass requires node >= {_MIN_NODE_MAJOR} "
            f"(obsidian-mcp-server dependency @hono/node-server requires >= 18.14.1)"
        )

    logger.debug("node %s OK (>= %d required)", raw, _MIN_NODE_MAJOR)


_EXTRA_MCP_SERVERS = [
    StdioServerParameters(
        command="uvx",
        args=["mcp-server-fetch"],
        env=_get_mcp_env(),
    ),
]


class MCPToolLike(typing.Protocol):
    name: str
    description: str | None
    inputSchema: dict[str, JsonValue]  # noqa: N815


def mcp_tool_to_litellm(tool: MCPToolLike) -> Tool:
    function: ToolFunction = {
        "name": tool.name,
        "description": tool.description or "",
        "parameters": tool.inputSchema,
    }
    return {
        "type": "function",
        "function": function,
    }


class _StdioSessionContext:
    def __init__(self, params: StdioServerParameters) -> None:
        self._params = params
        self._inner_stack = contextlib.AsyncExitStack()

    async def __aenter__(self) -> ClientSession:
        read, write = await self._inner_stack.enter_async_context(
            stdio_client(self._params)
        )
        session = ClientSession(read, write)
        await self._inner_stack.enter_async_context(session)
        await session.initialize()
        return session

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: types.TracebackType | None,
    ) -> None:
        _ = exc_type
        _ = exc
        _ = tb
        await self._inner_stack.aclose()
