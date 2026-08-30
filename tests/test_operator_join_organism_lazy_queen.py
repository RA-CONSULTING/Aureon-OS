"""Hermetic coverage for side-effect-free operator organism registration."""

from __future__ import annotations

import hashlib
import socket
import sys
import types
from pathlib import Path
from typing import Any

import pytest

from aureon.operator import aureon_operator as operator_module

_REPO = Path(__file__).resolve().parents[1]


def _file_fingerprint(path: Path) -> tuple[bool, int, int, str]:
    if not path.exists():
        return (False, 0, 0, "")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    stat = path.stat()
    return (True, stat.st_size, stat.st_mtime_ns, digest)


def _root_state_fingerprint() -> tuple[tuple[str, int, int], ...]:
    state_dir = _REPO / "state"
    if not state_dir.exists():
        return ()
    return tuple(
        sorted(
            (
                str(path.relative_to(_REPO)),
                path.stat().st_size,
                path.stat().st_mtime_ns,
            )
            for path in state_dir.rglob("*")
            if path.is_file()
        )
    )


@pytest.fixture
def isolated_organism_modules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Install inert hubs and prove registration has no network or root-state effects."""
    root_thoughts_before = _file_fingerprint(_REPO / "thoughts.jsonl")
    root_state_before = _root_state_fingerprint()
    socket_attempts: list[tuple[Any, ...]] = []
    mesh_calls: list[tuple[str, Any]] = []
    forbidden_factory_calls: list[str] = []

    def reject_socket(*args: Any, **kwargs: Any) -> None:
        del kwargs
        socket_attempts.append(args)
        raise AssertionError("join_organism attempted a network connection")

    monkeypatch.setattr(socket, "create_connection", reject_socket)
    monkeypatch.setattr(socket.socket, "connect", reject_socket)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AUREON_BUS_TRACE_DIR", str(tmp_path / "bus-traces"))
    monkeypatch.setenv("AUREON_STATE_DIR", str(tmp_path / "state"))

    class FakeMycelium:
        def connect_subsystem(self, name: str, subsystem: Any) -> None:
            mesh_calls.append((name, subsystem))

    mycelium_module = types.ModuleType("aureon.core.aureon_mycelium")
    mycelium_module.get_mycelium = lambda: FakeMycelium()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, mycelium_module.__name__, mycelium_module)

    queen_module = types.ModuleType("aureon.utils.aureon_queen_hive_mind")
    queen_module._QUEEN = None  # type: ignore[attr-defined]
    queen_module.get_existing_queen = lambda: queen_module._QUEEN  # type: ignore[attr-defined]

    def forbidden_factory(*args: Any, **kwargs: Any) -> None:
        del args, kwargs
        forbidden_factory_calls.append("called")
        raise AssertionError("join_organism must not create the Queen")

    queen_module.get_queen = forbidden_factory  # type: ignore[attr-defined]
    queen_module.create_queen_hive_mind = forbidden_factory  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, queen_module.__name__, queen_module)

    yield {
        "queen_module": queen_module,
        "mesh_calls": mesh_calls,
        "forbidden_factory_calls": forbidden_factory_calls,
        "socket_attempts": socket_attempts,
    }

    assert socket_attempts == []
    assert _file_fingerprint(_REPO / "thoughts.jsonl") == root_thoughts_before
    assert _root_state_fingerprint() == root_state_before


def test_join_organism_defers_unstarted_queen_without_factory_or_socket(
    isolated_organism_modules: dict[str, Any],
) -> None:
    subsystem = object()

    report = operator_module.join_organism(subsystem, "lazy-queen-test")

    assert report == {"mycelium": True, "queen": False}
    assert isolated_organism_modules["mesh_calls"] == [("lazy-queen-test", subsystem)]
    assert isolated_organism_modules["forbidden_factory_calls"] == []
    assert isolated_organism_modules["socket_attempts"] == []


def test_join_organism_registers_once_with_existing_queen(
    isolated_organism_modules: dict[str, Any],
) -> None:
    registrations: list[tuple[str, str, Any]] = []

    class ExistingQueen:
        def _register_child(self, name: str, system_type: str, subsystem: Any) -> None:
            registrations.append((name, system_type, subsystem))

    subsystem = object()
    isolated_organism_modules["queen_module"]._QUEEN = ExistingQueen()

    report = operator_module.join_organism(subsystem, "existing-queen-test")

    assert report == {"mycelium": True, "queen": True}
    assert registrations == [("existing-queen-test", "OPERATOR", subsystem)]
    assert isolated_organism_modules["forbidden_factory_calls"] == []


def test_join_organism_keeps_broken_existing_queen_registration_nonfatal(
    isolated_organism_modules: dict[str, Any],
) -> None:
    registration_attempts = 0

    class BrokenQueen:
        def _register_child(self, name: str, system_type: str, subsystem: Any) -> None:
            nonlocal registration_attempts
            del name, system_type, subsystem
            registration_attempts += 1
            raise RuntimeError("fixture registration failure")

    isolated_organism_modules["queen_module"]._QUEEN = BrokenQueen()

    report = operator_module.join_organism(object(), "broken-queen-test")

    assert report == {"mycelium": True, "queen": False}
    assert registration_attempts == 1
    assert isolated_organism_modules["forbidden_factory_calls"] == []
