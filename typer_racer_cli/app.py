from __future__ import annotations

from textual.app import App

from .screens.setup import SetupScreen


class TyperRacerApp(App):
    CSS_PATH = "app.tcss"
    TITLE = "typer_racer_cli"
    ENABLE_COMMAND_PALETTE = False

    def on_mount(self) -> None:
        self.push_screen(SetupScreen())


def main() -> None:
    TyperRacerApp().run()


if __name__ == "__main__":
    main()
