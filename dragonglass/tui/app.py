from __future__ import annotations

import typing

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, Input, RichLog

from dragonglass.agent.agent import DoneEvent, StatusEvent, TextChunk, VaultAgent
from dragonglass.config import get_settings

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

#log {
    border: solid $primary-darken-2;
    height: 1fr;
    margin: 1 1 0 1;
    padding: 0 1;
    scrollbar-gutter: stable;
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
        self._agent: VaultAgent | None = None

    def compose(self) -> ComposeResult:  # noqa: PLR6301
        yield Header(show_clock=True)
        yield RichLog(id="log", wrap=True, highlight=True, markup=True)
        yield Input(id="input", placeholder="Type a prompt or /help…")
        yield Footer()

    async def on_mount(self) -> None:
        settings = get_settings()
        self._agent = VaultAgent(settings)
        log = self.query_one("#log", RichLog)
        log.write("[dim]Connecting to vault…[/dim]")
        await self._agent.initialise()
        log.write("[dim]Ready. Type your prompt below.[/dim]\n")
        self.query_one("#input", Input).focus()

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

        assert self._agent is not None
        await self._stream_response(message)

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

    async def _stream_response(self, message: str) -> None:
        log = self.query_one("#log", RichLog)
        assert self._agent is not None

        response_parts: list[str] = []
        gen = self._agent.run(message)
        try:
            async for event in gen:
                match event:
                    case StatusEvent(message=status):
                        log.write(f"[dim italic]⟳ {status}…[/dim italic]")
                    case TextChunk(text=chunk):
                        response_parts.append(chunk)
                    case DoneEvent():
                        break
        finally:
            await gen.aclose()

        if response_parts:
            log.write(
                f"[bold green]Dragonglass[/bold green]  {''.join(response_parts)}"
            )
        log.write("")

    def action_clear(self) -> None:
        self.query_one("#log", RichLog).clear()
