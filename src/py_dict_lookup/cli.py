"""
py_dict_lookup.cli

Command-line interface for py-dict-lookup.

This project is intended to look up word definitions and synonyms from the CLI
(using Merriam-Webster APIs, as described in README.md).

Environment variables (recommended via a local `.env` file):
- MW_COLLEGIATE_KEY: Merriam-Webster Collegiate Dictionary API key
- MW_THESAURUS_KEY: Merriam-Webster Thesaurus API key

Examples:
    py-dict-lookup define serendipity
    py-dict-lookup synonyms fast --limit 10
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Final, Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from rich.markdown import Markdown

from py_dict_lookup.providers.merriam_webster import (
    MerriamWebsterError,
    NotFound,
    get_definitions,
    get_synonyms,
)

APP_NAME: Final[str] = "py-dict-lookup"
DEFAULT_TIMEOUT_SECONDS: Final[float] = 10.0

console = Console()
app = typer.Typer(
    name="py-dict-lookup",
    add_completion=False,
    no_args_is_help=True,
    invoke_without_command=True,
    help="Look up word definitions and synonyms from the command line.",
)


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime configuration loaded from environment variables."""

    mw_collegiate_key: Optional[str]
    mw_thesaurus_key: Optional[str]
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    @staticmethod
    def from_env() -> Settings:
        """
        Load settings from environment variables.

        `.env` is loaded (if present) to support local development.
        """
        load_dotenv()  # no-op if .env doesn't exist
        return Settings(
            mw_collegiate_key=_clean_env("MW_COLLEGIATE_KEY"),
            mw_thesaurus_key=_clean_env("MW_THESAURUS_KEY"),
            timeout_seconds=_clean_timeout(os.getenv("DICT_LOOKUP_TIMEOUT_SECONDS")),
        )


def _clean_env(name: str) -> Optional[str]:
    """Return a stripped env var value, or None if missing/blank."""
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _clean_timeout(value: Optional[str]) -> float:
    """Parse a timeout value from env; fall back to DEFAULT_TIMEOUT_SECONDS."""
    if not value:
        return DEFAULT_TIMEOUT_SECONDS
    try:
        parsed = float(value)
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS
    return parsed if parsed > 0 else DEFAULT_TIMEOUT_SECONDS


class CliError(RuntimeError):
    """A user-facing CLI error (friendly message, non-zero exit)."""


def _require_key(key: Optional[str], env_name: str) -> str:
    """Ensure an API key exists; raise CliError if not."""
    if key:
        return key
    raise CliError(
        f"Missing {env_name}. Set it in your environment or in a local .env file."
    )


def _print_error(message: str) -> None:
    console.print(Panel.fit(message, title="Error", border_style="red"))


def _print_info(message: str) -> None:
    console.print(Panel.fit(message, title=APP_NAME, border_style="blue"))


@app.command()
def define(word: str = typer.Argument(..., help="Word to define.")) -> None:
    """Look up definitions for a word via the Merriam-Webster Collegiate API."""
    settings = Settings.from_env()
    key = _require_key(settings.mw_collegiate_key, "MW_COLLEGIATE_KEY")

    try:
        result = get_definitions(
            word=word,
            api_key=key,
            timeout_seconds=settings.timeout_seconds,
        )
    except NotFound as e:
        msg = f"'{e.word}' not found."
        if e.suggestions:
            msg += "\n\nSuggestions:\n- " + "\n- ".join(e.suggestions[:10])
        raise CliError(msg) from e
    except MerriamWebsterError as e:
        raise CliError(str(e)) from e

    lines = [f"# Definitions: {result.word}", ""]
    for i, d in enumerate(result.items, start=1):
        lines.append(f"{i}. {d}")
    console.print(Markdown("\n".join(lines)))


@app.command()
def synonyms(
    word: str = typer.Argument(..., help="Word to find synonyms for."),
    limit: int = typer.Option(
        10,
        "--limit",
        "-n",
        min=1,
        max=100,
        help="Maximum number of synonyms to display.",
    ),
) -> None:
    """Look up synonyms for a word via the Merriam-Webster Thesaurus API."""
    settings = Settings.from_env()
    key = _require_key(settings.mw_thesaurus_key, "MW_THESAURUS_KEY")

    try:
        result = get_synonyms(
            word=word,
            api_key=key,
            limit=limit,
            timeout_seconds=settings.timeout_seconds,
        )
    except NotFound as e:
        msg = f"'{e.word}' not found."
        if e.suggestions:
            msg += "\n\nSuggestions:\n- " + "\n- ".join(e.suggestions[:10])
        raise CliError(msg) from e
    except MerriamWebsterError as e:
        raise CliError(str(e)) from e

    lines = [f"# Synonyms: {result.word}", ""]
    for i, s in enumerate(result.items, start=1):
        lines.append(f"{i}. {s}")
    console.print(Markdown("\n".join(lines)))


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        help="Show version and exit.",
        is_eager=True,
    ),
) -> None:
    """Top-level CLI callback (runs before subcommands)."""
    if version:
        # Avoid importing package metadata until needed.
        try:
            from importlib.metadata import version as pkg_version  # py>=3.8
        except Exception:
            console.print("unknown")
            raise typer.Exit(code=0)

        console.print(pkg_version("py-dict-lookup"))
        raise typer.Exit(code=0)


def _run() -> None:
    """Entrypoint wrapper with consistent error handling."""
    try:
        app()
    except CliError as e:
        _print_error(str(e))
        raise typer.Exit(code=2) from e
    except KeyboardInterrupt:
        _print_error("Interrupted.")
        raise typer.Exit(code=130) from None


if __name__ == "__main__":
    _run()
