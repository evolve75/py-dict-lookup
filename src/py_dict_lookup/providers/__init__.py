"""
py_dict_lookup.providers

Provider interface, registry, and built-in provider registrations.
"""

from __future__ import annotations

from py_dict_lookup.providers.base import (
    DefinitionResult,
    NotFound,
    Provider,
    ProviderError,
    SynonymsResult,
    UnsupportedOperation,
)
from py_dict_lookup.providers.merriam_webster import MerriamWebsterProvider
from py_dict_lookup.providers.registry import (
    DEFAULT_PROVIDER,
    get_provider,
    list_providers,
    register_provider,
)


def register_builtin_providers() -> None:
    """Register built-in providers shipped with this package."""
    register_provider("mw", lambda settings: MerriamWebsterProvider(settings))


__all__ = [
    "Provider",
    "ProviderError",
    "NotFound",
    "UnsupportedOperation",
    "DefinitionResult",
    "SynonymsResult",
    "DEFAULT_PROVIDER",
    "get_provider",
    "list_providers",
    "register_builtin_providers",
]
