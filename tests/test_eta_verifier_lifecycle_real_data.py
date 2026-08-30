from __future__ import annotations

import time

import aureon.analytics.eta_verification_system as eta_module
from aureon.analytics.eta_verification_system import ETAVerificationEngine


def test_global_accessor_is_background_inert(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(eta_module, "ETA_VERIFIER", None)

    engine = eta_module.get_eta_verifier()

    assert engine._omni_running is False
    assert engine._omni_thread is None


def test_explicit_eta_lifecycle_is_idempotent_and_stoppable(tmp_path):
    engine = ETAVerificationEngine(str(tmp_path / "eta-history.json"))
    engine._OMNI_INITIAL_DELAY = 0.01
    engine._OMNI_INTERVAL = 0.01

    engine.start_omnipresent()
    first_thread = engine._omni_thread
    engine.start_omnipresent()

    assert first_thread is not None
    assert engine._omni_thread is first_thread
    assert first_thread.is_alive()

    engine.stop_omnipresent()
    assert engine._omni_running is False
    assert engine._omni_thread is None
    assert first_thread.is_alive() is False


def test_housekeeping_never_estimates_pnl_from_price_or_velocity(monkeypatch, tmp_path):
    engine = ETAVerificationEngine(str(tmp_path / "eta-history.json"))
    engine.active_predictions["kraken:BTC/USD"] = object()
    expiry_calls = []

    monkeypatch.setattr(
        engine,
        "check_expired_predictions",
        lambda: expiry_calls.append(time.time()) or [],
    )

    def reject_generated_state(*_args, **_kwargs):
        raise AssertionError("housekeeping must not generate a P&L observation")

    monkeypatch.setattr(engine, "update_prediction_state", reject_generated_state)
    engine._sweep_with_open_source_prices()

    assert len(expiry_calls) == 1
