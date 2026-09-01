"""Pure life-context tests and fail-closed opportunity-scanner tests."""

from __future__ import annotations

from typing import Any

import pytest

from aureon.vault.voice.aureon_personas import (
    ArtistVoice,
    EngineerVoice,
    MysticVoice,
    QuantumPhysicistVoice,
)
from aureon.vault.voice.life_context import LifeContext, LifeEvent
from aureon.vault.voice.opportunity_scanner import OpportunityHit, OpportunityScanner
from aureon.vault.voice.persona_action import PersonaActuator


class _Trap:
    def __getattribute__(self, _name: str) -> Any:
        raise AssertionError("release-held opportunity path touched an effect owner")


def test_life_event_round_trip_payload() -> None:
    event = LifeEvent(
        event_id="e1",
        title="Wedding in May",
        tags=["wedding", "family"],
        date="May 12",
    )
    payload = event.to_dict()
    assert payload["event_id"] == "e1"
    assert payload["title"] == "Wedding in May"
    assert payload["tags"] == ["wedding", "family"]
    assert payload["date"] == "May 12"


def test_life_context_local_add_archive_complete_and_remove() -> None:
    context = LifeContext()
    wedding = context.add("Wedding in May", tags=["wedding"], date="May 12")
    work = context.add("Finish design for work", tags=["work"])
    assert {event.event_id for event in context.active()} == {wedding.event_id, work.event_id}
    assert context.archive(wedding.event_id) is True
    assert {event.event_id for event in context.active()} == {work.event_id}
    assert context.complete(work.event_id) is True
    assert context.active() == []
    assert context.remove(wedding.event_id) is True


def test_life_context_vault_mutation_and_reload_paths_are_held() -> None:
    context = LifeContext(vault=_Trap())
    with pytest.raises(RuntimeError, match="life_context_hold"):
        context.add("Must not persist")
    assert len(context) == 0

    local = LifeContext()
    event = local.add("Local draft")
    local._vault = _Trap()
    with pytest.raises(RuntimeError, match="life_context_hold"):
        local.archive(event.event_id)
    assert event.status == "active"
    with pytest.raises(RuntimeError, match="life_context_hold"):
        local.complete(event.event_id)
    assert event.status == "active"
    with pytest.raises(RuntimeError, match="life_context_hold"):
        local._persist(event)
    with pytest.raises(RuntimeError, match="life_context_hold"):
        local.load_from_vault(_Trap())


def test_persona_opportunity_scans_are_pure() -> None:
    wedding = LifeEvent("w", "Wedding in May", tags=["wedding"], date="May 12")
    research = LifeEvent("r", "Research thesis", tags=["research"])
    work = LifeEvent("x", "Work deadline", tags=["work"])
    assert "visual" in (ArtistVoice().scan_for_opportunity(wedding) or "")
    assert "528 Hz" in (MysticVoice().scan_for_opportunity(wedding) or "")
    assert "most-cited" in (QuantumPhysicistVoice().scan_for_opportunity(research) or "")
    assert "small tool" in (EngineerVoice().scan_for_opportunity(work) or "")


def test_scanner_start_scan_dispatch_and_loop_are_held(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "aureon.vault.voice.opportunity_scanner.threading.Thread",
        lambda *_args, **_kwargs: pytest.fail("scanner must not create a thread"),
    )
    context = LifeContext()
    event = context.add("Wedding in May", tags=["wedding"])
    scanner = OpportunityScanner(
        personas={"artist": ArtistVoice()},
        life_context=context,
        actuator=PersonaActuator(thought_bus=_Trap()),
    )
    hit = OpportunityHit("artist", event.event_id, "build a visual", 0.7)
    calls = (
        scanner.start,
        scanner.scan_once,
        lambda: scanner._dispatch(hit, event),
        scanner._loop,
    )
    for call in calls:
        with pytest.raises(RuntimeError, match="opportunity_scanner_hold"):
            call()
    assert scanner.running is False
    assert scanner.history() == []
