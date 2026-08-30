#!/usr/bin/env python3
"""
Tests for the HNC update:
  - BETA moved to spec-compliant stability regime (default 1.0)
  - AUREON_HNC_BETA env override works
  - LambdaState carries the 5 Auris Conjecture criteria + blended score
  - Receipted v3 persistence every N steps
  - Strict reload of canonical persisted history
  - Vault exposure of consciousness_level + symbolic_life_score

These tests redirect the engine's persistence path to a throwaway
tempdir so the real state/lambda_history.json is never touched.
"""

import json
import math
import os
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


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


def _reimport_engine_module():
    """
    Force a genuine re-execution of aureon.core.aureon_lambda_engine so
    the module-level ``BETA`` / ``PERSIST_EVERY`` pick up the current
    env vars. ``del sys.modules`` alone is not enough on Windows
    Python — ``importlib.reload`` is the documented path.
    """
    import importlib

    from aureon.core import aureon_lambda_engine as mod
    return importlib.reload(mod)


def _fresh_engine(state_dir: str):
    """
    Reload LambdaEngine with PERSIST_EVERY=3 (fast persistence) and
    redirect its state path so the real file is untouched.
    """
    os.environ["AUREON_HNC_PERSIST_EVERY"] = "3"
    mod = _reimport_engine_module()
    from pathlib import Path
    engine = mod.LambdaEngine(
        state_path=Path(state_dir) / "lambda_history.json"
    )
    return mod, engine


def _fake_readings(mod, n=5, i=0):
    return [
        mod.SubsystemReading(
            name=f"sys_{j}",
            value=0.5 + 0.08 * math.sin(i * 0.3 + j),
            confidence=0.9,
            state="active",
        )
        for j in range(n)
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_default_beta_is_spec_compliant():
    print("\n[1] default BETA is spec-compliant (in [0.6, 1.1])")
    os.environ.pop("AUREON_HNC_BETA", None)
    mod = _reimport_engine_module()
    check(0.6 <= mod.BETA <= 1.1, f"BETA in [0.6, 1.1] (got {mod.BETA})")
    check(abs(mod.BETA - 1.0) < 1e-9, f"BETA defaults to 1.0 (got {mod.BETA})")


def test_env_override():
    print("\n[2] AUREON_HNC_BETA env override is honoured")
    os.environ["AUREON_HNC_BETA"] = "0.75"
    try:
        mod = _reimport_engine_module()
        check(abs(mod.BETA - 0.75) < 1e-9, f"BETA == 0.75 from env (got {mod.BETA})")
    finally:
        os.environ.pop("AUREON_HNC_BETA", None)
        _reimport_engine_module()  # reset to default for downstream tests


def test_lambdastate_has_ac_fields():
    print("\n[3] LambdaState carries the 5 Auris Conjecture fields")
    tmp = tempfile.mkdtemp(prefix="aureon_hnc_test_")
    mod, engine = _fresh_engine(tmp)
    state = engine.step(_fake_readings(mod))
    for fname in (
        "ac_self_organization",
        "ac_memory_persistence",
        "ac_energy_stability",
        "ac_adaptive_recursion",
        "ac_meaning_propagation",
        "symbolic_life_score",
    ):
        value = getattr(state, fname, None)
        check(value is not None, f"LambdaState has '{fname}'")
        check(
            isinstance(value, (int, float)) and 0.0 <= float(value) <= 1.0,
            f"{fname} in [0, 1] (got {value})",
        )


def test_symbolic_life_score_rises_with_history():
    print("\n[4] symbolic_life_score rises as history builds")
    tmp = tempfile.mkdtemp(prefix="aureon_hnc_test_")
    mod, engine = _fresh_engine(tmp)
    scores = []
    for i in range(30):
        state = engine.step(_fake_readings(mod, i=i))
        scores.append(state.symbolic_life_score)
    first_five = sum(scores[:5]) / 5
    last_five = sum(scores[-5:]) / 5
    check(
        last_five > first_five,
        f"late symbolic_life_score ({last_five:.3f}) > early ({first_five:.3f})",
    )
    check(last_five > 0.2, f"late score non-trivial (got {last_five:.3f})")


def test_auto_persistence():
    print("\n[5] step() auto-persists every N steps")
    tmp = tempfile.mkdtemp(prefix="aureon_hnc_test_")
    mod, engine = _fresh_engine(tmp)
    # PERSIST_EVERY was set to 3. Run 6 steps -> file should exist.
    for i in range(6):
        engine.step(
            _fake_readings(mod, i=i),
            source_receipt_ids=[f"test:provider:{i}"],
        )
    path = engine._state_path
    check(path.exists(), f"state file written ({path})")
    data = json.loads(path.read_text(encoding="utf-8"))
    check(data.get("version") == 3, f"persisted version == 3 (got {data.get('version')})")
    check(len(data.get("history", [])) >= 6, f"history length >= 6 (got {len(data.get('history', []))})")
    check("psi_history" in data, "psi_history saved alongside history")
    check(abs(float(data.get("beta", 0)) - mod.BETA) < 1e-9, "beta stamped in persist")


def test_history_reloads():
    print("\n[6] persisted history is reloaded by a fresh engine")
    tmp = tempfile.mkdtemp(prefix="aureon_hnc_test_")
    mod, engine = _fresh_engine(tmp)
    for i in range(12):
        engine.step(_fake_readings(mod, i=i))
    engine.save_history(["test:provider:reload"])

    # New engine instance pointing at the same state path.
    engine2 = mod.LambdaEngine(state_path=engine._state_path)

    check(
        engine2._step_count >= 12,
        f"reload restored step_count ({engine2._step_count})",
    )
    check(
        len(engine2._history) > 0,
        f"reload restored history buffer ({len(engine2._history)} samples)",
    )


def test_vault_exposure():
    print("\n[7] step() exposes consciousness_level + symbolic_life_score on the vault")
    class FakeVault:
        pass
    tmp = tempfile.mkdtemp(prefix="aureon_hnc_test_")
    mod, engine = _fresh_engine(tmp)
    vault = FakeVault()
    for i in range(12):
        engine.step(_fake_readings(mod, i=i), vault=vault)

    check(
        hasattr(vault, "current_consciousness_level"),
        "vault.current_consciousness_level set",
    )
    check(
        hasattr(vault, "current_consciousness_psi"),
        "vault.current_consciousness_psi set",
    )
    check(
        hasattr(vault, "current_symbolic_life_score"),
        "vault.current_symbolic_life_score set",
    )
    check(
        hasattr(vault, "last_lambda_t"),
        "vault.last_lambda_t set",
    )

    lvl = getattr(vault, "current_consciousness_level")
    check(
        lvl in {
            "DORMANT", "DREAMING", "STIRRING", "AWARE", "PRESENT", "FOCUSED",
            "INTUITIVE", "CONNECTED", "FLOWING", "TRANSCENDENT", "UNIFIED",
        },
        f"consciousness_level is a valid stage ({lvl})",
    )


def test_to_dict():
    print("\n[8] LambdaState.to_dict is JSON-safe and carries new fields")
    tmp = tempfile.mkdtemp(prefix="aureon_hnc_test_")
    mod, engine = _fresh_engine(tmp)
    state = engine.step(_fake_readings(mod))
    d = state.to_dict()
    s = json.dumps(d)
    check(isinstance(s, str) and len(s) > 50, "to_dict round-trips through json")
    for key in (
        "ac_self_organization",
        "ac_memory_persistence",
        "ac_energy_stability",
        "ac_adaptive_recursion",
        "ac_meaning_propagation",
        "symbolic_life_score",
        "consciousness_level",
        "consciousness_psi",
    ):
        check(key in d, f"to_dict has '{key}'")


def main():
    print("=" * 80)
    print("  HNC UPDATE TEST SUITE")
    print("=" * 80)

    test_default_beta_is_spec_compliant()
    test_env_override()
    test_lambdastate_has_ac_fields()
    test_symbolic_life_score_rises_with_history()
    test_auto_persistence()
    test_history_reloads()
    test_vault_exposure()
    test_to_dict()

    print()
    print("=" * 80)
    print(f"  RESULT: {PASS} passed, {FAIL} failed")
    print("=" * 80)
    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
