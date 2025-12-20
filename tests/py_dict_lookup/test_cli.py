from __future__ import annotations

from dataclasses import dataclass

import pytest
from typer.testing import CliRunner

from py_dict_lookup.cli import app
from py_dict_lookup.providers import registry as reg
from py_dict_lookup.providers.base import DefinitionResult, NotFound, Provider, ProviderError, SynonymsResult

runner = CliRunner()


@dataclass(frozen=True, slots=True)
class FakeProvider(Provider):
    name: str = "mw"

    def define(self, word: str, *, timeout_seconds: float) -> DefinitionResult:
        # Deterministic, stable output for assertions
        return DefinitionResult(word=word, items=("fake definition",))

    def synonyms(self, word: str, *, limit: int, timeout_seconds: float) -> SynonymsResult:
        # Return exactly `limit` items so tests can assert behavior precisely
        items = tuple([f"syn{i}" for i in range(1, limit + 1)])
        return SynonymsResult(word=word, items=items)


@dataclass(frozen=True, slots=True)
class ErroringProvider(Provider):
    """
    Provider used for error-mapping tests.
    Controlled by constructor flags.
    """

    name: str = "mw"
    mode: str = "provider_error"  # "provider_error" | "not_found"

    def define(self, word: str, *, timeout_seconds: float) -> DefinitionResult:
        if self.mode == "not_found":
            raise NotFound(word=word, suggestions=("alpha", "beta"))
        raise ProviderError("boom")

    def synonyms(self, word: str, *, limit: int, timeout_seconds: float) -> SynonymsResult:
        if self.mode == "not_found":
            raise NotFound(word=word, suggestions=("alpha", "beta"))
        raise ProviderError("boom")


@pytest.fixture(autouse=True)
def fake_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Replace provider registry with a deterministic fake for all tests.
    Default to FakeProvider for 'mw'.
    """
    monkeypatch.setattr(reg, "_PROVIDERS", {"mw": lambda settings: FakeProvider()}, raising=True)


def test_version_runs_without_command() -> None:
    res = runner.invoke(app, ["--version"])
    assert res.exit_code == 0
    assert res.output.strip() != ""


def test_help_shows_commands_and_aliases() -> None:
    res = runner.invoke(app, ["--help"])
    assert res.exit_code == 0
    out = res.output
    # Primary commands
    assert "define" in out
    assert "synonyms" in out
    assert "lookup" in out
    assert "providers" in out
    # Aliases
    assert "\n│ d" in out or " d " in out
    assert "\n│ s" in out or " s " in out
    assert "\n│ l" in out or " l " in out
    assert "\n│ p" in out or " p " in out


def test_providers_lists_mw() -> None:
    res = runner.invoke(app, ["providers"])
    assert res.exit_code == 0
    assert "mw" in res.output


def test_providers_alias_p() -> None:
    res = runner.invoke(app, ["p"])
    assert res.exit_code == 0
    assert "mw" in res.output


def test_define_uses_provider() -> None:
    res = runner.invoke(app, ["define", "test"])
    assert res.exit_code == 0
    assert "Definitions:" in res.output
    assert "fake definition" in res.output


def test_define_alias_d() -> None:
    res = runner.invoke(app, ["d", "test"])
    assert res.exit_code == 0
    assert "Definitions:" in res.output
    assert "fake definition" in res.output


def test_define_missing_word_is_error() -> None:
    res = runner.invoke(app, ["define"])
    assert res.exit_code != 0
    assert "Missing argument" in res.output
    assert "WORD" in res.output


def test_synonyms_default_limit() -> None:
    res = runner.invoke(app, ["synonyms", "fast"])
    assert res.exit_code == 0
    assert "Synonyms:" in res.output
    # Default limit is 10 in the CLI; FakeProvider returns exactly `limit`.
    assert "syn10" in res.output


def test_synonyms_limit() -> None:
    res = runner.invoke(app, ["synonyms", "fast", "--limit", "3"])
    assert res.exit_code == 0
    assert "Synonyms:" in res.output
    assert "syn3" in res.output
    assert "syn4" not in res.output


def test_synonyms_alias_s() -> None:
    res = runner.invoke(app, ["s", "fast", "--limit", "2"])
    assert res.exit_code == 0
    assert "Synonyms:" in res.output
    assert "syn2" in res.output
    assert "syn3" not in res.output


def test_lookup_runs_both_sections() -> None:
    res = runner.invoke(app, ["lookup", "serendipity"])
    assert res.exit_code == 0
    out = res.output
    assert "Definitions:" in out
    assert "Synonyms:" in out
    assert "fake definition" in out
    assert "syn10" in out


def test_lookup_alias_l() -> None:
    res = runner.invoke(app, ["l", "serendipity"])
    assert res.exit_code == 0
    out = res.output
    assert "Definitions:" in out
    assert "Synonyms:" in out


def test_lookup_missing_word_is_error() -> None:
    res = runner.invoke(app, ["lookup"])
    assert res.exit_code != 0
    assert "Missing argument" in res.output
    assert "WORD" in res.output


def test_unknown_provider_is_error() -> None:
    res = runner.invoke(app, ["--provider", "nope", "define", "x"])
    assert res.exit_code != 0
    assert "Unknown provider" in res.output


def test_provider_error_is_shown(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        reg,
        "_PROVIDERS",
        {"mw": lambda settings: ErroringProvider(mode="provider_error")},
        raising=True,
    )
    res = runner.invoke(app, ["define", "x"])
    assert res.exit_code != 0
    assert "boom" in res.output


def test_not_found_includes_suggestions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        reg,
        "_PROVIDERS",
        {"mw": lambda settings: ErroringProvider(mode="not_found")},
        raising=True,
    )
    res = runner.invoke(app, ["define", "x"])
    assert res.exit_code != 0
    assert "not found" in res.output.lower()
    assert "Suggestions" in res.output
    assert "alpha" in res.output
    assert "beta" in res.output
