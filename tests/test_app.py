import json

import pytest
from textual.widgets import Input

from typer_racer_cli.app import TyperRacerApp
from typer_racer_cli.screens.results import ResultsScreen
from typer_racer_cli.screens.setup import SetupScreen
from typer_racer_cli.screens.typing import TypingScreen

KEYS = {" ": "space", "=": "equals_sign", "(": "left_parenthesis", ")": "right_parenthesis", ":": "colon"}


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    root = tmp_path / "repo"
    root.mkdir()
    (root / "main.py").write_text("def f():\n    x = 1\n")
    return root


async def wait_for_screen(pilot, screen_type):
    for _ in range(100):
        if isinstance(pilot.app.screen, screen_type):
            return pilot.app.screen
        await pilot.pause(0.02)
    raise AssertionError(f"{screen_type.__name__} se neukázala")


async def start_test(pilot, repo, mode_index):
    setup = await wait_for_screen(pilot, SetupScreen)
    setup.query_one("#repo", Input).value = str(repo)
    await pilot.press("enter")
    for _ in range(100):
        if setup.step == "languages":
            break
        await pilot.pause(0.02)
    assert setup.step == "languages"
    await pilot.press("enter")
    assert setup.step == "modes"
    await pilot.press(*["down"] * mode_index, "enter")
    return await wait_for_screen(pilot, TypingScreen)


async def type_text(pilot, text):
    await pilot.press(*[KEYS.get(c, c) for c in text])


async def test_block_flow(repo, tmp_path):
    async with TyperRacerApp().run_test(size=(100, 30)) as pilot:
        typing = await start_test(pilot, repo, 0)
        assert typing.session.lines == ["def f():", "    x = 1"]

        await type_text(pilot, "def g")
        await pilot.press("backspace")
        await type_text(pilot, "f():")
        await pilot.press("enter")
        assert typing.session.row == 1 and typing.session.col == 4
        await type_text(pilot, "x = 1")

        results = await wait_for_screen(pilot, ResultsScreen)
        assert results.stats.lines == 2 and results.stats.errors == 1
        scores = json.loads((tmp_path / "data" / "typer_racer_cli" / "scores.json").read_text())
        assert list(scores) == [f"{repo.resolve()}|Python|block"]

        await pilot.press("enter")
        await wait_for_screen(pilot, TypingScreen)
        await pilot.press("escape")
        setup = await wait_for_screen(pilot, SetupScreen)
        assert setup.step == "modes"


async def test_minute_flow_keeps_feeding_lines(repo):
    async with TyperRacerApp().run_test(size=(100, 30)) as pilot:
        typing = await start_test(pilot, repo, 1)
        assert typing.config.mode == "minute"
        for _ in range(15):
            await type_text(pilot, "def f():")
            await pilot.press("enter")
            await type_text(pilot, "x = 1")
            await pilot.press("enter")
        assert typing.session.completed_lines == 30
        assert len(typing.session.lines) - typing.session.row >= 20
        await pilot.press("tab")
        assert typing.session.completed_lines == 0


async def test_bad_repo_shows_error(repo):
    async with TyperRacerApp().run_test(size=(100, 30)) as pilot:
        setup = await wait_for_screen(pilot, SetupScreen)
        setup.query_one("#repo", Input).value = "to neni repo"
        await pilot.press("enter")
        await pilot.pause(0.2)
        assert setup.step == "repo"
        assert setup.query_one("#status").has_class("error")
