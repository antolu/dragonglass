from __future__ import annotations

import asyncio

import pytest

from dragonglass.server.server import DragonglassServer


def test_wait_for_mcp_server_allows_existing_server_when_task_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = DragonglassServer()

    async def check_ok(port: int) -> bool:
        await asyncio.sleep(0)
        _ = port
        return True

    monkeypatch.setattr(DragonglassServer, "_check_mcp_server", staticmethod(check_ok))

    async def run() -> None:
        async def fail() -> None:
            await asyncio.sleep(0)
            raise RuntimeError("bind failed")

        task = asyncio.create_task(fail())
        await asyncio.sleep(0)
        server._mcp_task = task  # noqa: SLF001
        wait_for_mcp_server = server._wait_for_mcp_server  # noqa: SLF001
        await wait_for_mcp_server(51364)

    asyncio.run(run())


def test_wait_for_mcp_server_raises_when_task_fails_and_no_server(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = DragonglassServer()

    async def check_not_ok(port: int) -> bool:
        await asyncio.sleep(0)
        _ = port
        return False

    monkeypatch.setattr(
        DragonglassServer,
        "_check_mcp_server",
        staticmethod(check_not_ok),
    )

    async def run() -> None:
        async def fail() -> None:
            await asyncio.sleep(0)
            raise RuntimeError("bind failed")

        task = asyncio.create_task(fail())
        await asyncio.sleep(0)
        server._mcp_task = task  # noqa: SLF001
        wait_for_mcp_server = server._wait_for_mcp_server  # noqa: SLF001
        with pytest.raises(RuntimeError, match="MCP server task failed to start"):
            await wait_for_mcp_server(51364)

    asyncio.run(run())
