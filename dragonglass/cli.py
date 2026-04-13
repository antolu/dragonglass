from __future__ import annotations

import asyncio
import os
import signal
import socket
import time

import click
import dotenv

from dragonglass import paths
from dragonglass.agent.headless import run_headless
from dragonglass.config import get_settings
from dragonglass.hybrid_search import SearchEngine
from dragonglass.log import LOG_FILE, setup_logging
from dragonglass.mcp import create_search_server
from dragonglass.search import ObsidianHttpBackend
from dragonglass.server import DEFAULT_PORT, run, start_server_daemon

_PID_FILE = paths.DATA_DIR / "dragonglass.pid"
_LOG_FILE = str(LOG_FILE)
_SERVER_STARTUP_WAIT_SECONDS = 1.0


@click.group()
@click.pass_context
def cli(ctx: click.Context) -> None:
    pass


@cli.command()
def serve() -> None:
    """Run the dragonglass server (WebSocket)."""
    run()


@cli.command()
def chat() -> None:
    """Run a headless chat REPL (client mode)."""
    dotenv.load_dotenv()
    setup_logging()

    # Check if server is running
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("localhost", DEFAULT_PORT)) != 0:
            click.echo("server not running, starting it...")
            start_server_daemon()
            # Brief wait for it to bind
            time.sleep(_SERVER_STARTUP_WAIT_SECONDS)

    asyncio.run(run_headless())


@cli.command()
def start() -> None:
    """Start the agent server as a background daemon."""
    pid = start_server_daemon()
    click.echo(f"started dragonglass server daemon (pid {pid})")


@cli.command()
def stop() -> None:
    """Stop the running daemon."""
    try:
        with open(_PID_FILE, encoding="utf-8") as f:
            pid = int(f.read().strip())
        os.kill(pid, signal.SIGTERM)
        os.remove(_PID_FILE)
        click.echo(f"stopped pid {pid}")
    except FileNotFoundError:
        click.echo("no pid file found — is the daemon running?", err=True)
    except ProcessLookupError:
        click.echo("process not running, removing stale pid file")
        os.remove(_PID_FILE)


@cli.command()
def mcp() -> None:
    """Run the MCP server (STDIO)."""
    setup_logging(rollover=False)
    settings = get_settings()
    backend = ObsidianHttpBackend(base_url=settings.vector_search_url)
    engine = SearchEngine(keyword_backend=backend, vector_backend=backend)
    server = create_search_server(engine, settings)
    server.run()


@cli.command()
@click.option("--lines", "-n", default=50, help="Number of lines to tail.")
def logs(lines: int) -> None:
    """Tail the daemon log."""
    os.execlp("tail", "tail", "-f", "-n", str(lines), _LOG_FILE)
