"""
py_dict_lookup.providers.merriam_webster

Minimal Merriam-Webster provider implementation.

This module targets the Merriam-Webster Dictionary API products referenced in README.md:
- Collegiate Dictionary (definitions)
- Collegiate Thesaurus (synonyms)

Endpoints (JSON):
- Collegiate Dictionary:
  https://www.dictionaryapi.com/api/v3/references/collegiate/json/{word}?key=...
- Collegiate Thesaurus:
  https://www.dictionaryapi.com/api/v3/references/thesaurus/json/{word}?key=...

Notes on response shape:
- Successful lookups typically return a JSON list of entry objects.
- “Not found” responses often return a JSON list of strings (spelling suggestions).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, Iterable, Mapping, Sequence
from urllib.parse import quote

import httpx

__all__ = [
    "LookupResult",
    "NotFound",
    "MerriamWebsterError",
    "get_definitions",
    "get_synonyms",
]

_COLLEGIATE_BASE_URL: Final[str] = "https://www.dictionaryapi.com/api/v3/references/collegiate/json"
_THESAURUS_BASE_URL: Final[str] = "https://www.dictionaryapi.com/api/v3/references/thesaurus/json"


class MerriamWebsterError(RuntimeError):
    """Base error for Merriam-Webster provider failures."""


@dataclass(frozen=True, slots=True)
class NotFound(MerriamWebsterError):
    """
    Raised when a word is not found.

    Merriam-Webster frequently returns a list of suggestion strings in this case.
    """

    word: str
    suggestions: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LookupResult:
    """Common shape returned by lookups."""

    word: str
    items: tuple[str, ...]


def get_definitions(
    *,
    word: str,
    api_key: str,
    timeout_seconds: float = 10.0,
) -> LookupResult:
    """
    Look up short definitions for a word via the Collegiate Dictionary API.

    Returns:
        LookupResult where `items` are definitions (strings).

    Raises:
        NotFound: if the API returns no entries (optionally with suggestions)
        MerriamWebsterError: for network/HTTP/protocol issues
    """
    w = _normalize_word(word)
    payload = _fetch_json(
        base_url=_COLLEGIATE_BASE_URL,
        word=w,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
    )
    entries = _as_entries_or_raise_not_found(word=w, payload=payload)
    defs = _extract_shortdef(entries)
    if not defs:
        # Some entries might not contain `shortdef`; treat as not found-ish for CLI purposes.
        raise NotFound(word=w)
    return LookupResult(word=w, items=tuple(defs))


def get_synonyms(
    *,
    word: str,
    api_key: str,
    limit: int = 10,
    timeout_seconds: float = 10.0,
) -> LookupResult:
    """
    Look up synonyms for a word via the Collegiate Thesaurus API.

    Returns:
        LookupResult where `items` are synonyms (strings), de-duplicated, up to `limit`.

    Raises:
        NotFound: if the API returns no entries (optionally with suggestions)
        MerriamWebsterError: for network/HTTP/protocol issues
        ValueError: if `limit` is invalid
    """
    if limit < 1:
        raise ValueError("limit must be >= 1")

    w = _normalize_word(word)
    payload = _fetch_json(
        base_url=_THESAURUS_BASE_URL,
        word=w,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
    )
    entries = _as_entries_or_raise_not_found(word=w, payload=payload)
    syns = _extract_synonyms(entries)

    # De-dupe while preserving order
    seen: set[str] = set()
    ordered: list[str] = []
    for s in syns:
        if s not in seen:
            seen.add(s)
            ordered.append(s)
        if len(ordered) >= limit:
            break

    if not ordered:
        raise NotFound(word=w)
    return LookupResult(word=w, items=tuple(ordered))


def _fetch_json(*, base_url: str, word: str, api_key: str, timeout_seconds: float) -> Any:
    """Fetch JSON from a Merriam-Webster endpoint with friendly error handling."""
    url = f"{base_url}/{quote(word, safe='')}"
    params = {"key": api_key}

    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        # Surface status code (e.g., 401 for bad key) without dumping huge body.
        status = e.response.status_code
        raise MerriamWebsterError(f"Merriam-Webster API HTTP error: {status}") from e
    except httpx.RequestError as e:
        raise MerriamWebsterError(f"Network error contacting Merriam-Webster API: {e}") from e
    except ValueError as e:
        # JSON decode issues
        raise MerriamWebsterError("Invalid JSON received from Merriam-Webster API") from e


def _as_entries_or_raise_not_found(*, word: str, payload: Any) -> list[Mapping[str, Any]]:
    """
    Convert the API payload into a list of entry mappings.

    MW “not found” commonly returns: ["suggestion1", "suggestion2", ...]
    """
    if not isinstance(payload, list):
        raise MerriamWebsterError("Unexpected API response shape (expected a JSON list)")

    if not payload:
        raise NotFound(word=word)

    # Suggestions-only case (list[str])
    if all(isinstance(x, str) for x in payload):
        suggestions = tuple(str(x) for x in payload)
        raise NotFound(word=word, suggestions=suggestions)

    # Entries case (list[dict])
    entries: list[Mapping[str, Any]] = []
    for item in payload:
        if isinstance(item, Mapping):
            entries.append(item)
    if not entries:
        raise NotFound(word=word)
    return entries


def _extract_shortdef(entries: Sequence[Mapping[str, Any]]) -> list[str]:
    """Extract `shortdef` strings from Collegiate dictionary entries."""
    out: list[str] = []
    for entry in entries:
        shortdef = entry.get("shortdef")
        if isinstance(shortdef, list):
            for d in shortdef:
                if isinstance(d, str) and d.strip():
                    out.append(d.strip())
    return out


def _extract_synonyms(entries: Sequence[Mapping[str, Any]]) -> list[str]:
    """
    Extract synonyms from Thesaurus entries.

    Thesaurus entries typically use:
      entry["meta"]["syns"] -> list[list[str]]
    """
    out: list[str] = []
    for entry in entries:
        meta = entry.get("meta")
        if not isinstance(meta, Mapping):
            continue
        syns = meta.get("syns")
        if not isinstance(syns, list):
            continue

        # Flatten list[list[str]] safely
        for group in syns:
            if isinstance(group, list):
                for s in group:
                    if isinstance(s, str) and s.strip():
                        out.append(s.strip())
    return out


def _normalize_word(word: str) -> str:
    """Normalize a user-provided word for lookup."""
    w = word.strip()
    if not w:
        raise ValueError("word must not be empty")
    return w
