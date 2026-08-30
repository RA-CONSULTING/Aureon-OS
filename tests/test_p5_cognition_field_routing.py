"""P5: cognition / metacognition / Auris run on REAL canonical HNC data.

Each test drives a real consumer with the canonical field injected at its real
resolution seam (``aureon.core.hnc_field.read_canonical_field``) and proves the
field GOVERNS the output — tighten-only where the wire is a reconcile (b46),
blend where it is a Pattern-B merge, honest dark-field passthrough everywhere.
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

_FIELD = "aureon.core.hnc_field.read_canonical_field"


def _field(gamma: float | None = None, sls: float | None = None,
           psi: float | None = None, lam: float | None = None):
    from aureon.core.hnc_field import CanonicalField

    return CanonicalField(
        available=True,
        symbolic_life_score=sls if sls is not None else gamma,
        coherence_gamma=gamma,
        consciousness_psi=psi,
        consciousness_level="RECURSIVE",
        lambda_t=lam if lam is not None else 0.7,
        source="p5_test_probe",
    )


def _dark():
    from aureon.core.hnc_field import CanonicalField

    return CanonicalField()


# ── the shared Pattern-A helper ─────────────────────────────────────────────


def test_canonical_field_reading_live_and_dark():
    from aureon.core.hnc_field import canonical_field_reading

    with patch(_FIELD, lambda *a, **k: _field(gamma=0.62, sls=0.62)):
        r = canonical_field_reading()
        assert r is not None
        assert r.name == "hnc_canonical_field"
        assert r.value == pytest.approx(0.62)
    with patch(_FIELD, lambda *a, **k: _dark()):
        assert canonical_field_reading() is None, (
            "a dark field must contribute NOTHING — never a placeholder"
        )


def test_canonical_field_reading_moves_local_gamma(tmp_path):
    """The Pattern-A merge is load-bearing: a low shared field among healthy
    local readings strictly lowers the local engine's Γ."""
    from aureon.core.aureon_lambda_engine import LambdaEngine, SubsystemReading
    from aureon.core.hnc_field import canonical_field_reading

    base = [SubsystemReading(f"s{i}", 0.9, 0.9, "ok") for i in range(4)]

    eng_a = LambdaEngine()
    eng_a._state_path = tmp_path / "a.json"
    gamma_without = eng_a.step(list(base)).coherence_gamma

    with patch(_FIELD, lambda *a, **k: _field(gamma=0.1, sls=0.1)):
        merged = list(base) + [canonical_field_reading()]
    eng_b = LambdaEngine()
    eng_b._state_path = tmp_path / "b.json"
    gamma_with = eng_b.step(merged).coherence_gamma

    assert gamma_with < gamma_without


# ── miner cognition runtime ─────────────────────────────────────────────────


def test_miner_cognition_gamma_reconciled_tighten_only():
    from aureon.autonomous.aureon_cognition_runtime import MinerModule

    miner = object.__new__(MinerModule)
    market = {"momentum": 0.5, "gamma": 0.9}

    with patch(_FIELD, lambda *a, **k: _field(gamma=0.1)):
        assert miner.compute_signal("BTC/USD", market) is None, (
            "a LOW shared Γ must gate the signal the private gamma would pass"
        )
    with patch(_FIELD, lambda *a, **k: _field(gamma=0.95)):
        sig = miner.compute_signal("BTC/USD", market)
        assert sig is not None
        assert sig["coherence_gamma"] == pytest.approx(0.9), "min() never loosens"
    with patch(_FIELD, lambda *a, **k: _dark()):
        sig = miner.compute_signal("BTC/USD", market)
        assert sig is not None and sig["coherence_gamma"] == pytest.approx(0.9)


# ── Auris reconciles ────────────────────────────────────────────────────────


def test_auris_trader_coherence_reconciled():
    from aureon.trading.aureon_auris_trader import AurisEngine, MarketSnapshot

    snap = MarketSnapshot(symbol="BTC/USD", price=100.0, volume=0.8,
                          volatility=0.3, momentum=0.4, spread=0.2,
                          timestamp=time.time())
    engine = AurisEngine()
    with patch(_FIELD, lambda *a, **k: _dark()):
        local = engine.calculate_coherence(snap)
    with patch(_FIELD, lambda *a, **k: _field(gamma=0.05)):
        tightened = engine.calculate_coherence(snap)
    with patch(_FIELD, lambda *a, **k: _field(gamma=0.99)):
        untouched = engine.calculate_coherence(snap)

    assert tightened == pytest.approx(0.05)
    assert untouched == pytest.approx(local), "a high field never loosens"


def test_hive_mind_auris_gamma_reconciled():
    from aureon.utils.aureon_queen_hive_mind import QueenHiveMind

    hive = object.__new__(QueenHiveMind)
    market = {"volatility": 0.2, "momentum": 0.3, "volume": 0.7, "spread": 0.4}

    with patch(_FIELD, lambda *a, **k: _dark()):
        local, _ = hive.get_auris_coherence(market)
    with patch(_FIELD, lambda *a, **k: _field(gamma=0.05)):
        tightened, status = hive.get_auris_coherence(market)
    with patch(_FIELD, lambda *a, **k: _field(gamma=0.99)):
        untouched, _ = hive.get_auris_coherence(market)

    assert tightened == pytest.approx(0.05)
    assert "COHERENCE BREAK" in status
    assert untouched == pytest.approx(local)


def test_enigma_node_sweep_reconciled():
    from aureon.wisdom.aureon_enigma import RotorGamma

    rotor = RotorGamma()
    with patch(_FIELD, lambda *a, **k: _field(gamma=0.2)):
        assert rotor._reconcile(0.9) == pytest.approx(0.2)
    with patch(_FIELD, lambda *a, **k: _field(gamma=0.95)):
        assert rotor._reconcile(0.4) == pytest.approx(0.4)
    with patch(_FIELD, lambda *a, **k: _dark()):
        assert rotor._reconcile(0.9) == pytest.approx(0.9)


# ── Seer oracles ────────────────────────────────────────────────────────────


_TICKER = {"prices": {"BTCUSDT": 100.0, "ETHUSDT": 50.0},
           "changes": {"BTCUSDT": 2.0, "ETHUSDT": 1.0}}


def test_seer_spirits_blends_canonical_gamma():
    from aureon.intelligence.aureon_seer import OracleOfSpirits

    with patch(_FIELD, lambda *a, **k: _dark()):
        base = OracleOfSpirits().read(dict(_TICKER))
    with patch(_FIELD, lambda *a, **k: _field(gamma=0.1)):
        low = OracleOfSpirits().read(dict(_TICKER))

    expected = 0.75 * base.score + 0.25 * 0.1
    assert low.score == pytest.approx(expected, abs=1e-6)
    assert low.details.get("canonical_gamma") == pytest.approx(0.1)


def test_seer_maeshowe_fallback_reads_real_field(monkeypatch):
    from aureon.intelligence.aureon_seer import OracleOfMaeshowe

    oracle = OracleOfMaeshowe()
    monkeypatch.setattr(oracle, "_load", lambda: None)  # decoder honestly absent

    with patch(_FIELD, lambda *a, **k: _field(gamma=0.42)):
        r = oracle.read()
    assert r.score == pytest.approx(0.42)
    assert r.details.get("source") == "canonical_field"
    assert r.phase == "ACTIVE_FIELD"

    with patch(_FIELD, lambda *a, **k: _dark()):
        r2 = oracle.read()
    assert r2.score == pytest.approx(0.5)
    assert r2.confidence == pytest.approx(0.2), (
        "module AND field dark → the labeled low-confidence neutral, not a fake Γ"
    )


# ── cognition pipeline ──────────────────────────────────────────────────────


def test_pipeline_lambda_values_are_real_field_reads():
    from aureon.cognition.pipeline import CognitionPipeline

    with patch(_FIELD, lambda *a, **k: _field(gamma=0.8, psi=0.44, lam=0.66)):
        env = CognitionPipeline().run("analyse the harmonic field")

    assert env.complexity is not None
    assert env.complexity.components["lambda_psi"] == pytest.approx(0.44)
    assert env.branches[0].lambda_snapshot == pytest.approx(0.66)
    assert env.collapsed is not None
    assert env.collapsed.lambda_at_collapse == pytest.approx(0.66)
    from aureon.queen.queen_conscience import ConscienceVerdict

    real_verdicts = {v.name for v in ConscienceVerdict} | {"UNREVIEWED"}
    assert env.collapsed.conscience_verdict in real_verdicts, (
        "the verdict must come from the real conscience (or honest UNREVIEWED), "
        "never a hardcoded APPROVED"
    )


def test_pipeline_dark_field_is_honest_zero():
    from aureon.cognition.pipeline import CognitionPipeline

    with patch(_FIELD, lambda *a, **k: _dark()):
        env = CognitionPipeline().run("hello")

    assert env.complexity.components["lambda_psi"] == pytest.approx(0.0)
    assert env.branches[0].lambda_snapshot == pytest.approx(0.0)
