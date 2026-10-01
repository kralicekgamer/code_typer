"""Naposledy použitá repa a osobní rekordy (malé JSON soubory)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .engine import Stats
from .repo import cache_dir

MAX_RECENT = 8


def data_dir() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"
    return Path(base) / "typer_racer_cli"


def _read(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _write(path: Path, data) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass  # rekordy nejsou důvod shodit test


def recent_repos() -> list[str]:
    data = _read(cache_dir() / "recent.json", [])
    return [r for r in data if isinstance(r, str)] if isinstance(data, list) else []


def remember_repo(label: str) -> None:
    repos = [label] + [r for r in recent_repos() if r != label]
    _write(cache_dir() / "recent.json", repos[:MAX_RECENT])


def save_score(repo: str, language: str, mode: str, stats: Stats) -> tuple[bool, dict | None]:
    """Uloží výsledek, pokud je rekord. Vrací (je_rekord, předchozí_rekord)."""
    path = data_dir() / "scores.json"
    scores = _read(path, {})
    if not isinstance(scores, dict):
        scores = {}
    key = f"{repo}|{language}|{mode}"
    best = scores.get(key) if isinstance(scores.get(key), dict) else None
    # minuta: rozhodují řádky, pak WPM; blok: jen WPM
    rank = (lambda s: (s.get("lines", 0), s.get("wpm", 0))) if mode == "minute" else (lambda s: s.get("wpm", 0))
    current = {"wpm": round(stats.wpm, 1), "lines": stats.lines, "accuracy": round(stats.accuracy, 1)}
    is_record = best is None or rank(current) > rank(best)
    if is_record:
        scores[key] = current
        _write(path, scores)
    return is_record, best
