from __future__ import annotations

import pytest

from py_dict_lookup.providers.base import (
    DefinitionResult,
    NotFound,
    ProviderError,
    SynonymsResult,
    UnsupportedOperation,
)


def test_results_are_immutable_dataclasses() -> None:
    d = DefinitionResult(word="x", items=("a", "b"))
    s = SynonymsResult(word="y", items=("c",))
    assert d.word == "x"
    assert d.items == ("a", "b")
    assert s.word == "y"
    assert s.items == ("c",)


def test_not_found_is_provider_error() -> None:
    e = NotFound(word="nope", suggestions=("a", "b"))
    assert isinstance(e, ProviderError)
    assert e.word == "nope"
    assert e.suggestions == ("a", "b")


def test_unsupported_operation_is_provider_error() -> None:
    e = UnsupportedOperation(operation="synonyms")
    assert isinstance(e, ProviderError)
    assert e.operation == "synonyms"


def test_provider_error_can_be_raised() -> None:
    with pytest.raises(ProviderError):
        raise ProviderError("boom")
