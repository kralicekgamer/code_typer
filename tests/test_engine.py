from typer_racer_cli.engine import CORRECT, PENDING, WRONG, TypingSession


class FakeClock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def type_text(session, text):
    for char in text:
        session.type_char(char)


def test_correct_and_wrong_chars():
    session = TypingSession(["abc", "x"])
    type_text(session, "abX")
    assert session.states[0] == [CORRECT, CORRECT, WRONG]
    assert session.errors == 1
    assert session.col == 3


def test_backspace_clears_state_and_stops_at_indent():
    session = TypingSession(["    ab", "x"])
    assert session.col == 4
    session.backspace()
    assert session.col == 4
    type_text(session, "z")
    session.backspace()
    assert session.col == 4
    assert session.states[0][4] == PENDING


def test_enter_only_at_line_end_and_skips_indent():
    session = TypingSession(["ab", "    cd", "e"])
    session.type_char("a")
    session.enter()
    assert session.row == 0 and session.errors == 1
    session.type_char("b")
    session.enter()
    assert session.row == 1 and session.col == 4
    assert session.completed_lines == 1


def test_extra_chars_at_line_end_are_errors():
    session = TypingSession(["a", "b"])
    type_text(session, "ax")
    assert session.col == 1 and session.errors == 1


def test_last_char_finishes_without_enter():
    session = TypingSession(["a", "b"])
    session.type_char("a")
    session.enter()
    assert not session.finished
    session.type_char("b")
    assert session.finished
    assert session.completed_lines == 2
    session.type_char("c")
    assert session.keystrokes == 3


def test_stats():
    clock = FakeClock()
    session = TypingSession(["abcd", "efgh", "zz"], clock=clock)
    type_text(session, "abcd")
    session.enter()
    type_text(session, "efgX")
    clock.now += 30
    stats = session.stats()
    # 7 správných znaků + 1 Enter = 8 znaků za půl minuty
    assert stats.wpm == 8 / 5 / 0.5
    assert stats.raw_wpm == 9 / 5 / 0.5
    assert stats.accuracy == 8 / 9 * 100
    assert stats.lines == 1 and stats.errors == 1 and stats.elapsed == 30


def test_timer_starts_on_first_key():
    clock = FakeClock()
    session = TypingSession(["ab"], clock=clock)
    clock.now += 50
    assert session.elapsed() == 0
    session.type_char("a")
    clock.now += 2
    assert session.elapsed() == 2
