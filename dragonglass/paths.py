from __future__ import annotations

import os
import pathlib


def get_xdg_dir(env_var: str, default_path: pathlib.Path) -> pathlib.Path:
    """Get an XDG directory from an environment variable or a default path."""
    val = os.environ.get(env_var)
    if val:
        return pathlib.Path(val) / "dragonglass"
    return default_path / "dragonglass"


CONFIG_DIR = get_xdg_dir("XDG_CONFIG_HOME", pathlib.Path.home() / ".config")
DATA_DIR = get_xdg_dir("XDG_DATA_HOME", pathlib.Path.home() / ".local" / "share")
CACHE_DIR = get_xdg_dir("XDG_CACHE_HOME", pathlib.Path.home() / ".cache")

# Ensure directories exist
for d in (CONFIG_DIR, DATA_DIR, CACHE_DIR):
    d.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = CONFIG_DIR / "config.toml"
