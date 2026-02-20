from __future__ import annotations

import asyncio
import contextlib
import typing

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Footer, Header, Input, RichLog

from dragonglass.agent.agent import (
    DoneEvent,
    StatusEvent,
    TextChunk,
    UsageEvent,
    VaultAgent,
)
from dragonglass.config import get_settings
from dragonglass.log import LOG_FILE

_SLASH_COMMANDS: dict[str, str | None] = {
    "/autolink": "Auto-linking is coming in phase 2.",
    "/manage": "Vault management is coming in phase 3.",
    "/help": (
        "Type a natural-language prompt, e.g.\n"
        "  remember that I like cookies\n"
        "  what do I know about Melanie?\n\n"
        "Slash commands: /autolink  /manage  /help  /clear"
    ),
    "/clear": None,
}

CSS = """
Screen {
    background: $surface;
}

#main-area {
    height: 1fr;
    margin: 1 1 0 1;
}

#log {
    border: solid $primary-darken-2;
    width: 1fr;
    padding: 0 1;
    scrollbar-gutter: stable;
}

#stats {
    border: solid $primary-darken-3;
    width: 26;
    margin-left: 1;
    padding: 0 1;
}

#input {
    dock: bottom;
    margin: 0 1 1 1;
}
"""


class DragonglassApp(App[None]):
    TITLE = "dragonglass"
    CSS = CSS
    BINDINGS: typing.ClassVar = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+l", "clear", "Clear"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._query_queue: asyncio.Queue[str | None] | None = None
        self._agent_task: asyncio.Task[None] | None = None
        self._session_total: int = 0
        self._last_prompt: int = 0
        self._last_completion: int = 0

    @typing.override
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main-area"):
            yield RichLog(id="log", wrap=True, highlight=True, markup=True)
            yield RichLog(id="stats", wrap=False, highlight=False, markup=True)
        yield Input(id="input", placeholder="Type a prompt or /help…")
        yield Footer()

    async def on_mount(self) -> None:
        self._query_queue = asyncio.Queue()
        self._agent_task = asyncio.create_task(self._agent_worker())
        self._refresh_stats()

    def _refresh_stats(self) -> None:
        stats = self.query_one("#stats", RichLog)
        stats.clear()
        stats.write("[dim bold]tokens[/dim bold]")
        stats.write("")
        stats.write("[dim]prompt[/dim]")
        stats.write(f"  {self._last_prompt:,}")
        stats.write("[dim]completion[/dim]")
        stats.write(f"  {self._last_completion:,}")
        stats.write("")
        stats.write("[dim]session[/dim]")
        stats.write(f"  {self._session_total:,}")
        stats.write("")
        stats.write("[dim]log[/dim]")
        stats.write(f"  [dim]{LOG_FILE}[/dim]")

    async def _agent_worker(self) -> None:
        settings = get_settings()
        agent = VaultAgent(settings)
        log = self.query_one("#log", RichLog)
        log.write("[dim]Connecting to vault…[/dim]")
        try:
            await agent.initialise()
        except Exception as exc:
            log.write(f"[bold red]Failed to connect: {exc}[/bold red]")
            return

        if not agent.agents_note_found:
            log.write(
                f"[bold yellow]⚠ Agents note not found[/bold yellow] "
                f"[dim]({settings.agents_note_path})[/dim]\n"
                "[dim]Create it in your vault to give the agent custom instructions.[/dim]\n"
            )
        log.write("[dim]Ready. Type your prompt below.[/dim]\n")
        self.query_one("#input", Input).focus()

        assert self._query_queue is not None
        try:
            while True:
                message = await self._query_queue.get()
                if message is None:
                    break
                await self._process_message(agent, message)
        finally:
            await agent.close()

    async def _process_message(self, agent: VaultAgent, message: str) -> None:
        log = self.query_one("#log", RichLog)
        response_parts: list[str] = []
        gen = agent.run(message)
        try:
            async for event in gen:
                match event:
                    case StatusEvent(message=status):
                        self.notify(status, timeout=3)
                    case TextChunk(text=chunk):
                        response_parts.append(chunk)
                    case UsageEvent(
                        prompt_tokens=pt, completion_tokens=ct, session_total=st
                    ):
                        self._last_prompt = pt
                        self._last_completion = ct
                        self._session_total = st
                        self._refresh_stats()
                    case DoneEvent():
                        break
        finally:
            await gen.aclose()

        if response_parts:
            log.write(
                f"[bold green]Dragonglass[/bold green]  {''.join(response_parts)}"
            )
        log.write("")

    async def on_unmount(self) -> None:
        if self._agent_task is not None:
            self._agent_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._agent_task

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        message = event.value.strip()
        if not message:
            return

        self.query_one("#input", Input).clear()

        if message.startswith("/"):
            await self._handle_slash(message)
            return

        log = self.query_one("#log", RichLog)
        log.write(f"[bold cyan]You[/bold cyan]  {message}")
        log.write("")

        assert self._query_queue is not None
        await self._query_queue.put(message)

    async def _handle_slash(self, command: str) -> None:
        cmd = command.split(maxsplit=1)[0].lower()
        log = self.query_one("#log", RichLog)

        if cmd == "/clear":
            log.clear()
            return

        reply = _SLASH_COMMANDS.get(cmd)
        if reply is not None:
            log.write(f"[dim]{reply}[/dim]\n")
        else:
            log.write(f"[dim]Unknown command: {cmd}. Try /help.[/dim]\n")

    def action_clear(self) -> None:
        self.query_one("#log", RichLog).clear()
