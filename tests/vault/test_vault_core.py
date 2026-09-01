#!/usr/bin/env python3
"""
tests/vault/test_vault_core.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Tests the core vault components in isolation:
  1. VaultContent dataclass + AureonVault ingest + eviction
  2. FibonacciCardShuffler — every card seen exactly once, stride walk
  3. LoveGratitudeClock — interval responds to love × gratitude
  4. CasimirQuantifier — present/past fingerprinting, bounded force
  5. AurisMetacognition — 9-node vote, tally rules
  6. HNCDeployer — gamma spike, auris rally, gratitude recovery
  7. RallyCoordinator — enter/exit burst mode
  8. HarmonicPinger — emits on both channels
"""

import os
import sys

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from aureon.vault import (
    AUREON_VAULT_RELEASE_HOLD,
    AureonVault,
    VaultContent,
    FibonacciCardShuffler,
    LoveGratitudeClock,
    CasimirQuantifier,
    AurisMetacognition,
    HNCDeployer,
    HarmonicPinger,
    RallyCoordinator,
    NODES,
)


PASS = 0
FAIL = 0


def check(condition: bool, msg: str) -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [OK] {msg}")
    else:
        FAIL += 1
        print(f"  [!!] {msg}")


# ─────────────────────────────────────────────────────────────────────────────
# 1. VaultContent + AureonVault
# ─────────────────────────────────────────────────────────────────────────────


def test_vault_ingest_and_eviction():
    print("\n[1] VaultContent + AureonVault ingest + eviction")
    vault = AureonVault(max_size=10)

    # Ingest 15 events → max_size=10 so 5 should be evicted
    for i in range(15):
        vault.ingest(
            topic=f"queen.cortex.state.{i}",
            payload={"i": i, "delta": {"amplitude": 0.1 * i}},
        )

    check(len(vault) == 10, f"max_size enforced (got {len(vault)} expected 10)")
    check(vault._total_ingested == 15, f"total_ingested={vault._total_ingested}")
    check(vault._total_dropped == 5, f"total_dropped={vault._total_dropped}")

    recent = vault.recent(n=3)
    check(len(recent) == 3, "recent(3) returned 3 cards")
    check(
        all(isinstance(c, VaultContent) for c in recent),
        "recent returns VaultContent instances",
    )
    check(recent[-1].source_topic.endswith("14"), "last ingested card is the newest")

    by_cortex = vault.by_category("cortex_band")
    check(len(by_cortex) > 0, "by_category('cortex_band') returns cortex cards")

    fp = vault.fingerprint()
    check(isinstance(fp, str) and len(fp) == 16, f"fingerprint is 16 hex chars ({fp})")


def test_vault_thought_bus_wiring_holds_before_lookup_or_mutation(monkeypatch):
    from aureon.core import aureon_thought_bus as thought_bus_module

    class _BusProbe:
        def __init__(self):
            self.subscriptions = []
            self.publications = []

        def subscribe(self, topic, handler):
            self.subscriptions.append((topic, handler))

        def publish(self, thought):
            self.publications.append(thought)

    bus = _BusProbe()
    lookups = []

    def _get_bus():
        lookups.append(True)
        return bus

    monkeypatch.setattr(thought_bus_module, "get_thought_bus", _get_bus)
    vault = AureonVault()

    with pytest.raises(RuntimeError, match=AUREON_VAULT_RELEASE_HOLD):
        vault.wire_thought_bus()

    assert lookups == []
    assert bus.subscriptions == []
    assert vault._thought_bus is None
    assert vault._subscribed is False

    vault.ingest(topic="persona.collapse", payload={"winner": "engineer"})
    assert bus.publications == []


# ─────────────────────────────────────────────────────────────────────────────
# 2. FibonacciCardShuffler
# ─────────────────────────────────────────────────────────────────────────────


def test_fibonacci_shuffler():
    print("\n[2] FibonacciCardShuffler")
    cards = [
        VaultContent.build(category="skill", source_topic=f"t{i}", payload={"i": i}, love_weight=i / 20)
        for i in range(20)
    ]
    shuffler = FibonacciCardShuffler(rng_seed=1)
    deck = shuffler.shuffle(cards)

    check(len(deck) == 20, f"shuffled deck has all 20 cards (got {len(deck)})")
    # Every card must appear exactly once
    ids = {c.content_id for c in deck}
    check(len(ids) == 20, "every card appears exactly once")
    # Order must be different from input (fibonacci walker displaces things)
    original_ids = [c.content_id for c in cards]
    shuffled_ids = [c.content_id for c in deck]
    check(original_ids != shuffled_ids, "deck is actually shuffled")

    strides = shuffler.stride_sequence(20)
    check(len(strides) == 20, "stride_sequence has correct length")
    check(all(0 <= p < 20 for p in strides), "stride positions are in bounds")


# ─────────────────────────────────────────────────────────────────────────────
# 3. LoveGratitudeClock
# ─────────────────────────────────────────────────────────────────────────────


def test_love_gratitude_clock():
    print("\n[3] LoveGratitudeClock")
    vault = AureonVault()
    clock = LoveGratitudeClock(base_interval_s=1.0)

    # High love + high gratitude → fast (interval ≈ base / 0.81 ≈ 1.23)
    vault.love_amplitude = 0.9
    vault.gratitude_score = 0.9
    fast = clock.current_interval_s(vault)

    # Low love + low gratitude → slow
    vault.love_amplitude = 0.1
    vault.gratitude_score = 0.1
    slow = clock.current_interval_s(vault)

    check(slow > fast, f"slow ({slow:.3f}) > fast ({fast:.3f})")

    # Rally mode → 10× faster than not-rally for same love/gratitude
    vault.love_amplitude = 0.9
    vault.gratitude_score = 0.9
    vault.rally_active = False
    normal = clock.current_interval_s(vault)
    vault.rally_active = True
    rally = clock.current_interval_s(vault)
    check(rally < normal, f"rally ({rally:.3f}) < normal ({normal:.3f})")

    # Status reports last reading
    status = clock.get_status()
    check("effective_interval_s" in status, "clock status exposes effective interval")


# ─────────────────────────────────────────────────────────────────────────────
# 4. CasimirQuantifier
# ─────────────────────────────────────────────────────────────────────────────


def test_casimir_quantifier():
    print("\n[4] CasimirQuantifier remains on production HOLD")
    vault = AureonVault()
    # Seed the vault with some cards so we have a history
    for i in range(10):
        vault.ingest(topic=f"seed.{i}", payload={"i": i})

    quantifier = CasimirQuantifier(tau_s=30.0)
    before = vault.last_casimir_force
    with pytest.raises(RuntimeError, match="casimir_quantifier_hold"):
        quantifier.measure(vault)
    with pytest.raises(RuntimeError, match="casimir_quantifier_hold"):
        quantifier._load_engine()
    assert vault.last_casimir_force == before
    assert quantifier.last_reading is None


# ─────────────────────────────────────────────────────────────────────────────
# 5. AurisMetacognition
# ─────────────────────────────────────────────────────────────────────────────


def test_auris_metacognition():
    print("\n[5] AurisMetacognition")
    auris = AurisMetacognition()

    check(len(NODES) == 9, "9 Auris nodes")

    vault = AureonVault()
    vault.love_amplitude = 0.8
    vault.gratitude_score = 0.7
    vault.last_lambda_t = 0.6
    vault.cortex_snapshot["alpha"] = 0.5
    vault.last_casimir_force = 1.0
    vault.dominant_chakra = "love"
    vault.dominant_frequency_hz = 528.0

    result = auris.vote(vault)

    check(len(result.per_node_votes) == 9, "9 node votes recorded")
    check(result.agreeing <= 9, "agreeing count ≤ 9")
    check(result.confidence in (0.3, 0.7, 0.95), f"confidence is one of 0.3/0.7/0.95 (got {result.confidence})")
    check(
        result.consensus in ("BUY", "SELL", "NEUTRAL", "RALLY", "STABILISE"),
        f"consensus is valid (got {result.consensus})",
    )

    # Force a high drift → Tiger should vote RALLY
    vault.last_casimir_force = 8.0
    result2 = auris.vote(vault)
    tiger_vote = next(v for v in result2.per_node_votes if v.node == "Tiger")
    check(tiger_vote.verdict == "RALLY", f"Tiger votes RALLY under high drift (got {tiger_vote.verdict})")


# ─────────────────────────────────────────────────────────────────────────────
# 6. HNCDeployer
# ─────────────────────────────────────────────────────────────────────────────


def test_hnc_deployer():
    print("\n[6] HNCDeployer")
    deployer = HNCDeployer(max_cells_per_tick=5)
    vault = AureonVault()

    # Calm state → 0 cells
    vault.cortex_snapshot["gamma"] = 0.1
    vault.last_lambda_t = 0.1
    vault.gratitude_score = 0.8
    d0 = deployer.should_deploy(vault, auris_result=None)
    check(d0.count == 0, f"calm → 0 cells (got {d0.count})")

    # Gamma spike → deploy cells
    vault.cortex_snapshot["gamma"] = 0.5
    vault.last_lambda_t = 0.3
    d1 = deployer.should_deploy(vault, auris_result=None)
    check(d1.count >= 1, f"gamma spike → deploy (got {d1.count})")
    check(d1.count <= 5, "capped by max_cells_per_tick")

    # Gratitude recovery
    vault.cortex_snapshot["gamma"] = 0.1
    vault.gratitude_score = 0.2
    d2 = deployer.should_deploy(vault, auris_result=None)
    check(d2.count >= 1, f"low gratitude → recovery (got {d2.count})")


# ─────────────────────────────────────────────────────────────────────────────
# 7. RallyCoordinator
# ─────────────────────────────────────────────────────────────────────────────


def test_rally_coordinator():
    print("\n[7] RallyCoordinator")
    rally = RallyCoordinator(burst_ticks=3, casimir_threshold=2.0)
    vault = AureonVault()

    class FakeVote:
        def __init__(self, consensus):
            self.consensus = consensus

    # Trigger via high Casimir force
    vault.last_casimir_force = 3.0
    rally.update(vault, FakeVote("NEUTRAL"))
    check(rally.active, "rally entered on high Casimir force")
    check(vault.rally_active, "vault.rally_active propagated")

    # Burst expires after burst_ticks cycles of low-pressure updates
    vault.last_casimir_force = 0.1
    for _ in range(4):
        rally.update(vault, FakeVote("NEUTRAL"))
    check(not rally.active, "rally exited after burst_ticks elapsed")

    # Trigger via Auris RALLY consensus
    rally.update(vault, FakeVote("RALLY"))
    check(rally.active, "rally entered on Auris RALLY consensus")


# ─────────────────────────────────────────────────────────────────────────────
# 8. HarmonicPinger
# ─────────────────────────────────────────────────────────────────────────────


def test_harmonic_pinger():
    print("\n[8] HarmonicPinger remains on production HOLD")
    pinger = HarmonicPinger()
    with pytest.raises(RuntimeError, match="harmonic_pinger_hold"):
        pinger.ping(frequency_hz=528, coherence=0.85, payload={"cycle": 1})
    with pytest.raises(RuntimeError, match="harmonic_pinger_hold"):
        pinger._load_chirp_bus()
    with pytest.raises(RuntimeError, match="harmonic_pinger_hold"):
        pinger._load_thought_bus()
    assert pinger.get_status()["total_pings"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────


def main():
    print("=" * 80)
    print("  VAULT CORE TEST SUITE")
    print("=" * 80)

    test_vault_ingest_and_eviction()
    test_fibonacci_shuffler()
    test_love_gratitude_clock()
    test_casimir_quantifier()
    test_auris_metacognition()
    test_hnc_deployer()
    test_rally_coordinator()
    test_harmonic_pinger()

    print()
    print("=" * 80)
    print(f"  RESULT: {PASS} passed, {FAIL} failed")
    print("=" * 80)
    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
