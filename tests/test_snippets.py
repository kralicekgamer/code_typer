import random
from itertools import islice

from typer_racer_cli.snippets import block_snippet, clean_lines, is_definition, language_sizes, line_stream, load_corpus


def test_clean_lines():
    text = "def f():\n\treturn 1   \n\n# žluťoučký\n" + "x" * 101 + "\nok\n"
    assert clean_lines(text) == ["def f():", "    return 1", "ok"]


def test_load_corpus_filters(tmp_path):
    (tmp_path / "a.py").write_text("a = 1\nb = 2\n")
    (tmp_path / "lib.min.js").write_text("x=1\n")
    (tmp_path / "app.js").write_text("let x = 1;\n")
    (tmp_path / "notes.txt").write_text("hello\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "dep.js").write_text("dep();\n")
    (tmp_path / "bin.py").write_bytes(b"\xff\xfe\x00")
    corpus = load_corpus(tmp_path)
    assert corpus == {"Python": [["a = 1", "b = 2"]], "JavaScript": [["let x = 1;"]]}
    assert language_sizes(corpus) == [("Python", 2), ("JavaScript", 1)]


def test_block_snippet_is_contiguous_and_starts_top_level():
    lines = [("    " if i % 3 else "") + f"line{i}" for i in range(60)]
    for seed in range(20):
        block = block_snippet([lines], rng=random.Random(seed))
        assert len(block) == 15
        start = lines.index(block[0])
        assert block == lines[start : start + 15]
        assert not block[0].startswith(" ")


def test_block_snippet_from_small_files():
    files = [[f"a{i}" for i in range(4)], [f"b{i}" for i in range(4)]]
    block = block_snippet(files, rng=random.Random(1))
    assert sorted(block) == sorted(files[0] + files[1])


def test_line_stream_is_endless():
    files = [["a", "b"], ["c"]]
    lines = list(islice(line_stream(files, random.Random(0)), 30))
    assert len(lines) == 30 and set(lines) == {"a", "b", "c"}
    assert list(line_stream([])) == []


PY_FILE = (
    ["import os", "X = 1"]
    + ["def first(a):"] + [f"    a += {i}" for i in range(8)]
    + ["class Thing:", "    size = 1", "    @property", "    async def method(self):"]
    + [f"        self.x = {i}" for i in range(20)]
    + ["def last():", "    pass"]
)


def test_python_block_always_starts_with_definition():
    firsts = set()
    for seed in range(50):
        block = block_snippet([PY_FILE], "Python", rng=random.Random(seed))
        assert len(block) == 15
        assert block[0].startswith(("def ", "async def ", "class "))
        firsts.add(block[0])
    assert firsts == {"def first(a):", "class Thing:", "async def method(self):"}


def test_indented_method_is_dedented():
    lines = ["class A:"] + ["    x = 1"] * 3 + ["    def m(self):"] + ["        return 1"] * 20
    blocks = [block_snippet([lines], "Python", rng=random.Random(seed)) for seed in range(20)]
    method = next(b for b in blocks if b[0] == "def m(self):")
    assert method[1] == "    return 1"


def test_definition_near_end_gives_shorter_block():
    lines = ["x = 1"] * 30 + ["def tail():", "    return 1", "    # end"]
    assert block_snippet([lines], "Python", rng=random.Random(0)) == lines[30:]


def test_fallback_without_definitions():
    lines = [f"a{i} = {i}" for i in range(40)]
    assert len(block_snippet([lines], "Python", rng=random.Random(0))) == 15
    assert len(block_snippet([lines], "CSS", rng=random.Random(0))) == 15


def test_definition_patterns():
    yes = [
        ("JavaScript", "export default async function load() {"),
        ("JavaScript", "const add = (a, b) => a + b;"),
        ("TypeScript", "export interface User {"),
        ("Rust", "pub(crate) async fn run() {"),
        ("Rust", "    impl Foo {"),
        ("Go", "func (s *Server) Start() error {"),
        ("Go", "type Server struct {"),
        ("Java", "    public static void main(String[] args) {"),
        ("C", "static int add(int a, int b) {"),
        ("Kotlin", "data class Point(val x: Int)"),
    ]
    no = [
        ("JavaScript", "const total = 5;"),
        ("JavaScript", "return function_name;"),
        ("Rust", "let fnord = 1;"),
        ("Go", "type ID int"),
        ("Java", "    private int count = compute();"),
        ("C", "    if (x) {"),
        ("C", "int add(int a, int b);"),
        ("Python", "definitely = 1"),
        ("CSS", "class {"),
    ]
    for language, line in yes:
        assert is_definition(line, language), line
    for language, line in no:
        assert not is_definition(line, language), line
