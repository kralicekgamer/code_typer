#!/bin/sh
set -eu

PROJECT_NAME="code_typer"
INSTALL_DIR=${CODE_TYPER_INSTALL_DIR:-"$HOME/.local/share/$PROJECT_NAME"}
BIN_DIR=${CODE_TYPER_BIN_DIR:-"$HOME/.local/bin"}
REPO_URL=${CODE_TYPER_REPO_URL:-"https://github.com/kralicekgamer/code_typer/archive/refs/heads/master.tar.gz"}
REPO_DIR="$INSTALL_DIR/repo"
VENV_DIR="$INSTALL_DIR/.venv"
WRAPPER="$BIN_DIR/$PROJECT_NAME"

for tool in python3 curl tar git; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "code_typer: $tool is required" >&2
        exit 1
    }
done

mkdir -p "$INSTALL_DIR" "$BIN_DIR"
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT INT TERM

curl -fsSL "$REPO_URL" -o "$TEMP_DIR/code_typer.tar.gz"
tar -xzf "$TEMP_DIR/code_typer.tar.gz" -C "$TEMP_DIR"
EXTRACTED_DIR=$(find "$TEMP_DIR" -mindepth 1 -maxdepth 1 -type d -print -quit)
if [ -z "$EXTRACTED_DIR" ]; then
    echo "code_typer: downloaded archive is empty" >&2
    exit 1
fi
rm -rf "$REPO_DIR"
mv "$EXTRACTED_DIR" "$REPO_DIR"

if [ ! -x "$VENV_DIR/bin/python" ]; then
    python3 -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip >/dev/null
"$VENV_DIR/bin/python" -m pip install --upgrade "$REPO_DIR"

cat > "$WRAPPER" <<WRAPPER_EOF
#!/bin/sh
exec "$VENV_DIR/bin/code_typer" "\$@"
WRAPPER_EOF
chmod +x "$WRAPPER"

echo "Installed code_typer to $WRAPPER"
case ":${PATH:-}:" in
    *:"$BIN_DIR":*) ;;
    *) echo "Add $BIN_DIR to PATH to run code_typer from any shell." ;;
esac
