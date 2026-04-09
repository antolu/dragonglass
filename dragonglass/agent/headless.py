from __future__ import annotations

import asyncio
import collections.abc
import logging
import signal
import sys

from dragonglass.agent import (
    DoneEvent,
    MCPToolEvent,
    StatusEvent,
    TextChunk,
)
from dragonglass.agent.client import AgentClient

logger = logging.getLogger(__name__)


async def run_headless() -> None:
    client = AgentClient()
    logger.info("headless: client mode ready")

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _on_signal() -> None:
        logger.info("headless: received shutdown signal")
        stop_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _on_signal)

    try:
        async for line in _read_stdin_lines(stop_event):
            line = line.strip()
            if not line:
                continue
            logger.info("headless: message=%r", line)

            # Using AgentClient.run instead of VaultAgent.run
            async for event in client.run(line):
                match event:
                    case StatusEvent(message=msg):
                        sys.stdout.write(f"[status] {msg}\n")
                        sys.stdout.flush()
                    case TextChunk(text=chunk):
                        sys.stdout.write(chunk)
                        sys.stdout.flush()
                    case MCPToolEvent(
                        tool=tool, phase=phase, message=message, detail=detail
                    ):
                        if phase == "error":
                            sys.stdout.write(f"\n[error] {tool}: {detail}\n")
                        else:
                            sys.stdout.write(f"\n[mcp] {tool} [{phase}] {message}\n")
                        sys.stdout.flush()
                    case DoneEvent():
                        sys.stdout.write("\n")
                        sys.stdout.flush()
                        break
    finally:
        logger.info("headless: shut down")


async def _read_stdin_lines(
    stop: asyncio.Event,
) -> collections.abc.AsyncGenerator[str]:
    loop = asyncio.get_running_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    while not stop.is_set():
        # This await might be why SIGINT was blocked if the loop didn't return.
        # But wait([reader.readline(), stop.wait()]) should fix it.
        reading = asyncio.create_task(reader.readline())
        stopping = asyncio.create_task(stop.wait())

        done, pending = await asyncio.wait(
            [reading, stopping],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for p in pending:
            p.cancel()

        if reading in done:
            result = reading.result()
            if not result:  # EOF
                stop.set()
                return
            yield result.decode()
        else:
            return
