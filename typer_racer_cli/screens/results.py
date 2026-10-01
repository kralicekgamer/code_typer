from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Static

from ..config import MODES, TestConfig
from ..engine import Stats
from ..storage import save_score


class ResultsScreen(Screen):
    BINDINGS = [
        Binding("enter", "again", "Znovu"),
        Binding("m,escape", "menu", "Menu"),
        Binding("q", "quit", "Konec"),
    ]

    def __init__(self, config: TestConfig, stats: Stats) -> None:
        super().__init__()
        self.config = config
        self.stats = stats

    def compose(self) -> ComposeResult:
        config, stats = self.config, self.stats
        is_record, best = save_score(config.repo, config.language, config.mode, stats)
        if is_record and best is None:
            record = "První výsledek pro tohle repo, jazyk a mód."
        elif is_record:
            record = "Nový osobní rekord!"
        elif config.mode == "minute":
            record = f"Rekord: {best.get('lines', 0)} řádků, {best.get('wpm', 0):.0f} WPM"
        else:
            record = f"Rekord: {best.get('wpm', 0):.0f} WPM"
        headline = f"{stats.lines} řádků za minutu" if config.mode == "minute" else f"{stats.wpm:.0f} WPM"
        rows = [
            ("WPM", f"{stats.wpm:.0f}"),
            ("Raw WPM", f"{stats.raw_wpm:.0f}"),
            ("Přesnost", f"{stats.accuracy:.1f} %"),
            ("Řádky", str(stats.lines)),
            ("Čas", f"{stats.elapsed:.1f} s"),
            ("Chyby", str(stats.errors)),
        ]
        with Vertical(id="panel"):
            yield Static(f"{MODES[config.mode]} · {config.language} · {config.repo}", id="prompt")
            yield Static(headline, id="headline")
            yield Static("\n".join(f"{name:<10}{value:>8}" for name, value in rows), id="rows")
            yield Static(record, id="record", classes="record" if is_record else "")
        yield Static("Enter znovu · M menu · Q konec", id="help")

    def action_again(self) -> None:
        from .typing import TypingScreen

        self.app.switch_screen(TypingScreen(self.config))

    def action_menu(self) -> None:
        self.app.pop_screen()

    def action_quit(self) -> None:
        self.app.exit()
