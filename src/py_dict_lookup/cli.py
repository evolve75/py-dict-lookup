"""
py_dict_lookup.cli

Command-line interface for py-dict-lookup.

Commands:
- lookup (alias: l): definitions + synonyms
- define (alias: d): definitions only
- synonyms (alias: s): synonyms only
- providers (alias: p): list providers

Global options:
- --provider / -p: select provider (default: mw)
- --version / -v: show version
- --help: built-in (Click/Typer)

Notes:
- We intentionally do NOT support `-h` as an alias for `--help` to keep the CLI
  simple and avoid argument-rewrite complexity. Use `--help`.
"""

from __future__ import annotations

from typing import Final

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from py_dict_lookup import __version__
from py_dict_lookup.config import Settings
from py_dict_lookup.providers import (
    DEFAULT_PROVIDER,
    NotFound,
    ProviderError,
    get_provider,
    list_providers,
)

APP_NAME: Final[str] = "py-dict-lookup"
console = Console()

app = typer.Typer(
    name=APP_NAME,
    add_completion=False,
    invoke_without_command=True,
    no_args_is_help=True,
    help="Look up word definitions and synonyms from the command line.",
)


def _print_error(message: str) -> None:
    console.print(Panel.fit(message, title="Error", border_style="red"))


def _print_section_md(title: str, word: str, items: tuple[str, ...]) -> None:
    lines = [f"# {title}: {word}", ""]
    for i, item in enumerate(items, start=1):
        lines.append(f"{i}. {item}")
    console.print(Markdown("\n".join(lines)))


def _ctx_provider(ctx: typer.Context) -> str:
    ctx.ensure_object(dict)
    provider = ctx.obj.get("provider")
    if isinstance(provider, str) and provider.strip():
        return provider.strip()
    return DEFAULT_PROVIDER


def _run_define(ctx: typer.Context, word: str) -> None:
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

    _print_section_md("Definitions", result.word, result.items)


def _run_synonyms(ctx: typer.Context, word: str, limit: int) -> None:
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

    _print_section_md("Synonyms", result.word, result.items)


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
        "-v",
        help="Show version and exit.",
        is_eager=True,
    ),
) -> None:
    """Global options shared by all commands."""
    ctx.ensure_object(dict)
    ctx.obj["provider"] = provider

    if version:
        console.print(__version__)
        raise typer.Exit(code=0)


# --- Commands (and short aliases) ---


@app.command("lookup")
def lookup(
    ctx: typer.Context,
    word: str = typer.Argument(..., help="Word to look up (definitions + synonyms)."),
    limit: int = typer.Option(
        10,
        "--limit",
        "-n",
        min=1,
        max=100,
        help="Maximum number of synonyms to display.",
        show_default=True,
    ),
) -> None:
    """Look up BOTH definitions and synonyms for a word."""
    _run_define(ctx, word)
    _run_synonyms(ctx, word, limit)


@app.command("l")
def l(
    ctx: typer.Context,
    word: str = typer.Argument(..., help="Alias for 'lookup'."),
    limit: int = typer.Option(
        10,
        "--limit",
        "-n",
        min=1,
        max=100,
        help="Maximum number of synonyms to display.",
        show_default=True,
    ),
) -> None:
    """Alias for lookup."""
    lookup(ctx, word, limit)


@app.command("define")
def define(
    ctx: typer.Context,
    word: str = typer.Argument(..., help="Word to define."),
) -> None:
    """Look up definitions for a word."""
    _run_define(ctx, word)


@app.command("d")
def d(
    ctx: typer.Context,
    word: str = typer.Argument(..., help="Alias for 'define'."),
) -> None:
    """Alias for define."""
    _run_define(ctx, word)


@app.command("synonyms")
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
        show_default=True,
    ),
) -> None:
    """Look up synonyms for a word."""
    _run_synonyms(ctx, word, limit)


@app.command("s")
def s(
    ctx: typer.Context,
    word: str = typer.Argument(..., help="Alias for 'synonyms'."),
    limit: int = typer.Option(
        10,
        "--limit",
        "-n",
        min=1,
        max=100,
        help="Maximum number of synonyms to display.",
        show_default=True,
    ),
) -> None:
    """Alias for synonyms."""
    _run_synonyms(ctx, word, limit)


@app.command("providers")
def providers() -> None:
    """List available providers."""
    names = list_providers()
    if not names:
        console.print("No providers registered.")
        raise typer.Exit(code=1)
    console.print(Markdown("\n".join([f"- `{n}`" for n in names])))


@app.command("p")
def p() -> None:
    """Alias for providers."""
    providers()


if __name__ == "__main__":
    app()
