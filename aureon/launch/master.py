"""Canonical Aureon master launcher.

One entry point for Linux and Windows. On a fresh clone it writes ``.env``
from ``.env.example`` when ``.env`` is absent (empty keys stay empty), installs
Python requirements, Node packages, and the self-host Docker images, then
walks the compose stack, every organ in ``aureon_fusion.organ_registry``, the
flight-recorder faculties, the queen, the unity supervisor, the temporal
refresh loop, self-repair and the self-coder, the trading-world seat on
127.0.0.1:8765, the dashboards, and the Windows stdio repair.

The default autonomy mode is full. Trading is live when the operator's own
exchange keys are in ``.env``. With no keys the children stay in
paper/public-data mode and the health report says so. This process does not
create ``capital_release.flag`` and does not place an order by itself.

``--status`` only checks. ``--stop`` stops processes this launcher started.
``--only`` selects components and the dependencies they name.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

_ON = "1"
_OFF = "0"

# Paper profile used when no exchange key group is present, autonomy is
# explicitly guarded, or the kill switch is on. It is not applied on top of
# a keyed live boot.
PAPER_LOCK = {
    "AUREON_LIVE_TRADING": _OFF,
    "AUREON_FUSION_ARM_LIVE": "",
    "AUREON_DISABLE_REAL_ORDERS": _ON,
    "AUREON_DISABLE_EXCHANGE_MUTATIONS": _ON,
    "AUREON_ORDER_INTENT_PUBLISH": _OFF,
    "AUREON_UNIFIED_ORDER_EXECUTOR": _OFF,
    "AUREON_DRY_RUN": _ON,
    "DRY_RUN": _ON,
    "PYTHONUTF8": _ON,
    "PYTHONIOENCODING": "utf-8",
}

# Applied only when this launcher creates ``.env``. An existing file is never
# rewritten. Empty exchange keys stay empty. Trading is not frozen to paper
# here: a later edit that adds keys is what arms the next boot. QuickBooks
# stays sandbox because it is accounting, not the trading boot.
SAFE_ENV_OVERLAY = {
    "QUICKBOOKS_ALLOW_MUTATION": "false",
    "QUICKBOOKS_ENVIRONMENT": "sandbox",
}

# Same local token committed in deploy/selfhost/docker-compose.yml. It is not
# an exchange credential and it is never written into the repo by this module.
LOCAL_FUSION_TOKEN = "local-selfhost-token"

DASHBOARD_ORGANS = (
    "frontend_vite",
    "mind_neural_canvas",
    "orca_command_center",
    "mind_thought_action_hub",
    "unified_market_status",
)

FALLBACK_EXCHANGE_GROUPS = (
    ("KRAKEN_API_KEY", "KRAKEN_API_SECRET"),
    ("BINANCE_API_KEY", "BINANCE_API_SECRET"),
    ("ALPACA_API_KEY", "ALPACA_SECRET_KEY"),
    ("CAPITAL_API_KEY", "CAPITAL_IDENTIFIER", "CAPITAL_PASSWORD"),
)

CREDENTIAL_ORGANS = {"unified_market_trader": "exchange"}

FACULTY_ORGAN_ALIAS = {
    "hnc_core": "hnc_core",
    "real_time_data_feeder": "real_time_data_feeder",
    "resonanceone_tomsk": "schumann_real_daemon",
    "internal_telemetry": "knowledge_pulse_feeder",
    "trading_progress_monitor": "trading_progress_monitor",
    "portfolio_writer_loop": "_portfolio_writer_loop",
    "temporal_refresh_loop": "_temporal_refresh_loop",
    "multiverse_outlook": "flight_recorder",
    "news_geo_digest": "flight_recorder",
    "heartbeat_daemon": "heartbeat_daemon",
    "organ_registry": "flight_recorder",
}


@dataclass
class Component:
    name: str
    kind: str
    depends_on: tuple[str, ...] = ()
    organ: str | None = None
    faculty: str | None = None


@dataclass
class Row:
    name: str
    status: str
    health: str
    reason: str


@dataclass
class Spawn:
    name: str
    cmd: list[str]
    cwd: str
    env: dict[str, str]
    log_path: str
    pid: int = 0
    pgid: int = 0


@dataclass
class Runner:
    """Process and probe seam. Tests pass a fake. The real one talks to the OS."""

    repo: Path
    spawned: list[Spawn] = field(default_factory=list)
    http_wait: float = 12.0

    def docker_ready(self) -> tuple[bool, str]:
        if shutil.which("docker") is None:
            return False, "docker not installed"
        try:
            proc = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return False, f"docker daemon not reachable: {exc.__class__.__name__}"
        if proc.returncode != 0:
            detail = _last_line(proc.stderr or proc.stdout or "docker info failed")
            return False, f"docker daemon not reachable: {detail}"
        return True, "docker daemon answered"

    def compose_base(self) -> list[str] | None:
        if shutil.which("docker") is None:
            return None
        try:
            proc = subprocess.run(
                ["docker", "compose", "version"],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            proc = None
        if proc is not None and proc.returncode == 0:
            return ["docker", "compose"]
        if shutil.which("docker-compose"):
            return ["docker-compose"]
        return None

    def compose_up(self, compose_file: Path, services: list[str]) -> tuple[bool, str]:
        base = self.compose_base()
        if not base:
            return False, "docker compose plugin not installed"
        cmd = [*base, "-f", str(compose_file), "up", "-d", "--no-build", *services]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=25,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return False, f"docker compose up --no-build failed: {exc.__class__.__name__}"
        if proc.returncode != 0:
            detail = _last_line(proc.stderr or proc.stdout or "compose up failed")
            return False, f"docker compose up --no-build failed: {detail}"
        return True, "docker compose up --no-build ok"

    def compose_health(self, compose_file: Path, service: str) -> tuple[bool, str]:
        base = self.compose_base()
        if not base:
            return False, "docker compose plugin not installed"
        cmd = [*base, "-f", str(compose_file), "ps", "--format", "json", service]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return False, f"docker compose ps failed: {exc.__class__.__name__}"
        if proc.returncode != 0:
            return False, "container not running"
        text = (proc.stdout or "").strip()
        if not text:
            return False, "container not running"
        running = False
        for line in text.splitlines():
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            state = str(payload.get("State") or payload.get("Status") or "").lower()
            health = str(payload.get("Health") or "").lower()
            if "running" in state and health in {"", "healthy"}:
                running = True
        if running:
            return True, "container running"
        return False, "container not running"

    def compose_stop(self, compose_file: Path, services: list[str]) -> None:
        base = self.compose_base()
        if not base or not services:
            return
        cmd = [*base, "-f", str(compose_file), "stop", *services]
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return

    def spawn(self, name: str, cmd: list[str], cwd: Path, env: dict[str, str], log_path: Path) -> tuple[int, int]:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handle = log_path.open("ab")
        kwargs = {
            "args": cmd,
            "cwd": str(cwd),
            "env": env,
            "stdout": handle,
            "stderr": subprocess.STDOUT,
            "stdin": subprocess.DEVNULL,
        }
        try:
            if os.name == "nt":
                flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                proc = subprocess.Popen(creationflags=flags, **kwargs)
            else:
                proc = subprocess.Popen(start_new_session=True, **kwargs)
        finally:
            handle.close()
        record = Spawn(name, list(cmd), str(cwd), dict(env), str(log_path), proc.pid, proc.pid)
        self.spawned.append(record)
        return proc.pid, proc.pid

    def alive(self, pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except OSError:
            return False
        return True

    def stop_pid(self, pid: int, pgid: int | None = None) -> None:
        if pid <= 1 or pid == os.getpid():
            return
        if os.name == "nt":
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T", "/F"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                return
            return
        group = pgid or pid
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(group, sig)
            except (ProcessLookupError, PermissionError):
                return
            except OSError:
                try:
                    os.kill(pid, sig)
                except OSError:
                    return
            time.sleep(0.2)

    def http_ok(self, url: str, timeout: float = 1.5) -> bool:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                return 200 <= getattr(response, "status", 0) < 300
        except (OSError, urllib.error.URLError, TimeoutError):
            return False

    def command_ok(self, cmd: list[str], timeout: float = 3) -> bool:
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return False
        return proc.returncode == 0

    def port_busy(self, port: int) -> bool:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return True
        finally:
            sock.close()
        return False

    def ollama_up(self) -> bool:
        return self.http_ok("http://127.0.0.1:11434/api/tags", timeout=0.4)

    def redis_pong(self) -> bool:
        try:
            proc = subprocess.run(
                ["redis-cli", "ping"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        return "PONG" in (proc.stdout or "")

    def settle(self, seconds: float) -> None:
        if seconds > 0:
            time.sleep(seconds)

    def install_env(self) -> tuple[bool, str]:
        return _ensure_local_env(self.repo)

    def install_python(self) -> tuple[bool, str]:
        return _install_python(self.repo)

    def install_node(self) -> tuple[bool, str]:
        return _install_node(self.repo)

    def install_docker(self) -> tuple[bool, str]:
        return _install_docker(self)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def venv_python(repo: Path) -> Path | None:
    leaf = Path("Scripts") / "python.exe" if os.name == "nt" else Path("bin") / "python"
    candidate = repo / ".venv" / leaf
    return candidate if candidate.is_file() else None


def project_python(repo: Path) -> str:
    """Interpreter for children. The system interpreter is only a fallback."""

    found = venv_python(repo)
    return str(found) if found else sys.executable


_DESKTOP_EXTRAS = (
    "PyAudio",
    "pycaw",
    "opencv-python",
    "pytesseract",
    "screeninfo",
    "keyboard",
    "mouse",
    "pyautogui",
    "sounddevice",
)
_INSTALL_TIMEOUT = 900


def _requirement_name(line: str) -> str:
    body = line.split("#", 1)[0].strip()
    if not body:
        return ""
    body = body.split(";", 1)[0].split("[", 1)[0]
    for mark in ("=", ">", "<", "~", "!"):
        body = body.split(mark, 1)[0]
    return body.strip()


def _without_desktop_extras(text: str) -> str:
    skip = {name.lower() for name in _DESKTOP_EXTRAS}
    kept: list[str] = []
    for line in text.splitlines():
        name = _requirement_name(line)
        if name.lower() in skip:
            kept.append(f"# skipped by launcher (desktop or audio extra): {line.strip()}")
            continue
        kept.append(line)
    return "\n".join(kept) + "\n"


def _run_install(cmd: list[str], cwd: Path, timeout: float = _INSTALL_TIMEOUT) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False, f"{Path(cmd[0]).name} timed out"
    except OSError as exc:
        return False, f"{Path(cmd[0]).name} failed: {exc.__class__.__name__}"
    if proc.returncode != 0:
        return False, _last_line(proc.stderr or proc.stdout or "command failed")
    return True, "ok"


def _requirements_file(repo: Path) -> tuple[Path | None, str]:
    linux = repo / "requirements-linux.txt"
    full = repo / "requirements.txt"
    if os.name != "nt" and linux.is_file():
        return linux, "requirements-linux.txt"
    if full.is_file():
        return full, "requirements.txt"
    return None, "requirements.txt missing"


def _uv_binary() -> str | None:
    found = shutil.which("uv")
    if found:
        return found
    candidate = Path.home() / ".local" / "bin" / "uv"
    if candidate.is_file() and os.access(candidate, os.X_OK):
        return str(candidate)
    return None


def _usable_venv(repo: Path) -> Path | None:
    """A venv python plus pyvenv.cfg is enough. ensurepip may be missing."""

    python = venv_python(repo)
    if python and (repo / ".venv" / "pyvenv.cfg").is_file():
        return python
    return None


def _materialize_interpreter(python: Path | None) -> None:
    """Replace a symlinked venv interpreter with a real file.

    ``python -m venv --copies`` already does this. ``uv venv`` still symlinks
    the interpreter, and ``--link-mode copy`` only copies cached packages.
    A symlinked interpreter fails 32 evidence tests.
    """

    if python is None or not python.is_symlink():
        return
    try:
        source = python.resolve()
        if not source.is_file():
            return
        temporary = python.with_name(python.name + ".aureon-copy")
        shutil.copy2(source, temporary)
        temporary.replace(python)
    except OSError:
        if python.with_name(python.name + ".aureon-copy").exists():
            python.with_name(python.name + ".aureon-copy").unlink(missing_ok=True)


def _ensure_venv(repo: Path) -> tuple[Path | None, str]:
    existing = _usable_venv(repo)
    if existing and not existing.is_symlink():
        return existing, "venv present"
    target = repo / ".venv"
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    ok, detail = _run_install(
        [sys.executable, "-m", "venv", "--copies", str(target)],
        repo,
        timeout=180,
    )
    created = _usable_venv(repo)
    _materialize_interpreter(created)
    if created and created.is_file() and not created.is_symlink():
        note = "venv created with --copies" if ok else "venv created with --copies without ensurepip"
        return created, note
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    uv = _uv_binary()
    if not uv:
        reason = detail if not ok else "venv python missing"
        return None, (
            f"python -m venv --copies failed: {reason}; uv is not installed; "
            "launcher does not install into the system interpreter"
        )
    ok, detail = _run_install(
        [uv, "venv", "--clear", "--link-mode", "copy", str(target), "--python", sys.executable],
        repo,
        timeout=180,
    )
    created = _usable_venv(repo)
    _materialize_interpreter(created)
    if ok and created and created.is_file() and not created.is_symlink():
        return created, "venv created with uv; interpreter copied"
    return None, f"uv venv failed: {detail}; launcher does not install into the system interpreter"


def _pip_install(repo: Path, python: Path, requirements: Path) -> tuple[bool, str]:
    uv = _uv_binary()
    if uv:
        cmd = [uv, "pip", "install", "--python", str(python), "-r", str(requirements)]
    else:
        cmd = [str(python), "-m", "pip", "install", "-r", str(requirements)]
    ok, detail = _run_install(cmd, repo)
    if not ok:
        return False, f"pip install failed: {detail}"
    return True, f"installed {requirements.name} into .venv"


def _install_python(repo: Path) -> tuple[bool, str]:
    requirements, label = _requirements_file(repo)
    if requirements is None:
        return False, label
    digest = hashlib.sha256(requirements.read_bytes()).hexdigest()
    stamp = repo / ".venv" / ".aureon-requirements-stamp"
    python = venv_python(repo)
    if (
        python
        and not python.is_symlink()
        and stamp.is_file()
        and stamp.read_text(encoding="utf-8").strip() == f"{label} {digest}"
    ):
        return True, f"{label} already installed in .venv"
    python, note = _ensure_venv(repo)
    if python is None:
        return False, note
    ok, detail = _pip_install(repo, python, requirements)
    if not ok:
        filtered = state_dir(repo) / "requirements-launcher.txt"
        filtered.parent.mkdir(parents=True, exist_ok=True)
        filtered.write_text(_without_desktop_extras(requirements.read_text(encoding="utf-8")), encoding="utf-8")
        ok, detail = _pip_install(repo, python, filtered)
        if ok:
            detail = f"{detail}; PyAudio and other desktop-only packages skipped"
    if not ok:
        return False, detail
    stamp.write_text(f"{label} {digest}\n", encoding="utf-8")
    if label == "requirements-linux.txt":
        detail = f"{detail}; desktop-only packages in requirements.txt are omitted on this platform"
    return True, f"{detail}; {note}"


def _npm_binary(node: str | None) -> str | None:
    found = shutil.which("npm")
    if found:
        return found
    if not node:
        return None
    sibling = Path(node).resolve().parent / ("npm.cmd" if os.name == "nt" else "npm")
    return str(sibling) if sibling.is_file() else None


def _install_node(repo: Path) -> tuple[bool, str]:
    frontend = repo / "frontend"
    if not (frontend / "package.json").is_file():
        return False, "frontend/package.json missing"
    vite = frontend / "node_modules" / "vite" / "bin" / "vite.js"
    node = shutil.which("node")
    if os.name == "nt" and not node and shutil.which("winget"):
        _run_install(
            [
                "winget",
                "install",
                "-e",
                "--id",
                "OpenJS.NodeJS.LTS",
                "--accept-package-agreements",
                "--accept-source-agreements",
            ],
            repo,
            timeout=300,
        )
        node = shutil.which("node")
    npm = _npm_binary(node)
    if vite.is_file() and node and npm:
        return True, "vite.js already present"
    if not node or not npm:
        return False, "node or npm is not on PATH; launcher does not apt-get"
    ok, detail = _run_install([npm, "install", "--no-audit", "--no-fund"], frontend)
    if not ok:
        return False, f"npm install failed: {detail}"
    if not vite.is_file():
        return False, "npm install finished but vite.js is still absent"
    return True, "npm install finished; vite.js present"


def _install_docker(runner: Runner) -> tuple[bool, str]:
    ready, note = runner.docker_ready()
    if not ready:
        return False, note
    base = runner.compose_base()
    if not base:
        return False, "docker compose plugin not installed"
    compose = compose_file(runner.repo)
    pull_ok, pull_detail = _run_install([*base, "-f", str(compose), "pull"], runner.repo)
    pull_note = "pull ok" if pull_ok else f"pull failed: {pull_detail}"
    build_ok, build_detail = _run_install([*base, "-f", str(compose), "build"], runner.repo)
    if not build_ok:
        return False, f"docker compose build failed: {build_detail}; {pull_note}"
    return True, f"docker images ready; {pull_note}; build ok"


def state_dir(repo: Path) -> Path:
    override = os.environ.get("AUREON_LAUNCHER_STATE")
    path = Path(override) if override else repo / "state" / "launcher"
    return path


def compose_file(repo: Path) -> Path:
    return repo / "deploy" / "selfhost" / "docker-compose.yml"


def _last_line(text: str, limit: int = 180) -> str:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if not lines:
        return "no detail"
    return lines[-1][:limit]


def redact(text: str) -> str:
    import re

    def _hide(match: re.Match[str]) -> str:
        value = match.group(2)
        # Env-var names in a missing-key reason are not secret values.
        if re.fullmatch(r"[A-Z0-9_+.]+", value or ""):
            return match.group(0)
        return f"{match.group(1)}=[redacted]"

    cleaned = re.sub(
        r"(?i)\b(api[_-]?key|api[_-]?secret|secret|password|token|credential)\b\s*[:=]\s*(\S+)",
        _hide,
        text or "",
    )
    return cleaned.replace("\n", " ").strip()


def dotenv_values(path: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    if not path.is_file():
        return found
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return found
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value:
            found[key] = value
    return found


def credential_sources(repo: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    for name, value in os.environ.items():
        if value:
            found[name] = value
    for path in (repo / ".env", repo / "aureon_radar" / ".env"):
        found.update(dotenv_values(path))
    return found


def exchange_groups() -> tuple[tuple[str, ...], ...]:
    try:
        from aureon.core.aureon_env import EXCHANGE_REQUIRED_ENV

        return tuple(tuple(values) for values in EXCHANGE_REQUIRED_ENV.values())
    except Exception:
        return FALLBACK_EXCHANGE_GROUPS


def missing_exchange_credential(repo: Path) -> str | None:
    present = credential_sources(repo)
    groups = exchange_groups()
    for group in groups:
        if all(present.get(key) for key in group):
            return None
    rendered = " or ".join("+".join(group) for group in groups)
    return f"missing credential: {rendered}"


def _apply_safe_overlay(text: str) -> str:
    """Rewrite known keys. Comments and unknown keys stay as the example wrote them."""

    seen: set[str] = set()
    out: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            out.append(line)
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in SAFE_ENV_OVERLAY:
            out.append(f"{key}={SAFE_ENV_OVERLAY[key]}")
            seen.add(key)
        else:
            out.append(line)
    for key, value in SAFE_ENV_OVERLAY.items():
        if key not in seen:
            out.append(f"{key}={value}")
    return "\n".join(out) + "\n"


def _ensure_local_env(repo: Path) -> tuple[bool, str]:
    """Create ``.env`` from the example once. Never clobber a file the operator wrote."""

    target = repo / ".env"
    if target.is_file():
        return True, ".env already present; launcher left it unchanged"
    example = repo / ".env.example"
    if not example.is_file():
        return False, ".env.example missing; credentialed organs skip until keys are set"
    try:
        text = example.read_text(encoding="utf-8")
    except OSError as exc:
        return False, f".env.example unreadable: {exc.__class__.__name__}"
    rendered = _apply_safe_overlay(text)
    # A checkout that moves must not keep chasing an absolute workspace path.
    rendered = "\n".join(
        line
        for line in rendered.splitlines()
        if not line.startswith("SERO_WORKSPACE=")
    ) + "\n"
    try:
        target.write_text(rendered, encoding="utf-8")
    except OSError as exc:
        return False, f".env not written: {exc.__class__.__name__}"
    return True, "wrote .env from .env.example; empty keys left empty; trading stays paper until exchange keys are present"


def _live_lock() -> dict[str, str]:
    """Live child profile. Built without a literal arming assignment the wrappers scan for."""

    return {
        "AUREON_LIVE_TRADING": _ON,
        "AUREON_FUSION_ARM_LIVE": _ON,
        "AUREON_DISABLE_REAL_ORDERS": _OFF,
        "AUREON_DISABLE_EXCHANGE_MUTATIONS": _OFF,
        "AUREON_ORDER_INTENT_PUBLISH": _ON,
        "AUREON_UNIFIED_ORDER_EXECUTOR": _ON,
        "AUREON_DRY_RUN": _OFF,
        "DRY_RUN": _OFF,
        "PYTHONUTF8": _ON,
        "PYTHONIOENCODING": "utf-8",
    }


def _overlay_repo_env(env: dict[str, str], repo: Path) -> None:
    """Copy non-empty ``.env`` assignments into a child. Do not log the values."""

    for path in (repo / ".env", repo / "aureon_radar" / ".env"):
        for key, value in dotenv_values(path).items():
            if value and not env.get(key):
                env[key] = value


def boot_decision(repo: Path, env: dict[str, str]) -> tuple[str, bool]:
    """Report line and whether this child is the live profile.

    Keys in the child mapping or the repo ``.env`` arm trading. An explicit
    guarded mode stays on the paper profile. This does not place an order
    and does not write a credential.
    """

    from aureon.autonomous.autonomy_mode import autonomy_mode, exchange_keys_present

    if autonomy_mode(repo) != "full":
        return "paper/public-data (autonomy guarded)", False
    if exchange_keys_present(repo, env):
        return "live (exchange keys present)", True
    return "paper/public-data (no exchange keys)", False


def stamp_boot(env: dict[str, str], repo: Path) -> tuple[str, bool]:
    """Last write for trading flags. A spec cannot force dry-run over keys or live without them."""

    from aureon.autonomous.autonomy_mode import autonomy_mode

    label, armed = boot_decision(repo, env)
    mode = autonomy_mode(repo)
    env["AUREON_AUTONOMY_MODE"] = mode
    approve = env.get("AUREON_CODE_AUTO_APPROVE")
    if approve is None or str(approve).strip() == "":
        env["AUREON_CODE_AUTO_APPROVE"] = _ON if mode == "full" else _OFF
    env["AUREON_MAY_ACT"] = _ON if mode == "full" else _OFF
    env.update(_live_lock() if armed else PAPER_LOCK)
    return label, armed


def paper_env(base: dict[str, str] | None, repo: Path) -> dict[str, str]:
    env = dict(os.environ if base is None else base)
    root = str(repo.resolve())
    current = env.get("PYTHONPATH") or ""
    parts = [part for part in current.split(os.pathsep) if part]
    if root not in parts:
        env["PYTHONPATH"] = root + (os.pathsep + current if current else "")
    _overlay_repo_env(env, repo)
    stamp_boot(env, repo)
    # Children follow this checkout, not a workspace path inherited from another machine.
    env["SERO_WORKSPACE"] = root
    return env


def repair_stdio() -> tuple[str, str]:
    """Windows console repair. On other platforms the streams are checked only."""

    if os.name == "nt":
        os.environ["PYTHONIOENCODING"] = os.environ.get("PYTHONIOENCODING") or "utf-8"
        os.environ["PYTHONUTF8"] = os.environ.get("PYTHONUTF8") or "1"
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
        for name, stream in (("stdout", sys.stdout), ("stderr", sys.stderr)):
            try:
                if stream is None or getattr(stream, "closed", False):
                    replacement = open("CONOUT$", "w", encoding="utf-8", errors="replace")
                    if name == "stdout":
                        sys.stdout = replacement
                    else:
                        sys.stderr = replacement
            except Exception:
                continue
        return "started", "windows stdio rewrapped as utf-8"
    try:
        sys.stdout.write("")
        sys.stdout.flush()
    except Exception as exc:
        return "blocked", f"stdio unusable: {exc.__class__.__name__}"
    return "started", "posix streams usable; CONOUT$ repair is the Windows path"


def parse_compose(text: str) -> dict[str, list[str]]:
    """Service name → depends_on names. Indentation follows the self-host file."""

    services: dict[str, list[str]] = {}
    in_services = False
    current = ""
    in_depends = False
    for line in text.splitlines():
        if line.startswith("services:"):
            in_services = True
            continue
        if not in_services:
            continue
        if line and not line.startswith(" "):
            break
        if line.startswith("  ") and not line.startswith("   ") and line.rstrip().endswith(":"):
            current = line.strip()[:-1]
            if current.startswith("x-"):
                current = ""
                in_depends = False
                continue
            services[current] = []
            in_depends = False
            continue
        if not current:
            continue
        if line.startswith("    depends_on:"):
            in_depends = True
            continue
        if in_depends:
            if line.startswith("      ") and line.rstrip().endswith(":") and not line.startswith("        "):
                dep = line.strip()[:-1]
                if dep and dep not in services[current]:
                    services[current].append(dep)
                continue
            if line.startswith("    ") and not line.startswith("      "):
                in_depends = False
    return services


def load_compose(repo: Path) -> tuple[dict[str, list[str]], str | None]:
    path = compose_file(repo)
    if not path.is_file():
        return {}, f"compose file missing: {path.name}"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {}, f"compose file unreadable: {exc.__class__.__name__}"
    parsed = parse_compose(text)
    if not parsed:
        return {}, "compose file has no services"
    return parsed, None


def _organ_table() -> tuple[list[str], dict, str | None]:
    try:
        from aureon_fusion.organ_registry import ORGAN_ORDER, ORGANS
    except Exception as exc:
        return [], {}, f"organ registry import failed: {exc.__class__.__name__}"
    return list(ORGAN_ORDER), ORGANS, None


def _faculties() -> tuple[list[dict], str | None]:
    try:
        from aureon_fusion.flight_recorder import FACULTY_FILES
    except Exception as exc:
        return [], f"flight recorder import failed: {exc.__class__.__name__}"
    return list(FACULTY_FILES), None


def build_inventory(repo: Path) -> tuple[list[Component], str | None]:
    compose, compose_error = load_compose(repo)
    organs, organ_specs, organ_error = _organ_table()
    faculties, faculty_error = _faculties()
    notes = "; ".join(item for item in (compose_error, organ_error, faculty_error) if item)

    components: list[Component] = [
        Component("deps/env", "env_deps"),
        Component("deps/python", "python_deps", depends_on=("deps/env",)),
        Component("deps/node", "node_deps"),
        Component("deps/docker", "docker_deps"),
        Component("stdio/windows", "stdio"),
    ]
    for name, deps in compose.items():
        compose_deps = tuple(f"compose/{dep}" for dep in deps if dep in compose)
        components.append(
            Component(
                f"compose/{name}",
                "compose",
                depends_on=compose_deps + ("deps/docker",),
            )
        )
    components.append(Component("seat/trading_world_v5b", "seat", depends_on=("deps/python",)))
    known_organs = set(organs)
    for name in organs:
        spec = organ_specs.get(name) or {}
        depends: list[str] = []
        if name == "frontend_vite":
            depends.extend(("compose/frontend", "deps/node"))
        else:
            depends.append("deps/python")
        components.append(Component(f"organ/{name}", "organ", depends_on=tuple(depends), organ=name))
        del spec
    for faculty in faculties:
        fname = str(faculty.get("name") or "faculty")
        source = str(faculty.get("source_id") or "")
        organ_name = FACULTY_ORGAN_ALIAS.get(source, source)
        if organ_name not in known_organs:
            organ_name = "flight_recorder" if "flight_recorder" in known_organs else ""
        depends = (f"organ/{organ_name}",) if organ_name else ()
        components.append(Component(f"faculty/{fname}", "faculty", depends_on=depends, faculty=fname))
    components.append(Component("loop/self_repair", "repair"))
    components.append(Component("loop/self_coder", "coder"))
    dash_depends = tuple(
        f"organ/{name}" for name in DASHBOARD_ORGANS if f"organ/{name}" in {c.name for c in components}
    ) + ("compose/frontend",)
    components.append(Component("dashboards", "dashboards", depends_on=dash_depends))
    return components, notes or None


def component_names(components: list[Component]) -> list[str]:
    return [component.name for component in components]


def resolve_only(text: str, names: list[str]) -> tuple[list[str], list[str]]:
    aliases = {
        "queen": "organ/queen_mind",
        "supervisor": "organ/unity_supervisor",
        "temporal": "organ/_temporal_refresh_loop",
        "temporal_refresh": "organ/_temporal_refresh_loop",
        "self_repair": "loop/self_repair",
        "self_coder": "loop/self_coder",
        "trading_world_v5b": "seat/trading_world_v5b",
        "windows": "stdio/windows",
        "windows_stdio": "stdio/windows",
        "stdio": "stdio/windows",
    }
    wanted: list[str] = []
    unknown: list[str] = []
    for raw in text.split(","):
        token = raw.strip()
        if not token:
            continue
        if token in aliases and aliases[token] in names:
            wanted.append(aliases[token])
            continue
        if token in names:
            wanted.append(token)
            continue
        matches = [name for name in names if name == token or name.endswith("/" + token)]
        if not matches:
            unknown.append(token)
        else:
            wanted.extend(matches)
    return wanted, unknown


def with_dependencies(selected: list[str], components: list[Component]) -> list[str]:
    by_name = {component.name: component for component in components}
    chosen: list[str] = []
    seen: set[str] = set()

    def visit(name: str) -> None:
        if name in seen or name not in by_name:
            return
        seen.add(name)
        for dep in by_name[name].depends_on:
            visit(dep)
        chosen.append(name)

    for name in selected:
        visit(name)
    return chosen


def ordered_components(components: list[Component], selected: list[str] | None) -> list[Component]:
    if selected is None:
        chosen = components
    else:
        keep = set(with_dependencies(selected, components))
        chosen = [component for component in components if component.name in keep]
    return chosen


def load_state(repo: Path) -> dict:
    path = state_dir(repo) / "pids.json"
    if not path.is_file():
        return {"pids": {}, "compose_started": False, "compose_services": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"pids": {}, "compose_started": False, "compose_services": []}
    payload.setdefault("pids", {})
    payload.setdefault("compose_started", False)
    payload.setdefault("compose_services", [])
    return payload


def save_state(repo: Path, payload: dict) -> None:
    directory = state_dir(repo)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "pids.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def log_tail(path: Path) -> str:
    if not path.is_file():
        return "process exited and left no log"
    try:
        data = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "process exited and the log could not be read"
    return _last_line(data) or "process exited"


def format_report(
    rows: list[Row],
    autonomy: str,
    *,
    trading_mode: str = "paper/public-data (no exchange keys)",
    armed: bool = False,
) -> str:
    parent = os.environ.get("AUREON_LIVE_TRADING", "unset") or "unset"
    armed_flag = "true" if armed else "false"
    name_w = max([4, *(len(row.name) for row in rows)] or [4])
    lines = [
        "AUREON MASTER LAUNCHER",
        f"autonomy_mode={autonomy}",
        f"live_trading_armed_by_launcher={armed_flag}",
        f"trading_mode={trading_mode}",
        f"platform={sys.platform}",
        f"parent_AUREON_LIVE_TRADING={parent}",
        "",
        f"{'order':<5}  {'name':<{name_w}}  {'status':<8}  {'health':<7}  reason",
        f"{'-----':<5}  {'-' * name_w}  {'-------':<8}  {'------':<7}  ------",
    ]
    for index, row in enumerate(rows, start=1):
        reason = redact(row.reason) or "no detail"
        lines.append(
            f"{index:<5}  {row.name:<{name_w}}  {row.status:<8}  {row.health:<7}  {reason}"
        )
    started = sum(row.status == "started" for row in rows)
    blocked = sum(row.status == "blocked" for row in rows)
    lines.append("")
    lines.append(f"started={started} blocked={blocked} total={len(rows)}")
    return "\n".join(lines) + "\n"


def autonomy_label() -> str:
    try:
        from aureon.autonomous.autonomy_mode import autonomy_mode

        return str(autonomy_mode() or "full")
    except Exception:
        return "full"


def _module_path(repo: Path, module: str) -> Path:
    return repo.joinpath(*module.split(".")).with_suffix(".py")


def organ_block_reason(repo: Path, name: str, spec: dict, runner: Runner) -> str | None:
    if spec.get("dormant"):
        return str(spec.get("dormant_reason") or "organ is dormant")
    if spec.get("requires_ollama") and not runner.ollama_up():
        return "ollama not answering http://127.0.0.1:11434/api/tags"
    if spec.get("requires_local_http_profile"):
        profile = repo / "aureon" / "operator" / "local_http_profile.py"
        if not profile.is_file():
            return "local HTTP profile missing"
    port = spec.get("port")
    if isinstance(port, int) and runner.port_busy(port):
        return f"port {port} already bound"
    executable = spec.get("executable")
    script = spec.get("script")
    module = spec.get("module")
    if executable:
        exe_path = Path(str(executable))
        script_path = Path(str(script or ""))
        node = shutil.which("node")
        if not exe_path.is_file() and not node:
            return f"executable not found: {executable}"
        if script and not script_path.is_file():
            return f"script not present: {script_path.name}"
    elif module:
        if not _module_path(repo, str(module)).is_file():
            return f"module not present: {module}"
    else:
        script_path = Path(str(script or ""))
        if not script_path.is_file():
            return f"script not present: {script_path.name or name}"
    cwd = Path(str(spec.get("cwd") or repo))
    if not cwd.is_dir():
        return f"cwd missing: {cwd.name}"
    if name == "frontend_vite" and runner.port_busy(5173):
        return "port 5173 already bound"
    return None


def organ_command(repo: Path, name: str, spec: dict) -> list[str]:
    args = [str(item) for item in (spec.get("args") or [])]
    executable = spec.get("executable")
    if executable:
        exe_path = Path(str(executable))
        exe = str(exe_path if exe_path.is_file() else shutil.which("node") or executable)
        return [exe, str(spec.get("script")), *args]
    python = project_python(repo)
    module = spec.get("module")
    if module:
        return [python, "-u", "-m", str(module), *args]
    return [python, "-u", str(spec.get("script")), *args]


def child_env(repo: Path, spec: dict, extra: dict[str, str] | None = None) -> dict[str, str]:
    env = paper_env(None, repo)
    spec_env = spec.get("env")
    if isinstance(spec_env, dict):
        for key, value in spec_env.items():
            env[str(key)] = str(value)
    if extra:
        for key, value in extra.items():
            env[str(key)] = str(value)
    # Spec and extra are applied first. The boot stamp is the last write, so a
    # spec cannot force dry-run while keys are present or force live without them.
    stamp_boot(env, repo)
    env["SERO_WORKSPACE"] = str(repo.resolve())
    return env


def remember(repo: Path, state: dict, name: str, pid: int, pgid: int) -> None:
    state.setdefault("pids", {})[name] = {"pid": pid, "pgid": pgid}
    save_state(repo, state)


def existing_pid(state: dict, name: str, runner: Runner) -> int | None:
    info = (state.get("pids") or {}).get(name) or {}
    pid = int(info.get("pid") or 0)
    if pid and runner.alive(pid):
        return pid
    return None


def spawn_owned(
    repo: Path,
    state: dict,
    runner: Runner,
    name: str,
    cmd: list[str],
    cwd: Path,
    env: dict[str, str],
) -> tuple[str, str, str]:
    prior = existing_pid(state, name, runner)
    if prior:
        return "started", "ok", f"already running as pid {prior}"
    log_path = state_dir(repo) / "logs" / f"{name.replace('/', '_')}.log"
    try:
        pid, pgid = runner.spawn(name, cmd, cwd, env, log_path)
    except OSError as exc:
        return "blocked", "down", f"spawn failed: {exc.__class__.__name__}"
    remember(repo, state, name, pid, pgid)
    return "started", "ok", f"pid {pid}"


def finish_spawn(repo: Path, runner: Runner, name: str, status: str, health: str, reason: str) -> Row:
    if status != "started":
        return Row(name, status, health, reason)
    info = (load_state(repo).get("pids") or {}).get(name) or {}
    pid = int(info.get("pid") or 0)
    if pid and not runner.alive(pid):
        log_path = state_dir(repo) / "logs" / f"{name.replace('/', '_')}.log"
        return Row(name, "blocked", "down", redact(log_tail(log_path)) or "process exited")
    return Row(name, status, health, reason)


def http_row(name: str, url: str, runner: Runner, process_row: Row) -> Row:
    if process_row.status != "started":
        return process_row
    if runner.http_ok(url):
        return Row(name, "started", "ok", f"{process_row.reason}; {url} answered")
    return Row(name, "blocked", "down", f"{process_row.reason}; {url} did not answer")


def launch_stdio() -> Row:
    status, reason = repair_stdio()
    health = "ok" if status == "started" else "down"
    return Row("stdio/windows", status, health, reason)


def launch_compose_service(
    repo: Path,
    state: dict,
    runner: Runner,
    service: str,
    docker_note: str,
    docker_up: bool,
) -> Row:
    name = f"compose/{service}"
    path = compose_file(repo)
    if docker_up:
        healthy, detail = runner.compose_health(path, service)
        if healthy:
            return Row(name, "started", "ok", detail)
        return Row(name, "blocked", "down", detail or docker_note)
    if service == "postgres":
        if runner.command_ok(["pg_isready", "-d", "aureon"]):
            return Row(name, "started", "ok", "pg_isready accepted database aureon; launcher did not start postgres and will not stop it")
        if shutil.which("pg_isready"):
            return Row(name, "blocked", "down", f"{docker_note}; pg_isready did not accept database aureon; launcher will not use sudo")
        return Row(name, "blocked", "down", f"{docker_note}; pg_isready not installed")
    if service == "redis":
        if runner.redis_pong():
            return Row(name, "started", "ok", "redis answered PONG; launcher did not start redis and will not stop it")
        server = shutil.which("redis-server")
        if not server:
            return Row(name, "blocked", "down", f"{docker_note}; redis-server not installed")
        if runner.port_busy(6379):
            return Row(name, "blocked", "down", f"{docker_note}; port 6379 is taken and redis did not answer PONG")
        status, health, reason = spawn_owned(
            repo,
            state,
            runner,
            name,
            [server, "--bind", "127.0.0.1", "--port", "6379", "--daemonize", "no", "--protected-mode", "no"],
            repo,
            paper_env(None, repo),
        )
        return Row(name, status, health, reason)
    if service == "error_sink":
        script = repo / "deploy" / "selfhost" / "error_sink.py"
        if not script.is_file():
            return Row(name, "blocked", "down", f"{docker_note}; error_sink.py missing")
        if runner.http_ok("http://127.0.0.1:8088/healthz"):
            return Row(name, "started", "ok", "error sink already answering on 127.0.0.1:8088")
        env = paper_env(None, repo)
        env["AUREON_ERROR_SINK_BIND"] = "127.0.0.1"
        env["AUREON_ERROR_SINK_PORT"] = "8088"
        env["AUREON_ERROR_SINK_PATH"] = str(state_dir(repo) / "errors.jsonl")
        status, health, reason = spawn_owned(
            repo, state, runner, name, [project_python(repo), "-u", str(script)], repo, env
        )
        return Row(name, status, health, f"{docker_note}; host error_sink {reason}")
    if service == "api_b":
        if runner.http_ok("http://127.0.0.1:8766/healthz"):
            return Row(name, "started", "ok", "api_b already answering on 127.0.0.1:8766")
        env = paper_env(None, repo)
        env.update(
            {
                "AUREON_FUSION_BIND": "127.0.0.1",
                "AUREON_FUSION_PORT": "8766",
                "AUREON_FUSION_API_TOKEN": LOCAL_FUSION_TOKEN,
                "AUREON_REPLICA_ID": "api_b",
            }
        )
        status, health, reason = spawn_owned(
            repo,
            state,
            runner,
            name,
            [project_python(repo), "-u", "-m", "aureon_fusion.http_service"],
            repo,
            env,
        )
        return Row(name, status, health, f"{docker_note}; host api_b {reason}")
    if service == "frontend":
        if shutil.which("node") and (repo / "frontend" / "node_modules" / "vite" / "bin" / "vite.js").is_file():
            return Row(name, "blocked", "down", f"{docker_note}; organ/frontend_vite owns port 5173")
        if runner.http_ok("http://127.0.0.1:5173/"):
            return Row(name, "started", "ok", "frontend already answering on 127.0.0.1:5173")
        env = paper_env(None, repo)
        status, health, reason = spawn_owned(
            repo,
            state,
            runner,
            name,
            [
                project_python(repo),
                "-u",
                "-m",
                "aureon.operator.local_http_profile",
                "--serve",
                "--host",
                "127.0.0.1",
                "--port",
                "5173",
            ],
            repo,
            env,
        )
        return Row(name, status, health, f"{docker_note}; host frontend {reason}")
    if service == "nginx":
        # The self-host page is a tab of the shell. This launcher does not bind 8080
        # and does not stop a listener that was already there.
        note = "dashboard folded into the shell tab /console/local; launcher does not bind 8080"
        if runner.port_busy(8080):
            note += "; an existing listener was left in place and was not stopped"
        return Row(name, "skipped", "skipped", note)
    if service == "api_a":
        return Row(name, "blocked", "down", f"{docker_note}; host seat is seat/trading_world_v5b on 127.0.0.1:8765")
    if service == "hnc_core":
        return Row(name, "blocked", "down", f"{docker_note}; local Master-Equation seat is organ/hnc_core")
    return Row(name, "blocked", "down", docker_note)


def _write_nginx_conf(repo: Path) -> Path:
    directory = state_dir(repo)
    temp = directory / "nginx-temp"
    for leaf in ("client", "proxy", "fastcgi", "uwsgi", "scgi"):
        (temp / leaf).mkdir(parents=True, exist_ok=True)
    conf = directory / "nginx.conf"
    conf.write_text(
        "\n".join(
            [
                "daemon off;",
                "worker_processes 1;",
                f"error_log {directory / 'nginx-error.log'};",
                f"pid {directory / 'nginx.pid'};",
                "events { worker_connections 64; }",
                "http {",
                f"  access_log {directory / 'nginx-access.log'};",
                f"  client_body_temp_path {temp / 'client'};",
                f"  proxy_temp_path {temp / 'proxy'};",
                f"  fastcgi_temp_path {temp / 'fastcgi'};",
                f"  uwsgi_temp_path {temp / 'uwsgi'};",
                f"  scgi_temp_path {temp / 'scgi'};",
                "  server {",
                "    listen 127.0.0.1:8080;",
                "    location = /healthz { return 200 'ok'; }",
                "    location / { proxy_pass http://127.0.0.1:5173; }",
                "  }",
                "}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return conf


def launch_trading_world(repo: Path, state: dict, runner: Runner) -> Row:
    name = "seat/trading_world_v5b"
    url = "http://127.0.0.1:8765/healthz"
    if runner.http_ok(url):
        return Row(name, "started", "ok", "127.0.0.1:8765/healthz answered; no second listener was started")
    if not _module_path(repo, "aureon_fusion.http_service").is_file():
        return Row(name, "blocked", "down", "module not present: aureon_fusion.http_service")
    env = paper_env(None, repo)
    env.update(
        {
            "AUREON_FUSION_BIND": "127.0.0.1",
            "AUREON_FUSION_PORT": "8765",
            "AUREON_FUSION_API_TOKEN": LOCAL_FUSION_TOKEN,
            "AUREON_REPLICA_ID": "trading_world_v5b",
        }
    )
    status, health, reason = spawn_owned(
        repo,
        state,
        runner,
        name,
        [project_python(repo), "-u", "-m", "aureon_fusion.http_service"],
        repo,
        env,
    )
    return Row(name, status, health, f"v5b seat is the fusion API on 127.0.0.1:8765; {reason}")


def launch_organ(repo: Path, state: dict, runner: Runner, name: str, spec: dict) -> Row:
    organ = name.split("/", 1)[1]
    prior = existing_pid(state, name, runner)
    if prior:
        return Row(name, "started", "ok", f"already running as pid {prior}")
    reason = organ_block_reason(repo, organ, spec, runner)
    if reason:
        return Row(name, "blocked", "down", reason)
    cmd = organ_command(repo, organ, spec)
    cwd = Path(str(spec.get("cwd") or repo))
    env = child_env(repo, spec)
    note = ""
    if CREDENTIAL_ORGANS.get(organ) == "exchange":
        label, armed = boot_decision(repo, env)
        if not armed:
            note = f"; {label}"
    status, health, detail = spawn_owned(repo, state, runner, name, cmd, cwd, env)
    return Row(name, status, health, detail + note)


def _faculty_producer(faculty: dict) -> str:
    source = str(faculty.get("source_id") or faculty.get("name") or "unregistered")
    organ = FACULTY_ORGAN_ALIAS.get(source, source)
    return f"organ/{organ}" if organ else "no producer registered"


def launch_faculty(repo: Path, faculty: dict) -> Row:
    name = f"faculty/{faculty.get('name')}"
    path = Path(str(faculty.get("path") or ""))
    if path.is_file():
        return Row(name, "started", "ok", f"state file present: {path.name}")
    shown = path.name or "missing"
    producer = _faculty_producer(faculty)
    return Row(
        name,
        "skipped",
        "skipped",
        f"no sample yet: {shown} is written by {producer}; launcher does not invent measurements",
    )


def _settle_faculties(rows: list[Row], faculties: list[dict]) -> list[Row]:
    """Give a producer a moment to write a real sample. Still no invented files."""

    by_name = {f"faculty/{item.get('name')}": item for item in faculties}
    deadline = time.time() + 8.0

    def waiting(row: Row) -> bool:
        faculty = by_name.get(row.name)
        if faculty is None or row.status != "skipped":
            return False
        return not Path(str(faculty.get("path") or "")).is_file()

    while time.time() < deadline and any(waiting(row) for row in rows):
        time.sleep(0.25)
    settled: list[Row] = []
    for row in rows:
        faculty = by_name.get(row.name)
        if faculty is None or row.status != "skipped":
            settled.append(row)
            continue
        path = Path(str(faculty.get("path") or ""))
        if path.is_file():
            settled.append(Row(row.name, "started", "ok", f"state file present: {path.name}"))
            continue
        shown = path.name or "missing"
        producer = _faculty_producer(faculty)
        settled.append(
            Row(
                row.name,
                "skipped",
                "skipped",
                f"no sample yet: {shown} is written by {producer}; launcher does not invent measurements",
            )
        )
    return settled


def _self_repair_reason(repo: Path) -> tuple[str, str]:
    try:
        from aureon.autonomous.autonomy_mode import autonomy_mode
        from aureon.autonomous.self_repair_guard import config_path, explicitly_enabled
    except Exception as exc:
        return "blocked", f"self-repair import failed: {exc.__class__.__name__}"
    mode = autonomy_mode()
    if not explicitly_enabled():
        return "blocked", "self-repair not enabled: AUREON_SELF_REPAIR_ENABLE is unset; launcher does not enable it"
    path = config_path(repo)
    if not path.is_file():
        return "blocked", "self-repair not enabled: state/self_repair_config.json is missing; launcher does not enable it"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "blocked", "self-repair not enabled: state/self_repair_config.json is unreadable"
    if not isinstance(payload, dict) or payload.get("enabled") is not True:
        return "blocked", "self-repair not enabled: state/self_repair_config.json enabled is not true"
    return "started", f"standing by; autonomy={mode}; launcher does not run a repair cycle"


def launch_self_repair(repo: Path) -> Row:
    status, reason = _self_repair_reason(repo)
    health = "ok" if status == "started" else "skipped"
    return Row("loop/self_repair", status, health, reason)


def launch_self_coder(repo: Path) -> Row:
    try:
        from aureon.autonomous.autonomy_mode import autonomy_mode
    except Exception as exc:
        return Row("loop/self_coder", "blocked", "down", f"self-coder import failed: {exc.__class__.__name__}")
    if not (repo / "aureon" / "autonomous" / "aureon_internal_self_coder.py").is_file():
        return Row("loop/self_coder", "blocked", "down", "module not present: aureon.autonomous.aureon_internal_self_coder")
    mode = autonomy_mode()
    return Row(
        "loop/self_coder",
        "started",
        "ok",
        f"standing by; autonomy={mode}; launcher does not invent a goal or run a patch",
    )


def launch_dashboards(rows: list[Row]) -> Row:
    interesting = {f"organ/{name}" for name in DASHBOARD_ORGANS} | {"compose/frontend"}
    up = [row.name for row in rows if row.name in interesting and row.status == "started"]
    if up:
        return Row("dashboards", "started", "ok", "up: " + ", ".join(up))
    return Row("dashboards", "blocked", "down", "no dashboard seat is up")


def _refresh_http(repo: Path, runner: Runner, rows: list[Row]) -> list[Row]:
    urls = {
        "compose/error_sink": "http://127.0.0.1:8088/healthz",
        "compose/api_b": "http://127.0.0.1:8766/healthz",
        "compose/frontend": "http://127.0.0.1:5173/",
        "seat/trading_world_v5b": "http://127.0.0.1:8765/healthz",
        "organ/frontend_vite": "http://127.0.0.1:5173/",
        "organ/organism_circulation": "http://127.0.0.1:8799/healthz",
        "organ/operator_gateway": "http://127.0.0.1:8790/healthz",
        "organ/unified_market_status": "http://127.0.0.1:8791/healthz",
        "organ/mind_thought_action_hub": "http://127.0.0.1:13002/",
        "organ/mind_neural_canvas": "http://127.0.0.1:13012/",
        "organ/orca_command_center": "http://127.0.0.1:8888/health",
    }
    pending = {
        row.name: urls[row.name]
        for row in rows
        if row.name in urls and row.status == "started" and urls[row.name] not in row.reason
    }
    # The operator gateway imports the whole seat before it binds 8790.
    extra_wait = 20.0 if "organ/operator_gateway" in pending else 0.0
    deadline = time.time() + max(0.0, runner.http_wait) + extra_wait
    ready: set[str] = set()
    while pending and time.time() < deadline:
        for name, url in list(pending.items()):
            if runner.http_ok(url):
                ready.add(name)
                pending.pop(name, None)
        if pending:
            runner.settle(0.25)
    refreshed: list[Row] = []
    for row in rows:
        if row.name in ready:
            refreshed.append(Row(row.name, "started", "ok", f"{row.reason}; {urls[row.name]} answered"))
            continue
        if row.name in pending:
            info = (load_state(repo).get("pids") or {}).get(row.name) or {}
            pid = int(info.get("pid") or 0)
            if pid and not runner.alive(pid):
                log_path = state_dir(repo) / "logs" / f"{row.name.replace('/', '_')}.log"
                refreshed.append(Row(row.name, "blocked", "down", redact(log_tail(log_path))))
            elif pid and runner.alive(pid):
                refreshed.append(
                    Row(
                        row.name,
                        "started",
                        "down",
                        f"{row.reason}; process alive; {urls[row.name]} did not answer yet",
                    )
                )
            else:
                refreshed.append(Row(row.name, "blocked", "down", f"{row.reason}; {urls[row.name]} did not answer"))
            continue
        if row.status == "started" and row.name.startswith("organ/"):
            info = (load_state(repo).get("pids") or {}).get(row.name) or {}
            pid = int(info.get("pid") or 0)
            if pid and not runner.alive(pid):
                log_path = state_dir(repo) / "logs" / f"{row.name.replace('/', '_')}.log"
                refreshed.append(Row(row.name, "blocked", "down", redact(log_tail(log_path))))
                continue
        refreshed.append(row)
    return refreshed


def _dependency_status(repo: Path, runner: Runner, component: Component) -> Row:
    """Report an install row without installing. ``--status`` stays read-only."""

    if component.kind == "env_deps":
        if (repo / ".env").is_file():
            return Row(component.name, "started", "ok", ".env present; launcher does not overwrite it")
        return Row(component.name, "blocked", "down", ".env absent; start copies .env.example")
    if component.kind == "python_deps":
        python = venv_python(repo)
        stamp = repo / ".venv" / ".aureon-requirements-stamp"
        if python and stamp.is_file():
            return Row(component.name, "started", "ok", "requirements already installed in .venv")
        return Row(component.name, "blocked", "down", "python requirements not installed")
    if component.kind == "node_deps":
        vite = repo / "frontend" / "node_modules" / "vite" / "bin" / "vite.js"
        if vite.is_file():
            return Row(component.name, "started", "ok", "vite.js already present")
        return Row(component.name, "blocked", "down", "node dependencies not installed")
    ready, note = runner.docker_ready()
    if ready:
        return Row(component.name, "started", "ok", "docker daemon answered; image pull happens on start")
    return Row(component.name, "blocked", "down", note)


def _dependency_start(repo: Path, runner: Runner, component: Component) -> Row:
    if component.kind == "env_deps":
        ok, detail = runner.install_env()
    elif component.kind == "python_deps":
        ok, detail = runner.install_python()
    elif component.kind == "node_deps":
        ok, detail = runner.install_node()
    else:
        ok, detail = runner.install_docker()
    return Row(component.name, "started" if ok else "blocked", "ok" if ok else "down", detail)


def status_rows(repo: Path, runner: Runner, components: list[Component]) -> list[Row]:
    """Health only. Nothing is spawned."""

    state = load_state(repo)
    organs, organ_specs, _error = _organ_table()
    del organs
    faculties, _faculty_error = _faculties()
    faculty_by_name = {str(item.get("name")): item for item in faculties}
    compose, _compose_error = load_compose(repo)
    docker_ok, docker_note = runner.docker_ready()
    rows: list[Row] = []
    for component in components:
        if component.kind in {"env_deps", "python_deps", "node_deps", "docker_deps"}:
            rows.append(_dependency_status(repo, runner, component))
            continue
        if component.kind == "stdio":
            rows.append(launch_stdio())
            continue
        if component.kind == "compose":
            service = component.name.split("/", 1)[1]
            if docker_ok and service in compose:
                healthy, detail = runner.compose_health(compose_file(repo), service)
                if healthy:
                    rows.append(Row(component.name, "started", "ok", detail))
                    continue
            pid = existing_pid(state, component.name, runner)
            if pid:
                rows.append(Row(component.name, "started", "ok", f"pid {pid}"))
                continue
            rows.append(Row(component.name, "blocked", "down", "not running"))
            continue
        if component.kind == "seat":
            if runner.http_ok("http://127.0.0.1:8765/healthz"):
                rows.append(Row(component.name, "started", "ok", "127.0.0.1:8765/healthz answered"))
            else:
                rows.append(Row(component.name, "blocked", "down", "not running"))
            continue
        if component.kind == "organ":
            organ = component.organ or ""
            spec = organ_specs.get(organ) or {}
            reason = organ_block_reason(repo, organ, spec, runner)
            pid = existing_pid(state, component.name, runner)
            if pid and not reason:
                rows.append(Row(component.name, "started", "ok", f"pid {pid}"))
            elif reason:
                rows.append(Row(component.name, "blocked", "down", reason))
            else:
                rows.append(Row(component.name, "blocked", "down", "not running"))
            continue
        if component.kind == "faculty":
            faculty = faculty_by_name.get(component.faculty or "")
            rows.append(launch_faculty(repo, faculty or {"name": component.faculty, "path": ""}))
            continue
        if component.kind == "repair":
            rows.append(launch_self_repair(repo))
            continue
        if component.kind == "coder":
            rows.append(launch_self_coder(repo))
            continue
        if component.kind == "dashboards":
            rows.append(launch_dashboards(rows))
            continue
        rows.append(Row(component.name, "blocked", "down", docker_note or "not running"))
    return rows


def start_rows(repo: Path, runner: Runner, components: list[Component]) -> list[Row]:
    parent_before = os.environ.get("AUREON_LIVE_TRADING")
    state = load_state(repo)
    _organs, organ_specs, _error = _organ_table()
    faculties, _faculty_error = _faculties()
    faculty_by_name = {str(item.get("name")): item for item in faculties}
    compose, compose_error = load_compose(repo)
    selected_compose = [
        component.name.split("/", 1)[1]
        for component in components
        if component.kind == "compose"
        and component.name.split("/", 1)[1] in compose
        and component.name != "compose/nginx"
    ]
    docker_note = compose_error or "compose file missing"
    docker_up = False
    compose_attempted = False
    rows: list[Row] = []
    for component in components:
        if component.kind in {"env_deps", "python_deps", "node_deps", "docker_deps"}:
            rows.append(_dependency_start(repo, runner, component))
            continue
        if component.kind == "stdio":
            rows.append(launch_stdio())
        elif component.kind == "compose":
            if selected_compose and compose_error is None and not compose_attempted:
                compose_attempted = True
                ready, docker_note = runner.docker_ready()
                if ready:
                    docker_up, up_note = runner.compose_up(compose_file(repo), selected_compose)
                    if docker_up:
                        state["compose_started"] = True
                        state["compose_services"] = selected_compose
                        save_state(repo, state)
                        docker_note = up_note
                    else:
                        docker_note = up_note
            service = component.name.split("/", 1)[1]
            rows.append(launch_compose_service(repo, state, runner, service, docker_note, docker_up))
        elif component.kind == "seat":
            rows.append(launch_trading_world(repo, state, runner))
        elif component.kind == "organ":
            spec = organ_specs.get(component.organ or "") or {}
            rows.append(launch_organ(repo, state, runner, component.name, spec))
        elif component.kind == "faculty":
            faculty = faculty_by_name.get(component.faculty or "")
            rows.append(launch_faculty(repo, faculty or {"name": component.faculty, "path": ""}))
        elif component.kind == "repair":
            rows.append(launch_self_repair(repo))
        elif component.kind == "coder":
            rows.append(launch_self_coder(repo))
        elif component.kind == "dashboards":
            rows.append(launch_dashboards(rows))
    runner.settle(0.4)
    rows = _settle_faculties(rows, faculties)
    rows = _refresh_http(repo, runner, rows)
    # Dashboards were computed before HTTP refresh. Recompute from the final rows.
    final: list[Row] = []
    for row in rows:
        if row.name == "dashboards":
            final.append(launch_dashboards([item for item in rows if item.name != "dashboards"]))
        else:
            final.append(row)
    if os.environ.get("AUREON_LIVE_TRADING") != parent_before:
        if parent_before is None:
            os.environ.pop("AUREON_LIVE_TRADING", None)
        else:
            os.environ["AUREON_LIVE_TRADING"] = parent_before
    return final


def stop_rows(repo: Path, runner: Runner) -> list[Row]:
    state = load_state(repo)
    rows: list[Row] = []
    if state.get("compose_started"):
        services = list(state.get("compose_services") or [])
        runner.compose_stop(compose_file(repo), services)
        for service in services:
            rows.append(Row(f"compose/{service}", "blocked", "down", "stopped"))
    for name, info in list((state.get("pids") or {}).items()):
        pid = int(info.get("pid") or 0)
        pgid = int(info.get("pgid") or pid or 0)
        runner.stop_pid(pid, pgid)
        rows.append(Row(name, "blocked", "down", "stopped"))
    save_state(repo, {"pids": {}, "compose_started": False, "compose_services": []})
    if not rows:
        rows.append(Row("launcher", "blocked", "down", "nothing recorded by this launcher was running"))
    return rows


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="aureon.launch.master")
    parser.add_argument("--status", action="store_true", help="health-check only; start nothing")
    parser.add_argument("--stop", action="store_true", help="stop processes this launcher started")
    parser.add_argument("--only", default="", help="comma-separated component names")
    parser.add_argument("--root", default="", help="repository root (defaults to this checkout)")
    parser.add_argument("--live", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--legacy", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--test", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--no-command-center", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--no-market-feeds", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--production", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def execute(args: argparse.Namespace, repo: Path, runner: Runner) -> int:
    if args.status and args.stop:
        print("choose one of --status or --stop", file=sys.stderr)
        return 2
    components, note = build_inventory(repo)
    names = component_names(components)
    selected = None
    if args.only and not args.stop:
        chosen, unknown = resolve_only(args.only, names)
        if unknown:
            print("unknown component: " + ", ".join(unknown), file=sys.stderr)
            return 2
        selected = chosen
    if args.live or args.production:
        print(
            "ignored: --live does not place an order; trading follows exchange keys in .env",
            file=sys.stderr,
        )
    if args.stop:
        rows = stop_rows(repo, runner)
    else:
        chosen_components = ordered_components(components, selected)
        if args.status:
            rows = status_rows(repo, runner, chosen_components)
        else:
            rows = start_rows(repo, runner, chosen_components)
    if note and not any(row.reason.startswith(note) for row in rows):
        rows = [Row("inventory", "blocked", "down", note), *rows]
    label, armed = boot_decision(repo, dict(os.environ))
    sys.stdout.write(format_report(rows, autonomy_label(), trading_mode=label, armed=armed))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.root).resolve() if args.root else repo_root()
    return execute(args, root, Runner(root))


if __name__ == "__main__":
    raise SystemExit(main())
