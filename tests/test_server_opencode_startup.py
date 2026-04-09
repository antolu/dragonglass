from __future__ import annotations

import asyncio

import pytest

from dragonglass.server.opencode import OpenCodeManager


def test_resolve_opencode_executable_prefers_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENCODE_BIN", "/tmp/opencode")
    monkeypatch.setattr(
        "dragonglass.server.opencode.os.path.isfile", lambda p: p == "/tmp/opencode"
    )
    monkeypatch.setattr(
        "dragonglass.server.opencode.os.access", lambda p, mode: p == "/tmp/opencode"
    )
    monkeypatch.setattr("dragonglass.server.opencode.shutil.which", lambda name: None)

    assert OpenCodeManager.resolve_executable() == "/tmp/opencode"


def test_resolve_opencode_executable_uses_path_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENCODE_BIN", raising=False)
    monkeypatch.setattr(
        "dragonglass.server.opencode.shutil.which",
        lambda name: "/usr/local/bin/opencode",
    )

    assert OpenCodeManager.resolve_executable() == "/usr/local/bin/opencode"


def test_restart_reports_missing_binary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = OpenCodeManager()
    monkeypatch.setattr(
        OpenCodeManager, "resolve_executable", staticmethod(lambda: None)
    )

    async def run() -> None:
        ok = await manager.restart("github-copilot/gpt-5-mini")
        assert ok is False
        assert manager.start_error is not None

    asyncio.run(run())
