"""The restored Sero module is the real one, and the launcher seat runs it."""

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_real_module_replaces_placeholder(tmp_path, monkeypatch):
    monkeypatch.setenv("SERO_WORKSPACE", str(tmp_path))
    sys.modules.pop("aureon_fusion.paths", None)
    spec = importlib.util.spec_from_file_location("sero_ae_under_test", REPO / "sero_autonomous_expansion.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "SeroAutonomousExpansion")
    assert (tmp_path / "sero_autonomous_state").is_dir()
    text = (REPO / "sero_autonomous_expansion.py").read_text(encoding="utf-8")
    assert "checkout_daemons" not in text
    assert "Math.random" not in text
    sys.modules.pop("aureon_fusion.paths", None)


def test_launcher_seat_delegates_to_real_module():
    text = (REPO / "aureon" / "launch" / "daemons" / "sero_autonomous_expansion.py").read_text(encoding="utf-8")
    assert '"sero_autonomous_expansion.py"' in text and "_load_real().main()" in text
    assert "--continuous" in text
    assert "checkout_daemons" not in text
