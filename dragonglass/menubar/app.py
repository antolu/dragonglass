from __future__ import annotations

import logging
import typing

import dotenv
import objc
import rumps
from AppKit import (
    NSBackingStoreBuffered,
    NSBorderlessWindowMask,
    NSButton,
    NSColor,
    NSFont,
    NSNonactivatingPanelMask,
    NSPanel,
    NSScrollView,
    NSTextField,
    NSTextView,
    NSUtilityWindowMask,
    NSView,
    NSWindowStyleMaskResizable,
)
from Foundation import NSMakeRect, NSObject, NSPoint

from dragonglass.agent.agent import (
    DoneEvent,
    FileAccessEvent,
    StatusEvent,
    TextChunk,
    ToolErrorEvent,
    UsageEvent,
)
from dragonglass.config import get_settings
from dragonglass.log import setup_logging
from dragonglass.menubar import state
from dragonglass.menubar.agent_thread import AgentThread

logger = logging.getLogger(__name__)

_PANEL_WIDTH = 520
_PANEL_HEIGHT = 640
_PAD = 8


class _SendDelegate(NSObject):  # type: ignore[misc]
    """NSTextField delegate that intercepts Return key presses."""

    def initWithCallback_(  # noqa: N802
        self, callback: typing.Callable[[str], None]
    ) -> _SendDelegate:
        self = objc.super(_SendDelegate, self).init()  # noqa: PLW0642
        self._callback = callback
        return self

    def control_textView_doCommandBySelector_(  # noqa: N802
        self,
        control: object,
        text_view: object,
        selector: object,
    ) -> bool:
        if objc.selector.name(selector) == b"insertNewline:":
            field = typing.cast(NSTextField, control)
            text = str(field.stringValue()).strip()
            if text:
                self._callback(text)
                field.setStringValue_("")
            return True
        return False


class DragonglassMenubarApp(rumps.App):  # type: ignore[misc]
    def __init__(self) -> None:
        super().__init__("🔮", quit_button=None)
        self.menu = [
            rumps.MenuItem("Open", callback=self._toggle_panel),
            rumps.separator,
            rumps.MenuItem("Quit dragonglass", callback=self._quit),
        ]

        self._panel: NSPanel | None = None
        self._log_view: NSTextView | None = None
        self._status_field: NSTextField | None = None
        self._token_panel: NSView | None = None
        self._token_visible = False
        self._file_field: NSTextField | None = None
        self._obsidian_dot: NSTextField | None = None
        self._model_field: NSTextField | None = None
        self._send_delegate: _SendDelegate | None = None
        self._tok_prompt_lbl: NSTextField | None = None
        self._tok_completion_lbl: NSTextField | None = None
        self._tok_session_lbl: NSTextField | None = None

        self._session_state = state.load()
        self._last_prompt = 0
        self._last_completion = 0
        self._session_total = 0
        self._file_paths: list[str] = []
        self._panel_visible = False

        settings = get_settings()
        settings.llm_model = str(self._session_state.get("model", settings.llm_model))
        self._settings = settings

        self._agent: AgentThread | None = None
        self._agent_started = False

    # ------------------------------------------------------------------
    # Panel construction
    # ------------------------------------------------------------------

    def _build_panel(self) -> None:
        style = (
            NSBorderlessWindowMask
            | NSNonactivatingPanelMask
            | NSUtilityWindowMask
            | NSWindowStyleMaskResizable
        )
        panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, _PANEL_WIDTH, _PANEL_HEIGHT),
            style,
            NSBackingStoreBuffered,
            False,
        )
        panel.setFloatingPanel_(True)
        panel.setHidesOnDeactivate_(False)
        panel.setBackgroundColor_(NSColor.windowBackgroundColor())

        content = panel.contentView()
        y = self._build_bottom_widgets(content)
        y = self._build_controls_row(content, y)
        self._build_chat_log(content, y)
        self._panel = panel

    def _build_bottom_widgets(self, content: object) -> float:
        y: float = _PAD

        send_field = NSTextField.alloc().initWithFrame_(
            NSMakeRect(_PAD, y, _PANEL_WIDTH - 2 * _PAD, 24)
        )
        send_field.setPlaceholderString_("Type a message and press Return…")
        send_field.setBezeled_(True)
        send_field.setDrawsBackground_(True)
        self._send_delegate = _SendDelegate.alloc().initWithCallback_(self._handle_send)
        send_field.setDelegate_(self._send_delegate)
        content.addSubview_(send_field)  # type: ignore[attr-defined]
        y += 24 + _PAD

        status = NSTextField.labelWithString_("")
        status.setFrame_(NSMakeRect(_PAD, y, _PANEL_WIDTH - 2 * _PAD, 16))
        status.setTextColor_(NSColor.secondaryLabelColor())
        status.setFont_(NSFont.systemFontOfSize_(10))
        content.addSubview_(status)  # type: ignore[attr-defined]
        self._status_field = status
        y += 16 + _PAD

        file_field = NSTextField.labelWithString_("No files accessed yet")
        file_field.setFrame_(NSMakeRect(_PAD, y, _PANEL_WIDTH - 2 * _PAD, 14))
        file_field.setTextColor_(NSColor.tertiaryLabelColor())
        file_field.setFont_(NSFont.systemFontOfSize_(9))
        content.addSubview_(file_field)  # type: ignore[attr-defined]
        self._file_field = file_field
        y += 14 + _PAD

        tok_h: float = 52
        tok_view = NSView.alloc().initWithFrame_(
            NSMakeRect(_PAD, y, _PANEL_WIDTH - 2 * _PAD, tok_h)
        )
        tok_view.setHidden_(True)
        self._token_panel = tok_view
        self._tok_prompt_lbl = self._small_label("prompt: 0", tok_view, 0, tok_h - 16)
        self._tok_completion_lbl = self._small_label(
            "completion: 0", tok_view, 0, tok_h - 30
        )
        self._tok_session_lbl = self._small_label("session: 0", tok_view, 0, tok_h - 44)
        content.addSubview_(tok_view)  # type: ignore[attr-defined]
        return y + tok_h + _PAD

    def _build_controls_row(self, content: object, y: float) -> float:
        dot = NSTextField.labelWithString_("⬤")
        dot.setFrame_(NSMakeRect(_PANEL_WIDTH - _PAD - 16, y + 4, 16, 16))
        dot.setTextColor_(NSColor.systemGrayColor())
        dot.setToolTip_("Obsidian status")
        content.addSubview_(dot)  # type: ignore[attr-defined]
        self._obsidian_dot = dot

        tok_btn = NSButton.alloc().initWithFrame_(
            NSMakeRect(_PANEL_WIDTH - _PAD - 16 - _PAD - 24, y + 2, 24, 20)
        )
        tok_btn.setTitle_(">")
        tok_btn.setBezelStyle_(1)
        tok_btn.setFont_(NSFont.systemFontOfSize_(10))
        tok_btn.setTarget_(self)
        tok_btn.setAction_(objc.selector(self._toggle_tokens, signature=b"v@:@"))
        content.addSubview_(tok_btn)  # type: ignore[attr-defined]

        model_w = _PANEL_WIDTH - _PAD - 16 - _PAD - 24 - _PAD * 3
        model_field = NSTextField.alloc().initWithFrame_(
            NSMakeRect(_PAD, y, model_w, 24)
        )
        model_field.setStringValue_(
            str(self._session_state.get("model", self._settings.llm_model))
        )
        model_field.setPlaceholderString_("model (e.g. gemini/gemini-2.5-flash)")
        model_field.setBezeled_(True)
        model_field.setDrawsBackground_(True)
        content.addSubview_(model_field)  # type: ignore[attr-defined]
        self._model_field = model_field

        return y + 24 + _PAD

    def _build_chat_log(self, content: object, y: float) -> None:
        log_h = _PANEL_HEIGHT - y - _PAD
        scroll = NSScrollView.alloc().initWithFrame_(
            NSMakeRect(_PAD, y, _PANEL_WIDTH - 2 * _PAD, log_h)
        )
        scroll.setHasVerticalScroller_(True)
        scroll.setAutoresizingMask_(18)  # NSViewWidthSizable | NSViewHeightSizable

        text_view = NSTextView.alloc().initWithFrame_(
            NSMakeRect(0, 0, _PANEL_WIDTH - 2 * _PAD, log_h)
        )
        text_view.setEditable_(False)
        text_view.setFont_(NSFont.monospacedSystemFontOfSize_weight_(11, 0))
        text_view.setAutoresizingMask_(2)  # NSViewWidthSizable
        scroll.setDocumentView_(text_view)
        content.addSubview_(scroll)  # type: ignore[attr-defined]
        self._log_view = text_view

    @staticmethod
    def _small_label(text: str, parent: NSView, x: float, y: float) -> NSTextField:
        lbl = NSTextField.labelWithString_(text)
        lbl.setFrame_(NSMakeRect(x, y, 300, 14))
        lbl.setFont_(NSFont.systemFontOfSize_(9))
        lbl.setTextColor_(NSColor.secondaryLabelColor())
        parent.addSubview_(lbl)
        return lbl

    # ------------------------------------------------------------------
    # Panel positioning / toggling
    # ------------------------------------------------------------------

    def _toggle_panel(self, _sender: object = None) -> None:
        if not self._agent_started:
            self._agent = AgentThread(self._settings)
            self._agent.set_on_ready(self._on_agent_ready)
            self._agent.set_on_event(self._on_agent_event)
            self._agent.start()
            self._agent_started = True

        if self._panel is None:
            self._build_panel()
        assert self._panel is not None
        if self._panel_visible:
            self._panel.orderOut_(None)
            self._panel_visible = False
        else:
            self._position_panel()
            self._panel.orderFront_(None)
            self._panel_visible = True
            if self._agent:
                self._agent.ping_obsidian(self._on_obsidian_ping)

    def _position_panel(self) -> None:
        assert self._panel is not None
        status_item = self._status_item  # type: ignore[attr-defined]
        if status_item is None:
            return
        button = status_item.button()
        if button is None:
            return
        frame = button.window().frame()
        icon_x = frame.origin.x + frame.size.width / 2
        icon_y = frame.origin.y
        self._panel.setFrameOrigin_(
            NSPoint(icon_x - _PANEL_WIDTH / 2, icon_y - _PANEL_HEIGHT - 4)
        )

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------

    def _handle_send(self, text: str) -> None:
        model = (
            str(self._model_field.stringValue())
            if self._model_field
            else self._settings.llm_model
        )
        self._settings.llm_model = model
        self._append_log(f"You:  {text}\n")
        self._set_status("Thinking…")
        if self._agent:
            self._agent.send(text)

    def _append_log(self, text: str) -> None:
        def _do() -> None:
            if self._log_view is None:
                return
            storage = self._log_view.textStorage()
            end = storage.length()
            storage.replaceCharactersInRange_withString_(objc.NSRange(end, 0), text)
            self._log_view.scrollRangeToVisible_(objc.NSRange(storage.length(), 0))

        _dispatch_main(_do)

    def _set_status(self, text: str) -> None:
        def _do() -> None:
            if self._status_field:
                self._status_field.setStringValue_(text)

        _dispatch_main(_do)

    # ------------------------------------------------------------------
    # Token panel
    # ------------------------------------------------------------------

    def _toggle_tokens(self, _sender: object) -> None:
        self._token_visible = not self._token_visible
        if self._token_panel:
            self._token_panel.setHidden_(not self._token_visible)

    def _update_tokens(self) -> None:
        def _do() -> None:
            if self._tok_prompt_lbl:
                self._tok_prompt_lbl.setStringValue_(f"prompt: {self._last_prompt:,}")
            if self._tok_completion_lbl:
                self._tok_completion_lbl.setStringValue_(
                    f"completion: {self._last_completion:,}"
                )
            if self._tok_session_lbl:
                self._tok_session_lbl.setStringValue_(
                    f"session: {self._session_total:,}"
                )

        _dispatch_main(_do)

    # ------------------------------------------------------------------
    # Event callbacks (agent thread → main thread)
    # ------------------------------------------------------------------

    def _on_agent_ready(self, ok: bool, error: str) -> None:
        if ok:
            self._append_log("Ready. Type a message below.\n\n")
        else:
            self._append_log(f"Failed to connect: {error}\n")

    def _on_agent_event(self, event: object) -> None:
        match event:
            case StatusEvent(message=msg):
                self._set_status(f"⟳ {msg}…")
            case TextChunk(text=chunk):
                self._append_log(chunk)
            case ToolErrorEvent(tool=tool, error=err):
                self._append_log(f"✗ {tool}: {err}\n")
            case UsageEvent(prompt_tokens=pt, completion_tokens=ct, session_total=st):
                self._last_prompt = pt
                self._last_completion = ct
                self._session_total = st
                self._update_tokens()
            case FileAccessEvent(path=path):
                self._file_paths = ([path, *self._file_paths])[:5]
                paths_str = "  ".join(self._file_paths)

                def _do() -> None:
                    if self._file_field:
                        self._file_field.setStringValue_(paths_str)

                _dispatch_main(_do)
            case DoneEvent():
                self._set_status("")
                self._append_log("\n")
                model = (
                    str(self._model_field.stringValue()) if self._model_field else ""
                )
                if model:
                    state.save({"model": model})

    def _on_obsidian_ping(self, online: bool) -> None:
        def _do() -> None:
            if self._obsidian_dot:
                color = (
                    NSColor.systemGreenColor() if online else NSColor.systemRedColor()
                )
                self._obsidian_dot.setTextColor_(color)
                self._obsidian_dot.setToolTip_(
                    "Obsidian online" if online else "Obsidian offline"
                )

        _dispatch_main(_do)

    # ------------------------------------------------------------------
    # rumps hooks
    # ------------------------------------------------------------------

    @rumps.clicked("Open")
    def _open(self, _: object) -> None:
        self._toggle_panel()

    def _quit(self, _: object) -> None:
        if self._agent:
            self._agent.stop()
        rumps.quit_application()


def _dispatch_main(fn: typing.Callable[[], None]) -> None:
    from AppKit import NSApplication  # noqa: PLC0415

    app = NSApplication.sharedApplication()
    if not app:
        return
    app.performSelectorOnMainThread_withObject_waitUntilDone_(
        objc.selector(lambda _: fn(), signature=b"v@:@"),
        None,
        False,
    )


def main() -> None:
    dotenv.load_dotenv()
    setup_logging()
    DragonglassMenubarApp().run()
