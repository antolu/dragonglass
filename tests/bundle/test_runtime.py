from __future__ import annotations

import sys

from dragonglass.bundle.runtime import detect_runtime, is_supported
from dragonglass.bundle.types import RuntimeTuple


def test_detect_runtime_returns_runtime_tuple() -> None:
    rt = detect_runtime()
    assert isinstance(rt, RuntimeTuple)
    assert rt.os in {"darwin", "linux", "windows"}
    assert rt.arch in {"arm64", "x86_64", "amd64"}
    assert rt.python.count(".") == 1
    major, minor = rt.python.split(".")
    assert int(major) >= 3  # noqa: PLR2004
    assert int(minor) >= 11  # noqa: PLR2004


def test_detect_runtime_matches_current_process() -> None:
    rt = detect_runtime()
    expected_python = f"{sys.version_info.major}.{sys.version_info.minor}"
    assert rt.python == expected_python


def test_is_supported_current_runtime() -> None:
    rt = detect_runtime()
    assert is_supported(rt), f"current runtime {rt} should be supported"


def test_is_supported_rejects_old_python() -> None:
    rt = RuntimeTuple(os="darwin", arch="arm64", python="3.10")
    assert not is_supported(rt)


def test_is_supported_rejects_unknown_os() -> None:
    rt = RuntimeTuple(os="freebsd", arch="arm64", python="3.13")
    assert not is_supported(rt)
