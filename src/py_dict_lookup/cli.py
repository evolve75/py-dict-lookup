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
- --json: machine-readable output
- --no-rich: force plain text output (better for piping / dumb terminals)
"""

from __future__ import annotations

import sys
from typing import Final

import typer
from rich.markdown import Markdown

from py_dict_lookup import __version__
from py_dict_lookup.providers import DEFAULT_PROVIDER, list_providers

# Ensure provider registration side-effects occur.
from py_dict_lookup.providers import register_builtin_providers

from py_dict_lookup.cli_runtime import (
    EXIT_OK,
    EXIT_PROVIDER_ERROR,
    RunConfig,
    emit_definitions,
    emit_lookup_json,
    emit_synonyms,
    make_console,
    normalize_provider,
    run_define,
    run_synonyms,
    write_json,
)

register_builtin_providers()


APP_NAME: Final[str] = "py-dict-lookup"

app = typer.Typer(
    name=APP_NAME,
    add_completion=False,
    invoke_without_command=True,
    no_args_is_help=True,
    help="Look up word definitions and synonyms from the command line.",
)


def _ctx_config(ctx: typer.Context) -> RunConfig:
    """Build RunConfig from ctx.obj."""
    ctx.ensure_object(dict)
    provider = normalize_provider(ctx.obj.get("provider"))
    json_mode = bool(ctx.obj.get("json"))
    rich_mode = bool(ctx.obj.get("rich"))
    return RunConfig(provider=provider, json=json_mode, rich=rich_mode)


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
    json_out: bool = typer.Option(False, "--json", help="Output machine-readable JSON."),
    no_rich: bool = typer.Option(
        False,
        "--no-rich",
        help="Disable Rich rendering; output plain text (useful for piping/dumb terminals).",
    ),
    version: bool = typer.Option(
        False, "--version", "-v", help="Show version and exit.", is_eager=True
    ),
) -> None:
    """Global options shared by all commands."""
    ctx.ensure_object(dict)
    ctx.obj["provider"] = provider
    ctx.obj["json"] = bool(json_out)
    ctx.obj["rich"] = (not no_rich) and (not json_out)

    if version:
        sys.stdout.write(__version__ + "\n")
        raise typer.Exit(code=EXIT_OK)


# --- Commands (and short aliases) ---


@app.command("providers")
def providers(ctx: typer.Context) -> None:
    cfg = _ctx_config(ctx)
    console = make_console(cfg.rich)

    names = list_providers()

    if cfg.json:
        write_json({"providers": list(names)})
        raise typer.Exit(code=EXIT_OK)

    if not names:
        console.print("No providers registered.")
        raise typer.Exit(code=EXIT_PROVIDER_ERROR)

    if not cfg.rich:
        for n in names:
            console.print(n)
        return

    console.print(Markdown("\n".join([f"- `{n}`" for n in names])))


@app.command("p")
def providers_alias(ctx: typer.Context) -> None:
    """Alias for providers."""
    providers(ctx)


@app.command("define")
def define(ctx: typer.Context, word: str = typer.Argument(..., help="Word to define.")) -> None:
    cfg = _ctx_config(ctx)
    console = make_console(cfg.rich)

    w, defs, code = run_define(cfg=cfg, console=console, word=word)
    if code != EXIT_OK:
        raise typer.Exit(code=code)

    emit_definitions(console, cfg=cfg, word=w, definitions=defs)


@app.command("d")
def define_alias(
    ctx: typer.Context, word: str = typer.Argument(..., help="Alias for define.")
) -> None:
    """Alias for define."""
    define(ctx, word)


@app.command("synonyms")
def synonyms(
    ctx: typer.Context,
    word: str = typer.Argument(..., help="Word to find synonyms for."),
    limit: int = typer.Option(10, "--limit", "-n", min=1, max=100, show_default=True),
) -> None:
    cfg = _ctx_config(ctx)
    console = make_console(cfg.rich)

    w, syns, code = run_synonyms(cfg=cfg, console=console, word=word, limit=limit)
    if code != EXIT_OK:
        raise typer.Exit(code=code)

    emit_synonyms(console, cfg=cfg, word=w, synonyms=syns)


@app.command("s")
def synonyms_alias(
    ctx: typer.Context,
    word: str = typer.Argument(..., help="Alias for synonyms."),
    limit: int = typer.Option(10, "--limit", "-n", min=1, max=100, show_default=True),
) -> None:
    """Alias for synonyms."""
    synonyms(ctx, word, limit)


@app.command("lookup")
def lookup(
    ctx: typer.Context,
    word: str = typer.Argument(..., help="Word to look up (definitions + synonyms)."),
    limit: int = typer.Option(10, "--limit", "-n", min=1, max=100, show_default=True),
) -> None:
    cfg = _ctx_config(ctx)
    console = make_console(cfg.rich)

    w1, defs, code1 = run_define(cfg=cfg, console=console, word=word)
    if code1 != EXIT_OK:
        raise typer.Exit(code=code1)

    w2, syns, code2 = run_synonyms(cfg=cfg, console=console, word=word, limit=limit)
    if code2 != EXIT_OK:
        raise typer.Exit(code=code2)

    word_final = w1 or w2 or word

    if cfg.json:
        emit_lookup_json(provider=cfg.provider, word=word_final, defs=defs, syns=syns)
        raise typer.Exit(code=EXIT_OK)

    emit_definitions(console, cfg=cfg, word=word_final, definitions=defs)
    emit_synonyms(console, cfg=cfg, word=word_final, synonyms=syns)


@app.command("l")
def lookup_alias(
    ctx: typer.Context,
    word: str = typer.Argument(..., help="Alias for lookup."),
    limit: int = typer.Option(10, "--limit", "-n", min=1, max=100, show_default=True),
) -> None:
    """Alias for lookup."""
    lookup(ctx, word, limit)


if __name__ == "__main__":
    app()
