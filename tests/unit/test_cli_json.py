from __future__ import annotations

from conftest import ErroringProvider, parse_json_output
from typer.testing import CliRunner

from py_dict_lookup.cli import app
from py_dict_lookup.providers import registry as reg

runner = CliRunner()


def test_define_json() -> None:
    res = runner.invoke(app, ["--json", "define", "test"])
    assert res.exit_code == 0
    payload = parse_json_output(res.output)
    assert payload["provider"] == "mw"
    assert payload["word"] == "test"
    assert payload["definitions"] == ["fake definition"]


def test_synonyms_json_default_limit() -> None:
    res = runner.invoke(app, ["--json", "synonyms", "fast"])
    assert res.exit_code == 0
    payload = parse_json_output(res.output)
    assert payload["provider"] == "mw"
    assert payload["word"] == "fast"
    assert payload["synonyms"][-1] == "syn10"
    assert len(payload["synonyms"]) == 10


def test_lookup_json() -> None:
    res = runner.invoke(app, ["--json", "lookup", "serendipity", "--limit", "3"])
    assert res.exit_code == 0
    payload = parse_json_output(res.output)
    assert payload["provider"] == "mw"
    assert payload["word"] == "serendipity"
    assert payload["definitions"] == ["fake definition"]
    assert payload["synonyms"] == ["syn1", "syn2", "syn3"]


def test_providers_json() -> None:
    res = runner.invoke(app, ["--json", "providers"])
    assert res.exit_code == 0
    payload = parse_json_output(res.output)
    assert payload["providers"] == ["mw"]


def test_unknown_provider_is_error_json() -> None:
    res = runner.invoke(app, ["--json", "--provider", "nope", "define", "x"])
    assert res.exit_code == 3
    payload = parse_json_output(res.output)
    assert "error" in payload
    assert "Unknown provider" in payload["error"]


def test_provider_error_is_exit_3_json(monkeypatch) -> None:
    monkeypatch.setattr(
        reg,
        "_PROVIDERS",
        {"mw": lambda settings: ErroringProvider(mode="provider_error", message="boom")},
        raising=True,
    )
    res = runner.invoke(app, ["--json", "define", "x"])
    assert res.exit_code == 3
    payload = parse_json_output(res.output)
    assert payload["error"] == "boom"


def test_config_error_is_exit_4_json(monkeypatch) -> None:
    monkeypatch.setattr(
        reg,
        "_PROVIDERS",
        {"mw": lambda settings: ErroringProvider(mode="config_error")},
        raising=True,
    )
    res = runner.invoke(app, ["--json", "define", "x"])
    assert res.exit_code == 4
    payload = parse_json_output(res.output)
    assert "Missing" in payload["error"]


def test_not_found_is_exit_2_json_with_suggestions(monkeypatch) -> None:
    monkeypatch.setattr(
        reg,
        "_PROVIDERS",
        {"mw": lambda settings: ErroringProvider(mode="not_found")},
        raising=True,
    )
    res = runner.invoke(app, ["--json", "define", "x"])
    assert res.exit_code == 2
    payload = parse_json_output(res.output)
    assert "not found" in payload["error"].lower()
    assert payload["suggestions"] == ["alpha", "beta"]
