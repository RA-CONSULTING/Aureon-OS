"""
The QGITA trader must not size real orders from simulated models or a coin flip.

Two defects in ``aureon/wisdom/aureon_qgita.py``, both on the live path:

  * ``DecisionFusion.generate_model_signal`` was labelled "Simulate ensemble model signals"
    and did exactly that — four named models (lstm, randomForest, xgboost, transformer),
    each given ``normalized_trend + bias + (random()-0.5)*0.1`` as a score and a random
    confidence. That stand-in carried 60% of the fused decision weight, and the fused
    decision reached ``RiskManager.evaluate`` and then real Binance orders.
  * ``RiskManager.evaluate`` computed ``win_rate = 0.55*confidence + 0.45*random()`` and fed
    it to the Kelly criterion, so the same signal sized differently every time it appeared,
    for a reason nobody could name or reproduce.

Now: the simulated ensemble is opt-in and paper-only; with no ensemble the fusion runs on
the QGITA lighthouse alone and reports ``blocker`` when there is nothing to decide on; and
Kelly uses this session's measured win rate once enough trades have closed, and a
deterministic function of confidence before that.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
os.environ.setdefault("PYTHON_DOTENV_DISABLED", "1")

pytest.importorskip("aureon.exchanges.binance_client",
                    reason="the QGITA trader imports the Binance client at module scope")

import aureon.wisdom.aureon_qgita as qgita  # noqa: E402

_SNAP = {"momentum": 0.03, "volatility": 0.01, "price": 100.0}


# ── the ensemble ────────────────────────────────────────────────────────────────

def test_simulated_models_are_off_by_default():
    fusion = qgita.DecisionFusion()
    assert fusion.allow_simulated_models is False
    assert fusion.generate_model_signal(_SNAP) == []


def test_no_ensemble_and_no_lighthouse_is_a_named_hold_not_a_guess():
    """The original defect: with nothing real connected the fusion still emitted buy/sell."""
    decision = qgita.DecisionFusion().decide(_SNAP, None)
    assert decision["action"] == "hold"
    assert decision["confidence"] == 0.0
    assert decision["ensemble"] == "absent"
    assert decision["blocker"] == "no_model_ensemble_connected"


def test_a_real_lighthouse_event_still_decides_without_the_ensemble():
    """Dropping the stand-in must not mute the one real signal the engine does compute."""
    decision = qgita.DecisionFusion().decide(
        _SNAP, {"direction": "long", "confidence": 0.8})
    assert decision["action"] == "buy"
    assert decision["score"] == pytest.approx(0.8)
    assert decision["ensemble"] == "absent"
    assert "blocker" not in decision


def test_a_short_lighthouse_event_decides_the_other_way():
    decision = qgita.DecisionFusion().decide(
        _SNAP, {"direction": "short", "confidence": 0.9})
    assert decision["action"] == "sell"
    assert decision["score"] == pytest.approx(-0.9)


def test_the_simulated_ensemble_still_works_when_asked_for_and_says_so():
    fusion = qgita.DecisionFusion(allow_simulated_models=True)
    signals = fusion.generate_model_signal(_SNAP)
    assert {s["model"] for s in signals} == {"lstm", "randomForest", "xgboost", "transformer"}
    assert all(s["truth_status"] == "simulated" for s in signals)
    assert all(s["generated_values"] is True for s in signals)
    assert all(s["action_eligible"] is False for s in signals)
    assert signals == fusion.generate_model_signal(_SNAP)
    assert fusion.decide(_SNAP, None)["ensemble"] == "simulated"


def test_provider_ensemble_is_never_mislabelled_as_simulated():
    provider_signal = {
        "model": "provider-model",
        "score": 0.4,
        "confidence": 0.8,
        "source_id": "provider:model",
        "source_event_id": "provider:event:1",
        "source_timestamp": 1_800_000_000.0,
        "truth_status": "provider_observed",
        "generated_values": False,
    }
    snapshot = {**_SNAP, "model_signals": [provider_signal]}

    decision = qgita.DecisionFusion().decide(snapshot, None)

    assert decision["ensemble"] == "provider_observed"


# ── Kelly sizing ────────────────────────────────────────────────────────────────

def test_position_size_is_reproducible_for_the_same_signal():
    """45% of the Kelly input used to be random(), so identical signals sized differently."""
    manager = qgita.RiskManager(initial_equity=1000)
    decision = {"action": "buy", "confidence": 0.9}
    first = manager.evaluate(decision, _SNAP, 1000.0)
    second = manager.evaluate(decision, _SNAP, 1000.0)
    assert first == second
    assert first is not None and first["notional"] > 0


def test_a_hold_still_sizes_nothing():
    manager = qgita.RiskManager(initial_equity=1000)
    assert manager.evaluate({"action": "hold", "confidence": 0.9}, _SNAP, 1000.0) is None


def test_win_rate_is_withheld_until_it_has_been_measured():
    """A win rate off 3 trades is noise; Kelly gets None and falls back deterministically."""
    manager = qgita.RiskManager()
    assert manager.measured_win_rate() is None
    for _ in range(19):
        manager.record_outcome(1.0)
    assert manager.measured_win_rate() is None, "19 trades is still not a measurement"
    manager.record_outcome(1.0)
    assert manager.measured_win_rate() == pytest.approx(1.0)


def test_the_measured_win_rate_reflects_the_actual_outcomes():
    manager = qgita.RiskManager()
    for i in range(40):
        manager.record_outcome(1.0 if i % 4 == 0 else -1.0)
    assert manager.measured_win_rate() == pytest.approx(0.25)
    assert manager.wins == 10 and manager.losses == 30


def test_a_losing_session_sizes_smaller_than_a_winning_one():
    """The point of measuring: the sizing has to actually respond to being wrong."""
    winner = qgita.RiskManager(initial_equity=1000)
    loser = qgita.RiskManager(initial_equity=1000)
    for i in range(40):
        winner.record_outcome(1.0 if i % 5 else -1.0)     # 80% wins
        loser.record_outcome(1.0 if i % 5 == 0 else -1.0)  # 20% wins

    decision = {"action": "buy", "confidence": 0.9}
    won = winner.evaluate(decision, _SNAP, 1000.0)
    lost = loser.evaluate(decision, _SNAP, 1000.0)
    assert won is not None
    assert lost is None or lost["notional"] < won["notional"]


# ── the live path ───────────────────────────────────────────────────────────────

def test_live_mode_refuses_the_simulated_ensemble(monkeypatch):
    """Real money is never sized from a stand-in, whatever the flags say."""
    monkeypatch.setattr(qgita, "get_binance_client", lambda: object())
    monkeypatch.setattr(qgita.LotSizeManager, "__init__", lambda self, client: None)

    live = qgita.AureonQGITATrader(dry_run=False, allow_simulated_models=True)
    assert live.allow_simulated_models is False
    assert live.decision_fusion.allow_simulated_models is False
    assert live.decision_fusion.generate_model_signal(_SNAP) == []

    paper = qgita.AureonQGITATrader(dry_run=True, allow_simulated_models=True)
    assert paper.decision_fusion.allow_simulated_models is True
