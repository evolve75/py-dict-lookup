from __future__ import annotations

import pytest

from py_dict_lookup.config import Settings
from py_dict_lookup.providers import registry as reg
from py_dict_lookup.providers.base import Provider, ProviderError


class DummyProvider(Provider):
    name = "mw"

    def define(self, word: str, *, timeout_seconds: float):
        raise AssertionError("not used")

    def synonyms(self, word: str, *, limit: int, timeout_seconds: float):
        raise AssertionError("not used")


def _settings() -> Settings:
    return Settings(mw_collegiate_key=None, mw_thesaurus_key=None, timeout_seconds=1.0)


@pytest.fixture(autouse=True)
def clean_registry(monkeypatch) -> None:
    monkeypatch.setattr(reg, "_PROVIDERS", {}, raising=True)


def test_register_and_list_providers() -> None:
    reg.register_provider("mw", lambda settings: DummyProvider())
    assert reg.list_providers() == ("mw",)


def test_register_provider_normalizes_name() -> None:
    reg.register_provider(" MW ", lambda settings: DummyProvider())
    assert reg.list_providers() == ("mw",)


def test_register_provider_empty_name_is_error() -> None:
    with pytest.raises(ValueError):
        reg.register_provider("   ", lambda settings: DummyProvider())


def test_get_provider_unknown_is_error() -> None:
    with pytest.raises(ProviderError) as e:
        reg.get_provider("nope", _settings())
    assert "Unknown provider" in str(e.value)


def test_get_provider_uses_default_when_blank(monkeypatch) -> None:
    called = {"n": 0}

    def factory(settings):
        called["n"] += 1
        return DummyProvider()

    monkeypatch.setattr(reg, "DEFAULT_PROVIDER", "mw", raising=True)
    reg.register_provider("mw", factory)

    p = reg.get_provider("", _settings())
    assert isinstance(p, DummyProvider)
    assert called["n"] == 1
