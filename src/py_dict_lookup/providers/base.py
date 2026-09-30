"""
py_dict_lookup.providers.base

Provider interface and shared result/error types.

The CLI should depend only on these types (and the registry), not on any
provider implementation details.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class ProviderError(RuntimeError):
    """Base error for provider failures (network issues, auth, parsing, etc.)."""


@dataclass(frozen=True, slots=True)
class NotFound(ProviderError):
    """Raised when a word is not found (optionally includes suggestions)."""

    word: str
    suggestions: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class UnsupportedOperation(ProviderError):
    """Raised when a provider does not support an operation (e.g., synonyms)."""

    operation: str


@dataclass(frozen=True, slots=True)
class DefinitionResult:
    """Result of a definition lookup."""

    word: str
    items: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SynonymsResult:
    """Result of a synonyms lookup."""

    word: str
    items: tuple[str, ...]


class Provider(Protocol):
    """Contract that all providers must implement."""

    name: str

    def define(self, word: str, *, timeout_seconds: float) -> DefinitionResult: ...
    def synonyms(self, word: str, *, limit: int, timeout_seconds: float) -> SynonymsResult: ...


__all__ = [
    "DefinitionResult",
    "NotFound",
    "Provider",
    "ProviderError",
    "SynonymsResult",
    "UnsupportedOperation",
]
