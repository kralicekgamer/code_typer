"""Logika psaní a statistiky. Nezávislé na UI."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Iterable

PENDING, CORRECT, WRONG = 0, 1, 2


def indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


@dataclass(frozen=True)
class Stats:
    wpm: float
    raw_wpm: float
    accuracy: float
    lines: int
    errors: int
    elapsed: float


class TypingSession:
    """Drží cílové řádky, pozici kurzoru a stav každého znaku.

    Odsazení se nepíše: kurzor na novém řádku začíná až za úvodními mezerami.
    Čas běží od prvního stisku klávesy.
    """

    def __init__(self, lines: Iterable[str], clock: Callable[[], float] = time.monotonic):
        self.lines: list[str] = []
        self.states: list[list[int]] = []
        self.row = 0
        self.col = 0
        self.keystrokes = 0
        self.correct_keystrokes = 0
        self.errors = 0
        self.completed_lines = 0
        self.started_at: float | None = None
        self.finished_at: float | None = None
        self._clock = clock
        self.add_lines(lines)
        if self.lines:
            self.col = indent_of(self.lines[0])

    def add_lines(self, lines: Iterable[str]) -> None:
        for line in lines:
            self.lines.append(line)
            self.states.append([PENDING] * len(line))

    @property
    def started(self) -> bool:
        return self.started_at is not None

    @property
    def finished(self) -> bool:
        return self.finished_at is not None

    @property
    def at_line_end(self) -> bool:
        return self.col >= len(self.lines[self.row])

    def _keystroke(self, correct: bool) -> None:
        if self.started_at is None:
            self.started_at = self._clock()
        self.keystrokes += 1
        if correct:
            self.correct_keystrokes += 1
        else:
            self.errors += 1

    def type_char(self, char: str) -> None:
        if self.finished or not self.lines:
            return
        line = self.lines[self.row]
        if self.at_line_end:
            # znak navíc za koncem řádku: chyba, kurzor se nehýbe
            self._keystroke(False)
            return
        correct = char == line[self.col]
        self._keystroke(correct)
        self.states[self.row][self.col] = CORRECT if correct else WRONG
        self.col += 1
        # poslední znak posledního řádku ukončí test bez Enteru
        if self.at_line_end and self.row == len(self.lines) - 1:
            self.completed_lines += 1
            self.finish()

    def enter(self) -> None:
        if self.finished or not self.lines:
            return
        if not self.at_line_end:
            self._keystroke(False)
            return
        self._keystroke(True)
        self.completed_lines += 1
        self.row += 1
        self.col = indent_of(self.lines[self.row])

    def backspace(self) -> None:
        if self.finished or not self.lines:
            return
        if self.col > indent_of(self.lines[self.row]):
            self.col -= 1
            self.states[self.row][self.col] = PENDING

    def finish(self) -> None:
        if self.finished_at is None:
            self.finished_at = self._clock()

    def elapsed(self) -> float:
        if self.started_at is None:
            return 0.0
        end = self.finished_at if self.finished_at is not None else self._clock()
        return end - self.started_at

    def stats(self) -> Stats:
        elapsed = self.elapsed()
        minutes = elapsed / 60
        # správně napsané znaky, které na obrazovce zůstaly, + Entery
        correct_chars = sum(s == CORRECT for row in self.states[: self.row + 1] for s in row)
        correct_chars += self.row
        return Stats(
            wpm=correct_chars / 5 / minutes if minutes > 0 else 0.0,
            raw_wpm=self.keystrokes / 5 / minutes if minutes > 0 else 0.0,
            accuracy=self.correct_keystrokes / self.keystrokes * 100 if self.keystrokes else 100.0,
            lines=self.completed_lines,
            errors=self.errors,
            elapsed=elapsed,
        )
