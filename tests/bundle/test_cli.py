from __future__ import annotations

import json
import subprocess
import sys

from dragonglass.bundle.runtime import validate_runtime
from dragonglass.bundle.types import RuntimeTuple


def _run_bundle(*args: str) -> subprocess.CompletedProcess:  # type: ignore[type-arg]
    return subprocess.run(
        [sys.executable, "-m", "dragonglass.bundle", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_info_command() -> None:
    result = _run_bundle("info")
    assert result.returncode == 0
    data = json.loads(result.stdout.strip())
    assert "os" in data
    assert "python" in data
    assert "arch" in data


def test_verify_nonexistent_file() -> None:
    result = _run_bundle("verify", "/nonexistent/path.tar.gz")
    assert result.returncode != 0
    lines = [line for line in result.stdout.strip().splitlines() if line]
    last = json.loads(lines[-1])
    assert last["type"] == "error"


def test_install_rejects_unsupported_runtime() -> None:
    errors = validate_runtime(RuntimeTuple(os="freebsd", arch="arm64", python="3.13"))
    assert errors


def test_install_accepts_marker_path_arg() -> None:
    result = _run_bundle("install", "--help")
    assert "--marker-path" in result.stdout


def test_install_offline_accepts_marker_path_arg() -> None:
    result = _run_bundle("install-offline", "--help")
    assert "--marker-path" in result.stdout
