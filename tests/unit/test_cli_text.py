from __future__ import annotations

import sys

import pytest
from conftest import ErroringProvider, strip_ansi
from typer.testing import CliRunner

from py_dict_lookup.cli import app
from py_dict_lookup.providers import registry as reg

runner = CliRunner()


def test_providers_lists_mw_text() -> None:
    res = runner.invoke(app, ["providers"])
    assert res.exit_code == 0
    assert "mw" in strip_ansi(res.output)


def test_providers_alias_p_text() -> None:
    res = runner.invoke(app, ["p"])
    assert res.exit_code == 0
    assert "mw" in strip_ansi(res.output)


def test_define_text_output_has_heading() -> None:
    res = runner.invoke(app, ["define", "test"])
    assert res.exit_code == 0
    out = strip_ansi(res.output)
    assert "Definitions:" in out
    assert "fake definition" in out


def test_define_alias_d_text() -> None:
    res = runner.invoke(app, ["d", "test"])
    assert res.exit_code == 0
    out = strip_ansi(res.output)
    assert "Definitions:" in out
    assert "fake definition" in out


def test_synonyms_default_limit_text() -> None:
    res = runner.invoke(app, ["synonyms", "fast"])
    assert res.exit_code == 0
    out = strip_ansi(res.output)
    assert "Synonyms:" in out
    assert "syn10" in out


def test_synonyms_limit_text() -> None:
    res = runner.invoke(app, ["synonyms", "fast", "--limit", "3"])
    assert res.exit_code == 0
    out = strip_ansi(res.output)
    assert "Synonyms:" in out
    assert "syn3" in out
    assert "syn4" not in out


def test_synonyms_alias_s_text() -> None:
    res = runner.invoke(app, ["s", "fast", "--limit", "2"])
    assert res.exit_code == 0
    out = strip_ansi(res.output)
    assert "Synonyms:" in out
    assert "syn2" in out
    assert "syn3" not in out


def test_lookup_runs_both_sections_text() -> None:
    res = runner.invoke(app, ["lookup", "serendipity"])
    assert res.exit_code == 0
    out = strip_ansi(res.output)
    assert "Definitions:" in out
    assert "Synonyms:" in out
    assert "fake definition" in out
    assert "syn10" in out


def test_lookup_alias_l_text() -> None:
    res = runner.invoke(app, ["l", "serendipity"])
    assert res.exit_code == 0
    out = strip_ansi(res.output)
    assert "Definitions:" in out
    assert "Synonyms:" in out


def test_unknown_provider_is_error_text() -> None:
    res = runner.invoke(app, ["--provider", "nope", "define", "x"])
    assert res.exit_code == 3
    assert "Unknown provider" in strip_ansi(res.output)


def test_provider_error_is_exit_3_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        reg,
        "_PROVIDERS",
        {"mw": lambda settings: ErroringProvider(mode="provider_error", message="boom")},
        raising=True,
    )
    res = runner.invoke(app, ["define", "x"])
    assert res.exit_code == 3
    assert "boom" in strip_ansi(res.output)


def test_config_error_is_exit_4_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        reg,
        "_PROVIDERS",
        {"mw": lambda settings: ErroringProvider(mode="config_error")},
        raising=True,
    )
    res = runner.invoke(app, ["define", "x"])
    assert res.exit_code == 4
    assert "Missing" in strip_ansi(res.output)


def test_not_found_is_exit_2_with_suggestions_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        reg,
        "_PROVIDERS",
        {"mw": lambda settings: ErroringProvider(mode="not_found")},
        raising=True,
    )
    res = runner.invoke(app, ["define", "x"])
    assert res.exit_code == 2
    out = strip_ansi(res.output).lower()
    assert "not found" in out
    assert "suggestions" in out
    assert "alpha" in out
    assert "beta" in out


def test_no_rich_forces_plain_text(monkeypatch: pytest.MonkeyPatch) -> None:
    # Pretend stdout is a TTY so Rich would normally be used.
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)

    res = runner.invoke(app, ["--no-rich", "define", "test"])
    assert res.exit_code == 0

    out = strip_ansi(res.output)
    assert "Definitions: test" in out
    # No box-drawing chars from Rich panels/tables
    assert "┏" not in out
    assert "┃" not in out
