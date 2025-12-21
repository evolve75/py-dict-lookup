"""
py_dict_lookup.cli_runtime

Shared runtime helpers for the CLI.

This module centralizes:
- exit code policy
- Rich/plain/JSON output rules
- provider execution + error mapping
"""

from __future__ import annotations

import json
import sys
from typing import Callable, Optional, Protocol

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from py_dict_lookup.cli_types import (
    EXIT_CONFIG_ERROR,
    EXIT_NOT_FOUND,
    EXIT_OK,
    EXIT_PROVIDER_ERROR,
    RunConfig,
)
from py_dict_lookup.config import Settings
from py_dict_lookup.providers import DEFAULT_PROVIDER, NotFound, ProviderError, get_provider


class _HasWordItems(Protocol):
    word: str
    items: tuple[str, ...]


def is_config_error(message: str) -> bool:
    """Heuristic to map missing-key/provider-config messages to EXIT_CONFIG_ERROR."""
    return message.startswith("Missing ")


def make_console(rich_enabled: bool) -> Console:
    """
    Create a console appropriate for the output mode.

    - rich_enabled=True: auto-detect terminal capabilities (no forced behavior)
    - rich_enabled=False: disable markup/colors/control sequences
    """
    if rich_enabled:
        # Auto-detection: works well for iTerm2 + piping (you validated force_terminal=None).
        return Console(force_terminal=None)

    # Plain output: no colors, no markup, no control codes.
    return Console(force_terminal=False, color_system=None, markup=False, highlight=False)


def write_json(payload: dict) -> None:
    """
    Write JSON directly to stdout.

    Important: do NOT use Rich for JSON (it can wrap lines and break JSON).
    """
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")


def emit_error(
    console: Console,
    *,
    cfg: RunConfig,
    message: str,
    suggestions: Optional[list[str]] = None,
) -> None:
    """Emit an error in JSON/plain/rich mode."""
    if cfg.json:
        payload: dict = {"error": message}
        if suggestions:
            payload["suggestions"] = suggestions
        write_json(payload)
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


def emit_definitions(
    console: Console,
    *,
    cfg: RunConfig,
    word: str,
    definitions: tuple[str, ...],
) -> None:
    """Emit definitions in JSON/plain/rich mode."""
    if cfg.json:
        write_json({"provider": cfg.provider, "word": word, "definitions": list(definitions)})
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


def emit_synonyms(
    console: Console,
    *,
    cfg: RunConfig,
    word: str,
    synonyms: tuple[str, ...],
) -> None:
    """Emit synonyms in JSON/plain/rich mode."""
    if cfg.json:
        write_json({"provider": cfg.provider, "word": word, "synonyms": list(synonyms)})
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


def emit_lookup_json(
    *, provider: str, word: str, defs: tuple[str, ...], syns: tuple[str, ...]
) -> None:
    """Emit the combined lookup JSON payload."""
    write_json(
        {"provider": provider, "word": word, "definitions": list(defs), "synonyms": list(syns)}
    )


def normalize_provider(value: object) -> str:
    """Normalize provider name from ctx obj."""
    if isinstance(value, str) and value.strip():
        return value.strip()
    return DEFAULT_PROVIDER


def _run_provider_call(
    *,
    cfg: RunConfig,
    console: Console,
    word: str,
    call: Callable[[object, float], _HasWordItems],
) -> tuple[str, tuple[str, ...], int]:
    """
    Shared implementation for define/synonyms execution.

    `call(provider, timeout_seconds)` must return an object with:
      - `.word: str`
      - `.items: tuple[str, ...]`

    This function never raises Typer Exit; the caller decides how/when to exit.
    """
    settings = Settings.from_env()
    try:
        provider = get_provider(cfg.provider, settings)
        result = call(provider, settings.timeout_seconds)

        # Both DefinitionResult and SynonymsResult expose (word, items).
        res_word = getattr(result, "word")
        res_items = getattr(result, "items")
        return str(res_word), tuple(res_items), EXIT_OK

    except NotFound as e:
        emit_error(
            console,
            cfg=cfg,
            message=f"'{e.word}' not found.",
            suggestions=list(e.suggestions[:10]),
        )
        return word, (), EXIT_NOT_FOUND

    except ProviderError as e:
        msg = str(e)
        code = EXIT_CONFIG_ERROR if is_config_error(msg) else EXIT_PROVIDER_ERROR
        emit_error(console, cfg=cfg, message=msg)
        return word, (), code


def run_define(*, cfg: RunConfig, console: Console, word: str) -> tuple[str, tuple[str, ...], int]:
    """Execute provider.define and return (word, definitions, exit_code)."""

    def _call(provider: object, timeout_seconds: float) -> _HasWordItems:
        return provider.define(word, timeout_seconds=timeout_seconds)  # type: ignore[attr-defined]

    return _run_provider_call(cfg=cfg, console=console, word=word, call=_call)


def run_synonyms(
    *, cfg: RunConfig, console: Console, word: str, limit: int
) -> tuple[str, tuple[str, ...], int]:
    """Execute provider.synonyms and return (word, synonyms, exit_code)."""

    def _call(provider: object, timeout_seconds: float) -> _HasWordItems:
        return provider.synonyms(  # type: ignore[attr-defined]
            word, limit=limit, timeout_seconds=timeout_seconds
        )

    return _run_provider_call(cfg=cfg, console=console, word=word, call=_call)
