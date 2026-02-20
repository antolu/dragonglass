from __future__ import annotations

import logging
import logging.handlers
import pathlib

_LOG_DIR = pathlib.Path.home() / ".local" / "share" / "dragonglass"
LOG_FILE = _LOG_DIR / "dragonglass.log"

_NOISY_LOGGERS = [
    "litellm",
    "litellm.utils",
    "litellm.main",
    "httpx",
    "httpcore",
    "mcp",
    "asyncio",
]


def setup_logging() -> None:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(handler)

    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
