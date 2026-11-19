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
        # Kept open for the app's lifetime; closed in close().
        self._stderr = open(workdir / "testpad.stderr.log", "w")  # noqa: SIM115
        self.proc = subprocess.Popen(
            [sys.executable, str(HERE / "real_display_testpad.py"), str(self.state_path)],
            stdout=subprocess.DEVNULL,
            stderr=self._stderr,
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
        self._stderr.close()


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
    from aureon.autonomous import aureon_safe_desktop_control as sdc

    ctl = sdc.SafeDesktopControl(dry_run=False)
    # Go live with whatever the current build requires.  Arming / approval /
    # confirmation are passed when the API has them and are NOT asserted, so
    # this keeps working once they are removed.
    if hasattr(ctl, "arm_live"):
        ctl.arm_live()
    return sdc, ctl


def _safe_act(sdc, ctl, action: str, params: dict):
    req = sdc.DesktopAction(action, params)
    for name, value in (("approved", True), ("confirm_token", os.environ["AUREON_DESKTOP_CONFIRM_TOKEN"])):
        if hasattr(req, name):
            setattr(req, name, value)
    return ctl.execute(req)


def _safe_log(ctl) -> list:
    """The controller's persisted action log (state file ``recent_actions``)."""

    payload = json.loads(Path(ctl.state_path).read_text(encoding="utf-8"))
    return list(payload.get("recent_actions") or [])


def scenario_safe_controller(workdir: Path) -> dict:
    # Import the controller first: it is what must make pyautogui importable.
    sdc, ctl = _safe_controller(workdir)
    pad = TestPad(workdir)
    out: dict = {}
    try:
        st = pad.state()
        btn, box = st["button_center"], st["box_center"]
        out["png_before"] = _grab(workdir, "safe_01_before.png")
        r1 = _safe_act(sdc, ctl, "left_click", {"x": btn[0], "y": btn[1]})
        st = pad.settle(lambda s: s["clicks"] >= 1)
        out["click"] = {"ok": r1.ok, "reason": r1.reason, "clicks": st["clicks"]}
        r2 = _safe_act(sdc, ctl, "left_click", {"x": box[0], "y": box[1]})
        pad.settle(lambda s: s["box_focused"])
        out["focus"] = {"ok": r2.ok, "reason": r2.reason}
        r3 = _safe_act(sdc, ctl, "type_text", {"text": TEXT})
        st = pad.settle(lambda s: s["text"] == TEXT)
        out["type"] = {"ok": r3.ok, "reason": r3.reason, "text": st["text"]}
        r4 = _safe_act(sdc, ctl, "press_key", {"key": "enter"})
        st = pad.settle(lambda s: bool(s["submitted"]))
        out["enter"] = {"ok": r4.ok, "reason": r4.reason, "submitted": st["submitted"]}
        out["png_after"] = _grab(workdir, "safe_02_after_click_type_enter.png")
        log = _safe_log(ctl)
        out["log_actions"] = [(e.get("action"), e.get("ok")) for e in log]
        out["log_contains_typed_text"] = TEXT in Path(ctl.state_path).read_text(encoding="utf-8")
    finally:
        if hasattr(ctl, "disarm"):
            ctl.disarm()
        pad.close()
    return out


def scenario_safe_kill_switch(workdir: Path) -> dict:
    sdc, ctl = _safe_controller(workdir)
    pad = TestPad(workdir)
    out: dict = {}
    try:
        btn = pad.state()["button_center"]
        r1 = _safe_act(sdc, ctl, "left_click", {"x": btn[0], "y": btn[1]})
        st = pad.settle(lambda s: s["clicks"] >= 1)
        out["before_stop"] = {"ok": r1.ok, "clicks": st["clicks"]}
        ctl.kill_path.write_text("STOP\n", encoding="utf-8")
        before = pad.state()
        r2 = _safe_act(sdc, ctl, "left_click", {"x": btn[0], "y": btn[1]})
        st = pad.settle()
        out["after_stop"] = {"ok": r2.ok, "reason": r2.reason, "unchanged": st == before}
        out["png_stop"] = _grab(workdir, "safe_03_after_stop_file.png")
        out["log_last"] = (_safe_log(ctl) or [{}])[-1].get("reason")
    finally:
        if ctl.kill_path.exists():
            ctl.kill_path.unlink()
        pad.close()
    return out


def scenario_gateway(workdir: Path) -> dict:
    import inspect
    import secrets

    from aureon.autonomous.aureon_governed_desktop_gateway import GovernedDesktopGateway

    evidence = workdir / "gateway_evidence.jsonl"
    pad = TestPad(workdir)
    out: dict = {}
    gateway = GovernedDesktopGateway(evidence_path=evidence)
    try:
        st = pad.state()
        btn, box = st["button_center"], st["box_center"]
        out["png_before"] = _grab(workdir, "gateway_01_before.png")
        binding = gateway.bind_target_window(TITLE, expected_process_id=st["pid"])
        out["binding_pid_matches"] = binding.process_id == st["pid"]
        # Go live with whatever this build requires; not asserted.
        if hasattr(gateway, "authorize_live"):
            gateway.authorize_live(
                secrets.token_urlsafe(32), ttl_seconds=120, subject="real-display-test",
            )
        wants_hash = "expected_before_sha256" in inspect.signature(gateway.execute).parameters

        def act(action: str, params: dict) -> dict:
            kwargs: dict = {"target_binding_id": binding.binding_id}
            if wants_hash:
                kwargs["expected_before_sha256"] = gateway.observe(
                    target_binding_id=binding.binding_id
                ).before_sha256
            result = gateway.execute(action, params, **kwargs)
            return {"ok": result.ok, "reason": result.reason, "action_id": result.action_id,
                    "before": result.before_sha256, "after": result.after_sha256,
                    "_after_png": result.after.image_bytes if result.after else b""}

        click = act("click", {"x": btn[0], "y": btn[1]})
        click["clicks"] = pad.settle(lambda s: s["clicks"] >= 1)["clicks"]
        focus = act("click", {"x": box[0], "y": box[1]})
        pad.settle(lambda s: s["box_focused"])
        typed = act("type", {"text": TEXT})
        typed["text"] = pad.settle(lambda s: s["text"] == TEXT)["text"]
        enter = act("press", {"key": "enter"})
        enter["submitted"] = pad.settle(lambda s: bool(s["submitted"]))["submitted"]
        masked = _artifact(workdir, "gateway_02_after_masked_observation.png")
        masked.write_bytes(enter["_after_png"])
        steps = {"click": click, "focus": focus, "type": typed, "enter": enter}
        for item in steps.values():
            item.pop("_after_png", None)
        out["steps"] = steps
        out["png_after"] = _grab(workdir, "gateway_02_after_click_type_enter.png")
        out["png_after_masked_observation"] = str(masked)

        text = evidence.read_text(encoding="utf-8")
        events = [json.loads(line) for line in text.splitlines() if line.strip()]
        completed = {e.get("action_id"): e for e in events if e.get("event") == "action_completed"}
        out["audited"] = {
            name: bool(
                completed.get(item["action_id"], {}).get("ok")
                and completed[item["action_id"]].get("before_sha256")
                and (completed[item["action_id"]].get("after") or {}).get("sha256")
            )
            for name, item in steps.items()
        }
        out["evidence_contains_typed_text"] = TEXT in text
    finally:
        if hasattr(gateway, "disarm"):
            gateway.disarm("real_display_test_end")
        pad.close()
    return out


SCENARIOS = {
    "import": scenario_import,
    "safe_controller": scenario_safe_controller,
    "safe_kill_switch": scenario_safe_kill_switch,
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
