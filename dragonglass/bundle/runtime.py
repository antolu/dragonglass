from __future__ import annotations

import platform
import sys

from dragonglass.bundle.types import RuntimeTuple

_SUPPORTED_OS = frozenset({"darwin", "linux"})
_SUPPORTED_ARCH = frozenset({"arm64", "x86_64"})
_MIN_PYTHON_MINOR = 11
_MAX_PYTHON_MINOR = 14


def detect_runtime() -> RuntimeTuple:
    raw_os = platform.system().lower()
    machine = platform.machine().lower()
    arch = "arm64" if machine in {"arm64", "aarch64"} else machine
    python = f"{sys.version_info.major}.{sys.version_info.minor}"
    return RuntimeTuple(os=raw_os, arch=arch, python=python)


def is_supported(rt: RuntimeTuple) -> bool:
    if rt.os not in _SUPPORTED_OS:
        return False
    if rt.arch not in _SUPPORTED_ARCH:
        return False
    try:
        major, minor = rt.python.split(".")
        if int(major) != 3:  # noqa: PLR2004
            return False
        if not (_MIN_PYTHON_MINOR <= int(minor) <= _MAX_PYTHON_MINOR):
            return False
    except ValueError:
        return False
    return True


def validate_runtime(rt: RuntimeTuple) -> list[str]:
    errors: list[str] = []
    if rt.os not in _SUPPORTED_OS:
        errors.append(f"unsupported OS '{rt.os}'; supported: {sorted(_SUPPORTED_OS)}")
    if rt.arch not in _SUPPORTED_ARCH:
        errors.append(
            f"unsupported arch '{rt.arch}'; supported: {sorted(_SUPPORTED_ARCH)}"
        )
    try:
        major, minor = rt.python.split(".")
        if int(major) != 3:  # noqa: PLR2004
            errors.append(
                f"Python {rt.python} unsupported; need Python 3.{_MIN_PYTHON_MINOR}+"
            )
        elif not (_MIN_PYTHON_MINOR <= int(minor) <= _MAX_PYTHON_MINOR):
            errors.append(
                f"Python {rt.python} unsupported; supported range: 3.{_MIN_PYTHON_MINOR}-3.{_MAX_PYTHON_MINOR}"
            )
    except ValueError:
        errors.append(f"cannot parse Python version: {rt.python!r}")
    return errors
