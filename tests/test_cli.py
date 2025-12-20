from __future__ import annotations

from dataclasses import dataclass

import pytest
from typer.testing import CliRunner

from py_dict_lookup.cli import app
from py_dict_lookup.providers import registry as reg
from py_dict_lookup.providers.base import DefinitionResult, Provider, SynonymsResult


runner = CliRunner()


@dataclass(frozen=True, slots=True)
class FakeProvider(Provider):
    name: str = "mw"

    def define(self, word: str, *, timeout_seconds: float) -> DefinitionResult:
        return DefinitionResult(word=word, items=("fake definition",))

    def synonyms(self, word: str, *, limit: int, timeout_seconds: float) -> SynonymsResult:
        items = tuple([f"syn{i}" for i in range(1, limit + 1)])
        return SynonymsResult(word=word, items=items)


@pytest.fixture(autouse=True)
def fake_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    # Replace provider registry with a deterministic fake for all tests.
    monkeypatch.setattr(reg, "_PROVIDERS", {"mw": lambda settings: FakeProvider()}, raising=True)


def test_version_runs_without_command() -> None:
    res = runner.invoke(app, ["--version"])
    assert res.exit_code == 0
    assert res.stdout.strip() != ""


def test_providers_lists_mw() -> None:
    res = runner.invoke(app, ["providers"])
    assert res.exit_code == 0
    assert "mw" in res.stdout


def test_define_uses_provider() -> None:
    res = runner.invoke(app, ["define", "test"])
    assert res.exit_code == 0
    assert "Definitions" in res.stdout
    assert "fake definition" in res.stdout


def test_synonyms_limit() -> None:
    res = runner.invoke(app, ["synonyms", "fast", "--limit", "3"])
    assert res.exit_code == 0
    assert "Synonyms" in res.stdout
    assert "syn3" in res.stdout


def test_unknown_provider_is_error() -> None:
    res = runner.invoke(app, ["--provider", "nope", "define", "x"])
    assert res.exit_code != 0
    assert "Unknown provider" in res.output
