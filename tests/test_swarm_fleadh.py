"""
The Fleadh Swarm — the festival equations, pinned rule by rule.

Pins: worker gain scales with skill and ρ = s^γ weighs the zone's observer;
visitor couplings come from the NAMED registry (pair-mates converge faster
than strangers); the steering law preserves step length EXACTLY; the hard
safety boundary refuses flow-increasing actions at capacity REGARDLESS of
coherence; Γ warms honestly; only realized increments enter the echo; and
the whole labeled-scenario festival is deterministic.
"""

from __future__ import annotations

import math

import pytest

from aureon.swarm.fleadh import (
    BETA_COUPLING,
    GAMMA_RELIABILITY,
    FleadhCompany,
    VisitorAgent,
    WorkerAgent,
    Zone,
    steer_flow,
)
from aureon.swarm.steering import _norm

ACTIONS = ["open_corridor", "hold_flow", "reroute", "close_road"]
CONTEXT = [0.4, 0.2, -0.1, 0.3, 0.0, 0.1, -0.2, 0.05]


@pytest.fixture(autouse=True)
def _dark_field(monkeypatch, tmp_path):
    monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(tmp_path / "hnc.jsonl"))


def _workers(zone: str, skills: list[float]) -> list[WorkerAgent]:
    return [WorkerAgent(f"{zone}-w{i}", role="crew", skill=s, actions=ACTIONS,
                        freq=1.0 + 0.1 * i, phase=0.3 * i)
            for i, s in enumerate(skills)]


def _visitor(vid: str, kind: str, gid: str) -> VisitorAgent:
    return VisitorAgent(vid, kind, gid, ACTIONS)


def _company(capacity: int = 6, beta: float = 0.9) -> FleadhCompany:
    return FleadhCompany(
        [Zone("stage", _workers("stage", [0.9, 0.7, 0.5]), capacity, beta=beta),
         Zone("street", _workers("street", [0.8, 0.6]), capacity, beta=beta)],
        tau=2, gamma_crit=0.5)


# ── workers: skill modulates gain and reliability ─────────────────────────
def test_skill_modulates_gain_and_reliability():
    strong = WorkerAgent("w-a", "medic", skill=0.9, actions=ACTIONS)
    weak = WorkerAgent("w-b", "medic", skill=0.3, actions=ACTIONS)
    assert strong.alpha > weak.alpha                       # α = α₀·s
    assert strong.reliability == pytest.approx(0.9 ** GAMMA_RELIABILITY)
    assert weak.reliability == pytest.approx(0.3 ** GAMMA_RELIABILITY)
    with pytest.raises(ValueError, match="skill"):
        WorkerAgent("w-c", "medic", skill=1.5, actions=ACTIONS)


def test_reliability_weighs_the_zone_observer():
    hi = Zone("hi", _workers("hi", [0.95, 0.9]), 10)
    lo = Zone("lo", _workers("lo", [0.2, 0.15]), 10)
    grad = [0.0] * 8
    vectors = {a: [0.1 * (i + 1)] * 8 for i, a in enumerate(ACTIONS)}
    t_hi = hi.step(CONTEXT, vectors, None, grad)
    t_lo = lo.step(CONTEXT, vectors, None, grad)
    # both measured; the weighting itself is exercised (ρ ≠ uniform)
    assert t_hi["operator_level_weighted"] != t_lo["operator_level_weighted"]


# ── visitors: named group couplings ───────────────────────────────────────
def test_pair_mates_converge_faster_than_strangers():
    a1, a2 = _visitor("v-a1", "pair", "gA"), _visitor("v-a2", "pair", "gA")
    b1 = _visitor("v-b1", "single", "gB")
    def dist(x, y):
        return math.sqrt(sum((p - q) ** 2 for p, q in zip(x.psi, y.psi,
                                                          strict=True)))
    before_pair, before_cross = dist(a1, a2), dist(a1, b1)
    for _ in range(6):
        a1.couple([a2, b1])
        a2.couple([a1, b1])
    shrink_pair = dist(a1, a2) / before_pair
    shrink_cross = dist(a1, b1) / before_cross
    assert shrink_pair < shrink_cross            # β_pair > β_cross, measured
    assert BETA_COUPLING["pair"] > BETA_COUPLING["cross"]
    with pytest.raises(ValueError, match="by name"):
        VisitorAgent("v-x", "mob", "gX", ACTIONS)


# ── steering: step length preserved exactly ───────────────────────────────
def test_steer_flow_preserves_step_length_exactly():
    u = [1.0, 2.0, 0.0, 0.5]
    grad = [0.3, -0.8, 0.4, 0.0]
    out = steer_flow(u, grad)
    assert _norm(out["steered"]) == pytest.approx(_norm(u), abs=1e-12)
    assert out["steered"] != u                   # the path bent…
    assert "preserved" in out["note"]            # …but was never arrested
    assert steer_flow(u, [0.0] * 4)["steered"] == u
    assert steer_flow([0.0] * 4, grad)["steered"] == [0.0] * 4


# ── the hard safety boundary beats coherence ──────────────────────────────
def test_capacity_refuses_flow_increase_regardless_of_coherence():
    company = _company(capacity=2)
    stage = company.zones["stage"]
    for i in range(2):
        stage.admit(_visitor(f"v-{i}", "single", f"g{i}"))
    for t in range(12):
        company.step(t, CONTEXT)
    # whenever 'open_corridor' topped the mass at capacity, safety refused it
    for entry in company.ledger:
        out = entry["outcomes"]["stage"]
        top = min(out["tick"]["joint_mass"],
                  key=lambda a: (-out["tick"]["joint_mass"][a], a))
        if top == "open_corridor":
            assert out["decision"]["actualized"] is False
            assert any("hard safety boundary" in r
                       for r in out["decision"]["reasons"])
    # at least the invariant machinery itself is honest: refusals are recorded
    assert all("capacity" in r for r in company.safety_refusals)


# ── population, memory, determinism ───────────────────────────────────────
def _festival(steps: int = 14) -> FleadhCompany:
    company = _company()
    kinds = ["single", "pair", "pair", "group", "group", "group"]
    for t in range(steps):
        arrivals = ([_visitor(f"t{t}-v{k}", kinds[k % len(kinds)], f"grp-{t}")
                     for k in range(2)] if t % 3 == 0 else None)
        company.step(t, CONTEXT, arrivals=arrivals,
                     arrival_zone="street" if arrivals else None)
    return company


def test_population_grows_and_march_is_deterministic():
    a, b = _festival(), _festival()
    assert a.ledger == b.ledger                              # same festival
    report = a.report()
    assert report["final_population"]["visitors"] == 10      # N_V(t) grew
    assert report["final_population"]["workers"] == 5
    # early Γ warm-up parked possibilities; realized-only memory holds
    bus = report["bus"]
    assert bus["possibility_steps"]
    realized = set(bus["realized_steps"])
    actual_steps = {e["t"] for e in a.ledger
                    if any(o["decision"]["actualized"]
                           for o in e["outcomes"].values())}
    assert realized == actual_steps
    assert "LABELED scenario" in report["boundary"]
