from __future__ import annotations

import os
import pathlib
import platform
import shutil

from dragonglass.config import Settings, get_settings


def _split_path_entries(value: str) -> list[str]:
    return [entry for entry in value.split(os.pathsep) if entry]


def _platform_default_tool_paths() -> list[str]:
    system_name = platform.system().lower()
    if system_name == "darwin":
        return [
            "/opt/homebrew/bin",
            "/opt/homebrew/sbin",
            os.path.expanduser("~/.local/bin"),
            "/usr/local/bin",
            "/usr/bin",
            "/bin",
            "/usr/sbin",
            "/sbin",
        ]
    if system_name == "linux":
        return [
            os.path.expanduser("~/.local/bin"),
            "/usr/local/bin",
            "/usr/bin",
            "/bin",
            "/snap/bin",
        ]
    return [
        os.path.expanduser("~/.local/bin"),
        "/usr/local/bin",
        "/usr/bin",
        "/bin",
    ]


def resolve_tool_paths(
    settings: Settings | None = None,
    extra: dict[str, str] | None = None,
) -> list[str]:
    active_settings = settings or get_settings()
    entries: list[str] = []

    entries.extend(_split_path_entries(os.environ.get("PATH", "")))

    settings_path = active_settings.env_vars.get("PATH")
    if settings_path:
        entries.extend(_split_path_entries(settings_path))

    if extra and "PATH" in extra:
        entries.extend(_split_path_entries(extra["PATH"]))

    candidate_path = os.pathsep.join(dict.fromkeys(entries))
    for binary in ("node", "uvx", "npx"):
        resolved = shutil.which(binary, path=candidate_path) or shutil.which(binary)
        if resolved:
            entries.append(str(pathlib.Path(resolved).parent))

    entries.extend(_platform_default_tool_paths())

    deduped: list[str] = []
    for entry in entries:
        if entry and entry not in deduped:
            deduped.append(entry)
    return deduped


def resolve_tool_binaries(
    settings: Settings | None = None,
    extra: dict[str, str] | None = None,
) -> dict[str, str | None]:
    search_path = os.pathsep.join(resolve_tool_paths(settings=settings, extra=extra))
    binaries = ["node", "npm", "npx", "uvx", "opencode"]
    return {name: shutil.which(name, path=search_path) for name in binaries}
