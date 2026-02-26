from __future__ import annotations

import asyncio
import logging
import typing

from dragonglass.agent.agent import AgentEvent
from dragonglass.agent.client import AgentClient
from dragonglass.config import Settings
from dragonglass.menubar import obsidian_ping

logger = logging.getLogger(__name__)

Callback = typing.Callable[[AgentEvent], None]
ObsidianCallback = typing.Callable[[bool], None]


class AgentThread:
    """Connects to the Dragonglass server on a background asyncio thread.

    Callbacks are invoked on the background thread — the caller must
    dispatch to the main Cocoa thread if needed.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._loop: asyncio.AbstractEventLoop | None = None
        self._client: AgentClient | None = None
        self._on_event: Callback | None = None
        self._on_ready: typing.Callable[[bool, str], None] | None = None

        import threading  # noqa: PLC0415

        self._thread = threading.Thread(
            target=self._run, daemon=True, name="agent-thread"
        )

    def set_on_event(self, cb: Callback) -> None:
        self._on_event = cb

    def set_on_ready(self, cb: typing.Callable[[bool, str], None]) -> None:
        self._on_ready = cb

    def start(self) -> None:
        self._thread.start()

    def send(self, message: str) -> None:
        if self._loop is None or self._client is None:
            return
        asyncio.run_coroutine_threadsafe(self._process(message), self._loop)

    def ping_obsidian(self, callback: ObsidianCallback) -> None:
        if self._loop is None:
            callback(False)
            return

        async def _ping() -> None:
            online = await obsidian_ping.is_obsidian_online(
                self._settings.obsidian_api_url, self._settings.obsidian_api_key
            )
            callback(online)

        asyncio.run_coroutine_threadsafe(_ping(), self._loop)

    def stop(self) -> None:
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)

    def _run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._init())
            self._loop.run_forever()
        finally:
            self._loop.close()

    async def _init(self) -> None:
        # Menubar is a client now.
        self._client = AgentClient()
        if self._on_ready:
            self._on_ready(True, "")

    async def _process(self, message: str) -> None:
        if self._client is None:
            return
        # Stream events from the server
        async for event in self._client.run(message):
            if self._on_event:
                self._on_event(event)
