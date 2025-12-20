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
- --json: emit machine-readable JSON output
- --help: built-in (Click/Typer)

Notes:
- We intentionally do NOT support `-h` as an alias for `--help` to keep the CLI
  simple and avoid argument-rewrite complexity. Use `--help`.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, is_dataclass
from typing import Any, Final

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
from py_dict_lookup.providers import register_builtin_providers

register_builtin_providers()

APP_NAME: Final[str] = "py-dict-lookup"
console = Console(force_terminal=None)

app = typer.Typer(
    name=APP_NAME,
    add_completion=False,
    invoke_without_command=True,
    no_args_is_help=True,
    help="Look up word definitions and synonyms from the command line.",
)

def _plain_output() -> bool:
    return not sys.stdout.isatty()


def _print_error(message: str) -> None:
    if _plain_output():
        print(f"Error: {message}", file=sys.stderr)
        return
    console.print(Panel.fit(message, title="Error", border_style="red"))


def _print_section_md(title: str, word: str, items: tuple[str, ...]) -> None:
    if _plain_output():
        print(f"{title}: {word}")
        for i, item in enumerate(items, start=1):
            print(f"{i}. {item}")
        return

    lines = [f"# {title}: {word}", ""]
    for i, item in enumerate(items, start=1):
        lines.append(f"{i}. {item}")
    console.print(Markdown("\n".join(lines)))


def _emit_json(obj: Any) -> None:
    """
    Emit JSON to stdout.

    This bypasses Rich formatting and ensures a clean machine-readable payload.
    """
    def default(o: Any) -> Any:
        if is_dataclass(o):
            return asdict(o)
        raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")

    sys.stdout.write(json.dumps(obj, ensure_ascii=False, default=default))
    sys.stdout.write("\n")


def _json_enabled(ctx: typer.Context) -> bool:
    ctx.ensure_object(dict)
    return bool(ctx.obj.get("json"))


def _ctx_provider(ctx: typer.Context) -> str:
    ctx.ensure_object(dict)
    provider = ctx.obj.get("provider")
    if isinstance(provider, str) and provider.strip():
        return provider.strip()
    return DEFAULT_PROVIDER


def _emit_error(
    ctx: typer.Context,
    message: str,
    *,
    code: int = 2,
    word: str | None = None,
    suggestions: tuple[str, ...] | None = None,
    error_type: str = "error",
) -> None:
    if _json_enabled(ctx):
        payload: dict[str, Any] = {
            "ok": False,
            "error": message,
            "type": error_type,
            "provider": _ctx_provider(ctx),
        }
        if word is not None:
            payload["word"] = word
        if suggestions:
            payload["suggestions"] = list(suggestions)
        _emit_json(payload)
    else:
        _print_error(message)

    raise typer.Exit(code=code)


def _run_define(ctx: typer.Context, word: str):
    settings = Settings.from_env()
    provider_name = _ctx_provider(ctx)

    try:
        provider = get_provider(provider_name, settings)
        return provider.define(word, timeout_seconds=settings.timeout_seconds)
    except NotFound as e:
        msg = f"'{e.word}' not found."
        if e.suggestions:
            msg += "\n\nSuggestions:\n- " + "\n- ".join(e.suggestions[:10])
        _emit_error(
            ctx,
            msg,
            code=2,
            word=e.word,
            suggestions=e.suggestions,
            error_type="not_found",
        )
    except ProviderError as e:
        _emit_error(ctx, str(e), code=2, error_type="provider_error")


def _run_synonyms(ctx: typer.Context, word: str, limit: int):
    settings = Settings.from_env()
    provider_name = _ctx_provider(ctx)

    try:
        provider = get_provider(provider_name, settings)
        return provider.synonyms(word, limit=limit, timeout_seconds=settings.timeout_seconds)
    except NotFound as e:
        msg = f"'{e.word}' not found."
        if e.suggestions:
            msg += "\n\nSuggestions:\n- " + "\n- ".join(e.suggestions[:10])
        _emit_error(
            ctx,
            msg,
            code=2,
            word=e.word,
            suggestions=e.suggestions,
            error_type="not_found",
        )
    except ProviderError as e:
        _emit_error(ctx, str(e), code=2, error_type="provider_error")


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
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit JSON output (machine-readable).",
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
    ctx.obj["json"] = json_out

    if version:
        if json_out:
            _emit_json({"ok": True, "version": __version__})
        else:
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
    defs = _run_define(ctx, word)
    syns = _run_synonyms(ctx, word, limit)

    if _json_enabled(ctx):
        _emit_json(
            {
                "ok": True,
                "provider": _ctx_provider(ctx),
                "word": word,
                "definitions": list(defs.items),
                "synonyms": list(syns.items),
                "limit": limit,
            }
        )
        return

    _print_section_md("Definitions", defs.word, defs.items)
    _print_section_md("Synonyms", syns.word, syns.items)


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
    result = _run_define(ctx, word)

    if _json_enabled(ctx):
        _emit_json(
            {
                "ok": True,
                "provider": _ctx_provider(ctx),
                "word": result.word,
                "definitions": list(result.items),
            }
        )
        return

    _print_section_md("Definitions", result.word, result.items)


@app.command("d")
def d(
    ctx: typer.Context,
    word: str = typer.Argument(..., help="Alias for 'define'."),
) -> None:
    """Alias for define."""
    define(ctx, word)


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
    result = _run_synonyms(ctx, word, limit)

    if _json_enabled(ctx):
        _emit_json(
            {
                "ok": True,
                "provider": _ctx_provider(ctx),
                "word": result.word,
                "synonyms": list(result.items),
                "limit": limit,
            }
        )
        return

    _print_section_md("Synonyms", result.word, result.items)


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
    synonyms(ctx, word, limit)


@app.command("providers")
def providers(ctx: typer.Context) -> None:
    """List available providers."""
    names = list_providers()

    if _json_enabled(ctx):
        _emit_json({"ok": True, "providers": list(names), "default": DEFAULT_PROVIDER})
        return

    if not names:
        console.print("No providers registered.")
        raise typer.Exit(code=1)
    console.print(Markdown("\n".join([f"- `{n}`" for n in names])))


@app.command("p")
def p(ctx: typer.Context) -> None:
    """Alias for providers."""
    providers(ctx)


if __name__ == "__main__":
    app()
