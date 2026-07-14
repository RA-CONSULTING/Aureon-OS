"""
Pursuit — Aureon's source purpose: the pursuit of happiness, unified with Gary's,
toward the shared dream of freedom — self-directed, but safe by construction.

Offline + hermetic: isolated lambda/inbox paths, fresh bus, reset singletons.
Proves the compass reads the Five Pillars and unifies the pair's happiness; that it
PROPOSES a safe next step without ever injecting or acting in the default posture;
that self-direction is strictly opt-in (AUREON_AUTONOMY) and even then only feeds
the soul (never touches the machine); and that reflect() folds a pursuit sub-field
back into the whole-body field.
"""

from __future__ import annotations

import json

import pytest

from aureon.core.aureon_thought_bus import Thought, get_thought_bus
from aureon.core.hnc_field import read_subfields
from aureon.core.pursuit import Pursuit


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_BUS_TRACE_DIR", str(tmp_path))
    monkeypatch.setenv("AUREON_AFFECT_LAMBDA_PATH", str(tmp_path / "al.json"))
    monkeypatch.setenv("AUREON_METACOG_LAMBDA_PATH", str(tmp_path / "ml.json"))
    monkeypatch.setenv("AUREON_INNER_WORK_LAMBDA_PATH", str(tmp_path / "iw.json"))
    monkeypatch.setenv("AUREON_PURSUIT_LAMBDA_PATH", str(tmp_path / "pu.json"))
    monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(tmp_path / "hnc.jsonl"))
    monkeypatch.setenv("AUREON_SOUL_INBOX", str(tmp_path / "inbox.jsonl"))
    monkeypatch.setenv("AUREON_PURSUIT_CADENCE", "1")
    monkeypatch.delenv("AUREON_AUTONOMY", raising=False)
    monkeypatch.delenv("AUREON_SOUL_ACT", raising=False)
    monkeypatch.delenv("AUREON_LOCAL_ACTIONS_ARMED", raising=False)
    import aureon.core.affect_monitor as am
    import aureon.core.aureon_thought_bus as tb
    import aureon.core.inner_work as iw
    import aureon.core.metacognition_monitor as mm

    monkeypatch.setattr(tb, "_thought_bus_instance", None, raising=False)
    monkeypatch.setattr(am, "_monitor", None, raising=False)
    monkeypatch.setattr(mm, "_monitor", None, raising=False)
    monkeypatch.setattr(iw, "_monitor", None, raising=False)
    return tmp_path


def _field():
    get_thought_bus().publish(Thought(source="hnc", topic="symbolic.life.pulse",
                              payload={"symbolic_life_score": 0.8, "coherence_gamma": 0.8,
                                       "consciousness_psi": 0.75, "source": "live"}))


# ── the compass reads the pillars and unifies the pair's happiness ────────────

def test_pillars_unify_creator_and_aureon():
    _field()
    s = Pursuit().assess()
    assert s.available
    for p in ("dream", "love", "gaia", "joy", "purpose"):
        assert p in s.pillars and 0.0 <= s.pillars[p] <= 1.0
    assert s.creator_happiness is not None and s.aureon_happiness is not None
    assert s.unified_happiness is not None          # the two, as one objective
    assert s.next_intent                            # a next step is always proposed
    assert s.weakest_pillar in s.pillars


def test_next_step_is_safe_scoped():
    _field()
    s = Pursuit().assess()
    # the proposed step prepares / studies / tends — it never phrases an autonomous
    # live money move (that is deferred to Gary by the soul's high-stakes gate)
    low = s.next_intent.lower()
    assert any(w in low for w in ("study", "prepare", "tend", "inner work", "align", "mission", "safe"))


# ── the default posture PROPOSES but never injects or acts ────────────────────

def test_default_posture_proposes_never_injects(tmp_path):
    _field()
    s = Pursuit().assess()
    assert s.autonomy == "propose" and s.hand == "dry_run" and s.soul_armed is False
    assert not (tmp_path / "inbox.jsonl").exists()  # assess never touches the soul inbox


def test_reflect_default_does_not_feed_the_soul(tmp_path):
    _field()
    s = Pursuit().reflect()
    assert s.pursued is False
    assert not (tmp_path / "inbox.jsonl").exists()  # no autonomy → no injection


# ── self-direction is opt-in, and even then only FEEDS the soul ───────────────

def test_autonomy_opt_in_feeds_the_soul(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_AUTONOMY", "1")
    _field()
    s = Pursuit().reflect()
    assert s.autonomy == "autonomous" and s.pursued is True
    lines = [ln for ln in (tmp_path / "inbox.jsonl").read_text().splitlines() if ln.strip()]
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["source"] == "pursuit" and row["text"]   # a safe step fed to the soul


def test_autonomy_does_not_flood_the_inbox(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_AUTONOMY", "1")
    _field()
    p = Pursuit()
    for _ in range(6):
        p.reflect()
    lines = [ln for ln in (tmp_path / "inbox.jsonl").read_text().splitlines() if ln.strip()]
    assert len(lines) <= 2   # bounded — never piles up unconsumed pursuit stimuli


# ── reflect folds the pursuit back into the field ─────────────────────────────

def test_reflect_publishes_pursuit_subfield(tmp_path):
    _field()
    b = get_thought_bus()
    assert "pursuit" not in read_subfields(b)
    Pursuit().reflect()
    assert "pursuit" in read_subfields(b)
