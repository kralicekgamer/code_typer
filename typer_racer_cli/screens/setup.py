from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

from ..config import TestConfig
from ..repo import RepoError, resolve
from ..snippets import BLOCK_LINES, Corpus, language_sizes, load_corpus
from ..storage import recent_repos, remember_repo
from .typing import TypingScreen

PROMPTS = {
    "repo": "Z jakého repa chceš psát?",
    "languages": "Vyber jazyk",
    "modes": "Vyber mód",
}
HELP = {
    "repo": "Enter potvrdit · Tab poslední repa · Ctrl+R stáhnout znovu · Ctrl+Q konec",
    "languages": "Enter vybrat · Esc zpět · Ctrl+Q konec",
    "modes": "Enter vybrat · Esc zpět · Ctrl+Q konec",
}


class SetupScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "Zpět"),
        Binding("ctrl+r", "refresh", "Stáhnout znovu"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.step = "repo"
        self.repo_label = ""
        self.corpus: Corpus = {}
        self.language = ""

    def compose(self) -> ComposeResult:
        with Vertical(id="panel"):
            yield Static("typer_racer_cli", id="title")
            yield Static("", id="prompt")
            yield Input(placeholder="owner/repo nebo https://github.com/owner/repo", id="repo")
            yield OptionList(id="recent")
            yield OptionList(id="languages")
            yield OptionList(
                Option(f"Blok — {BLOCK_LINES} řádků na čas", id="block"),
                Option("Minuta — co nejvíc řádků za 60 s", id="minute"),
                id="modes",
            )
            yield Static("", id="status")
        yield Static("", id="help")

    def on_mount(self) -> None:
        self.show_step("repo")

    def on_screen_resume(self) -> None:
        self.show_step(self.step)

    def show_step(self, step: str) -> None:
        self.step = step
        self.query_one("#prompt", Static).update(PROMPTS[step])
        self.query_one("#help", Static).update(HELP[step])
        recent = self.query_one("#recent", OptionList)
        if step == "repo":
            recent.clear_options()
            recent.add_options([Option(label) for label in recent_repos()])
        self.query_one("#repo").display = step == "repo"
        recent.display = step == "repo" and recent.option_count > 0
        self.query_one("#languages").display = step == "languages"
        self.query_one("#modes").display = step == "modes"
        target = self.query_one(f"#{step}")
        if isinstance(target, OptionList) and target.highlighted is None:
            target.highlighted = 0
        target.focus()

    def set_status(self, text: str, error: bool = False) -> None:
        status = self.query_one("#status", Static)
        status.set_class(error, "error")
        status.update(text)

    # --- krok 1: repo ---

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.load(event.value)

    def action_refresh(self) -> None:
        if self.step == "repo":
            self.load(self.query_one("#repo", Input).value, refresh=True)

    def load(self, text: str, refresh: bool = False) -> None:
        if not text.strip():
            self.set_status("Zadej owner/repo nebo adresu repa na GitHubu.", error=True)
            return
        self.query_one("#repo", Input).disabled = True
        self.set_status("Stahuji a načítám repo…")
        self.fetch(text, refresh)

    @work(thread=True, exclusive=True)
    def fetch(self, text: str, refresh: bool) -> None:
        try:
            label, path = resolve(text, refresh)
            corpus = load_corpus(path)
        except RepoError as error:
            self.app.call_from_thread(self.fetch_failed, str(error))
            return
        self.app.call_from_thread(self.fetch_done, label, corpus)

    def fetch_failed(self, message: str) -> None:
        repo_input = self.query_one("#repo", Input)
        repo_input.disabled = False
        repo_input.focus()
        self.set_status(message, error=True)

    def fetch_done(self, label: str, corpus: Corpus) -> None:
        self.query_one("#repo", Input).disabled = False
        if not corpus:
            self.fetch_failed("V tomhle repu jsem nenašel kód v žádném podporovaném jazyce. Zkus jiné repo.")
            return
        remember_repo(label)
        self.repo_label = label
        self.corpus = corpus
        self.set_status(label)
        languages = self.query_one("#languages", OptionList)
        languages.clear_options()
        languages.add_options(
            [Option(f"{lang}  ({count} řádků)", id=lang) for lang, count in language_sizes(corpus)]
        )
        languages.highlighted = 0
        self.show_step("languages")

    # --- kroky 2 a 3: jazyk a mód ---

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        source = event.option_list.id
        if source == "recent":
            self.query_one("#repo", Input).value = str(event.option.prompt)
            self.load(str(event.option.prompt))
        elif source == "languages":
            self.language = event.option.id or ""
            self.show_step("modes")
        elif source == "modes":
            config = TestConfig(
                repo=self.repo_label,
                language=self.language,
                mode=event.option.id or "block",
                files=self.corpus[self.language],
            )
            self.app.push_screen(TypingScreen(config))

    def action_back(self) -> None:
        if self.step == "modes":
            self.show_step("languages")
        elif self.step == "languages":
            self.set_status("")
            self.show_step("repo")
