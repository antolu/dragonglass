from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from dragonglass.server.server import DragonglassServer


def test_restart_opencode_uses_pipes_for_logging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = DragonglassServer()

    mock_process = MagicMock()
    mock_process.returncode = None
    mock_process.pid = 1234
    mock_process.wait = AsyncMock()

    # Pipes are setup inside run() now
    mock_create = AsyncMock(return_value=mock_process)
    monkeypatch.setattr("asyncio.create_subprocess_exec", mock_create)

    # Mock dependencies of _restart_opencode
    monkeypatch.setattr(server, "_kill_stale_opencode_on_port", AsyncMock())
    monkeypatch.setattr(
        server, "_resolve_opencode_executable", lambda: "/usr/bin/opencode"
    )
    monkeypatch.setattr(server, "_write_opencode_config", MagicMock())
    # Mock health check to pass immediately
    monkeypatch.setattr(server, "_wait_for_opencode_server", AsyncMock())

    async def run() -> None:
        # Mocking stdout and stderr as asyncio.StreamReader inside the loop
        mock_stdout = asyncio.StreamReader()
        mock_stderr = asyncio.StreamReader()
        mock_process.stdout = mock_stdout
        mock_process.stderr = mock_stderr

        ok = await server._restart_opencode("test-model")  # noqa: SLF001
        assert ok is True

        # Verify create_subprocess_exec was called with PIPE
        _, kwargs = mock_create.call_args
        assert kwargs["stdout"] == asyncio.subprocess.PIPE
        assert kwargs["stderr"] == asyncio.subprocess.PIPE

        # Verify log tasks were created
        expected_tasks = 2
        assert len(server._opencode_log_tasks) == expected_tasks  # noqa: SLF001

        # Stop server and verify tasks are cleaned up
        await server._stop_opencode()  # noqa: SLF001
        assert len(server._opencode_log_tasks) == 0  # noqa: SLF001

    asyncio.run(run())
