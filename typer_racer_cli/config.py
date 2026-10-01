from __future__ import annotations

from dataclasses import dataclass

MODES = {
    "block": "Blok",
    "minute": "Minuta",
}
MINUTE_SECONDS = 60


@dataclass(frozen=True)
class TestConfig:
    __test__ = False  # není to pytest test

    repo: str
    language: str
    mode: str
    files: list[list[str]]
