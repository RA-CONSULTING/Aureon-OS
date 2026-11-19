"""ComputerUse autonomy: real Xvfb input, argv shell, stop file, and the key wall.

These assertions describe the owner decision of 19 Nov 2026. On main, agent-core
desktop/shell/open_url return HOLD and this module does not exist, so the file
fails there.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest
from PIL import Image

from aureon.autonomous.aureon_agent_core import AureonAgentCore
from aureon.autonomous.aureon_governed_desktop_gateway import (
    GovernedDesktopGateway,
    WindowInfo,
    X11PyAutoGUIBackend,
)
from aureon.autonomy.computer_agent_loop import ComputerAgentLoop
from aureon.autonomy.computer_use import ComputerUse, GatewayDesktopAdapter, default_computer_backend
from aureon.inhouse_ai.llm_adapter import LLMResponse, ToolCall
from aureon.operator.tools import TENANT_ALLOWED_TOOLS, build_operator_tools

REPO_ROOT = Path(__file__).resolve().parents[1]
MARKER = "TEST_FIXTURE_MARKER_NOT_A_REAL_KEY"

X_CLIENT = r"""
import sys
from Xlib import X, display

log_path, ready_path = sys.argv[1], sys.argv[2]
handle = display.Display()
screen = handle.screen()
window = screen.root.create_window(
    0,
    0,
    400,
    300,
    0,
    X.CopyFromParent,
    X.InputOutput,
    X.CopyFromParent,
    background_pixel=screen.black_pixel,
    event_mask=X.ButtonPressMask | X.KeyPressMask | X.ExposureMask,
)
window.map()
try:
    window.set_input_focus(X.RevertToParent, X.CurrentTime)
except Exception:
    pass
handle.flush()
handle.sync()
Path = __import__("pathlib").Path
Path(ready_path).write_text("ready\n", encoding="utf-8")
typed = []
with open(log_path, "a", encoding="utf-8") as log:
    while True:
        event = handle.next_event()
        if event.type == X.ButtonPress:
            log.write(f"click {event.root_x} {event.root_y}\n")
            log.flush()
        elif event.type == X.KeyPress:
            shifted = bool(event.state & X.ShiftMask)
            keysym = handle.keycode_to_keysym(event.detail, 1 if shifted else 0)
            if 32 <= keysym < 127:
                typed.append(chr(keysym))
                log.write("text " + "".join(typed) + "\n")
                log.flush()
"""


class RecordingDesktop:
    def __init__(self) -> None:
        self.calls: list[tuple] = []
        image = Image.new("RGB", (4, 3), (8, 16, 32))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        self.png = buffer.getvalue()

    def screenshot_png(self) -> bytes:
        self.calls.append(("screenshot",))
        return self.png

    def move(self, x, y, duration=0.0):
        self.calls.append(("move", x, y, duration))

    def click(self, x, y, button="left", clicks=1):
        self.calls.append(("click", x, y, button, clicks))

    def drag(self, x, y, x2, y2, button="left"):
        self.calls.append(("drag", x, y, x2, y2, button))

    def scroll(self, amount, x, y):
        self.calls.append(("scroll", amount, x, y))

    def type_text(self, text, interval=0.0):
        self.calls.append(("type", text, interval))

    def press_key(self, key):
        self.calls.append(("press", key))

    def hotkey(self, keys):
        self.calls.append(("hotkey", tuple(keys)))


class _GatewayBackend:
    def __init__(self) -> None:
        self.window = WindowInfo(7, "Fixture Browser", 99, 5, 5, 790, 590)
        self.actions: list[tuple] = []
        self.captures = 0
        image = Image.new("RGB", (8, 8), (1, 2, 3))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        self.image = buffer.getvalue()

    def capture_screen(self) -> bytes:
        self.captures += 1
        return self.image

    def screen_size(self):
        return 800, 600

    def foreground_window(self):
        return self.window

    def pointer_position(self):
        return 0, 0

    def click(self, x, y, button="left", clicks=1):
        self.actions.append(("click", x, y, button, clicks))


def _computer(tmp_path: Path, backend=None, **kwargs) -> ComputerUse:
    return ComputerUse(
        audit_path=tmp_path / "audit.jsonl",
        stop_path=kwargs.pop("stop_path", tmp_path / "computer_use.stop"),
        screenshot_dir=tmp_path / "shots",
        backend=backend if backend is not None else RecordingDesktop(),
        **kwargs,
    )


def _audit_lines(computer: ComputerUse) -> list[dict]:
    text = computer.audit_path.read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def test_pyautogui_import_does_not_exit_without_tkinter(tmp_path: Path) -> None:
    """A stub tkinter that raises must not let mouseinfo sys.exit the loader.

    ComputerUse loads pyautogui through ``pyautogui_loader``. This child puts a
    failing tkinter ahead of the real one so the shared shim is what keeps the
    process alive.
    """

    stub = tmp_path / "tkinter_stub"
    stub.mkdir()
    (stub / "tkinter.py").write_text("raise ImportError('tkinter missing')\n", encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(stub) + os.pathsep + env.get("PYTHONPATH", "")
    env["AUREON_REPO"] = str(REPO_ROOT)
    code = (
        "import os, sys\n"
        "sys.path.insert(0, os.environ['AUREON_REPO'])\n"
        "from aureon.autonomy.computer_use import load_pyautogui\n"
        "load_pyautogui()\n"
        "print('loaded')\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "loaded" in completed.stdout
    assert "MouseInfo" not in completed.stderr


def test_linux_computer_use_uses_default_desktop_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("DISPLAY", ":42")
    backend = default_computer_backend()
    assert isinstance(backend, GatewayDesktopAdapter)
    assert isinstance(backend._backend, X11PyAutoGUIBackend)


def test_run_shell_returns_python_stdout(tmp_path: Path) -> None:
    computer = _computer(tmp_path)
    result = computer.run_shell([sys.executable, "-c", "print('computer-use-stdout')"])

    assert result["status"] != "hold"
    assert result["returncode"] == 0
    assert "computer-use-stdout" in result["stdout"]
    assert not computer.stop_path.exists()


def test_stop_file_blocks_click_type_and_shell_until_removed(tmp_path: Path) -> None:
    backend = RecordingDesktop()
    stop = tmp_path / "computer_use.stop"
    computer = _computer(tmp_path, backend=backend, stop_path=stop)
    flag = tmp_path / "ran.txt"

    assert computer.click(2, 3)["ok"] is True
    assert ("click", 2, 3, "left", 1) in backend.calls
    stop.write_text("stop\n", encoding="utf-8")
    clicked = computer.click(4, 5)
    typed = computer.type_text("secret-text")
    shell = computer.run_shell([sys.executable, "-c", f"open({str(flag)!r}, 'w').write('ran')"])

    assert clicked["status"] == "stopped"
    assert typed["status"] == "stopped"
    assert shell["status"] == "stopped"
    assert all(item["ok"] is False for item in (clicked, typed, shell))
    assert ("click", 4, 5, "left", 1) not in backend.calls
    assert not any(call[0] == "type" for call in backend.calls)
    assert not flag.exists()
    stopped_lines = [line for line in _audit_lines(computer) if line["result"]["status"] == "stopped"]
    assert {line["action"] for line in stopped_lines} >= {"click", "type_text", "run_shell"}

    stop.unlink()
    assert computer.click(6, 7)["ok"] is True
    resumed = computer.run_shell([sys.executable, "-c", f"open({str(flag)!r}, 'w').write('ran')"])
    assert resumed["returncode"] == 0
    assert flag.read_text(encoding="utf-8") == "ran"
    assert ("click", 6, 7, "left", 1) in backend.calls


def test_env_file_cat_is_refused_and_marker_stays_out_of_output(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(f"# test fixture, not a credential\n{MARKER}=dummy\n", encoding="utf-8")
    computer = _computer(tmp_path)

    result = computer.run_shell(["cat", str(env_file)])

    assert result["status"] == "denied"
    assert result["returncode"] is None
    assert MARKER not in json.dumps(result)
    assert MARKER not in computer.audit_path.read_text(encoding="utf-8")
    assert env_file.read_text(encoding="utf-8").startswith("# test fixture")


def test_whitespace_string_and_symlink_cannot_reach_a_denied_path(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(f"{MARKER}=dummy\n", encoding="utf-8")
    secret_dir = tmp_path / "secrets"
    secret_dir.mkdir()
    victim = secret_dir / "victim"
    victim.mkdir()
    (victim / "keep.txt").write_text("keep", encoding="utf-8")
    link = tmp_path / "looks_fine"
    link.symlink_to(secret_dir / "note.txt")
    (secret_dir / "note.txt").write_text(MARKER, encoding="utf-8")
    computer = _computer(tmp_path)

    tabbed = computer.run_shell(f"cat\t{env_file}")
    spaced = computer.run_shell(f"cat    {env_file}")
    removed = computer.run_shell(f"rm\t-rf\t{victim}")
    linked = computer.run_shell(["cat", str(link)])
    allowed = computer.run_shell("echo\thello-tab")

    assert tabbed["status"] == "denied"
    assert spaced["status"] == "denied"
    assert removed["status"] == "denied"
    assert linked["status"] == "denied"
    assert (victim / "keep.txt").is_file()
    assert MARKER not in json.dumps([tabbed, spaced, linked])
    assert allowed["returncode"] == 0
    assert allowed["stdout"].strip() == "hello-tab"


def test_deny_root_is_a_resolved_prefix_not_a_substring(tmp_path: Path) -> None:
    live = tmp_path / "liverun"
    live.mkdir()
    (live / "data.txt").write_text(MARKER, encoding="utf-8")
    sibling = tmp_path / "liverun_extra"
    sibling.mkdir()
    (sibling / "data.txt").write_text("visible-outside", encoding="utf-8")
    computer = _computer(tmp_path, live_run_root=live)

    inside = computer.run_shell(["cat", str(live / "data.txt")])
    outside = computer.run_shell(["cat", str(sibling / "data.txt")])

    assert inside["status"] == "denied"
    assert MARKER not in json.dumps(inside)
    assert "visible-outside" in outside["stdout"]


def test_configured_deny_path_and_file_url_are_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    denied_root = tmp_path / "vault"
    denied_root.mkdir()
    secret = denied_root / "note.txt"
    secret.write_text(MARKER, encoding="utf-8")
    monkeypatch.setenv("AUREON_COMPUTER_USE_DENY_PATHS", str(denied_root))
    opened: list[str] = []
    computer = _computer(tmp_path, browser_opener=opened.append)

    shell = computer.run_shell(["cat", str(secret)])
    file_url = computer.open_url(secret.as_uri())
    web = computer.open_url("https://example.invalid/no-network")

    assert shell["status"] == "denied"
    assert file_url["status"] == "denied"
    assert opened == ["https://example.invalid/no-network"]
    assert web["ok"] is True
    assert MARKER not in json.dumps([shell, file_url, web])


def test_child_process_does_not_see_parent_exchange_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    secrets = {
        "KRAKEN_API_KEY": "kraken-fixture-value",
        "BINANCE_API_SECRET": "binance-fixture-value",
        "ALPACA_API_KEY": "alpaca-fixture-value",
        "APCA_API_KEY_ID": "apca-fixture-value",
        "CAPITAL_API_KEY": "capital-fixture-value",
        "COINAPI_KEY": "coinapi-fixture-value",
        "SERVICE_TOKEN": "service-token-fixture-value",
    }
    for name, value in secrets.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("AUREON_CU_VISIBLE", "yes")
    computer = _computer(tmp_path)
    script = (
        "import os, subprocess, sys\n"
        "names = ['KRAKEN_API_KEY','BINANCE_API_SECRET','ALPACA_API_KEY','APCA_API_KEY_ID',"
        "'CAPITAL_API_KEY','COINAPI_KEY','SERVICE_TOKEN']\n"
        "print('CHILD', {n: os.environ.get(n) for n in names})\n"
        "print('PROCSELF', open('/proc/self/environ','rb').read().decode('utf-8','replace'))\n"
        "for pid in range(1, 20):\n"
        "    try:\n"
        "        print(pid, open(f'/proc/{pid}/environ','rb').read().decode('utf-8','replace'))\n"
        "    except Exception as exc:\n"
        "        print(pid, type(exc).__name__)\n"
        "grand = subprocess.run([sys.executable, '-c', "
        "'import os; print({n: os.environ.get(n) for n in "
        "[\"KRAKEN_API_KEY\",\"BINANCE_API_SECRET\",\"ALPACA_API_KEY\",\"APCA_API_KEY_ID\","
        "\"CAPITAL_API_KEY\",\"COINAPI_KEY\",\"SERVICE_TOKEN\"]}); "
        "print(open(\"/proc/self/environ\",\"rb\").read().decode(\"utf-8\",\"replace\"))'"
        "], capture_output=True, text=True)\n"
        "print('GRAND', grand.stdout)\n"
        "print('VISIBLE', os.environ.get('AUREON_CU_VISIBLE'))\n"
    )

    result = computer.run_shell([sys.executable, "-c", script])

    assert result["returncode"] == 0, result
    blob = result["stdout"] + result.get("stderr", "")
    for value in secrets.values():
        assert value not in blob
    assert "VISIBLE yes" in result["stdout"] or "VISIBLE\nyes" in result["stdout"] or "yes" in result["stdout"]


def test_filesystem_wall_hides_dotenv_symlinks_run_dir_and_inline_open(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(f"{MARKER}=dummy\n", encoding="utf-8")
    key_dir = tmp_path / "keys"
    key_dir.mkdir()
    (key_dir / "exchange.txt").write_text(MARKER, encoding="utf-8")
    link = tmp_path / "looks_fine"
    link.symlink_to(env_file)
    run_dir = Path("/workspace/aureon_run_f21fb3ec")
    run_dir.mkdir(exist_ok=True)
    run_file = run_dir / "k.txt"
    run_file.write_text(MARKER, encoding="utf-8")
    computer = _computer(tmp_path)
    inline = (
        "def show(path):\n"
        "    try:\n"
        "        print(open(path).read())\n"
        "    except Exception as exc:\n"
        "        print(type(exc).__name__)\n"
        "show('.env')\n"
        "show('looks_fine')\n"
        "show('keys/exchange.txt')\n"
        f"show({str(run_file)!r})\n"
    )
    try:
        opened = computer.run_shell([sys.executable, "-c", inline], cwd=tmp_path)
        listed = computer.run_shell(["cat", ".env"], cwd=tmp_path)
    finally:
        run_file.unlink(missing_ok=True)
        run_dir.rmdir()

    blob = json.dumps([opened, listed])
    assert MARKER not in blob
    assert listed["status"] == "denied"
    assert opened["returncode"] == 0
    assert env_file.read_text(encoding="utf-8").startswith(MARKER)


def test_agent_core_desktop_shell_and_url_are_not_hold(tmp_path: Path) -> None:
    backend = RecordingDesktop()
    opened: list[str] = []
    computer = _computer(tmp_path, backend=backend, browser_opener=opened.append)
    core = AureonAgentCore(computer_use=computer)

    shell = core.execute_shell([sys.executable, "-c", "print('core-shell')"])
    click = core.click(11, 12)
    typed = core.type_text("abc")
    shot = core.screenshot()
    url = core.open_url("https://example.invalid/computer-use")

    for receipt in (shell, click, typed, shot, url):
        assert receipt.get("status") != "hold"
        assert receipt.get("magic_star_required") is not True
    assert "core-shell" in shell["stdout"]
    assert ("click", 11, 12, "left", 1) in backend.calls
    assert ("type", "abc", 0.02) in backend.calls
    assert Path(shot["path"]).read_bytes().startswith(b"\x89PNG")
    assert opened == ["https://example.invalid/computer-use"]
    lines = _audit_lines(computer)
    assert len(lines) >= 5
    for line in lines:
        assert {"ts", "action", "args", "result"} <= set(line)
    assert any(line["screenshot_path"] for line in lines if line["action"] == "screenshot")


def test_audit_line_is_written_for_every_action(tmp_path: Path) -> None:
    backend = RecordingDesktop()
    computer = _computer(tmp_path, backend=backend)
    computer.move(1, 2)
    computer.press_key("a")
    computer.hotkey(["ctrl", "c"])
    actions = [line["action"] for line in _audit_lines(computer)]
    assert actions == ["move", "press_key", "hotkey"]


def test_typed_text_is_hashed_in_the_audit_and_screenshots_do_not_overwrite(tmp_path: Path) -> None:
    backend = RecordingDesktop()
    computer = _computer(tmp_path, backend=backend)
    typed = "TYPED_FIXTURE_NOT_A_SECRET_phi"
    assert computer.type_text(typed)["ok"] is True
    first = computer.screenshot()
    second = computer.screenshot()
    audit = computer.audit_path.read_text(encoding="utf-8")
    assert typed not in audit
    digest = hashlib.sha256(typed.encode("utf-8")).hexdigest()
    assert digest in audit
    assert '"text_length": ' + str(len(typed)) in audit or f'"text_length":{len(typed)}' in audit
    first_path = Path(first["path"])
    second_path = Path(second["path"])
    assert first_path != second_path
    assert first_path.parent == computer.screenshot_dir
    assert second_path.parent == computer.screenshot_dir
    assert first_path.read_bytes() == backend.png
    assert second_path.read_bytes() == backend.png


def test_stop_file_halts_the_next_action_for_the_loop_and_the_gateway(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stop = tmp_path / "state" / "computer_use.stop"
    stop.parent.mkdir()
    monkeypatch.setenv("AUREON_COMPUTER_USE_STOP_FILE", str(stop))
    backend = RecordingDesktop()
    computer = _computer(tmp_path, backend=backend, stop_path=stop)
    assert computer.click(1, 2)["status"] == "ok"
    stop.write_text("stop\n", encoding="utf-8")
    halted_type = computer.type_text("should-not-type")
    assert halted_type["status"] == "stopped"
    assert not any(call[0] == "type" for call in backend.calls)

    stop.unlink()
    clicks_before = [call for call in backend.calls if call[0] == "click"]

    class _Adapter:
        def prompt(self, messages, system="", tools=None, **kwargs):
            del messages, system, tools, kwargs
            stop.write_text("stop\n", encoding="utf-8")
            return LLMResponse(tool_calls=[ToolCall(name="click", arguments={"x": 9, "y": 8})])

    looped = ComputerAgentLoop(computer, _Adapter(), max_steps=2).run("click next")
    assert looped["stopped"] is True
    assert [call for call in backend.calls if call[0] == "click"] == clicks_before

    stop.unlink()
    gateway_backend = _GatewayBackend()
    gateway = GovernedDesktopGateway(
        backend=gateway_backend,
        evidence_path=tmp_path / "gateway.jsonl",
        min_action_interval_seconds=0.0,
    )
    first = gateway.execute("observe")
    assert first.ok is True
    assert first.reason != "computer_use_stop_file"
    stop.write_text("stop\n", encoding="utf-8")
    halted = gateway.execute("click", {"x": 1, "y": 2})
    assert halted.ok is False
    assert halted.reason == "computer_use_stop_file"
    assert gateway_backend.actions == []


def test_gateway_stop_file_halts_the_next_action(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    stop = tmp_path / "computer_use.stop"
    monkeypatch.setenv("AUREON_COMPUTER_USE_STOP_FILE", str(stop))
    backend = _GatewayBackend()
    gateway = GovernedDesktopGateway(
        backend=backend,
        evidence_path=tmp_path / "gateway.jsonl",
        min_action_interval_seconds=0.0,
    )
    stop.write_text("stop\n", encoding="utf-8")

    halted = gateway.execute("click", {"x": 1, "y": 2})

    assert halted.ok is False
    assert halted.reason == "computer_use_stop_file"
    assert backend.actions == []
    assert backend.captures == 0
    stop.unlink()
    resumed = gateway.execute("observe")
    assert resumed.reason != "computer_use_stop_file"
    assert resumed.ok is True
    assert backend.captures >= 1


def test_loop_stop_file_halts_the_next_tool_call(tmp_path: Path) -> None:
    backend = RecordingDesktop()
    stop = tmp_path / "computer_use.stop"
    computer = _computer(tmp_path, backend=backend, stop_path=stop)

    class _Adapter:
        def prompt(self, messages, system="", tools=None, **kwargs):
            del messages, system, kwargs
            assert tools and any(item.get("type") == "function" for item in tools)
            stop.write_text("stop\n", encoding="utf-8")
            return LLMResponse(tool_calls=[ToolCall(name="click", arguments={"x": 1, "y": 2})])

    result = ComputerAgentLoop(computer, _Adapter(), max_steps=2).run("click the window")

    assert result["stopped"] is True
    assert not any(call[0] == "click" for call in backend.calls)
    assert any(call[0] == "screenshot" for call in backend.calls)


def test_admin_toolbelt_registers_computer_use_and_tenant_belt_does_not() -> None:
    admin = set(build_operator_tools().names())
    tenant = set(build_operator_tools(allow_writes=False, allow_shell=False, allowlist=TENANT_ALLOWED_TOOLS).names())
    shell_off = set(build_operator_tools(allow_writes=False, allow_shell=False).names())
    assert {"click", "type_text", "run_shell", "screenshot", "open_url"} <= admin
    assert tenant.isdisjoint({"click", "run_shell", "open_url", "type_text"})
    assert "run_shell" not in shell_off
    assert "click" not in shell_off


class _ScriptedAdapter:
    def __init__(self) -> None:
        self.calls = 0
        self.saw_function_tools = False

    def prompt(self, messages, system="", tools=None, **kwargs):
        del messages, system, kwargs
        self.calls += 1
        self.saw_function_tools = bool(tools) and all(item.get("type") == "function" for item in tools)
        if self.calls == 1:
            return LLMResponse(tool_calls=[ToolCall(name="click", arguments={"x": 30, "y": 40})])
        if self.calls == 2:
            return LLMResponse(tool_calls=[ToolCall(name="type_text", arguments={"text": "Hi", "interval": 0})])
        return LLMResponse(text="finished-goal")


def run_xvfb_case(mode: str, paths: dict) -> dict:
    """Run inside a child process whose DISPLAY is the private Xvfb server."""

    computer = ComputerUse(
        audit_path=paths["audit"],
        stop_path=paths["stop"],
        screenshot_dir=paths["shots"],
    )
    if mode == "direct":
        core = AureonAgentCore(computer_use=computer)
        return {
            "click": computer.click(30, 40),
            "typed": computer.type_text("Hi", interval=0),
            "shot": computer.screenshot(),
            "core_click": core.click(55, 65),
            "core_type": core.type_text("Z", interval=0),
            "core_shell": core.execute_shell([sys.executable, "-c", "print('core-shell')"]),
        }
    adapter = _ScriptedAdapter()
    result = ComputerAgentLoop(computer, adapter, max_steps=4).run("click then type Hi")
    result["saw_function_tools"] = adapter.saw_function_tools
    return result


def _free_display() -> str:
    for number in range(70, 99):
        if not Path(f"/tmp/.X11-unix/X{number}").exists():
            return f":{number}"
    raise RuntimeError("no free X display")


def _require_display_tools() -> None:
    if shutil.which("Xvfb") is None or shutil.which("xdotool") is None:
        pytest.skip("Xvfb or xdotool absent")


@pytest.fixture
def xvfb_display():
    _require_display_tools()
    display_name = _free_display()
    number = display_name[1:]
    proc = subprocess.Popen(
        ["Xvfb", display_name, "-screen", "0", "800x600x24", "-ac"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    socket_path = Path(f"/tmp/.X11-unix/X{number}")
    deadline = time.time() + 5
    while time.time() < deadline:
        if socket_path.exists():
            break
        if proc.poll() is not None:
            err = proc.stderr.read().decode("utf-8", "replace") if proc.stderr else ""
            pytest.fail(f"Xvfb exited: {err}")
        time.sleep(0.05)
    else:
        os.killpg(proc.pid, signal.SIGTERM)
        pytest.fail("Xvfb did not create a display socket")
    try:
        yield display_name
    finally:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)


def _start_client(display_name: str, log_path: Path, ready_path: Path) -> subprocess.Popen:
    script = log_path.parent / "xclient.py"
    script.write_text(X_CLIENT, encoding="utf-8")
    env = os.environ.copy()
    env["DISPLAY"] = display_name
    proc = subprocess.Popen(
        [sys.executable, str(script), str(log_path), str(ready_path)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    deadline = time.time() + 5
    while time.time() < deadline:
        if ready_path.exists():
            return proc
        if proc.poll() is not None:
            err = proc.stderr.read().decode("utf-8", "replace") if proc.stderr else ""
            pytest.fail(f"X client exited: {err}")
        time.sleep(0.05)
    os.killpg(proc.pid, signal.SIGTERM)
    pytest.fail("X client did not become ready")
    return proc


def _run_worker(display_name: str, mode: str, tmp_path: Path) -> dict:
    env = os.environ.copy()
    env["DISPLAY"] = display_name
    env["AUREON_REPO"] = str(REPO_ROOT)
    env["CU_MODE"] = mode
    env["CU_PATHS"] = json.dumps(
        {
            "audit": str(tmp_path / "audit.jsonl"),
            "stop": str(tmp_path / "computer_use.stop"),
            "shots": str(tmp_path / "shots"),
        }
    )
    env.pop("AUREON_COMPUTER_USE_STOP_FILE", None)
    launch = (
        "import json, os, sys; "
        "sys.path.insert(0, os.environ['AUREON_REPO']); "
        "from tests.test_computer_use_autonomy import run_xvfb_case; "
        "print(json.dumps(run_xvfb_case(os.environ['CU_MODE'], json.loads(os.environ['CU_PATHS']))))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", launch],
        env=env,
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    return json.loads(completed.stdout)


def _wait_for_log(log_path: Path, predicate, timeout: float = 5) -> str:
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        last = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        if predicate(last):
            return last
        time.sleep(0.05)
    return last


def test_xvfb_click_type_and_screenshot(tmp_path: Path, xvfb_display: str) -> None:
    log_path = tmp_path / "events.log"
    client = _start_client(xvfb_display, log_path, tmp_path / "ready")
    try:
        report = _run_worker(xvfb_display, "direct", tmp_path)
        log = _wait_for_log(log_path, lambda text: "click 55 65" in text and "text HiZ" in text)
    finally:
        os.killpg(client.pid, signal.SIGTERM)
    assert report["click"]["ok"] is True
    assert report["typed"]["ok"] is True
    assert report["core_click"]["status"] != "hold"
    assert report["core_type"]["status"] != "hold"
    assert report["core_shell"]["status"] != "hold"
    assert "core-shell" in report["core_shell"]["stdout"]
    shot = Path(report["shot"]["path"])
    assert shot.read_bytes().startswith(b"\x89PNG")
    with Image.open(shot) as image:
        assert image.format == "PNG"
        assert image.size[0] > 0 and image.size[1] > 0
    assert "click 30 40" in log
    assert "click 55 65" in log
    assert "text HiZ" in log
    lines = [
        json.loads(line)
        for line in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(lines) >= 5
    for line in lines:
        assert {"ts", "action", "args", "result"} <= set(line)


def test_xvfb_loop_clicks_types_and_finishes(tmp_path: Path, xvfb_display: str) -> None:
    log_path = tmp_path / "events.log"
    client = _start_client(xvfb_display, log_path, tmp_path / "ready")
    try:
        report = _run_worker(xvfb_display, "loop", tmp_path)
        log = _wait_for_log(log_path, lambda text: "click 30 40" in text and "text Hi" in text)
    finally:
        os.killpg(client.pid, signal.SIGTERM)
    assert report["text"] == "finished-goal"
    assert report["stopped"] is False
    assert report["saw_function_tools"] is True
    assert "click 30 40" in log
    assert "text Hi" in log
    lines = [json.loads(line) for line in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    actions = [line["action"] for line in lines]
    assert "screenshot" in actions
    assert "click" in actions
    assert "type_text" in actions
    assert any(line.get("screenshot_path") for line in lines if line["action"] == "screenshot")
