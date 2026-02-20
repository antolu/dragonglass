from __future__ import annotations

import logging
import logging.handlers
import pathlib
import sys

_LOG_DIR = pathlib.Path.home() / ".local" / "share" / "dragonglass"
LOG_FILE = _LOG_DIR / "dragonglass.log"

_STRIP_HANDLERS_ONLY = [
    "LiteLLM",
    "LiteLLM Router",
    "LiteLLM Proxy",
]

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

    for h in root.handlers[:]:
        root.removeHandler(h)

    root.addHandler(handler)

    logging.lastResort = None

    for name in _STRIP_HANDLERS_ONLY:
        lg = logging.getLogger(name)
        for h in lg.handlers[:]:
            lg.removeHandler(h)

    for name in _NOISY_LOGGERS:
        lg = logging.getLogger(name)
        lg.setLevel(logging.WARNING)
        for h in lg.handlers[:]:
            lg.removeHandler(h)


def redirect_stderr() -> None:
    """Redirect sys.stderr to the log file.

    Call this just before launching the TUI so that any library that adds a
    StreamHandler(sys.stderr) after setup_logging() (e.g. litellm on first use)
    writes to the log file instead of the terminal.

    We only reassign sys.stderr — we do NOT touch fd 2, because Textual's Linux
    driver writes to sys.__stderr__ which shares fd 2 with the real terminal.
    """
    sys.stderr = open(LOG_FILE, "a", encoding="utf-8")  # noqa: SIM115
