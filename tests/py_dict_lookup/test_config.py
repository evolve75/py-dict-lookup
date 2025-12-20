from __future__ import annotations

import os

from py_dict_lookup.config import DEFAULT_TIMEOUT_SECONDS, Settings


def test_settings_from_env_reads_keys_and_default_timeout(monkeypatch) -> None:
    monkeypatch.setenv("MW_COLLEGIATE_KEY", "abc")
    monkeypatch.setenv("MW_THESAURUS_KEY", "def")
    monkeypatch.delenv("DICT_LOOKUP_TIMEOUT_SECONDS", raising=False)

    s = Settings.from_env()
    assert s.mw_collegiate_key == "abc"
    assert s.mw_thesaurus_key == "def"
    assert s.timeout_seconds == DEFAULT_TIMEOUT_SECONDS


def test_settings_from_env_strips_blank_values_to_none(monkeypatch) -> None:
    monkeypatch.setenv("MW_COLLEGIATE_KEY", "   ")
    monkeypatch.setenv("MW_THESAURUS_KEY", "\n\t")
    monkeypatch.delenv("DICT_LOOKUP_TIMEOUT_SECONDS", raising=False)

    s = Settings.from_env()
    assert s.mw_collegiate_key is None
    assert s.mw_thesaurus_key is None


def test_settings_timeout_parses_float(monkeypatch) -> None:
    monkeypatch.delenv("MW_COLLEGIATE_KEY", raising=False)
    monkeypatch.delenv("MW_THESAURUS_KEY", raising=False)
    monkeypatch.setenv("DICT_LOOKUP_TIMEOUT_SECONDS", "2.5")

    s = Settings.from_env()
    assert s.timeout_seconds == 2.5


def test_settings_timeout_invalid_falls_back(monkeypatch) -> None:
    monkeypatch.setenv("DICT_LOOKUP_TIMEOUT_SECONDS", "nope")
    s = Settings.from_env()
    assert s.timeout_seconds == DEFAULT_TIMEOUT_SECONDS


def test_settings_timeout_non_positive_falls_back(monkeypatch) -> None:
    monkeypatch.setenv("DICT_LOOKUP_TIMEOUT_SECONDS", "0")
    s0 = Settings.from_env()
    assert s0.timeout_seconds == DEFAULT_TIMEOUT_SECONDS

    monkeypatch.setenv("DICT_LOOKUP_TIMEOUT_SECONDS", "-10")
    sneg = Settings.from_env()
    assert sneg.timeout_seconds == DEFAULT_TIMEOUT_SECONDS
