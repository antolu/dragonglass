from __future__ import annotations

import asyncio
import logging

import dotenv

from dragonglass.log import setup_logging
from dragonglass.server.server import main


def run() -> None:
    dotenv.load_dotenv()
    setup_logging()
    # websockets logger is very chatty
    logging.getLogger("websockets").setLevel(logging.WARNING)
    asyncio.run(main())


if __name__ == "__main__":
    run()
