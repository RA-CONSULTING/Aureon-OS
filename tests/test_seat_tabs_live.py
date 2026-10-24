"""Live seat tabs refuse invented readings."""

from __future__ import annotations

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
FORBIDDEN = ("Math.random", "faker", "mockData", "placeholder", "lorem", "simulated")


def test_seat_tabs_match_and_do_not_invent_readings() -> None:
    from aureon.core.simulated_boot import simulated_boot_enabled
    from aureon.operator.seat_proxy import SEATS

    assert simulated_boot_enabled() is False
    page = (REPO / "frontend/src/shell/pages/LiveSeatsPage.tsx").read_text(encoding="utf-8")
    manifest = (REPO / "frontend/src/shell/seatManifest.ts").read_text(encoding="utf-8")
    proxy = (REPO / "aureon/operator/seat_proxy.py").read_text(encoding="utf-8")
    for label, text in (("page", page), ("manifest", manifest), ("proxy", proxy)):
        for token in FORBIDDEN:
            assert token not in text, f"{label} contains {token}"
    ids = re.findall(r'id: "([^"]+)"', manifest)
    assert ids == [seat["id"] for seat in SEATS]
    assert 'fetch(`/api/seats/${seat.id}`' in page
    assert "setInterval" in page
    dashboards = list((REPO / "frontend/src/components").glob("*Dashboard*.tsx"))
    dashboards += list((REPO / "frontend/src/shell/pages").glob("*.tsx"))
    for path in dashboards:
        text = path.read_text(encoding="utf-8")
        for token in ("Math.random", "faker", "mockData"):
            assert token not in text, f"{path.name} contains {token}"


def test_a_down_upstream_is_unavailable_and_an_upstream_number_is_kept(tmp_path: Path) -> None:
    import aureon.operator.seat_proxy as seat_proxy

    original = seat_proxy.SEATS
    seat_proxy.SEATS = (
        {
            "id": "closed-seat",
            "label": "Closed",
            "was": "closed port",
            "upstream": "http://127.0.0.1:1/healthz",
        },
    )
    try:
        down = seat_proxy.read_seat("closed-seat")
    finally:
        seat_proxy.SEATS = original
    assert down["available"] is False
    assert down["payload"] is None
    assert down["reason"]
    assert down["fetched_at"]

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            raw = json.dumps({"ok": True, "kp_index": 4, "live_trading": False}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, fmt: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = int(server.server_address[1])
        import aureon.operator.seat_proxy as seat_proxy

        original = seat_proxy.SEATS
        seat_proxy.SEATS = (
            {
                "id": "fusion",
                "label": "Fusion seat",
                "was": "port 8765",
                "upstream": f"http://127.0.0.1:{port}/healthz",
            },
        )
        try:
            reading = seat_proxy.read_seat("fusion")
        finally:
            seat_proxy.SEATS = original
    finally:
        server.shutdown()
        server.server_close()
    assert reading["available"] is True
    assert reading["payload"]["kp_index"] == 4
    assert reading["fetched_at"]


def test_a_gated_dashboard_tab_serves_no_reading() -> None:
    from aureon.operator.seat_proxy import read_seat

    reading = read_seat("queen-unified")
    assert reading["available"] is False
    assert reading["payload"] is None
    assert reading["reason"]
    assert reading["fetched_at"]
    assert "AUREON_SIMULATED_BOOT" in reading["reason"]


def test_missing_faculty_file_records_absence_without_a_measurement(tmp_path: Path) -> None:
    from aureon.launch.faculty_files import record_absence

    path = tmp_path / "hnc_core_state.json"
    saved = record_absence({"name": "hnc_core", "path": str(path)}, "organ/hnc_core")
    assert saved == path
    body = json.loads(path.read_text(encoding="utf-8"))
    assert body["truth_status"] == "no_data"
    assert body["available"] is False
    assert "no sample yet" in body["reason"]
    assert "timestamp" in body
    assert "kp_index" not in body
    again = record_absence({"name": "hnc_core", "path": str(path)}, "organ/hnc_core")
    assert again == path
    assert json.loads(path.read_text(encoding="utf-8")) == body


def test_workspace_scripts_from_the_preflight_are_present() -> None:
    names = (
        "real_time_data_feeder.py",
        "schumann_real_daemon.py",
        "planetary_monitor_daemon.py",
        "solar_system_collector.py",
        "sero_space_weather.py",
        "sero_autonomous_expansion.py",
        "soul_protection_daemon.py",
        "aureon_self_questioning_runner.py",
    )
    for name in names:
        text = (REPO / name).read_text(encoding="utf-8")
        assert "invent" in text or "checkout_daemons" in text or "no question" in text
        assert "Math.random" not in text


@pytest.mark.parametrize("name", ["real_time_data_feeder.py", "solar_system_collector.py"])
def test_workspace_script_delegates(name: str) -> None:
    text = (REPO / name).read_text(encoding="utf-8")
    assert "checkout_daemons" in text
