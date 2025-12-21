"""
py_dict_lookup.providers.merriam_webster

Merriam-Webster provider implementation (registered as provider name 'mw').

Endpoints (JSON):
- Collegiate Dictionary:
  https://www.dictionaryapi.com/api/v3/references/collegiate/json/{word}?key=...
- Collegiate Thesaurus:
  https://www.dictionaryapi.com/api/v3/references/thesaurus/json/{word}?key=...

Response shape:
- Successful lookups typically return a JSON list of entry objects.
- “Not found” responses often return a JSON list of strings (spelling suggestions).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, Mapping, Sequence
from urllib.parse import quote
import atexit
from threading import Lock

import httpx

from py_dict_lookup.config import Settings
from py_dict_lookup.providers.base import (
    DefinitionResult,
    NotFound,
    Provider,
    ProviderError,
    SynonymsResult,
)

_COLLEGIATE_BASE_URL: Final[str] = "https://www.dictionaryapi.com/api/v3/references/collegiate/json"
_THESAURUS_BASE_URL: Final[str] = "https://www.dictionaryapi.com/api/v3/references/thesaurus/json"

_CLIENT: httpx.Client | None = None
_CLIENT_LOCK: Lock = Lock()


def _get_client() -> httpx.Client:
    """Return a shared httpx client (connection pool reuse)."""
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT

    with _CLIENT_LOCK:
        if _CLIENT is None:
            _CLIENT = httpx.Client()
            atexit.register(_close_client)
    return _CLIENT


def _close_client() -> None:
    """Close the shared client at process exit."""
    global _CLIENT
    if _CLIENT is not None:
        _CLIENT.close()
        _CLIENT = None


@dataclass(frozen=True, slots=True)
class MerriamWebsterProvider(Provider):
    """Merriam-Webster provider ('mw')."""

    settings: Settings
    name: str = "mw"

    def define(self, word: str, *, timeout_seconds: float) -> DefinitionResult:
        key = _require(self.settings.mw_collegiate_key, "MW_COLLEGIATE_KEY")
        w = _normalize_word(word)
        payload = _fetch_json(
            base_url=_COLLEGIATE_BASE_URL,
            word=w,
            api_key=key,
            timeout_seconds=timeout_seconds,
        )
        entries = _as_entries_or_raise_not_found(word=w, payload=payload)
        defs = _extract_shortdef(entries)
        if not defs:
            raise NotFound(word=w)
        return DefinitionResult(word=w, items=tuple(defs))

    def synonyms(self, word: str, *, limit: int, timeout_seconds: float) -> SynonymsResult:
        if limit < 1:
            raise ValueError("limit must be >= 1")

        key = _require(self.settings.mw_thesaurus_key, "MW_THESAURUS_KEY")
        w = _normalize_word(word)
        payload = _fetch_json(
            base_url=_THESAURUS_BASE_URL,
            word=w,
            api_key=key,
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
        return SynonymsResult(word=w, items=tuple(ordered))


def _require(value: str | None, env_name: str) -> str:
    """Require a setting; raise ProviderError with a friendly message if missing."""
    if value:
        return value
    raise ProviderError(f"Missing {env_name}. Set it in your environment or .env file.")


def _fetch_json(*, base_url: str, word: str, api_key: str, timeout_seconds: float) -> Any:
    """Fetch JSON from a Merriam-Webster endpoint with friendly error handling."""
    url = f"{base_url}/{quote(word, safe='')}"
    params = {"key": api_key}

    try:
        client = _get_client()
        resp = client.get(url, params=params, timeout=timeout_seconds)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        raise ProviderError(f"Merriam-Webster API HTTP error: {e.response.status_code}") from e
    except httpx.RequestError as e:
        raise ProviderError(f"Network error contacting Merriam-Webster API: {e}") from e
    except ValueError as e:
        raise ProviderError("Invalid JSON received from Merriam-Webster API") from e


def _as_entries_or_raise_not_found(*, word: str, payload: Any) -> list[Mapping[str, Any]]:
    """Convert payload into entry dicts, or raise NotFound (with suggestions if present)."""
    if not isinstance(payload, list):
        raise ProviderError("Unexpected API response shape (expected a JSON list)")
    if not payload:
        raise NotFound(word=word)

    if all(isinstance(x, str) for x in payload):
        raise NotFound(word=word, suggestions=tuple(payload))

    entries: list[Mapping[str, Any]] = []
    for item in payload:
        if isinstance(item, Mapping):
            entries.append(item)

    if not entries:
        raise NotFound(word=word)
    return entries


def _extract_shortdef(entries: Sequence[Mapping[str, Any]]) -> list[str]:
    """Extract `shortdef` strings from dictionary entries."""
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
    Extract synonyms from thesaurus entries via entry['meta']['syns'] (list[list[str]]).
    """
    out: list[str] = []
    for entry in entries:
        meta = entry.get("meta")
        if not isinstance(meta, Mapping):
            continue
        syns = meta.get("syns")
        if not isinstance(syns, list):
            continue
        for group in syns:
            if isinstance(group, list):
                for s in group:
                    if isinstance(s, str) and s.strip():
                        out.append(s.strip())
    return out


def _normalize_word(word: str) -> str:
    w = word.strip()
    if not w:
        raise ValueError("word must not be empty")
    return w


__all__ = ["MerriamWebsterProvider"]
