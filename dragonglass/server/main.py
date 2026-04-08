from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys

import dotenv

from dragonglass import paths
from dragonglass.log import setup_logging
from dragonglass.server.server import main

DEFAULT_PORT = 51363
_PID_FILE = paths.DATA_DIR / "dragonglass.pid"
logger = logging.getLogger(__name__)


def run() -> None:
    dotenv.load_dotenv()
    setup_logging()
    # websockets logger is very chatty
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logger.info("server.main run starting")
    asyncio.run(main())


def start_server_daemon() -> int:
    """Start the agent server as a background daemon."""
    paths.DATA_DIR.mkdir(parents=True, exist_ok=True)
    # The server process calls setup_logging() which handles rotation.
    # We redirect the initial boot output to /dev/null to avoid descriptor conflicts
    # with the rotating log file.
    with open(os.devnull, "w", encoding="utf-8") as null_fd:
        proc = subprocess.Popen(
            [sys.executable, "-m", "dragonglass.server.main"],
            stdout=null_fd,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    with open(_PID_FILE, "w", encoding="utf-8") as f:
        f.write(str(proc.pid))
    logger.info("server daemon started pid=%d pid_file=%s", proc.pid, _PID_FILE)
    return proc.pid


if __name__ == "__main__":
    run()
