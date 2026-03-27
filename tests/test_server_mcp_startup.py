from __future__ import annotations

import asyncio
import types

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
        while not task.done():
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
        while not task.done():
            await asyncio.sleep(0)
        server._mcp_task = task  # noqa: SLF001
        wait_for_mcp_server = server._wait_for_mcp_server  # noqa: SLF001
        with pytest.raises(RuntimeError, match="MCP server task failed to start"):
            await wait_for_mcp_server(51364)

    asyncio.run(run())


def test_run_continues_when_managed_services_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = DragonglassServer()

    async def fail_start(settings: object) -> None:
        await asyncio.sleep(0)
        _ = settings
        raise RuntimeError("managed services failed")

    init_called = False
    close_called = False

    class DummyAgent:
        async def initialise(self) -> None:
            _ = self
            nonlocal init_called
            init_called = True

        async def close(self) -> None:
            _ = self
            nonlocal close_called
            close_called = True

    class DummyAsyncContext:
        async def __aenter__(self) -> None:
            return None

        async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    monkeypatch.setattr(server, "_start_managed_services", fail_start)
    monkeypatch.setattr("dragonglass.server.server.VaultAgent", lambda _: DummyAgent())
    monkeypatch.setattr(
        "dragonglass.server.server.get_settings",
        lambda: types.SimpleNamespace(
            opencode_url="http://opencode", vector_search_url="http://vector"
        ),
    )
    monkeypatch.setattr(
        "dragonglass.server.server.websockets.serve",
        lambda *args, **kwargs: DummyAsyncContext(),
    )
    monkeypatch.setattr(
        asyncio,
        "get_running_loop",
        lambda: types.SimpleNamespace(add_signal_handler=lambda *args, **kwargs: None),
    )

    async def run() -> None:
        task = asyncio.create_task(server.run())
        await asyncio.sleep(0)
        server._stop_event.set()  # noqa: SLF001
        await task

    asyncio.run(run())

    assert init_called is True
    assert close_called is True
