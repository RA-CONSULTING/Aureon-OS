from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = REPO_ROOT / "integrations" / "aureon_murge" / "web_app"


def test_flameborn_referenced_assets_exist() -> None:
    index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")

    assert 'src="script.js"' in index
    assert 'src="assets/flameborn-logo-current.svg"' in index
    assert (WEB_ROOT / "script.js").is_file()
    assert (WEB_ROOT / "assets" / "flameborn-logo-current.svg").is_file()
    assert (WEB_ROOT / "scripts" / "aureon_cli.mjs").is_file()


def test_flameborn_server_exposes_supervisor_bridge() -> None:
    server = (WEB_ROOT / "server.mjs").read_text(encoding="utf-8")

    assert "DEFAULT_AUREON_TERMINAL_STATE_URL" in server
    assert "DEFAULT_AUREON_PHI_BASE_URL" in server
    assert "buildSupervisorSnapshot" in server
    assert 'req.url === "/api/aureon/supervisor"' in server
    assert 'req.url === "/api/aureon/full-capability-stress"' in server
    assert 'req.url === "/api/aureon/chat"' in server
    assert "noTradingGateBypass" in server


def test_flameborn_ui_renders_full_launch_proof_panel() -> None:
    index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    script = (WEB_ROOT / "script.js").read_text(encoding="utf-8")

    assert "Full Launch Proof" in index
    assert 'id="fullCapabilityStressCard"' in index
    assert "renderFullCapabilityStress" in script
    assert "/api/aureon/full-capability-stress" in script
