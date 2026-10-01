# Code Typer

A typing speed test for the terminal. Instead of plain text you type real code from your own GitHub repo. Correct characters turn green, wrong ones red.

## Install

```sh
curl -s https://raw.githubusercontent.com/kralicekgamer/code_typer/refs/heads/master/install.sh | bash
```

The installer creates an isolated environment in `$HOME/.local/share/code_typer` and installs the command as `$HOME/.local/bin/code_typer`. Add `$HOME/.local/bin` to your `PATH` if the installer tells you to. It needs `python3`, `curl`, `tar` and `git`.

## Run

```sh
code_typer
```

Enter a repo (`owner/repo`, a GitHub URL or a local folder), pick a language and a mode, then type.

Block mode gives you 15 lines starting at a function or class and measures your time. Minute mode counts how many lines you finish in 60 seconds.

Indentation is skipped for you, press Enter at the end of each line. Tab loads a new snippet, Esc goes back, Ctrl+Q quits.

## Uninstall

```sh
curl -s https://raw.githubusercontent.com/kralicekgamer/code_typer/refs/heads/master/uninstall.sh | bash
```

The uninstall script removes the wrapper, the installation directory, the cached repos and your saved scores.
