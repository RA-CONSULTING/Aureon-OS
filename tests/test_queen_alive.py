"""The Queen accessor reports life without constructing provider machinery."""

from __future__ import annotations

from typing import Any

from aureon.utils import aureon_queen_hive_mind as queen_module


def test_existing_queen_accessor_never_invokes_the_factory(monkeypatch: Any) -> None:
    factory_calls: list[str] = []

    def forbidden_factory(*_args: Any, **_kwargs: Any) -> None:
        factory_calls.append("called")
        raise AssertionError("nonconstructing Queen accessor invoked the factory")

    monkeypatch.setattr(queen_module, "_QUEEN", None)
    monkeypatch.setattr(queen_module, "create_queen_hive_mind", forbidden_factory)

    assert queen_module.get_existing_queen() is None
    assert factory_calls == []


def test_existing_queen_accessor_returns_the_started_singleton(monkeypatch: Any) -> None:
    sentinel = object()
    monkeypatch.setattr(queen_module, "_QUEEN", sentinel)

    assert queen_module.get_existing_queen() is sentinel
