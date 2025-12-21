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

import json
import sys
from dataclasses import dataclass
from typing import Any, Final, Optional

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

# Ensure provider registration side-effects occur.
from py_dict_lookup.providers import register_builtin_providers

register_builtin_providers()


APP_NAME: Final[str] = "py-dict-lookup"

# Exit code spec
EXIT_OK: Final[int] = 0
EXIT_NOT_FOUND: Final[int] = 2
EXIT_PROVIDER_ERROR: Final[int] = 3
EXIT_CONFIG_ERROR: Final[int] = 4


@dataclass(frozen=True, slots=True)
class RunConfig:
    provider: str
    json: bool
    rich: bool


def _is_config_error(msg: str) -> bool:
    """Heuristic: map missing-key/provider-config messages to EXIT_CONFIG_ERROR."""
    return msg.startswith("Missing ")


def _make_console(rich_enabled: bool) -> Console:
    # force_terminal=None keeps Rich auto-detection sane; you validated this works well.
    if rich_enabled:
        return Console(force_terminal=None)
    # Plain output: no colors, no markup, no control codes.
    return Console(force_terminal=False, color_system=None, markup=False, highlight=False)


def _ctx_config(ctx: typer.Context) -> RunConfig:
    ctx.ensure_object(dict)
    provider = ctx.obj.get("provider")
    json_mode = bool(ctx.obj.get("json"))
    rich_mode = bool(ctx.obj.get("rich"))
    if not isinstance(provider, str) or not provider.strip():
        provider = DEFAULT_PROVIDER
    return RunConfig(provider=provider.strip(), json=json_mode, rich=rich_mode)


def _write_json(payload: dict[str, Any]) -> None:
    """
    Write JSON directly to stdout.

    Important: do NOT use Rich for JSON output (it may wrap long lines and break JSON).
    """
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _emit_error(
    console: Console,
    *,
    cfg: RunConfig,
    message: str,
    suggestions: Optional[list[str]] = None,
) -> None:
    if cfg.json:
        payload: dict[str, Any] = {"error": message}
        if suggestions:
            payload["suggestions"] = suggestions
        _write_json(payload)
        return

    if not cfg.rich:
        console.print(message)
        if suggestions:
            console.print("Suggestions:")
            for s in suggestions:
                console.print(f"- {s}")
        return

    console.print(Panel.fit(message, title="Error", border_style="red"))
    if suggestions:
        console.print("Suggestions:\n- " + "\n- ".join(suggestions))


def _emit_definitions(
    console: Console,
    *,
    cfg: RunConfig,
    word: str,
    definitions: tuple[str, ...],
) -> None:
    if cfg.json:
        _write_json({"provider": cfg.provider, "word": word, "definitions": list(definitions)})
        return

    if not cfg.rich:
        console.print(f"Definitions: {word}")
        for i, d in enumerate(definitions, start=1):
            console.print(f"{i}. {d}")
        return

    lines = [f"# Definitions: {word}", ""]
    for i, d in enumerate(definitions, start=1):
        lines.append(f"{i}. {d}")
    console.print(Markdown("\n".join(lines)))


def _emit_synonyms(
    console: Console,
    *,
    cfg: RunConfig,
    word: str,
    synonyms: tuple[str, ...],
) -> None:
    if cfg.json:
        _write_json({"provider": cfg.provider, "word": word, "synonyms": list(synonyms)})
        return

    if not cfg.rich:
        console.print(f"Synonyms: {word}")
        for i, s in enumerate(synonyms, start=1):
            console.print(f"{i}. {s}")
        return

    lines = [f"# Synonyms: {word}", ""]
    for i, s in enumerate(synonyms, start=1):
        lines.append(f"{i}. {s}")
    console.print(Markdown("\n".join(lines)))


def _emit_lookup_json(
    *, provider: str, word: str, defs: tuple[str, ...], syns: tuple[str, ...]
) -> None:
    _write_json(
        {"provider": provider, "word": word, "definitions": list(defs), "synonyms": list(syns)}
    )


def _run_define(*, cfg: RunConfig, console: Console, word: str) -> tuple[str, tuple[str, ...]]:
    settings = Settings.from_env()
    try:
        provider = get_provider(cfg.provider, settings)
        result = provider.define(word, timeout_seconds=settings.timeout_seconds)
        return result.word, result.items
    except NotFound as e:
        _emit_error(
            console,
            cfg=cfg,
            message=f"'{e.word}' not found.",
            suggestions=list(e.suggestions[:10]),
        )
        raise typer.Exit(code=EXIT_NOT_FOUND)
    except ProviderError as e:
        msg = str(e)
        code = EXIT_CONFIG_ERROR if _is_config_error(msg) else EXIT_PROVIDER_ERROR
        _emit_error(console, cfg=cfg, message=msg)
        raise typer.Exit(code=code)


def _run_synonyms(
    *, cfg: RunConfig, console: Console, word: str, limit: int
) -> tuple[str, tuple[str, ...]]:
    settings = Settings.from_env()
    try:
        provider = get_provider(cfg.provider, settings)
        result = provider.synonyms(word, limit=limit, timeout_seconds=settings.timeout_seconds)
        return result.word, result.items
    except NotFound as e:
        _emit_error(
            console,
            cfg=cfg,
            message=f"'{e.word}' not found.",
            suggestions=list(e.suggestions[:10]),
        )
        raise typer.Exit(code=EXIT_NOT_FOUND)
    except ProviderError as e:
        msg = str(e)
        code = EXIT_CONFIG_ERROR if _is_config_error(msg) else EXIT_PROVIDER_ERROR
        _emit_error(console, cfg=cfg, message=msg)
        raise typer.Exit(code=code)


app = typer.Typer(
    name=APP_NAME,
    add_completion=False,
    invoke_without_command=True,
    no_args_is_help=True,
    help="Look up word definitions and synonyms from the command line.",
)


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
        help="Output machine-readable JSON.",
    ),
    no_rich: bool = typer.Option(
        False,
        "--no-rich",
        help="Disable Rich rendering; output plain text (useful for piping/dumb terminals).",
    ),
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version and exit.",
        is_eager=True,
    ),
) -> None:
    ctx.ensure_object(dict)
    ctx.obj["provider"] = provider
    ctx.obj["json"] = bool(json_out)
    # If JSON is requested, force plain output (no rich panels/markdown).
    ctx.obj["rich"] = (not no_rich) and (not json_out)

    if version:
        # Always plain output for version.
        sys.stdout.write(__version__ + "\n")
        raise typer.Exit(code=EXIT_OK)


# --- Commands (and short aliases) ---


@app.command("providers")
def providers(ctx: typer.Context) -> None:
    cfg = _ctx_config(ctx)
    console = _make_console(cfg.rich)

    names = list_providers()

    if cfg.json:
        _write_json({"providers": list(names)})
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
    console = _make_console(cfg.rich)

    w, defs = _run_define(cfg=cfg, console=console, word=word)
    _emit_definitions(console, cfg=cfg, word=w, definitions=defs)


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
    console = _make_console(cfg.rich)

    w, syns = _run_synonyms(cfg=cfg, console=console, word=word, limit=limit)
    _emit_synonyms(console, cfg=cfg, word=w, synonyms=syns)


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
    console = _make_console(cfg.rich)

    w1, defs = _run_define(cfg=cfg, console=console, word=word)
    w2, syns = _run_synonyms(cfg=cfg, console=console, word=word, limit=limit)
    word_final = w1 or w2 or word

    if cfg.json:
        _emit_lookup_json(provider=cfg.provider, word=word_final, defs=defs, syns=syns)
        raise typer.Exit(code=EXIT_OK)

    _emit_definitions(console, cfg=cfg, word=word_final, definitions=defs)
    _emit_synonyms(console, cfg=cfg, word=word_final, synonyms=syns)


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
