from __future__ import annotations

import json
import pathlib

_STATE_FILE = pathlib.Path.home() / ".config" / "dragonglass" / "state.json"

_DEFAULTS: dict[str, object] = {
    "model": "gemini/gemini-2.5-flash",
    "auto_allow_edit": True,
    "auto_allow_create": True,
    "auto_allow_delete": False,
}


def load() -> dict[str, object]:
    try:
        with open(_STATE_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as _:
        return dict(_DEFAULTS)
    else:
        return {**_DEFAULTS, **data}


def save(state: dict[str, object]) -> None:
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    current = load()
    current.update(state)
    with open(_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2)
