from __future__ import annotations

from itertools import islice

from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static

from ..config import MINUTE_SECONDS, MODES, TestConfig
from ..engine import CORRECT, PENDING, WRONG, TypingSession, indent_of
from ..snippets import block_snippet, line_stream

STYLE_PENDING = "grey50"
STYLE_CORRECT = "green"
STYLE_WRONG = "bold red"
STYLE_WRONG_SPACE = "on red"
STYLE_CURSOR = "reverse"
NEWLINE = "↵"
# minutový mód: kolik řádků držet připravených před kurzorem
STREAM_BUFFER = 40


def render_session(session: TypingSession, height: int) -> Text:
    """Okno `height` řádků kolem kurzoru, obarvené podle stavu znaků."""
    total = len(session.lines)
    start = max(0, session.row - height // 3)
    start = max(0, min(start, total - height))
    text = Text(no_wrap=True)
    for i in range(start, min(total, start + height)):
        line = session.lines[i]
        states = session.states[i]
        indent = indent_of(line)
        text.append(line[:indent])
        for col in range(indent, len(line)):
            char = line[col]
            state = states[col] if i <= session.row else PENDING
            if state == CORRECT:
                style = STYLE_CORRECT
            elif state == WRONG:
                style = STYLE_WRONG_SPACE if char == " " else STYLE_WRONG
            else:
                style = STYLE_PENDING
            if i == session.row and col == session.col and not session.finished:
                style = STYLE_CURSOR
            text.append(char, style)
        if i < session.row:
            text.append(NEWLINE, STYLE_CORRECT)
        elif i == session.row and session.at_line_end and not session.finished:
            text.append(NEWLINE, STYLE_CURSOR)
        else:
            text.append(NEWLINE, STYLE_PENDING)
        text.append("\n")
    return text


class TypingScreen(Screen):
    def __init__(self, config: TestConfig) -> None:
        super().__init__()
        self.config = config
        self.session = TypingSession([])
        self.stream = iter(())
        self.done = False

    def compose(self) -> ComposeResult:
        yield Static("", id="stats")
        yield Static("", id="code")
        yield Static("Esc menu · Tab nový úryvek · Ctrl+Q konec", id="help")

    def on_mount(self) -> None:
        self.new_session()
        self.set_interval(0.1, self.tick)

    def on_resize(self) -> None:
        self.refresh_code()

    def new_session(self) -> None:
        if self.config.mode == "minute":
            self.stream = line_stream(self.config.files)
            lines = list(islice(self.stream, STREAM_BUFFER))
        else:
            lines = block_snippet(self.config.files, self.config.language)
        self.session = TypingSession(lines)
        self.done = False
        self.refresh_code()
        self.refresh_stats()

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.app.pop_screen()
        elif event.key == "tab":
            self.new_session()
        elif event.key == "enter":
            self.session.enter()
        elif event.key == "backspace":
            self.session.backspace()
        elif event.is_printable and event.character:
            self.session.type_char(event.character)
        else:
            return
        event.stop()
        event.prevent_default()
        if self.is_current:
            self.after_input()

    def after_input(self) -> None:
        if self.config.mode == "minute" and len(self.session.lines) - self.session.row < STREAM_BUFFER // 2:
            self.session.add_lines(islice(self.stream, STREAM_BUFFER))
        self.refresh_code()
        self.refresh_stats()
        if self.session.finished:
            self.show_results()

    def tick(self) -> None:
        if self.done or not self.session.started:
            return
        if self.config.mode == "minute" and self.session.elapsed() >= MINUTE_SECONDS:
            self.session.finish()
            self.show_results()
            return
        self.refresh_stats()

    def show_results(self) -> None:
        if self.done:
            return
        self.done = True
        from .results import ResultsScreen

        self.app.switch_screen(ResultsScreen(self.config, self.session.stats()))

    def refresh_code(self) -> None:
        code = self.query_one("#code", Static)
        height = code.content_size.height or 15
        code.update(render_session(self.session, height))

    def refresh_stats(self) -> None:
        stats = self.session.stats()
        if self.config.mode == "minute":
            left = max(0, MINUTE_SECONDS - stats.elapsed)
            clock = f"zbývá {left:4.1f} s"
            lines = f"řádky {stats.lines}"
        else:
            clock = f"čas {stats.elapsed:5.1f} s"
            lines = f"řádky {stats.lines}/{len(self.session.lines)}"
        self.query_one("#stats", Static).update(
            f"{MODES[self.config.mode]} · {self.config.language} · {self.config.repo}"
            f"    {clock}    WPM {stats.wpm:3.0f}    přesnost {stats.accuracy:3.0f} %    {lines}"
        )
