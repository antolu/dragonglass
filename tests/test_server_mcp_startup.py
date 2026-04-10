from __future__ import annotations

import asyncio
import types

import pytest

from dragonglass.config import Settings
from dragonglass.server.server import DragonglassServer
from dragonglass.server.ws import ConnectionHandler


def test_wait_for_mcp_server_allows_existing_server_when_task_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def check_ok(port: int) -> bool:
        await asyncio.sleep(0)
        _ = port
        return True

    monkeypatch.setattr(ConnectionHandler, "check_mcp_server", staticmethod(check_ok))

    async def run() -> None:
        async def fail() -> None:
            await asyncio.sleep(0)
            raise RuntimeError("bind failed")

        task = asyncio.create_task(fail())
        while not task.done():
            await asyncio.sleep(0)

        handler = ConnectionHandler.__new__(ConnectionHandler)
        await handler.wait_for_mcp_server(51364, task)

    asyncio.run(run())


def test_wait_for_mcp_server_raises_when_task_fails_and_no_server(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def check_not_ok(port: int) -> bool:
        await asyncio.sleep(0)
        _ = port
        return False

    monkeypatch.setattr(
        ConnectionHandler, "check_mcp_server", staticmethod(check_not_ok)
    )

    async def run() -> None:
        async def fail() -> None:
            await asyncio.sleep(0)
            raise RuntimeError("bind failed")

        task = asyncio.create_task(fail())
        while not task.done():
            await asyncio.sleep(0)

        handler = ConnectionHandler.__new__(ConnectionHandler)
        with pytest.raises(RuntimeError, match="MCP server task failed to start"):
            await handler.wait_for_mcp_server(51364, task)

    asyncio.run(run())


def test_run_continues_when_managed_services_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = DragonglassServer()

    async def fail_start(settings: Settings, handler: ConnectionHandler) -> None:
        await asyncio.sleep(0)
        _ = settings
        _ = handler
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

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: types.TracebackType | None,
        ) -> None:
            _ = exc_type
            _ = exc
            _ = tb

    monkeypatch.setattr(server, "_start_managed_services", fail_start)
    monkeypatch.setattr("dragonglass.server.server.VaultAgent", lambda _: DummyAgent())
    monkeypatch.setattr(
        "dragonglass.server.server.get_settings",
        lambda: types.SimpleNamespace(
            llm_backend="litellm",
            llm_model="test-model",
            mcp_http_port=51364,
            opencode_url="http://opencode",
            spawn_opencode=False,
            vector_search_url="http://vector",
            bind_host=lambda: "localhost",
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


def test_run_stops_when_agent_initialise_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = DragonglassServer()

    async def ok_start(settings: Settings, handler: ConnectionHandler) -> None:
        await asyncio.sleep(0)
        _ = settings
        _ = handler

    close_called = False

    class DummyAgent:
        async def initialise(self) -> None:
            _ = self
            raise RuntimeError("vault init failed")

        async def close(self) -> None:
            _ = self
            nonlocal close_called
            close_called = True

    class DummyAsyncContext:
        async def __aenter__(self) -> None:
            return None

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: types.TracebackType | None,
        ) -> None:
            _ = exc_type
            _ = exc
            _ = tb

    monkeypatch.setattr(server, "_start_managed_services", ok_start)
    monkeypatch.setattr("dragonglass.server.server.VaultAgent", lambda _: DummyAgent())
    monkeypatch.setattr(
        "dragonglass.server.server.get_settings",
        lambda: types.SimpleNamespace(
            llm_backend="litellm",
            llm_model="test-model",
            mcp_http_port=51364,
            opencode_url="http://opencode",
            spawn_opencode=False,
            vector_search_url="http://vector",
            bind_host=lambda: "localhost",
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
        await asyncio.wait_for(server.run(), timeout=1)

    asyncio.run(run())

    assert close_called is True
