"""
The Harmonic Swarm — every doctrine rule from the source papers, pinned.

Pins: soft mass only (simplex normalized, never one-hot before collapse);
steering preserves the parallel component EXACTLY and never arrests; the
echo bus holds realized increments only with a τ-delayed, honestly-dark
read; the island of stability refuses β beyond the cliff with a named
reason; Γ warms honestly (None → no collapse); the canonical field may only
TIGHTEN the Queen's gate (b46); collapse is deterministic; no single agent
ever owns a task; and the whole company march is reproducible.
"""

from __future__ import annotations

import math

import pytest

from aureon.swarm import (
    BETA_ISLAND,
    CausalEchoBus,
    Cluster,
    ClusterCoherence,
    Company,
    QueenGate,
    SteeringField,
    SwarmAgent,
)

ACTIONS = ["hold", "advance", "retreat"]
VECTORS = {
    "hold": [0.0] * 8,
    "advance": [1.0, 0.5, 0.0, 0.0, 0.2, 0.0, 0.0, 0.1],
    "retreat": [-1.0, -0.5, 0.0, 0.0, -0.2, 0.0, 0.0, -0.1],
}
CONTEXT = [0.4, 0.2, -0.1, 0.3, 0.0, 0.1, -0.2, 0.05]


@pytest.fixture(autouse=True)
def _dark_field(monkeypatch, tmp_path):
    monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(tmp_path / "hnc.jsonl"))


def _cluster(name="research", n=3, **kw) -> Cluster:
    agents = [SwarmAgent(f"{name}-{i}", role=name, actions=ACTIONS,
                         freq=1.0 + 0.1 * i, phase=0.3 * i) for i in range(n)]
    return Cluster(name, agents, **kw)


# ── agent: soft probability coordination ──────────────────────────────────
def test_agent_keeps_a_normalized_soft_simplex():
    agent = SwarmAgent("a1", role="research", actions=ACTIONS)
    for _ in range(5):
        agent.update(CONTEXT, [], None)
        p = agent.propose(VECTORS, cluster_gamma=0.7)
        assert abs(sum(p.values()) - 1.0) < 1e-9
        assert all(v > 0.0 for v in p.values())      # soft — never a hard vote
        assert max(p.values()) < 1.0                 # never one-hot pre-collapse
    assert math.isfinite(agent.purity)
    # deterministic seeding: the same identity always starts the same march
    twin = SwarmAgent("a1", role="research", actions=ACTIONS)
    assert twin.psi == SwarmAgent("a1", role="research", actions=ACTIONS).psi


# ── steering: shapes, never arrests ───────────────────────────────────────
def test_steering_preserves_parallel_component_exactly():
    field = SteeringField(resistance=0.8)
    heading = [1.0, 0.0, 0.0]
    proposal = [2.0, 3.0, -1.0]
    out = field.steer(proposal, heading)
    assert out["parallel"] == [2.0, 0.0, 0.0]        # untouched, exactly
    assert out["steered"][0] == pytest.approx(2.0)   # motion never arrested
    assert out["steered"][1] == pytest.approx(3.0 * 0.2)
    assert out["steered"][2] == pytest.approx(-1.0 * 0.2)


def test_steering_with_no_heading_passes_through_and_says_so():
    out = SteeringField(0.5).steer([1.0, 2.0], None)
    assert out["steered"] == [1.0, 2.0]
    assert "no heading" in out["note"]
    with pytest.raises(ValueError):
        SteeringField(1.0)                           # full arrest is not a field


# ── echo bus: realized-only, honestly dark ────────────────────────────────
def test_echo_bus_holds_realized_only_and_darkness_is_dark():
    bus = CausalEchoBus(tau=2)
    bus.record_possibilities(0, {"advance": 0.6, "hold": 0.4})
    assert bus.echo(2) is None                        # possibilities ≠ memory
    bus.record_realized(0, [1.0, 0.0])
    assert bus.echo(1) is None                        # τ not yet elapsed
    assert bus.echo(2) == [1.0, 0.0]
    assert bus.possibilities(0) == {"advance": 0.6, "hold": 0.4}


# ── coherence: honest warm-up ─────────────────────────────────────────────
def test_gamma_is_none_until_the_window_fills():
    c = ClusterCoherence(window=4)
    for i in range(3):
        c.push(float(i), float(i))
        assert c.gamma() is None
    c.push(3.0, 3.0)
    assert c.gamma() == pytest.approx(1.0)
    flat = ClusterCoherence(window=3)
    for _ in range(3):
        flat.push(1.0, 5.0)
    assert flat.gamma() == 0.0                        # constants ≠ coherence


# ── the Queen's gate ──────────────────────────────────────────────────────
def test_island_of_stability_refuses_beyond_the_cliff():
    gate = QueenGate()
    mass = {"advance": 0.9, "hold": 0.05, "retreat": 0.05}
    out = gate.actualize(mass, gamma_cluster=0.95, beta=1.2)
    assert not out.actualized
    assert any("island of stability" in r for r in out.reasons)
    lo, hi = BETA_ISLAND
    assert gate.actualize(mass, 0.95, (lo + hi) / 2).actualized


def test_warming_gamma_keeps_the_ensemble_open():
    out = QueenGate().actualize({"advance": 1.0}, gamma_cluster=None, beta=0.9)
    assert not out.actualized
    assert any("warming" in r for r in out.reasons)


def test_canonical_field_may_only_tighten(monkeypatch):
    import aureon.swarm.queen_gate as qg

    mass = {"advance": 0.9, "hold": 0.1}
    # dark field: cluster Γ stands alone, and the darkness is recorded
    dark = QueenGate().actualize(mass, 0.9, 0.9)
    assert dark.actualized and dark.canonical_status == "canonical_dark"
    # live LOW canonical Γ tightens the gate shut — never loosens it
    monkeypatch.setattr(qg, "_canonical_gamma", lambda: 0.2)
    tight = QueenGate().actualize(mass, 0.9, 0.9)
    assert not tight.actualized
    assert tight.gamma_effective == pytest.approx(0.2)
    # live HIGH canonical Γ cannot rescue a weak cluster
    monkeypatch.setattr(qg, "_canonical_gamma", lambda: 0.99)
    weak = QueenGate().actualize(mass, 0.3, 0.9)
    assert not weak.actualized
    assert weak.gamma_effective == pytest.approx(0.3)


def test_conscience_veto_is_a_recorded_refusal():
    gate = QueenGate(veto=lambda action: action == "advance")
    out = gate.actualize({"advance": 0.9, "hold": 0.1}, 0.95, 0.9)
    assert not out.actualized
    assert any("conscience veto" in r for r in out.reasons)
    assert gate.decisions[-1] is out                  # recorded, never silent


# ── company: no single-agent ownership, deterministic march ───────────────
def test_no_single_agent_ever_owns_a_task():
    solo = [SwarmAgent("only", role="x", actions=ACTIONS)]
    with pytest.raises(ValueError, match="never owned by a single agent"):
        Cluster("solo-dept", solo)


def _run_company(steps=12) -> Company:
    company = Company([_cluster("research"), _cluster("audit", n=2)],
                      tau=2, gamma_crit=0.5)
    for t in range(steps):
        company.step(t, CONTEXT, VECTORS)
    return company


def test_company_march_is_deterministic_and_measured():
    a, b = _run_company(), _run_company()
    assert a.ledger == b.ledger                       # same swarm, same march
    report = a.report()
    assert report["steps"] == 12
    assert report["decisions_total"] == 24            # every gate decision counted
    # early steps (warming Γ) parked possibilities in the UED
    assert report["bus"]["possibility_steps"], "warm-up must park possibilities"
    assert a.assign("month-end close", "audit")["assigned"]
    assert not a.assign("month-end close", "ghost-dept")["assigned"]
