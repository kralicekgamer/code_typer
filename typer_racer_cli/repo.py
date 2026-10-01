"""Import repa: GitHub URL / owner/repo (mělký clone do cache) nebo lokální složka."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

_NAME = r"[A-Za-z0-9_][A-Za-z0-9_.-]*"
_PATTERNS = [
    re.compile(rf"^(?:https?://)?(?:www\.)?github\.com/({_NAME})/({_NAME}?)(?:\.git)?/?$"),
    re.compile(rf"^git@github\.com:({_NAME})/({_NAME}?)(?:\.git)?$"),
    re.compile(rf"^({_NAME})/({_NAME}?)(?:\.git)?$"),
]
CLONE_TIMEOUT = 180


class RepoError(Exception):
    pass


@dataclass(frozen=True)
class RepoSpec:
    owner: str
    name: str

    @property
    def label(self) -> str:
        return f"{self.owner}/{self.name}"

    @property
    def url(self) -> str:
        return f"https://github.com/{self.owner}/{self.name}.git"


def cache_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
    return Path(base) / "typer_racer_cli"


def parse_repo(text: str) -> RepoSpec:
    text = text.strip()
    for pattern in _PATTERNS:
        match = pattern.match(text)
        if match:
            return RepoSpec(match.group(1), match.group(2))
    raise RepoError("Nerozumím. Zadej owner/repo nebo adresu repa na GitHubu.")


def ensure_repo(spec: RepoSpec, refresh: bool = False) -> Path:
    """Vrátí cestu k naklonovanému repu; klonuje jen když v cache není (nebo refresh)."""
    dest = cache_dir() / "repos" / f"{spec.owner}__{spec.name}"
    if dest.exists() and not refresh:
        return dest
    if shutil.which("git") is None:
        raise RepoError("Nenašel jsem git. Nainstaluj ho a zkus to znovu.")
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "--quiet", "--", spec.url, str(tmp)],
            capture_output=True,
            text=True,
            timeout=CLONE_TIMEOUT,
            # bez dotazu na heslo: soukromé repo bez přístupu rovnou selže
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
    except subprocess.TimeoutExpired:
        shutil.rmtree(tmp, ignore_errors=True)
        raise RepoError("Stahování trvalo moc dlouho. Zkus to znovu nebo menší repo.")
    if result.returncode != 0:
        shutil.rmtree(tmp, ignore_errors=True)
        detail = result.stderr.strip().splitlines()[-1:] or ["neznámá chyba"]
        raise RepoError(
            f"Repo {spec.label} se nepodařilo stáhnout ({detail[0]}). "
            "Zkontroluj název a jestli k němu máš přístup."
        )
    shutil.rmtree(dest, ignore_errors=True)
    tmp.rename(dest)
    return dest


def resolve(text: str, refresh: bool = False) -> tuple[str, Path]:
    """Ze vstupu uživatele udělá (popisek, cesta ke složce s kódem)."""
    text = text.strip()
    if not text:
        raise RepoError("Zadej owner/repo nebo adresu repa na GitHubu.")
    local = Path(text).expanduser()
    if (text.startswith(("/", "~", ".")) or os.sep in text) and local.is_dir():
        return str(local.resolve()), local.resolve()
    spec = parse_repo(text)
    return spec.label, ensure_repo(spec, refresh)
