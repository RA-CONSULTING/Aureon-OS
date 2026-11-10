import importlib.util
from pathlib import Path

from aureon.core import organism_circulation as oc

ROOT = Path(__file__).resolve().parents[1]


def _load_kill_chain():
    spec = importlib.util.spec_from_file_location(
        "kc_switch_test", ROOT / "aureon_radar" / "bots" / "orca_unified_kill_chain.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_hunting_organs_default_on(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_ORGANISM_STATE", str(tmp_path))
    state = oc.connector_state()
    for name in ("orca_kill_chain", "ira_sniper", "momentum_hunter"):
        assert state[name] is True


def test_kill_chain_reads_live_switch(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_ORGANISM_STATE", str(tmp_path))
    monkeypatch.setattr(oc, "connector_state_enabled", lambda name: False)  # no bus publish
    kc = _load_kill_chain()
    assert kc._organ_switch_on("orca_kill_chain") is True
    oc.switch_connector("orca_kill_chain", False)
    assert kc._organ_switch_on("orca_kill_chain") is False
    oc.switch_connector("orca_kill_chain", True)
    assert kc._organ_switch_on("orca_kill_chain") is True
