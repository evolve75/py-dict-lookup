"""
py_dict_lookup.config

Runtime configuration loaded from environment variables.

This module exists to avoid circular dependencies between the CLI and providers.
Providers should read required settings from `Settings`, not from the CLI module.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Final

from dotenv import load_dotenv

DEFAULT_TIMEOUT_SECONDS: Final[float] = 10.0


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime configuration loaded from environment variables."""

    mw_collegiate_key: str | None
    mw_thesaurus_key: str | None
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    @staticmethod
    def from_env() -> Settings:
        """
        Load settings from environment variables.

        A local `.env` file is loaded if present (development convenience).
        """
        load_dotenv()
        return Settings(
            mw_collegiate_key=_clean_env("MW_COLLEGIATE_KEY"),
            mw_thesaurus_key=_clean_env("MW_THESAURUS_KEY"),
            timeout_seconds=_clean_timeout(os.getenv("DICT_LOOKUP_TIMEOUT_SECONDS")),
        )


def _clean_env(name: str) -> str | None:
    """Return a stripped env var value, or None if missing/blank."""
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _clean_timeout(value: str | None) -> float:
    """Parse a timeout value from env; fall back to DEFAULT_TIMEOUT_SECONDS."""
    if not value:
        return DEFAULT_TIMEOUT_SECONDS
    try:
        parsed = float(value)
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS
    return parsed if parsed > 0 else DEFAULT_TIMEOUT_SECONDS
