from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from dragonglass.server.opencode import OpenCodeManager


def test_restart_uses_pipes_for_logging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = OpenCodeManager()

    mock_process = MagicMock()
    mock_process.returncode = None
    mock_process.pid = 1234
    mock_process.wait = AsyncMock()

    mock_create = AsyncMock(return_value=mock_process)
    monkeypatch.setattr("asyncio.create_subprocess_exec", mock_create)

    monkeypatch.setattr(manager, "kill_stale_on_port", AsyncMock())
    monkeypatch.setattr(
        OpenCodeManager, "resolve_executable", staticmethod(lambda: "/usr/bin/opencode")
    )
    monkeypatch.setattr(manager, "write_config", MagicMock())
    monkeypatch.setattr(manager, "_wait_for_server", AsyncMock())

    async def run() -> None:
        mock_stdout = asyncio.StreamReader()
        mock_stderr = asyncio.StreamReader()
        mock_process.stdout = mock_stdout
        mock_process.stderr = mock_stderr

        ok = await manager.restart("test-model")
        assert ok is True

        _, kwargs = mock_create.call_args
        assert kwargs["stdout"] == asyncio.subprocess.PIPE
        assert kwargs["stderr"] == asyncio.subprocess.PIPE

        expected_tasks = 2
        assert len(manager._log_tasks) == expected_tasks  # noqa: SLF001

        await manager.stop()
        assert len(manager._log_tasks) == 0  # noqa: SLF001

    asyncio.run(run())
