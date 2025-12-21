"""
py_dict_lookup.cli_types

Shared types and constants for the CLI.

"""

from dataclasses import dataclass
from typing import Final


# Exit code spec
EXIT_OK: Final[int] = 0
EXIT_NOT_FOUND: Final[int] = 2
EXIT_PROVIDER_ERROR: Final[int] = 3
EXIT_CONFIG_ERROR: Final[int] = 4


@dataclass(frozen=True, slots=True)
class RunConfig:
    """Runtime configuration derived from CLI options/context."""

    provider: str
    json: bool
    rich: bool
