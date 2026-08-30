"""
The MCP boundary must blame the call for what the CALL did — not for what the organism did.

``interior_unchanged`` was measured as ThoughtBus depth before vs after dispatch. On a quiet bus
that works. On a live organism it measures the wrong thing entirely: the mycelium, the nexus, the
scanners and a dozen other producers publish from their own threads while the call is in flight, the
depth moves, and the boundary reports ``laminar=False`` — a false accusation that nothing crossing
the membrane can clear.

This was not hypothetical. It appeared the moment the declared dependency set was actually installed
and those producers started: a read-only ``read_state`` call over the live Flask route came back
``laminar=False``, and the capability demo declared the MCP class unproven. Every earlier green run
had simply been on a partially-imported organism with a quiet bus.

The measure is now per calling thread — ThoughtBus invokes subscribers synchronously in the
publishing thread, so a publish can be attributed. A read-only tool that published would do so on the
dispatch thread; a producer on another thread is not this call's doing.
"""

from __future__ import annotations

import json
import threading

import pytest

from aureon.bio import mcp_transport as mt


class _Registry:
    """A minimal stand-in for GuardedToolRegistry with a controllable dispatch body."""

    def __init__(self, body=None) -> None:
        self.body = body
        self.calls: list[tuple[str, dict]] = []

    def execute(self, name: str, args: dict) -> str:
        self.calls.append((name, dict(args)))
        if self.body is not None:
            self.body()
        return json.dumps({"ok": True, "tool": name})


@pytest.fixture
def bus(monkeypatch):
    """The real ThoughtBus, isolated to this test."""
    monkeypatch.setenv("AUREON_AUDIT_MODE", "1")
    from aureon.core.aureon_thought_bus import ThoughtBus, get_thought_bus

    instance = ThoughtBus()
    monkeypatch.setattr("aureon.core.aureon_thought_bus._thought_bus_instance", instance,
                        raising=False)
    monkeypatch.setattr("aureon.core.aureon_thought_bus.get_thought_bus",
                        lambda *a, **k: instance)
    assert get_thought_bus is not None
    return instance


def _publish(bus, source: str = "other_producer") -> None:
    from aureon.core.aureon_thought_bus import Thought

    bus.publish(Thought(source=source, topic="test.noise", payload={"n": 1}))


# ── the false accusation ────────────────────────────────────────────────────────

def test_another_thread_publishing_does_not_make_the_call_leaky(bus):
    """The original defect, reproduced: a producer thread firing mid-dispatch used to flip
    interior_unchanged to False, accusing a read-only call of mutating the interior."""
    def noisy_dispatch() -> None:
        done = threading.Event()

        def producer() -> None:
            for _ in range(5):
                _publish(bus)
            done.set()

        t = threading.Thread(target=producer)
        t.start()
        done.wait(timeout=5)
        t.join(timeout=5)

    result = mt.handle_mcp_call("read_state", {}, registry=_Registry(noisy_dispatch))
    assert result.interior_unchanged is True
    assert result.laminar is True


def test_a_quiet_call_is_still_proven_unchanged(bus):
    result = mt.handle_mcp_call("read_state", {}, registry=_Registry())
    assert result.interior_unchanged is True
    assert result.laminar is True


# ── the accusation that must still stick ────────────────────────────────────────

def test_a_tool_that_publishes_is_caught(bus):
    """The invariant this measure exists to enforce: if the read-only surface ever widened and a
    tool published from the dispatch thread, the call must not be called laminar."""
    result = mt.handle_mcp_call("read_state", {}, registry=_Registry(lambda: _publish(bus, "the_tool")))
    assert result.interior_unchanged is False
    assert result.laminar is False


def test_publishing_is_caught_even_amid_other_traffic(bus):
    """A tool cannot hide its own publish behind the organism's background noise."""
    def sneaky() -> None:
        t = threading.Thread(target=lambda: [_publish(bus) for _ in range(3)])
        t.start()
        t.join(timeout=5)
        _publish(bus, "the_tool")        # this one is ours

    result = mt.handle_mcp_call("read_state", {}, registry=_Registry(sneaky))
    assert result.interior_unchanged is False


# ── the watch itself ────────────────────────────────────────────────────────────

def test_the_watch_leaves_no_subscriber_behind(bus):
    """A per-call subscription that is never removed would accumulate one handler per request."""
    before = bus.subscriber_count("*")
    for _ in range(5):
        mt.handle_mcp_call("read_state", {}, registry=_Registry())
    assert bus.subscriber_count("*") == before


def test_unsubscribe_removes_one_handler_and_is_idempotent(bus):
    """subscribe() had no counterpart, so an observer had to leak or touch private state."""
    seen: list = []

    def handler(thought) -> None:
        seen.append(thought)

    bus.subscribe("test.noise", handler)
    _publish(bus)
    assert len(seen) == 1

    assert bus.unsubscribe("test.noise", handler) is True
    _publish(bus)
    assert len(seen) == 1, "the handler must stop receiving after unsubscribe"
    assert bus.unsubscribe("test.noise", handler) is False, "removing twice is False, not an error"
    assert bus.unsubscribe("never.subscribed", handler) is False


def test_an_unwatchable_bus_falls_back_without_claiming_proof(monkeypatch):
    """No bus means the call cannot prove anything, and must not pretend it did."""
    monkeypatch.setattr(mt, "_interior_fingerprint", lambda: None)

    class _NoBus:
        watching = False
        published_here = 0

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return None

    monkeypatch.setattr(mt, "_PublishWatch", _NoBus)
    result = mt.handle_mcp_call("read_state", {}, registry=_Registry())
    assert result.interior_unchanged is False
    assert result.laminar is False


# ── the guards in front are unchanged ───────────────────────────────────────────

def test_an_out_of_surface_tool_is_still_refused_before_dispatch(bus):
    registry = _Registry()
    result = mt.handle_mcp_call("execute_shell", {"cmd": "ls"}, registry=registry)
    assert result.ok is False
    assert result.refusal and "read-only safe surface" in result.refusal
    assert registry.calls == [], "a refused tool must never reach dispatch"
