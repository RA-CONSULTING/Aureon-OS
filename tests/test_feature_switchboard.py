"""
Aureon Operator — feature switchboard tests.

The human control plane that turns system features on/off. Covers the registry
(every flag well-formed; hard-boundary flags default OFF), the encrypted store
(round-trip; corrupt store degrades), apply_to_env (sets/leaves env honestly),
the bootstrap integration (persisted flags reach the env at boot), and the
/api/switchboard surface (grouped list; safe flip; hard-boundary needs the typed
confirm; unknown → 404). Plus the load-bearing safety invariant: flipping a
hard-boundary flag ONLY sets its env var — it removes no gate and runs no
executor. Offline, no network.
"""

from __future__ import annotations

import importlib
import os
import pathlib
import tempfile

import pytest

pytest.importorskip("cryptography", reason="switchboard store requires cryptography (Fernet)")

from aureon.operator import feature_switchboard as fs  # noqa: E402


@pytest.fixture()
def temp_store(monkeypatch):
    """Point the store at a throwaway dir so we never touch ~/.aureon."""
    tmp = pathlib.Path(tempfile.mkdtemp())
    monkeypatch.setattr(fs, "CONFIG_DIR", tmp)
    monkeypatch.setattr(fs, "KEY_PATH", tmp / "feature_flags.key")
    monkeypatch.setattr(fs, "STORE_PATH", tmp / "feature_flags.json.enc")
    return tmp


# ── registry ──────────────────────────────────────────────────────────────────

def test_registry_is_well_formed():
    assert len(fs.FLAGS) >= 14
    ids = [f.id for f in fs.FLAGS]
    assert len(ids) == len(set(ids)), "flag ids must be unique"
    for f in fs.FLAGS:
        assert f.env_var == f.id and f.id.isupper()
        assert f.kind in ("safe", "hard_boundary")
        assert f.effect in ("live", "restart")
        assert f.effect_note and f.description


def test_hard_boundary_flags_default_off():
    hard = [f for f in fs.FLAGS if f.kind == "hard_boundary"]
    assert hard, "there should be hard-boundary flags"
    assert all(f.default is False for f in hard)
    # the canonical dangerous set is represented
    ids = {f.id for f in hard}
    for expected in ("AUREON_LIVE_TRADING", "AUREON_LOCAL_ACTIONS_ARMED",
                     "AUREON_SOUL_ACT", "AUREON_BILLING_CHARGE_ENABLED",
                     "AUREON_SOVEREIGN_MODE"):
        assert expected in ids


# ── store ───────────────────────────────────────────────────────────────────────

def test_store_roundtrip_and_persist(temp_store):
    fs.save_flag("AUREON_CONNECTOME_SWEEP", False)
    assert fs.load()["AUREON_CONNECTOME_SWEEP"]["enabled"] is False
    # a fresh module-level read still sees it (persisted, encrypted)
    assert fs.STORE_PATH.exists()


def test_save_unknown_flag_raises(temp_store):
    with pytest.raises(KeyError):
        fs.save_flag("AUREON_NOT_A_REAL_FLAG", True)


def test_corrupt_store_degrades_to_empty(temp_store):
    fs.STORE_PATH.write_bytes(b"not a valid fernet token")
    assert fs.load() == {}  # never raises


# ── apply_to_env ─────────────────────────────────────────────────────────────────

def test_apply_to_env_sets_and_leaves(temp_store, monkeypatch):
    monkeypatch.delenv("AUREON_LLM_OFFLINE", raising=False)
    monkeypatch.delenv("AUREON_CONNECTOME_WEAVE", raising=False)
    fs.save_flag("AUREON_LLM_OFFLINE", True)      # save_flag already applies
    assert os.environ.get("AUREON_LLM_OFFLINE") == "1"
    # a flag with no stored decision is left untouched
    assert "AUREON_CONNECTOME_WEAVE" not in os.environ
    fs.save_flag("AUREON_LLM_OFFLINE", False)
    assert os.environ.get("AUREON_LLM_OFFLINE") == "0"


def test_flag_view_source_precedence(temp_store, monkeypatch):
    flag = fs.get_flag("AUREON_APPROVAL_EMAIL")
    monkeypatch.delenv("AUREON_APPROVAL_EMAIL", raising=False)
    # unset → default / source default
    v = fs.flag_view(flag)
    assert v["source"] == "default" and v["enabled"] == flag.default
    # env present but no store decision → source env
    monkeypatch.setenv("AUREON_APPROVAL_EMAIL", "1")
    v = fs.flag_view(flag)
    assert v["source"] == "env" and v["enabled"] is True
    # a stored decision wins over env
    fs.save_flag("AUREON_APPROVAL_EMAIL", False)
    v = fs.flag_view(flag)
    assert v["source"] == "store" and v["enabled"] is False


def test_grouped_view_shape(temp_store):
    groups = fs.grouped_view()
    labels = [g["label"] for g in groups]
    assert labels == ["Organism & Connectome", "Cognition Routing", "Notifications", "Hard Boundary"]
    for g in groups:
        assert g["flags"] and all("armed" in f for f in g["flags"])


# ── pending-restart signal (decided_at vs last_awakened_at) ──────────────────────

def test_save_flag_records_decided_at(temp_store):
    entry = fs.save_flag("AUREON_LIVE_TRADING", True)
    assert isinstance(entry["decided_at"], float)
    assert isinstance(fs.load()["AUREON_LIVE_TRADING"]["decided_at"], float)


def test_pending_restart_truth_table(temp_store, monkeypatch):
    flag = fs.get_flag("AUREON_LIVE_TRADING")  # a restart-tier hard-boundary flag
    fs.save_flag("AUREON_LIVE_TRADING", True)
    decided = fs.load()["AUREON_LIVE_TRADING"]["decided_at"]

    # organism never awoke → unknown, honest None (never a fabricated "applied")
    monkeypatch.setattr(fs, "_last_awakened_at", lambda: None)
    assert fs.flag_view(flag)["pending_restart"] is None

    # booted BEFORE the decision → the decision has not been picked up → pending
    monkeypatch.setattr(fs, "_last_awakened_at", lambda: decided - 100)
    assert fs.flag_view(flag)["pending_restart"] is True

    # booted AFTER the decision → already applied → not pending
    monkeypatch.setattr(fs, "_last_awakened_at", lambda: decided + 100)
    assert fs.flag_view(flag)["pending_restart"] is False


def test_pending_restart_live_flag_never_pending(temp_store, monkeypatch):
    fs.save_flag("AUREON_LLM_OFFLINE", True)  # effect == "live"
    monkeypatch.setattr(fs, "_last_awakened_at", lambda: 0.0)  # ancient boot
    assert fs.flag_view(fs.get_flag("AUREON_LLM_OFFLINE"))["pending_restart"] is False


def test_pending_restart_no_decision_is_false(temp_store, monkeypatch):
    # env/default source (no human decision) → nothing the human is waiting on
    monkeypatch.delenv("AUREON_APPROVAL_EMAIL", raising=False)
    assert fs.flag_view(fs.get_flag("AUREON_APPROVAL_EMAIL"))["pending_restart"] is False


def test_pending_restart_legacy_entry_is_none(temp_store, monkeypatch):
    # a stored decision without decided_at (pre-Phase-55) → no_data, never fabricated
    fs._persist({"AUREON_LIVE_TRADING": {"enabled": True}})
    monkeypatch.setattr(fs, "_last_awakened_at", lambda: 1.0)
    assert fs.flag_view(fs.get_flag("AUREON_LIVE_TRADING"))["pending_restart"] is None


def test_last_awakened_at_guarded(monkeypatch):
    # an unreadable genome degrades to None, never raises
    import aureon.core.awakening as aw
    monkeypatch.setattr(aw, "read_genome", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    assert fs._last_awakened_at() is None


def test_switchboard_in_governance_catalog():
    from aureon.saas.consciousness_catalog import build_consciousness_catalog

    surfaces = build_consciousness_catalog()["surfaces"]
    sb = next((s for s in surfaces if s["key"] == "switchboard"), None)
    assert sb is not None
    assert sb["category"] == "governance"
    assert sb["route"] == "/api/switchboard"
    assert sb["safety_posture"] == "records_only_gated"


# ── bootstrap integration ────────────────────────────────────────────────────────

def test_bootstrap_credentials_applies_flags(temp_store, monkeypatch):
    monkeypatch.delenv("AUREON_TRACE_PUMP", raising=False)
    fs.save_flag("AUREON_TRACE_PUMP", False)
    monkeypatch.delenv("AUREON_TRACE_PUMP", raising=False)  # simulate a fresh process env
    from aureon.core import aureon_env
    aureon_env.bootstrap_credentials()
    assert os.environ.get("AUREON_TRACE_PUMP") == "0"


# ── HTTP surface ─────────────────────────────────────────────────────────────────

def _client():
    pytest.importorskip("flask", reason="HTTP surface requires the `.[operator]` extra")
    import aureon.operator.operator_server as srv

    importlib.reload(srv)
    return srv.create_app().test_client()


def test_route_list_grouped(temp_store):
    c = _client()
    r = c.get("/api/switchboard")
    assert r.status_code == 200
    body = r.get_json()
    assert [g["label"] for g in body["groups"]][0] == "Organism & Connectome"


def test_route_safe_flip(temp_store):
    c = _client()
    r = c.post("/api/switchboard/AUREON_LLM_OFFLINE", json={"enabled": True})
    assert r.status_code == 200 and r.get_json()["flag"]["enabled"] is True


def test_route_missing_enabled(temp_store):
    c = _client()
    assert c.post("/api/switchboard/AUREON_LLM_OFFLINE", json={}).status_code == 400


def test_route_hard_boundary_requires_confirm(temp_store, monkeypatch):
    monkeypatch.delenv("AUREON_LIVE_TRADING", raising=False)
    c = _client()
    # arm without the typed confirm → rejected, and nothing is armed
    r = c.post("/api/switchboard/AUREON_LIVE_TRADING", json={"enabled": True})
    assert r.status_code == 400
    assert fs.flag_view(fs.get_flag("AUREON_LIVE_TRADING"))["armed"] is False
    # arm WITH the typed confirm → accepted
    r = c.post("/api/switchboard/AUREON_LIVE_TRADING",
               json={"enabled": True, "confirm": "AUREON_LIVE_TRADING"})
    assert r.status_code == 200 and r.get_json()["flag"]["armed"] is True
    # disabling never needs a confirm
    assert c.post("/api/switchboard/AUREON_LIVE_TRADING", json={"enabled": False}).status_code == 200


def test_route_unknown_flag_404(temp_store):
    c = _client()
    assert c.post("/api/switchboard/NOPE", json={"enabled": True}).status_code == 404


# ── safety invariant ─────────────────────────────────────────────────────────────

def test_flipping_only_sets_env_no_executor(temp_store, monkeypatch):
    """Arming a hard-boundary flag sets ONLY its own env var — no other flag
    changes, and apply_to_env imports nothing from the trading/executor layer."""
    monkeypatch.delenv("AUREON_LOCAL_ACTIONS_ARMED", raising=False)
    before = dict(os.environ)
    fs.save_flag("AUREON_LOCAL_ACTIONS_ARMED", True)
    changed = {k for k in os.environ if os.environ.get(k) != before.get(k)}
    assert changed == {"AUREON_LOCAL_ACTIONS_ARMED"}
    # the module never imports an executor / trading path (checked on import lines only)
    import_lines = [
        ln for ln in pathlib.Path(fs.__file__).read_text(encoding="utf-8").splitlines()
        if ln.lstrip().startswith(("import ", "from "))
    ]
    joined = "\n".join(import_lines)
    for forbidden in ("local_action_bridge", "grounded_action", "aureon.trading",
                      "aureon_unified_live", "aureon.simulation"):
        assert forbidden not in joined, f"switchboard must not import {forbidden}"
