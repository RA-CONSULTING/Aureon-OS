"""
The Capability Grid — every Aureon capability marched through the hive.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The swarm is not a demo — it is the coordination layer the organism's real
capabilities route through. This module is the explicit registry of those
routes (a lane joins by NAME, never by inference), and the speed bench that
measures the logic across the five domains Gary named:

* **trading**            — real committed Kraken daily candles (provenance-
                           stamped, the b48 datasets) → return vectors
* **pattern_recognition**— autocorrelation spectra of the SAME real closes
                           (lag structure — the harmonic fingerprint)
* **accounting**         — the King's Court coordination steps from a real
                           labeled march (balance proofs as context)
* **fintech**            — the HMRC MTD v1.0 pressing of those books
                           (schema-validated payload as context)
* **coding**             — the repo's OWN logic-train audit (every wired
                           module hashed into the context stream)

Every lane declares its provenance; a lane whose source is dark returns
NAMED blockers and an empty context — the grid never fabricates a domain.
Throughput (steps/s, agent-updates/s) is measured with a monotonic clock;
timing is reported, never pinned into determinism checks.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aureon.swarm.agent import SwarmAgent, _seed_vector
from aureon.swarm.company import Cluster, Company

__all__ = ["CapabilityLane", "LANES", "build_lane", "run_lane", "run_grid"]

_REPO = Path(__file__).resolve().parents[2]
_OHLC = _REPO / "data" / "historical" / "kraken_ohlc_BTCUSD_1440m.json"
_DIM = 8


@dataclass
class CapabilityLane:
    """One capability routed through the swarm — real contexts or named blockers."""

    name: str
    contexts: list[list[float]]
    actions: dict[str, list[float]]
    provenance: str
    blockers: list[str] = field(default_factory=list)


def _action_vectors(names: list[str]) -> dict[str, list[float]]:
    """Deterministic distinct direction per action — hash-seeded, no RNG."""
    return {n: _seed_vector(f"action:{n}", _DIM) for n in names}


def _window_returns(closes: list[float]) -> list[list[float]]:
    """Sliding windows of 8 normalized returns — the trading context stream."""
    rets = [(b - a) / a for a, b in zip(closes[:-1], closes[1:], strict=True)]
    scale = max(abs(r) for r in rets) or 1.0
    rets = [r / scale for r in rets]
    return [rets[i:i + _DIM] for i in range(len(rets) - _DIM + 1)]


def _autocorr_context(closes: list[float], window: int = 32) -> list[list[float]]:
    """Rolling lag-1..8 autocorrelations — the pattern-recognition context."""
    contexts: list[list[float]] = []
    for i in range(window, len(closes)):
        seg = closes[i - window:i]
        mean = sum(seg) / len(seg)
        dev = [x - mean for x in seg]
        var = sum(d * d for d in dev) or 1.0
        contexts.append([
            sum(dev[k] * dev[k + lag] for k in range(len(dev) - lag)) / var
            for lag in range(1, _DIM + 1)])
    return contexts


def _load_closes() -> tuple[list[float], str, list[str]]:
    if not _OHLC.exists():
        return [], "", [f"real OHLC dataset missing at {_OHLC} — lane refuses, "
                        f"nothing is synthesized"]
    payload = json.loads(_OHLC.read_text(encoding="utf-8"))
    closes = [float(c["close"]) for c in payload.get("candles", [])]
    prov = (f"{payload['provenance'].get('source', '?')} — {payload.get('symbol')}"
            f", {len(closes)} real daily candles")
    if len(closes) < 64:
        return [], prov, [f"only {len(closes)} candles — too short to march"]
    return closes, prov, []


# ── the five lanes, each from a REAL organ ────────────────────────────────
def _lane_trading() -> CapabilityLane:
    closes, prov, blockers = _load_closes()
    return CapabilityLane(
        "trading", _window_returns(closes) if not blockers else [],
        _action_vectors(["buy", "hold", "sell"]), prov, blockers)


def _lane_pattern_recognition() -> CapabilityLane:
    closes, prov, blockers = _load_closes()
    return CapabilityLane(
        "pattern_recognition", _autocorr_context(closes) if not blockers else [],
        _action_vectors(["trend", "cycle", "noise"]),
        f"lag-1..8 autocorrelation spectra over {prov}", blockers)


def _lane_accounting() -> CapabilityLane:
    from aureon.accounting.client_ledger import ClientLedger, Posting

    led = ClientLedger("swarm-bench-books")  # labeled benchmark books
    for i in range(48):
        amount = 10_000 + 137 * i            # varied, deterministic, labeled
        led.post(f"bench row {i}",
                 [Posting("1000", debit_pennies=amount),
                  Posting("4000", credit_pennies=amount)], when=float(i))
    led.trial_balance()
    contexts = []
    for step in led.coordination:
        base = _seed_vector(f"coord:{step.detail[:40]}", _DIM)
        contexts.append([b * (1.0 if step.ok else -1.0) for b in base])
    return CapabilityLane(
        "accounting", contexts, _action_vectors(["post", "queue", "refuse"]),
        f"King's Court coordination record — {len(contexts)} measured steps "
        f"from labeled benchmark books", [])


def _lane_fintech() -> CapabilityLane:
    from aureon.accounting.client_ledger import ClientLedger, Posting
    from aureon.accounting.filings import vat_nine_box
    from aureon.accounting.hmrc_mtd import build_vat_return

    contexts = []
    for q in range(24):                       # 24 labeled quarters, varied books
        led = ClientLedger("swarm-fintech-books")
        sale = 100_000 + 7_919 * q
        led.post("invoice", [Posting("1100", debit_pennies=int(sale * 1.2)),
                             Posting("4000", credit_pennies=sale),
                             Posting("2110", credit_pennies=int(sale * 0.2))],
                 when=float(q))
        pressed = build_vat_return(vat_nine_box(led), f"26A{q % 4 + 1}")
        p = pressed["payload"]
        contexts.append([
            float(p["vatDueSales"]) / 100_000.0,
            float(p["netVatDue"]) / 100_000.0,
            float(p["totalValueSalesExVAT"]) / 10_000.0,
            float(len(pressed["violations"])),
            float(len(pressed["rounding_notes"])),
            1.0, 0.0, float(q % 4) / 4.0,
        ])
    return CapabilityLane(
        "fintech", contexts, _action_vectors(["draft_filing", "hold", "escalate"]),
        "HMRC MTD v1.0 pressings of 24 labeled quarters — schema-validated "
        "payload fields as context", [])


def _lane_coding() -> CapabilityLane:
    try:
        from aureon.cognition.logic_train_audit import compute_logic_train

        report = compute_logic_train()
    except Exception as exc:  # noqa: BLE001 — a dark audit is a named blocker
        return CapabilityLane("coding", [], _action_vectors(["merge", "hold"]),
                              "logic-train audit unavailable",
                              [f"logic-train audit failed: {exc}"])
    sites = [s for s in getattr(report, "sites", [])
             if s.get("role") in ("consumer", "producer", "authority")]
    if not sites:
        return CapabilityLane("coding", [], _action_vectors(["merge", "hold"]),
                              "logic-train audit returned no active sites",
                              ["no active HNC sites measured — lane refuses"])
    sites = sorted(sites, key=lambda s: s["module"])
    contexts = []
    for s in sites:
        base = _seed_vector(f"site:{s['module']}:{s['role']}", _DIM)
        contexts.append([b * (1.0 if s.get("wired") else -1.0) for b in base])
    return CapabilityLane(
        "coding", contexts, _action_vectors(["merge", "refactor", "hold"]),
        f"the repo's own logic-train audit — {len(sites)} active HNC sites "
        f"(consumers/producers/authorities), each hashed into the context stream",
        [])


LANES: dict[str, Any] = {
    "trading": _lane_trading,
    "pattern_recognition": _lane_pattern_recognition,
    "accounting": _lane_accounting,
    "fintech": _lane_fintech,
    "coding": _lane_coding,
}


def build_lane(name: str) -> CapabilityLane:
    if name not in LANES:
        raise ValueError(f"no capability lane named '{name}' — lanes join the "
                         f"grid by name: {sorted(LANES)}")
    return LANES[name]()


def run_lane(lane: CapabilityLane, max_steps: int = 200) -> dict[str, Any]:
    """March one capability through the hive; measure speed and decisions."""
    if lane.blockers:
        return {"lane": lane.name, "ran": False, "blockers": list(lane.blockers),
                "provenance": lane.provenance}

    def _dept(dept: str, n: int) -> Cluster:
        agents = [SwarmAgent(f"{lane.name}-{dept}-{i}", role=dept,
                             actions=sorted(lane.actions),
                             freq=1.0 + 0.1 * i, phase=0.3 * i)
                  for i in range(n)]
        return Cluster(f"{lane.name}-{dept}", agents, beta=0.9, window=6)

    company = Company([_dept("scout", 3), _dept("judge", 2)],
                      tau=2, gamma_crit=0.5)
    contexts = lane.contexts[:max_steps]
    n_agents = sum(len(c.agents) for c in company.clusters.values())

    started = time.perf_counter()
    for t, ctx in enumerate(contexts):
        company.step(t, ctx, lane.actions)
    elapsed = time.perf_counter() - started

    report = company.report()
    return {
        "lane": lane.name,
        "ran": True,
        "provenance": lane.provenance,
        "steps": len(contexts),
        "agents": n_agents,
        "elapsed_s": round(elapsed, 6),
        "steps_per_s": round(len(contexts) / elapsed, 1) if elapsed else None,
        "agent_updates_per_s": (round(len(contexts) * n_agents / elapsed, 1)
                                if elapsed else None),
        "decisions_total": report["decisions_total"],
        "decisions_actualized": report["decisions_actualized"],
        "ledger": company.ledger,          # for determinism proofs (no timing)
        "blockers": [],
    }


def run_grid(max_steps: int = 200) -> dict[str, Any]:
    """All five capabilities through the one hive — the speed-text of the logic."""
    results = {name: run_lane(build_lane(name), max_steps) for name in sorted(LANES)}
    ran = [r for r in results.values() if r["ran"]]
    return {
        "lanes": {n: {k: v for k, v in r.items() if k != "ledger"}
                  for n, r in results.items()},
        "_ledgers": {n: r.get("ledger") for n, r in results.items()},
        "lanes_ran": len(ran),
        "lanes_total": len(results),
        "total_steps": sum(r["steps"] for r in ran),
        "total_elapsed_s": round(sum(r["elapsed_s"] for r in ran), 6),
        "boundary": ("five capability lanes, each marching REAL organ output "
                     "through the hive; dark sources refuse with named blockers; "
                     "timing measured, never pinned"),
    }
