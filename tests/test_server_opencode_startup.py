from __future__ import annotations

import asyncio

import pytest

from dragonglass.server.server import DragonglassServer


def test_resolve_opencode_executable_prefers_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENCODE_BIN", "/tmp/opencode")
    monkeypatch.setattr(
        "dragonglass.server.server.os.path.isfile", lambda p: p == "/tmp/opencode"
    )
    monkeypatch.setattr(
        "dragonglass.server.server.os.access", lambda p, mode: p == "/tmp/opencode"
    )
    monkeypatch.setattr("dragonglass.server.server.shutil.which", lambda name: None)

    assert DragonglassServer._resolve_opencode_executable() == "/tmp/opencode"  # noqa: SLF001


def test_resolve_opencode_executable_uses_path_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENCODE_BIN", raising=False)
    monkeypatch.setattr(
        "dragonglass.server.server.shutil.which", lambda name: "/usr/local/bin/opencode"
    )

    assert DragonglassServer._resolve_opencode_executable() == "/usr/local/bin/opencode"  # noqa: SLF001


def test_restart_opencode_reports_missing_binary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = DragonglassServer()

    monkeypatch.setattr(server, "_resolve_opencode_executable", lambda: None)

    async def run() -> None:
        ok = await server._restart_opencode("github-copilot/gpt-5-mini")  # noqa: SLF001
        assert ok is False
        assert server._opencode_start_error is not None  # noqa: SLF001

    asyncio.run(run())
