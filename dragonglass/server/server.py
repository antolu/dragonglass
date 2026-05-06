from __future__ import annotations

import asyncio
import contextlib
import logging
import signal
from http import HTTPStatus

import websockets
import websockets.asyncio.server
import websockets.datastructures
import websockets.http11
from kv_search import SearchEngine
from uvicorn import Config, Server

from dragonglass.agent import VaultAgent
from dragonglass.config import Settings, get_settings
from dragonglass.mcp import create_search_server
from dragonglass.search import ObsidianHttpBackend
from dragonglass.server.conversations import ConversationStore
from dragonglass.server.models import (
    is_embedding_model,
    parse_ollama_models,
    resolve_chat_model,
    serialize_event,
)
from dragonglass.server.ws import ConnectionHandler

logger = logging.getLogger(__name__)

DEFAULT_WS_PORT = 51363

__all__ = [
    "DragonglassServer",
    "is_embedding_model",
    "main",
    "parse_ollama_models",
    "resolve_chat_model",
    "serialize_event",
]


class DragonglassServer:
    def __init__(self, host: str | None = None, port: int = DEFAULT_WS_PORT) -> None:
        self.host = host
        self.port = port
        self._stop_event = asyncio.Event()
        self._mcp_task: asyncio.Task[None] | None = None
        self._conversations = ConversationStore()

    async def run(self) -> None:
        settings = get_settings()
        server_host = self.host or settings.bind_host()
        logger.info(
            "server: startup model=%s ws_port=%d mcp_port=%d",
            settings.llm_model,
            self.port,
            settings.mcp_http_port,
        )
        agent = VaultAgent(settings)
        handler = ConnectionHandler(agent, self._conversations)

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._stop_event.set)

        def process_request(
            connection: websockets.asyncio.server.ServerConnection,
            request: websockets.http11.Request,
        ) -> websockets.http11.Response | None:
            if request.path == "/health":
                status = (
                    HTTPStatus.OK
                    if handler.agent_ready
                    else HTTPStatus.SERVICE_UNAVAILABLE
                )
                body = b"OK\n" if handler.agent_ready else b"STARTING\n"
                return websockets.http11.Response(
                    status,
                    status.phrase,
                    websockets.datastructures.Headers([]),
                    body,
                )
            return None

        async def _init() -> None:
            try:
                await self._start_managed_services(settings, handler)
            except Exception:
                logger.exception(
                    "server: failed to start managed services; continuing without them"
                )
            logger.info("server: connecting to vault")
            try:
                await agent.initialise()
                handler.agent_ready = True
            except Exception:
                logger.exception("server: failed to connect to vault")
                self._stop_event.set()

        async def _init_shielded() -> None:
            await asyncio.shield(asyncio.ensure_future(_init()))

        logger.info(
            "server: starting websocket server on %s:%d", server_host, self.port
        )
        async with websockets.serve(
            handler.handle_client,
            server_host,
            self.port,
            process_request=process_request,
        ):
            init_task = asyncio.create_task(_init_shielded())
            await self._stop_event.wait()
            init_task.cancel()
            with contextlib.suppress(Exception, asyncio.CancelledError):
                await init_task

        logger.info("server: shutting down")
        if self._mcp_task:
            self._mcp_task.cancel()
        await agent.close()

    async def _start_managed_services(
        self, settings: Settings, handler: ConnectionHandler
    ) -> None:

        backend = ObsidianHttpBackend(base_url=settings.vector_search_url)
        engine = SearchEngine(keyword_backend=backend, vector_backend=backend)
        mcp_server = create_search_server(engine, settings)

        def run_uvicorn() -> None:
            config = Config(
                app=mcp_server.http_app(path="/mcp"),
                host=settings.bind_host(),
                port=settings.mcp_http_port,
                log_level="warning",
            )
            server = Server(config)
            server.run()

        self._mcp_task = asyncio.create_task(asyncio.to_thread(run_uvicorn))
        await handler.wait_for_mcp_server(settings.mcp_http_port, self._mcp_task)
        logger.info(
            "server: MCP HTTP/SSE server ready on port %d", settings.mcp_http_port
        )


async def main() -> None:
    server = DragonglassServer()
    await server.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
