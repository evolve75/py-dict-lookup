from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable

import pytest

from py_dict_lookup.providers import registry as reg
from py_dict_lookup.providers.base import (
    DefinitionResult,
    NotFound,
    Provider,
    ProviderError,
    SynonymsResult,
)

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(s: str) -> str:
    """Remove ANSI escape sequences to make assertions stable."""
    return _ANSI_RE.sub("", s)


def parse_json_output(output: str) -> Any:
    """Parse JSON output; tolerate surrounding whitespace/newlines."""
    return json.loads(output.strip())


@dataclass(frozen=True, slots=True)
class FakeProvider(Provider):
    """Deterministic provider used for most CLI tests."""

    name: str = "mw"

    def define(self, word: str, *, timeout_seconds: float) -> DefinitionResult:
        return DefinitionResult(word=word, items=("fake definition",))

    def synonyms(self, word: str, *, limit: int, timeout_seconds: float) -> SynonymsResult:
        items = tuple([f"syn{i}" for i in range(1, limit + 1)])
        return SynonymsResult(word=word, items=items)


@dataclass(frozen=True, slots=True)
class ErroringProvider(Provider):
    """
    Provider used for error-mapping tests.

    mode:
      - "provider_error": raises ProviderError(message)
      - "not_found": raises NotFound(word, suggestions=("alpha","beta"))
      - "config_error": raises ProviderError("Missing ...") to trigger config exit 4
    """

    name: str = "mw"
    mode: str = "provider_error"
    message: str = "boom"

    def define(self, word: str, *, timeout_seconds: float) -> DefinitionResult:
        if self.mode == "not_found":
            raise NotFound(word=word, suggestions=("alpha", "beta"))
        if self.mode == "config_error":
            raise ProviderError(
                "Missing DICT_LOOKUP_MW_COLLEGIATE_KEY. Set it in your environment or .env file."
            )
        raise ProviderError(self.message)

    def synonyms(self, word: str, *, limit: int, timeout_seconds: float) -> SynonymsResult:
        if self.mode == "not_found":
            raise NotFound(word=word, suggestions=("alpha", "beta"))
        if self.mode == "config_error":
            raise ProviderError(
                "Missing DICT_LOOKUP_MW_THESAURUS_KEY. Set it in your environment or .env file."
            )
        raise ProviderError(self.message)


@pytest.fixture(autouse=True)
def fake_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Default registry for all tests:
      mw -> FakeProvider

    Tests can override using patch_registry().
    """
    monkeypatch.setattr(reg, "_PROVIDERS", {"mw": lambda settings: FakeProvider()}, raising=True)


@pytest.fixture()
def patch_registry(monkeypatch: pytest.MonkeyPatch) -> Callable[[Provider], None]:
    """
    Replace the 'mw' provider with an explicit Provider instance.
    Usage:
        patch_registry(ErroringProvider(...))
    """

    def _apply(provider: Provider) -> None:
        monkeypatch.setattr(reg, "_PROVIDERS", {"mw": lambda settings: provider}, raising=True)

    return _apply
