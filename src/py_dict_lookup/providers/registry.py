"""
py_dict_lookup.providers.registry

Provider selection and registration.

This module centralizes how providers are discovered/constructed.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Final

from py_dict_lookup.config import Settings
from py_dict_lookup.providers.base import Provider, ProviderError

DEFAULT_PROVIDER: Final[str] = "mw"

# Provider factories accept Settings and return a Provider instance.
ProviderFactory = Callable[[Settings], Provider]

_PROVIDERS: dict[str, ProviderFactory] = {}


def register_provider(name: str, factory: ProviderFactory) -> None:
    """Register a provider factory under a short name (e.g., 'mw')."""
    key = name.strip().lower()
    if not key:
        raise ValueError("provider name must not be empty")
    _PROVIDERS[key] = factory


def list_providers() -> tuple[str, ...]:
    """Return available provider names."""
    return tuple(sorted(_PROVIDERS.keys()))


def get_provider(name: str, settings: Settings) -> Provider:
    """Construct and return a provider instance by name."""
    key = (name or "").strip().lower()
    if not key:
        key = DEFAULT_PROVIDER

    factory = _PROVIDERS.get(key)
    if factory is None:
        available = ", ".join(list_providers()) or "(none)"
        raise ProviderError(f"Unknown provider '{key}'. Available: {available}")
    return factory(settings)


__all__ = ["DEFAULT_PROVIDER", "get_provider", "list_providers", "register_provider"]
