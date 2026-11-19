"""Scenario driver for tests/test_real_display_desktop_control.py.

Runs ONE scenario in a fresh interpreter against the X display in $DISPLAY and
prints ``RESULT <json>`` as its last line.  Each scenario starts its own
``real_display_testpad.py`` window and kills it afterwards.  Running in a
subprocess means a SystemExit from a desktop import shows up as a failed test
instead of terminating pytest.

Only point this at a throwaway virtual display (e.g. ``Xvfb :42``): it moves
the real pointer and types into the focused window of $DISPLAY.

    python tests/real_display_driver.py SCENARIO WORKDIR
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

TITLE = "Aureon Test Pad"
TEXT = "hello aureon 42"


class TestPad:
    def __init__(self, workdir: Path) -> None:
        self.state_path = workdir / "testpad_state.json"
        self.proc = subprocess.Popen(
            [sys.executable, str(HERE / "real_display_testpad.py"), str(self.state_path)],
            stdout=subprocess.DEVNULL,
            stderr=open(workdir / "testpad.stderr.log", "w"),
        )
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            state = self.state()
            if state.get("ready"):
                time.sleep(0.3)
                return
            if self.proc.poll() is not None:
                raise RuntimeError("testpad_exited_early")
            time.sleep(0.05)
        raise RuntimeError("testpad_not_ready")

    def state(self) -> dict:
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def settle(self, predicate=None, timeout: float = 3.0) -> dict:
        deadline = time.monotonic() + timeout
        state = self.state()
        while time.monotonic() < deadline:
            state = self.state()
            if predicate is None or predicate(state):
                break
            time.sleep(0.05)
        time.sleep(0.2)
        return self.state()

    def close(self) -> None:
        self.proc.terminate()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()


def _artifact(workdir: Path, name: str) -> Path:
    root = Path(os.environ.get("AUREON_REAL_DISPLAY_ARTIFACTS") or workdir)
    root.mkdir(parents=True, exist_ok=True)
    return root / name


def _grab(workdir: Path, name: str) -> str:
    from PIL import ImageGrab

    path = _artifact(workdir, name)
    ImageGrab.grab(xdisplay=os.environ["DISPLAY"]).save(path)
    return str(path)


def scenario_import(workdir: Path) -> dict:
    from aureon.autonomous import aureon_safe_desktop_control as sdc
    from aureon.autonomous.aureon_governed_desktop_gateway import LazyPyAutoGUIBackend

    LazyPyAutoGUIBackend()._pyautogui()
    return {"alive": True, "has_pyautogui": sdc.HAS_PYAUTOGUI}


def _safe_controller(workdir: Path):
    os.environ["AUREON_DESKTOP_CONTROL_STATE"] = str(workdir / "safe_state.json")
    os.environ["AUREON_DESKTOP_KILL_SWITCH"] = str(workdir / "safe_desktop_control.stop")
    os.environ["AUREON_DESKTOP_CONFIRM_TOKEN"] = "real-display-harness-token"
    os.environ.pop("AUREON_DESKTOP_REQUIRE_CONFIRMATION", None)
    from aureon.autonomous import aureon_safe_desktop_control as sdc

    return sdc, sdc.SafeDesktopControl(dry_run=True)


def scenario_safe_controller(workdir: Path) -> dict:
    # Import the controller first: it is what must make pyautogui importable.
    sdc, ctl = _safe_controller(workdir)
    import pyautogui

    token = os.environ["AUREON_DESKTOP_CONFIRM_TOKEN"]
    pad = TestPad(workdir)
    out: dict = {}
    try:
        st = pad.state()
        btn, box = st["button_center"], st["box_center"]
        pyautogui.moveTo(5, 5)
        out["png_before"] = _grab(workdir, "safe_01_before.png")

        ctl.arm_dry_run()
        r = ctl.propose(sdc.DesktopAction("left_click", {"x": btn[0], "y": btn[1]}))
        st = pad.settle()
        out["dry_run"] = {"status": r["status"], "clicks": st["clicks"], "pointer": list(pyautogui.position())}

        ctl.arm_live()
        r1 = ctl.execute(sdc.DesktopAction("left_click", {"x": btn[0], "y": btn[1]}, approved=True))
        st = pad.settle(lambda s: s["clicks"] >= 1)
        out["live_click"] = {"ok": r1.ok, "reason": r1.reason, "clicks": st["clicks"]}
        ctl.execute(sdc.DesktopAction("left_click", {"x": box[0], "y": box[1]}, approved=True))
        pad.settle(lambda s: s["box_focused"])
        r2 = ctl.execute(sdc.DesktopAction("type_text", {"text": TEXT}, approved=True, confirm_token=token))
        st = pad.settle(lambda s: s["text"] == TEXT)
        out["live_type"] = {"ok": r2.ok, "reason": r2.reason, "text": st["text"]}

        proposed = ctl.propose(sdc.DesktopAction("press_key", {"key": "enter"}, approved=True))
        approved = ctl.approve_next(token)
        st = pad.settle(lambda s: bool(s["submitted"]))
        out["propose_press_key"] = {
            "proposed_status": proposed["status"],
            "approve_ok": approved.ok,
            "approve_reason": approved.reason,
            "submitted": st["submitted"],
        }
        out["png_after"] = _grab(workdir, "safe_02_after_live.png")

        before = pad.state()
        ctl.kill_path.write_text("STOP\n", encoding="utf-8")
        r3 = ctl.execute(sdc.DesktopAction("left_click", {"x": btn[0], "y": btn[1]}, approved=True))
        st = pad.settle()
        out["stop_file"] = {"ok": r3.ok, "reason": r3.reason, "unchanged": st == before}
        out["png_stop"] = _grab(workdir, "safe_03_after_stop_file.png")
    finally:
        ctl.disarm()
        pad.close()
    return out


def scenario_gateway(workdir: Path) -> dict:
    import hashlib
    import secrets

    from aureon.autonomous.aureon_governed_desktop_gateway import (
        AuthorizationError,
        GovernedDesktopGateway,
    )

    evidence = workdir / "gateway_evidence.jsonl"
    token = secrets.token_urlsafe(32)  # one-time capability token, never persisted
    short_token = secrets.token_urlsafe(32)
    pad = TestPad(workdir)
    out: dict = {}
    gateway = GovernedDesktopGateway(evidence_path=evidence, min_action_interval_seconds=0.0)
    try:
        st = pad.state()
        btn, box = st["button_center"], st["box_center"]
        out["png_before"] = _grab(workdir, "gateway_01_before.png")
        binding = gateway.bind_target_window(TITLE, expected_process_id=st["pid"])
        out["binding"] = {"handle": binding.handle, "pid": binding.process_id}

        # Dry run: accepted, evidence written, nothing moves.
        dry = gateway.execute("click", {"x": btn[0], "y": btn[1]}, target_binding_id=binding.binding_id)
        st = pad.settle()
        out["dry_run"] = {"ok": dry.ok, "reason": dry.reason, "dry_run": dry.dry_run, "clicks": st["clicks"]}

        # Live action without a lease is refused when not dry-run; arm with a
        # one-time capability token and a short lease.
        lease = gateway.authorize_live(
            token,
            ttl_seconds=120,
            subject="real-display-test",
            allowed_actions=["click", "type", "press"],
        )
        try:
            gateway.authorize_live(token, ttl_seconds=60, subject="replay")
            out["token_replay"] = "accepted"
        except AuthorizationError as exc:
            out["token_replay"] = str(exc)

        no_hash = gateway.execute("click", {"x": btn[0], "y": btn[1]}, target_binding_id=binding.binding_id)
        out["live_without_before_hash"] = no_hash.reason
        stale = gateway.execute(
            "click", {"x": btn[0], "y": btn[1]}, target_binding_id=binding.binding_id,
            expected_before_sha256=hashlib.sha256(b"not the frame").hexdigest(),
        )
        out["live_stale_hash"] = stale.reason
        scoped = gateway.execute(
            "scroll", {"amount": 1, "x": btn[0], "y": btn[1]}, target_binding_id=binding.binding_id,
            expected_before_sha256=gateway.observe(target_binding_id=binding.binding_id).before_sha256,
        )
        out["outside_lease_scope"] = scoped.reason
        st = pad.settle()
        out["clicks_after_refusals"] = st["clicks"]

        def act(action: str, params: dict) -> dict:
            seen = gateway.observe(target_binding_id=binding.binding_id)
            result = gateway.execute(
                action, params, target_binding_id=binding.binding_id,
                expected_before_sha256=seen.before_sha256,
            )
            return {"ok": result.ok, "reason": result.reason, "dry_run": result.dry_run,
                    "before": result.before_sha256, "after": result.after_sha256,
                    "_after_png": result.after.image_bytes if result.after else b""}

        click = act("click", {"x": btn[0], "y": btn[1]})
        st = pad.settle(lambda s: s["clicks"] >= 1)
        click["clicks"] = st["clicks"]
        focus = act("click", {"x": box[0], "y": box[1]})
        pad.settle(lambda s: s["box_focused"])
        typed = act("type", {"text": TEXT})
        st = pad.settle(lambda s: s["text"] == TEXT)
        typed["text"] = st["text"]
        enter = act("press", {"key": "enter"})
        st = pad.settle(lambda s: bool(s["submitted"]))
        enter["submitted"] = st["submitted"]
        masked = _artifact(workdir, "gateway_02_after_live_masked_observation.png")
        masked.write_bytes(enter.pop("_after_png"))
        for item in (click, focus, typed):
            item.pop("_after_png", None)
        out.update(live_click=click, live_focus=focus, live_type=typed, live_enter=enter)
        out["png_after"] = _grab(workdir, "gateway_02_after_live.png")
        out["png_after_masked_observation"] = str(masked)
        out["lease_actions"] = sorted(lease.allowed_actions)

        # Emergency stop invalidates lease and binding; next action refused.
        before = pad.state()
        gateway.emergency_stop("real_display_test")
        stopped = gateway.execute("click", {"x": btn[0], "y": btn[1]}, target_binding_id=binding.binding_id)
        st = pad.settle()
        out["after_emergency_stop"] = {"ok": stopped.ok, "reason": stopped.reason, "unchanged": st == before}
        gateway.clear_emergency_stop("real_display_test")

        # A short lease expires on its own.
        binding2 = gateway.bind_target_window(TITLE, expected_process_id=st["pid"])
        gateway.authorize_live(short_token, ttl_seconds=1, subject="expiry", allowed_actions=["click"])
        time.sleep(1.5)
        seen = gateway.observe(target_binding_id=binding2.binding_id)
        expired = gateway.execute(
            "click", {"x": btn[0], "y": btn[1]}, target_binding_id=binding2.binding_id,
            expected_before_sha256=seen.before_sha256,
        )
        out["after_lease_expiry"] = expired.reason
        out["png_stop"] = _grab(workdir, "gateway_03_after_stop_and_expiry.png")

        events = [json.loads(line) for line in evidence.read_text(encoding="utf-8").splitlines() if line.strip()]
        out["evidence_events"] = sorted({e.get("event") for e in events})
        live_done = [e for e in events if e.get("event") == "action_completed" and e.get("mode") == "live" and e.get("ok")]
        out["live_completed_with_before_after"] = sum(
            1 for e in live_done if e.get("before_sha256") and (e.get("after") or {}).get("sha256")
        )
        out["evidence_contains_typed_text"] = TEXT in evidence.read_text(encoding="utf-8")
        out["evidence_contains_token"] = token in evidence.read_text(encoding="utf-8")
    finally:
        gateway.disarm("real_display_test_end")
        pad.close()
    return out


SCENARIOS = {
    "import": scenario_import,
    "safe_controller": scenario_safe_controller,
    "gateway": scenario_gateway,
}


def main(argv: list[str]) -> int:
    name, workdir = argv[1], Path(argv[2])
    workdir.mkdir(parents=True, exist_ok=True)
    result = SCENARIOS[name](workdir)
    print("RESULT " + json.dumps(result, default=str), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
