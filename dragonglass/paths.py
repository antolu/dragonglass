from __future__ import annotations

import os
import pathlib
import tempfile


def get_xdg_dir(env_var: str, default_path: pathlib.Path) -> pathlib.Path:
    """Get an XDG directory from an environment variable or a default path."""
    val = os.environ.get(env_var)
    if val:
        return pathlib.Path(val) / "dragonglass"
    return default_path / "dragonglass"


REPO_ROOT = pathlib.Path(__file__).parent.parent

CONFIG_DIR = get_xdg_dir("XDG_CONFIG_HOME", pathlib.Path.home() / ".config")
XDG_DATA_DIR = get_xdg_dir("XDG_DATA_HOME", pathlib.Path.home() / ".local" / "share")
CACHE_DIR = get_xdg_dir("XDG_CACHE_HOME", pathlib.Path.home() / ".cache")


TEMP_DIR = pathlib.Path(tempfile.gettempdir()) / "dragonglass"
DATA_DIR = TEMP_DIR / "data"
OPENCODE_CONFIG_DIR = TEMP_DIR / "config"
LOG_DIR = XDG_DATA_DIR
_opencode_config_path = os.environ.get("OPENCODE_CONFIG")
if _opencode_config_path:
    OPENCODE_CONFIG_FILE = pathlib.Path(_opencode_config_path).expanduser()
else:
    OPENCODE_CONFIG_FILE = OPENCODE_CONFIG_DIR / "opencode.json"
PROJECT_OPENCODE_CONFIG = OPENCODE_CONFIG_FILE

CONVERSATIONS_DIR = DATA_DIR / "conversations"

# Ensure directories exist
for d in (
    CONFIG_DIR,
    DATA_DIR,
    CACHE_DIR,
    CONVERSATIONS_DIR,
    OPENCODE_CONFIG_DIR,
    LOG_DIR,
):
    d.mkdir(parents=True, exist_ok=True)

OPENCODE_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = CONFIG_DIR / "config.toml"
EXTRA_MODELS_FILE = CONFIG_DIR / "extra_models.json"
