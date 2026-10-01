#!/bin/sh
set -eu

PROJECT_NAME="code_typer"
INSTALL_DIR=${CODE_TYPER_INSTALL_DIR:-"$HOME/.local/share/$PROJECT_NAME"}
BIN_DIR=${CODE_TYPER_BIN_DIR:-"$HOME/.local/bin"}
WRAPPER="$BIN_DIR/$PROJECT_NAME"
# cloned repos and personal bests written by the app itself
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/typer_racer_cli"
SCORES_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/typer_racer_cli"

rm -f "$WRAPPER"
rm -rf "$INSTALL_DIR" "$CACHE_DIR" "$SCORES_DIR"

echo "Removed code_typer from $INSTALL_DIR"
