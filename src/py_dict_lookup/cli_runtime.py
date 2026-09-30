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
from typing import Literal

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
from py_dict_lookup.providers.base import DefinitionResult, Provider, SynonymsResult

OpName = Literal["define", "synonyms"]


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
    suggestions: list[str] | None = None,
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


def emit_word_items(
    console: Console,
    *,
    cfg: RunConfig,
    title: str,
    json_key: Literal["definitions", "synonyms"],
    word: str,
    items: tuple[str, ...],
) -> None:
    """
    Emit a single word->items section in JSON/plain/rich mode.

    This consolidates the shared logic used by definitions and synonyms.
    """
    if cfg.json:
        write_json({"provider": cfg.provider, "word": word, json_key: list(items)})
        return

    if not cfg.rich:
        console.print(f"{title}: {word}")
        for i, item in enumerate(items, start=1):
            console.print(f"{i}. {item}")
        return

    lines = [f"# {title}: {word}", ""]
    for i, item in enumerate(items, start=1):
        lines.append(f"{i}. {item}")
    console.print(Markdown("\n".join(lines)))


def emit_definitions(
    console: Console,
    *,
    cfg: RunConfig,
    word: str,
    definitions: tuple[str, ...],
) -> None:
    """Emit definitions in JSON/plain/rich mode."""
    emit_word_items(
        console,
        cfg=cfg,
        title="Definitions",
        json_key="definitions",
        word=word,
        items=definitions,
    )


def emit_synonyms(
    console: Console,
    *,
    cfg: RunConfig,
    word: str,
    synonyms: tuple[str, ...],
) -> None:
    """Emit synonyms in JSON/plain/rich mode."""
    emit_word_items(
        console,
        cfg=cfg,
        title="Synonyms",
        json_key="synonyms",
        word=word,
        items=synonyms,
    )


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


def _extract_word_items(result: DefinitionResult | SynonymsResult) -> tuple[str, tuple[str, ...]]:
    """Convert a provider result into the common (word, items) shape."""
    return result.word, result.items


def _call_provider(
    provider: Provider,
    *,
    op: OpName,
    word: str,
    timeout_seconds: float,
    limit: int,
) -> tuple[str, tuple[str, ...]]:
    """
    Dispatch to the provider operation and return (word, items).

    `limit` is ignored for `define` and used for `synonyms`.
    """
    if op == "define":
        return _extract_word_items(provider.define(word, timeout_seconds=timeout_seconds))
    return _extract_word_items(
        provider.synonyms(word, limit=limit, timeout_seconds=timeout_seconds)
    )


def _run_word_items(
    *,
    cfg: RunConfig,
    console: Console,
    op: OpName,
    word: str,
    limit: int = 10,
) -> tuple[str, tuple[str, ...], int]:
    """
    Execute a provider operation and return (word, items, exit_code).

    This function emits errors according to cfg (JSON/plain/rich) and returns
    an exit code for the caller to decide how/when to exit.
    """
    settings = Settings.from_env()

    try:
        provider = get_provider(cfg.provider, settings)
        res_word, res_items = _call_provider(
            provider,
            op=op,
            word=word,
            timeout_seconds=settings.timeout_seconds,
            limit=limit,
        )
        return res_word, res_items, EXIT_OK

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
    return _run_word_items(cfg=cfg, console=console, op="define", word=word, limit=10)


def run_synonyms(
    *, cfg: RunConfig, console: Console, word: str, limit: int
) -> tuple[str, tuple[str, ...], int]:
    """Execute provider.synonyms and return (word, synonyms, exit_code)."""
    return _run_word_items(cfg=cfg, console=console, op="synonyms", word=word, limit=limit)
