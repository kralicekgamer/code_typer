"""Načtení kódu z repa a výběr úryvků k psaní."""

from __future__ import annotations

import os
import random
import re
from pathlib import Path
from typing import Iterator

from .engine import indent_of

LANGUAGES: dict[str, tuple[str, ...]] = {
    "Python": (".py",),
    "JavaScript": (".js", ".jsx", ".mjs", ".cjs"),
    "TypeScript": (".ts", ".tsx"),
    "Rust": (".rs",),
    "Go": (".go",),
    "C": (".c", ".h"),
    "C++": (".cpp", ".cc", ".cxx", ".hpp", ".hh"),
    "Java": (".java",),
    "C#": (".cs",),
    "PHP": (".php",),
    "Ruby": (".rb",),
    "Kotlin": (".kt", ".kts"),
    "Swift": (".swift",),
    "Bash": (".sh", ".bash"),
    "HTML": (".html", ".htm"),
    "CSS": (".css", ".scss"),
}
EXTENSIONS = {ext: lang for lang, exts in LANGUAGES.items() for ext in exts}

SKIP_DIRS = {
    ".git", "node_modules", "vendor", "dist", "build", "target", ".venv", "venv",
    "__pycache__", ".next", ".idea", ".vscode", "third_party",
}
MAX_FILE_BYTES = 200_000
MAX_FILES = 3000
MAX_LINE_LENGTH = 100
BLOCK_LINES = 15

# soubor = seznam vyčištěných řádků; korpus = jazyk -> soubory
Corpus = dict[str, list[list[str]]]


def clean_lines(text: str) -> list[str]:
    """Řádky, které jdou napsat na běžné klávesnici: bez prázdných, dlouhých a ne-ASCII."""
    lines = []
    for raw in text.splitlines():
        line = raw.expandtabs(4).rstrip()
        if not line or len(line) > MAX_LINE_LENGTH:
            continue
        if not all(" " <= c <= "~" for c in line):
            continue
        lines.append(line)
    return lines


def load_corpus(root: Path) -> Corpus:
    corpus: Corpus = {}
    seen = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            lang = EXTENSIONS.get(Path(name).suffix.lower())
            if lang is None or ".min." in name:
                continue
            path = Path(dirpath) / name
            try:
                if path.is_symlink() or path.stat().st_size > MAX_FILE_BYTES:
                    continue
                lines = clean_lines(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError):
                continue
            if lines:
                corpus.setdefault(lang, []).append(lines)
            seen += 1
            if seen >= MAX_FILES:
                return corpus
    return corpus


def language_sizes(corpus: Corpus) -> list[tuple[str, int]]:
    """Jazyky v repu s počtem řádků, od největšího."""
    sizes = [(lang, sum(len(f) for f in files)) for lang, files in corpus.items()]
    return sorted(sizes, key=lambda item: -item[1])


_MODS = (
    r"(?:(?:public|private|protected|internal|fileprivate|static|final|abstract|sealed|open|override"
    r"|async|export|default|data|suspend|virtual|partial|readonly|inline)\s+)*"
)
_METHOD = r"|(?:public|private|protected|internal)\s[^=;]*\([^;]*$"
_JS = (
    r"(?:export )?(?:default )?(?:async )?function\b"
    r"|(?:export )?(?:default )?(?:abstract )?class "
    r"|(?:export )?interface "
    r"|(?:export )?(?:const|let) \w+ = (?:async )?(?:\(|function\b)"
)
_C = r"(?:struct|class|enum|union|namespace) \w+|[A-Za-z_][\w\s*&:<>,~]*\([^;]*[{)]$"
# čím začíná definice (testuje se na řádku bez odsazení); jazyk bez vzoru definice nemá
DEFINITION_START: dict[str, re.Pattern[str]] = {
    lang: re.compile(pattern)
    for lang, pattern in {
        "Python": r"(?:async )?def |class ",
        "JavaScript": _JS,
        "TypeScript": _JS,
        "Rust": r"(?:pub(?:\([\w:]+\))? )?(?:async )?(?:unsafe )?(?:fn|struct|enum|impl|trait)\b",
        "Go": r"func |type \w+ (?:struct|interface)",
        "C": _C,
        "C++": _C,
        "Java": _MODS + r"(?:class|interface|enum|record) " + _METHOD,
        "C#": _MODS + r"(?:class|interface|enum|record|struct) " + _METHOD,
        "PHP": _MODS + r"(?:function|class|interface|trait) ",
        "Ruby": r"(?:def|class|module) ",
        "Kotlin": _MODS + r"(?:fun|class|object|interface) ",
        "Swift": _MODS + r"(?:func|class|struct|enum|protocol|extension) ",
    }.items()
}
# v C/C++ se hlavička funkce pozná jen na neodsazeném řádku (jinak by seděl i `if (x) {`)
_TOP_LEVEL_ONLY = {"C", "C++"}


def is_definition(line: str, language: str | None) -> bool:
    pattern = DEFINITION_START.get(language or "")
    if pattern is None:
        return False
    if language in _TOP_LEVEL_ONLY and line.startswith(" "):
        return False
    return pattern.match(line.lstrip(" ")) is not None


def _dedent(lines: list[str]) -> list[str]:
    """Posune blok doleva tak, aby první řádek začínal u kraje."""
    base = indent_of(lines[0])
    return [line[min(base, indent_of(line)) :] for line in lines]


def block_snippet(
    files: list[list[str]],
    language: str | None = None,
    n: int = BLOCK_LINES,
    rng: random.Random | None = None,
) -> list[str]:
    """Náhodný souvislý blok n řádků, který začíná definicí (def, class, fn…).

    Jazyk bez vzoru definice nebo repo bez definic: okno od neodsazeného řádku.
    """
    rng = rng or random
    starts = [
        (lines, i) for lines in files for i, line in enumerate(lines) if is_definition(line, language)
    ]
    if not starts:
        return _window_snippet(files, n, rng)
    # raději definice, za kterými je celých n řádků; jinak ty s nejdelším zbytkem souboru
    longest = min(n, max(len(lines) - i for lines, i in starts))
    lines, start = rng.choice([(lines, i) for lines, i in starts if len(lines) - i >= longest])
    return _dedent(lines[start : start + n])


def _window_snippet(files: list[list[str]], n: int, rng) -> list[str]:
    big = [f for f in files if len(f) >= n]
    if not big:
        # žádný soubor není dost dlouhý: poskládat z více souborů
        stream = line_stream(files, rng)
        total = sum(len(f) for f in files)
        return [next(stream) for _ in range(min(n, total))]
    lines = rng.choice(big)
    starts = range(len(lines) - n + 1)
    top_level = [i for i in starts if indent_of(lines[i]) == 0]
    start = rng.choice(top_level or starts)
    return lines[start : start + n]


def line_stream(files: list[list[str]], rng: random.Random | None = None) -> Iterator[str]:
    """Nekonečný proud řádků: soubory jdou za sebou v náhodném pořadí."""
    rng = rng or random
    files = [f for f in files if f]
    if not files:
        return
    while True:
        order = list(files)
        rng.shuffle(order)
        for lines in order:
            yield from lines
