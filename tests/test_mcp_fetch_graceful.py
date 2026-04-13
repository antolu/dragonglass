from __future__ import annotations

import importlib
import sys
import types

import pytest

import dragonglass.agent.mcp as mcp_mod


def test_mcp_extra_servers_empty_when_fetch_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_EXTRA_MCP_SERVERS should be empty list when mcp_server_fetch is not installed."""
    monkeypatch.setitem(sys.modules, "mcp_server_fetch", None)  # type: ignore[arg-type]
    importlib.reload(mcp_mod)
    assert mcp_mod._EXTRA_MCP_SERVERS == []  # noqa: SLF001


def test_mcp_extra_servers_present_when_fetch_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_EXTRA_MCP_SERVERS has mcp-server-fetch entry when package is available."""
    fake_pkg = types.ModuleType("mcp_server_fetch")
    monkeypatch.setitem(sys.modules, "mcp_server_fetch", fake_pkg)
    importlib.reload(mcp_mod)
    assert len(mcp_mod._EXTRA_MCP_SERVERS) == 1  # noqa: SLF001
    assert mcp_mod._EXTRA_MCP_SERVERS[0].command != "uvx"  # noqa: SLF001
