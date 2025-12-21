from __future__ import annotations

from typer.testing import CliRunner

from py_dict_lookup.cli import app

from conftest import strip_ansi  # noqa: F401  (imported for stable help assertions)

runner = CliRunner()


def test_version_runs_without_command() -> None:
    res = runner.invoke(app, ["--version"])
    assert res.exit_code == 0
    assert res.output.strip() != ""


def test_help_shows_primary_commands() -> None:
    """
    Help output is formatting-dependent (terminal width, Rich/Click rendering).
    We only assert on primary command names being present somewhere.
    """
    res = runner.invoke(app, ["--help"])
    assert res.exit_code == 0
    out = strip_ansi(res.output)

    assert "define" in out
    assert "synonyms" in out
    assert "lookup" in out
    assert "providers" in out


def test_define_missing_word_is_error() -> None:
    res = runner.invoke(app, ["define"])
    assert res.exit_code != 0
    out = strip_ansi(res.output)
    assert "Missing argument" in out
    assert "WORD" in out


def test_lookup_missing_word_is_error() -> None:
    res = runner.invoke(app, ["lookup"])
    assert res.exit_code != 0
    out = strip_ansi(res.output)
    assert "Missing argument" in out
    assert "WORD" in out
