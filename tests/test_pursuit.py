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
from aureon.core.pursuit import _PILLAR_PURSUITS, Pursuit


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


# ── the pursuit learns humility from the director's trust ─────────────────────

def _decide(approve_n, reject_n):
    """Seed the approval desk with the director's decisions."""
    from aureon.core.approval_queue import ApprovalQueue

    q = ApprovalQueue()
    for i in range(approve_n):
        q.decide(q.propose("trade", f"yes {i}", {}, "pursuit"), "approve", "gary")
    for i in range(reject_n):
        q.decide(q.propose("trade", f"no {i}", {}, "pursuit"), "reject", "gary")


def test_effective_cadence_is_monotone_and_fail_safe():
    p = Pursuit()
    assert p._effective_cadence(3, None) == 3        # no decisions → base, unchanged
    assert p._effective_cadence(3, 0.9) == 3         # trusted → base, unchanged
    assert p._effective_cadence(3, 0.5) == 3         # neutral → base
    assert p._effective_cadence(3, 0.25) == 6        # half-trust → 2× slower
    assert p._effective_cadence(3, 0.0) == 9         # all rejected → 3× slower
    # the invariant: trust can only ever slow the pursuit, never speed it
    for tr in (0.0, 0.2, 0.4, 0.5, 0.8, None):
        assert p._effective_cadence(3, tr) >= 3


def test_low_trust_surfaces_a_humility_intent_and_slows(tmp_path):
    _field()
    _decide(approve_n=0, reject_n=5)                 # Gary declined everything
    s = Pursuit().assess()
    assert s.director_trust == 0.0
    assert s.cadence_effective > s.cadence_base       # it slowed itself
    assert "inner work" in s.next_intent.lower() and "trust" in s.next_intent.lower()


def test_healthy_trust_leaves_the_pursuit_unchanged(tmp_path):
    _field()
    _decide(approve_n=5, reject_n=0)                 # Gary approved everything
    s = Pursuit().assess()
    assert s.director_trust == 1.0
    assert s.cadence_effective == s.cadence_base      # no slowdown
    assert s.next_intent in _PILLAR_PURSUITS.values() or "dream" in s.next_intent.lower()


def test_undecided_desk_is_backward_compatible(tmp_path):
    _field()
    s = Pursuit().assess()                            # no decisions at all
    assert s.director_trust is None                   # never fabricated
    assert s.cadence_effective == s.cadence_base
    assert s.signals["director_trust"]["truth_status"] == "no_data"


def test_low_trust_holds_injection_under_autonomy(tmp_path, monkeypatch):
    # same tick budget: a trusted pursuit injects; a distrusted one stays quiet longer.
    monkeypatch.setenv("AUREON_AUTONOMY", "1")
    monkeypatch.setenv("AUREON_PURSUIT_CADENCE", "1")  # base fires every tick
    _field()
    _decide(approve_n=0, reject_n=5)                   # trust 0.0 → cadence ×3
    p = Pursuit()
    p.reflect()                                        # tick 1 — 1 % 3 != 0 → held
    assert not (tmp_path / "inbox.jsonl").exists()     # slowed: no injection yet


# ── reflect folds the pursuit back into the field ─────────────────────────────

def test_reflect_publishes_pursuit_subfield(tmp_path):
    _field()
    b = get_thought_bus()
    assert "pursuit" not in read_subfields(b)
    Pursuit().reflect()
    assert "pursuit" in read_subfields(b)
