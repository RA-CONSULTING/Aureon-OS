"""Side-effect-free contract for Queen-directed scalper target selection."""

from aureon.trading.scalper_policy import resolve_scalper_targets


def test_scalper_mode_activation():
    tp, sl, active = resolve_scalper_targets(0.85, {})

    assert active is True
    assert tp == 0.005
    assert sl == 0.002


def test_scalper_mode_preserves_learned_targets_below_threshold():
    learned = {
        "suggested_take_profit": 0.02,
        "suggested_stop_loss": 0.01,
    }

    assert resolve_scalper_targets(0.8, learned) == (0.02, 0.01, False)


def test_scalper_mode_rejects_nonfinite_or_boolean_signal():
    assert resolve_scalper_targets(float("nan"), {}) == (None, None, False)
    assert resolve_scalper_targets(True, {}) == (None, None, False)
