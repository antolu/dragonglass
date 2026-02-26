from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import sys

import click
import dotenv

from dragonglass.log import LOG_FILE, redirect_stderr, setup_logging

_PID_FILE = os.path.expanduser("~/.local/share/dragonglass/dragonglass.pid")
_LOG_FILE = str(LOG_FILE)


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        dotenv.load_dotenv()
        setup_logging()
        redirect_stderr()
        from dragonglass.tui.app import DragonglassApp  # noqa: PLC0415

        DragonglassApp().run()


@cli.command()
def serve() -> None:
    """Run the dragonglass server (WebSocket)."""
    from dragonglass.server.main import run  # noqa: PLC0415

    run()


@cli.command()
def chat() -> None:
    """Run a headless chat REPL (client mode)."""
    dotenv.load_dotenv()
    setup_logging()
    from dragonglass.agent.headless import run_headless  # noqa: PLC0415

    asyncio.run(run_headless())


@cli.command()
def menubar() -> None:
    """Launch the macOS menubar application."""
    from dragonglass.menubar.app import main  # noqa: PLC0415

    main()


@cli.command()
def start() -> None:
    """Start the agent server as a background daemon."""
    os.makedirs(os.path.dirname(_PID_FILE), exist_ok=True)
    with open(_LOG_FILE, "a", encoding="utf-8") as log_fd:
        proc = subprocess.Popen(
            [sys.executable, "-m", "dragonglass.server.main"],
            stdout=log_fd,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    with open(_PID_FILE, "w", encoding="utf-8") as f:
        f.write(str(proc.pid))
    click.echo(f"started dragonglass server daemon (pid {proc.pid})")


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
@click.option("--lines", "-n", default=50, help="Number of lines to tail.")
def logs(lines: int) -> None:
    """Tail the daemon log."""
    os.execlp("tail", "tail", "-f", "-n", str(lines), _LOG_FILE)
