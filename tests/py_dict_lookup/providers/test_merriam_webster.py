from __future__ import annotations

import httpx
import pytest

from py_dict_lookup.config import Settings
from py_dict_lookup.providers.base import NotFound, ProviderError
from py_dict_lookup.providers.merriam_webster import MerriamWebsterProvider


class DummyResponse:
    def __init__(self, payload, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            req = httpx.Request("GET", "https://example.test")
            resp = httpx.Response(self.status_code, request=req)
            raise httpx.HTTPStatusError("bad", request=req, response=resp)

    def json(self):
        return self._payload


class DummyClient:
    """
    A stand-in for httpx.Client.

    Provide `payloads` as an iterator of JSON payloads to return per call.
    Or set `raise_exc` to raise a specific exception on get().
    """

    def __init__(self, payloads=None, raise_exc: Exception | None = None, **_kwargs) -> None:
        self._payloads = list(payloads or [])
        self._raise_exc = raise_exc

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def get(self, url, params=None):
        if self._raise_exc is not None:
            raise self._raise_exc
        if not self._payloads:
            raise AssertionError("No payloads configured for DummyClient")
        payload = self._payloads.pop(0)
        return DummyResponse(payload)


def _settings(keys: bool = True) -> Settings:
    return Settings(
        mw_collegiate_key="ckey" if keys else None,
        mw_thesaurus_key="tkey" if keys else None,
        timeout_seconds=1.0,
    )


def test_define_missing_key_is_provider_error() -> None:
    provider = MerriamWebsterProvider(_settings(keys=False))
    with pytest.raises(ProviderError) as e:
        provider.define("x", timeout_seconds=1.0)
    assert "MW_COLLEGIATE_KEY" in str(e.value)


def test_synonyms_missing_key_is_provider_error() -> None:
    provider = MerriamWebsterProvider(_settings(keys=False))
    with pytest.raises(ProviderError) as e:
        provider.synonyms("x", limit=3, timeout_seconds=1.0)
    assert "MW_THESAURUS_KEY" in str(e.value)


def test_define_not_found_suggestions(monkeypatch) -> None:
    # MW "not found" returns list[str]
    monkeypatch.setattr(httpx, "Client", lambda **kw: DummyClient(payloads=[["alpha", "beta"]]))
    provider = MerriamWebsterProvider(_settings(keys=True))

    with pytest.raises(NotFound) as e:
        provider.define("nope", timeout_seconds=1.0)
    assert e.value.word == "nope"
    assert e.value.suggestions == ("alpha", "beta")


def test_define_parses_shortdef(monkeypatch) -> None:
    payload = [
        {"shortdef": ["first def", "second def"]},
        {"shortdef": ["third def"]},
    ]
    monkeypatch.setattr(httpx, "Client", lambda **kw: DummyClient(payloads=[payload]))
    provider = MerriamWebsterProvider(_settings(keys=True))

    res = provider.define("word", timeout_seconds=1.0)
    assert res.word == "word"
    assert res.items == ("first def", "second def", "third def")


def test_synonyms_parses_and_dedupes_and_limits(monkeypatch) -> None:
    payload = [
        {"meta": {"syns": [["a", "b", "a"], ["c"]]}},
        {"meta": {"syns": [["b", "d"]]}},
    ]
    monkeypatch.setattr(httpx, "Client", lambda **kw: DummyClient(payloads=[payload]))
    provider = MerriamWebsterProvider(_settings(keys=True))

    res = provider.synonyms("word", limit=3, timeout_seconds=1.0)
    assert res.word == "word"
    # unique, ordered, limited
    assert res.items == ("a", "b", "c")


def test_synonyms_limit_validation() -> None:
    provider = MerriamWebsterProvider(_settings(keys=True))
    with pytest.raises(ValueError):
        provider.synonyms("word", limit=0, timeout_seconds=1.0)


def test_http_status_error_maps_to_provider_error(monkeypatch) -> None:
    # Return a response with status 401 -> raise_for_status -> HTTPStatusError
    class Client401(DummyClient):
        def get(self, url, params=None):
            return DummyResponse(payload=[], status_code=401)

    monkeypatch.setattr(httpx, "Client", lambda **kw: Client401(payloads=[]))
    provider = MerriamWebsterProvider(_settings(keys=True))

    with pytest.raises(ProviderError) as e:
        provider.define("word", timeout_seconds=1.0)
    assert "HTTP error" in str(e.value)


def test_request_error_maps_to_provider_error(monkeypatch) -> None:
    exc = httpx.RequestError("network down", request=httpx.Request("GET", "https://x"))
    monkeypatch.setattr(httpx, "Client", lambda **kw: DummyClient(raise_exc=exc))
    provider = MerriamWebsterProvider(_settings(keys=True))

    with pytest.raises(ProviderError) as e:
        provider.define("word", timeout_seconds=1.0)
    assert "Network error" in str(e.value)


def test_invalid_json_maps_to_provider_error(monkeypatch) -> None:
    class BadJSONResponse(DummyResponse):
        def json(self):
            raise ValueError("bad json")

    class ClientBadJSON(DummyClient):
        def get(self, url, params=None):
            return BadJSONResponse(payload=None, status_code=200)

    monkeypatch.setattr(httpx, "Client", lambda **kw: ClientBadJSON(payloads=[]))
    provider = MerriamWebsterProvider(_settings(keys=True))

    with pytest.raises(ProviderError) as e:
        provider.define("word", timeout_seconds=1.0)
    assert "Invalid JSON" in str(e.value)
