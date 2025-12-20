"""
py_dict_lookup.cli

Command-line interface for py-dict-lookup.

Environment variables (recommended via a local `.env` file):
- MW_COLLEGIATE_KEY: Merriam-Webster Collegiate Dictionary API key
- MW_THESAURUS_KEY: Merriam-Webster Thesaurus API key
- DICT_LOOKUP_TIMEOUT_SECONDS: optional request timeout in seconds

Examples:
    py-dict-lookup define serendipity
    py-dict-lookup synonyms fast --limit 10
    py-dict-lookup --provider mw define example
    py-dict-lookup providers
"""

from __future__ import annotations

from typing import Final

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from py_dict_lookup import __version__
from py_dict_lookup.config import Settings
from py_dict_lookup.providers import DEFAULT_PROVIDER, NotFound, ProviderError, get_provider, list_providers

APP_NAME: Final[str] = "py-dict-lookup"

console = Console()
app = typer.Typer(
    name="py-dict-lookup",
    add_completion=False,
    no_args_is_help=True,
    invoke_without_command=True,
    help="Look up word definitions and synonyms from the command line.",
)


class CliError(RuntimeError):
    """A user-facing CLI error (friendly message, non-zero exit)."""


def _print_error(message: str) -> None:
    console.print(Panel.fit(message, title="Error", border_style="red"))


def _ctx_provider(ctx: typer.Context) -> str:
    ctx.ensure_object(dict)
    provider = ctx.obj.get("provider")
    if isinstance(provider, str) and provider.strip():
        return provider.strip()
    return DEFAULT_PROVIDER


@app.callback()
def main(
    ctx: typer.Context,
    provider: str = typer.Option(
        DEFAULT_PROVIDER,
        "--provider",
        "-p",
        help=f"Provider to use (default: {DEFAULT_PROVIDER}).",
        show_default=True,
    ),
    version: bool = typer.Option(
        False,
        "--version",
        help="Show version and exit.",
        is_eager=True,
    ),
) -> None:
    """Top-level CLI callback (runs before subcommands)."""
    ctx.ensure_object(dict)
    ctx.obj["provider"] = provider

    if version:
        console.print(__version__)
        raise typer.Exit(code=0)


@app.command()
def providers() -> None:
    """List available providers."""
    names = list_providers()
    if not names:
        console.print("No providers registered.")
        raise typer.Exit(code=1)
    console.print(Markdown("\n".join([f"- `{n}`" for n in names])))


@app.command()
def define(
    ctx: typer.Context,
    word: str = typer.Argument(..., help="Word to define."),
) -> None:
    """Look up definitions for a word."""
    settings = Settings.from_env()
    provider_name = _ctx_provider(ctx)

    try:
        provider = get_provider(provider_name, settings)
        result = provider.define(word, timeout_seconds=settings.timeout_seconds)
    except NotFound as e:
        msg = f"'{e.word}' not found."
        if e.suggestions:
            msg += "\n\nSuggestions:\n- " + "\n- ".join(e.suggestions[:10])
        _print_error(msg)
        raise typer.Exit(code=2)
    except ProviderError as e:
        _print_error(str(e))
        raise typer.Exit(code=2)

    lines = [f"# Definitions: {result.word}", ""]
    for i, d in enumerate(result.items, start=1):
        lines.append(f"{i}. {d}")
    console.print(Markdown("\n".join(lines)))


@app.command()
def synonyms(
    ctx: typer.Context,
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
    """Look up synonyms for a word."""
    settings = Settings.from_env()
    provider_name = _ctx_provider(ctx)

    try:
        provider = get_provider(provider_name, settings)
        result = provider.synonyms(word, limit=limit, timeout_seconds=settings.timeout_seconds)
    except NotFound as e:
        msg = f"'{e.word}' not found."
        if e.suggestions:
            msg += "\n\nSuggestions:\n- " + "\n- ".join(e.suggestions[:10])
        _print_error(msg)
        raise typer.Exit(code=2)
    except ProviderError as e:
        _print_error(str(e))
        raise typer.Exit(code=2)

    lines = [f"# Synonyms: {result.word}", ""]
    for i, s in enumerate(result.items, start=1):
        lines.append(f"{i}. {s}")
    console.print(Markdown("\n".join(lines)))


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
