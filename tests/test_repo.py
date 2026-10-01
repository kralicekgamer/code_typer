import pytest

from typer_racer_cli.repo import RepoError, RepoSpec, parse_repo, resolve


@pytest.mark.parametrize(
    "text",
    [
        "torvalds/linux",
        "https://github.com/torvalds/linux",
        "https://github.com/torvalds/linux.git",
        "https://github.com/torvalds/linux/",
        "github.com/torvalds/linux",
        "git@github.com:torvalds/linux.git",
        "  torvalds/linux  ",
    ],
)
def test_parse_repo(text):
    assert parse_repo(text) == RepoSpec("torvalds", "linux")


def test_parse_keeps_dots_in_name():
    assert parse_repo("vercel/next.js") == RepoSpec("vercel", "next.js")


@pytest.mark.parametrize(
    "text",
    ["", "linux", "a/b/c", "https://gitlab.com/a/b", "--upload-pack=x/y", "a/..", "a b/c", "a/b; rm -rf"],
)
def test_parse_rejects(text):
    with pytest.raises(RepoError):
        parse_repo(text)


def test_resolve_local_directory(tmp_path):
    label, path = resolve(str(tmp_path))
    assert path == tmp_path.resolve() and label == str(tmp_path.resolve())
