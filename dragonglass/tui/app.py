from __future__ import annotations

import typing

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, RichLog, Static

from dragonglass.agent.agent import (
    DoneEvent,
    MCPToolEvent,
    StatusEvent,
    TextChunk,
    ToolErrorEvent,
    UsageEvent,
)
from dragonglass.agent.client import AgentClient
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

#main-area {
    height: 1fr;
    width: 100%;
}

#log {
    width: 1fr;
    height: 100%;
    border: solid $primary;
    background: $surface;
}

#stats {
    dock: right;
    width: 26;
    min-width: 26;
    max-width: 26;
    height: 100%;
    padding: 1;
    margin-left: 1;
    border-left: vline $secondary;
    display: none;
}

#status {
    height: 1;
    width: 100%;
    padding: 0 1;
    color: $text-muted;
}

Input {
    margin: 0 1 1 1;
}

.title {
    text-align: center;
    color: $secondary;
    text-style: bold underline;
    margin-bottom: 2;
}

#tokens {
    margin-bottom: 2;
}
"""


class DragonglassApp(App[None]):
    TITLE = "dragonglass"
    BINDINGS: typing.ClassVar[list[Binding]] = [
        Binding("ctrl+c", "quit", "Quit", show=False, priority=True),
        Binding("ctrl+z", "suspend_process", "Suspend", show=False),
        Binding("ctrl+l", "clear_log", "Clear Log"),
        Binding("f2", "toggle_stats", "Stats"),
        Binding("escape", "stop_chat", "Stop", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._settings = get_settings()
        self._client = AgentClient()
        self._total_tokens = 0
        self._is_thinking = False

    def compose(self) -> ComposeResult:  # noqa: PLR6301
        yield Header()
        with Horizontal(id="main-area"):
            yield RichLog(id="log", markup=True, wrap=True)
            with Vertical(id="stats"):
                yield Static("📊 STATS", classes="title")
                yield Static(id="tokens")
        yield Static(id="status")
        yield Input(placeholder="Ask me anything...", id="input")
        yield Footer()

    async def on_mount(self) -> None:
        self.query_one("#input", Input).focus()
        self._update_tokens(0, 0, 0, 0)
        await self._client.connect()

    async def on_unmount(self) -> None:
        await self._client.close()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return

        self.query_one("#input", Input).value = ""

        if text.startswith("/"):
            self._handle_slash_command(text)
            return

        await self._process_chat(text)

    def _handle_slash_command(self, text: str) -> None:
        log = self.query_one("#log", RichLog)
        if text == "/clear":
            log.clear()
        else:
            resp = _SLASH_COMMANDS.get(text, f"Unknown command: {text}")
            if resp:
                log.write(f"\n[bold magenta]system[/bold magenta]: {resp}\n")

    async def _process_chat(self, text: str) -> None:
        log = self.query_one("#log", RichLog)
        log.write(f"\n[bold green]user[/bold green]: {text}\n")
        log.write("[bold blue]agent[/bold blue]: ", scroll_end=True)

        status_widget = self.query_one("#status", Static)
        inp = self.query_one("#input", Input)
        inp.disabled = True
        self._is_thinking = True

        try:
            async for event in self._client.run(text):
                match event:
                    case StatusEvent(message=msg):
                        status_widget.update(f"⟳ {msg}...")
                    case TextChunk(text=chunk):
                        log.write(chunk, scroll_end=True)
                    case ToolErrorEvent(tool=tool, error=err):
                        log.write(f"\n[bold red]error ({tool})[/bold red]: {err}\n")
                    case UsageEvent(
                        prompt_tokens=pt,
                        completion_tokens=ct,
                        total_tokens=tt,
                        session_total=st,
                    ):
                        self._update_tokens(pt, ct, tt, st)
                    case MCPToolEvent(tool=tool, phase=phase, message=message):
                        log.write(
                            f"\n[bold yellow]mcp[/bold yellow] {tool} [{phase}]: {message}\n"
                        )
                    case DoneEvent():
                        break
        except Exception as exc:
            log.write(f"\n[bold red]system error[/bold red]: {exc}\n")
        finally:
            self._is_thinking = False
            status_widget.update("")
            inp.disabled = False
            inp.focus()
            log.write("\n")

    async def action_stop_chat(self) -> None:
        if self._is_thinking:
            await self._client.stop()

    def _update_tokens(
        self, prompt: int, completion: int, total: int, session: int
    ) -> None:
        content = (
            "[bold]Last request:[/bold]\n"
            f"  Prompt:     [cyan]{prompt:,}[/cyan]\n"
            f"  Completion: [cyan]{completion:,}[/cyan]\n"
            f"  Total:      [cyan]{total:,}[/cyan]\n\n"
            f"[bold]Session total:[/bold]\n[green]{session:,}[/green]"
        )
        self.query_one("#tokens", Static).update(content)

    def action_clear_log(self) -> None:
        self.query_one("#log", RichLog).clear()

    def action_toggle_stats(self) -> None:
        stats = self.query_one("#stats", Vertical)
        stats.display = not stats.display


def main() -> None:
    app = DragonglassApp()
    app.run()


if __name__ == "__main__":
    main()
