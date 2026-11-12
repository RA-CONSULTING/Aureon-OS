"""One scope for a launcher session.

Children call ``setsid`` and ``setpgid``. That leaves the launcher process
group, so ``os.killpg`` does not reach them. ``PR_SET_PDEATHSIG`` does not
either: the new session is not tied to the parent's death signal.

The session therefore runs in one ``systemd-run --user --scope`` when a
user manager answers, otherwise in one cgroup v2 directory created under
the current cgroup. The kill switch stops that scope. When neither systemd
nor a cgroup is available, the kill switch walks the pid tree from the
session root and signals every descendant, including a child that has
called ``setsid``.
"""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

SCOPE_ENV = "AUREON_LAUNCHER_SCOPE"
CGROUP_ENV = "AUREON_LAUNCHER_CGROUP"
ROOT_ENV = "AUREON_LAUNCHER_ROOT_PID"
INSIDE_ENV = "AUREON_LAUNCHER_INSIDE_SCOPE"
PROBE_ENV = "AUREON_LAUNCHER_SETSID_PROBE"
PROBE_PID_ENV = "AUREON_LAUNCHER_SETSID_PIDFILE"
PROBE_STARTED_ENV = "AUREON_LAUNCHER_PROBE_STARTED"

# A launcher started from inside another launcher's session (for example a
# self-repair pytest spawned by a running organ) must not inherit that
# session's scope, cgroup, root pid or workspace. If it did, it would think it
# is already inside the parent's scope, resolve organ scripts from the parent's
# folder, and its --stop could not find what it started.
INHERITED_SESSION_VARS = (
    SCOPE_ENV,
    CGROUP_ENV,
    ROOT_ENV,
    INSIDE_ENV,
    PROBE_STARTED_ENV,
    "AUREON_LAUNCHER_STATE",
    "SERO_WORKSPACE",
)


def strip_inherited_session(env: dict[str, str]) -> dict[str, str]:
    """Return a copy of env without a parent launcher's session variables."""

    return {key: value for key, value in env.items() if key not in INHERITED_SESSION_VARS}


# Credentials must never reach a test or repair child. Match by pattern, not
# a fixed list, so aliases nobody has listed yet (CAPITAL_API_PASSWORD,
# APCA_API_KEY_ID, BINANCE_SECRET, ...) are caught too.
CREDENTIAL_PREFIXES = ("CAPITAL_", "BINANCE_", "KRAKEN_", "ALPACA_", "APCA_", "COINBASE_")
CREDENTIAL_SUFFIXES = (
    "_KEY",
    "_SECRET",
    "_PASSWORD",
    "_PASSPHRASE",
    "_TOKEN",
    "_KEY_ID",
    "_ACCESS_KEY",
    "_SECRET_KEY",
)


# Any name that carries PASSWORD or TOKEN anywhere (UKDI_GRANT_PASSWORD_FILE,
# GH_TOKEN_RW, ...). "TOKENS" is left alone: AUREON_PHI_CHAT_MAX_TOKENS and
# AUREON_OLLAMA_WEAVER_SHARD_TOKENS are model limits, not secrets.
_CREDENTIAL_WORD = re.compile(r"PASSWORD|TOKEN(?!S)", re.IGNORECASE)


def is_credential_name(name: str) -> bool:
    upper = name.upper()
    if upper.startswith(CREDENTIAL_PREFIXES):
        return True
    if _CREDENTIAL_WORD.search(upper):
        return True
    return upper.endswith(CREDENTIAL_SUFFIXES)


def strip_credentials(env: dict[str, str]) -> dict[str, str]:
    """Return a copy of env without anything that looks like a credential."""

    return {key: value for key, value in env.items() if not is_credential_name(key)}


# Any name with LIVE as its own word part (AUREON_LIVE_TRADING, CONFIRM_LIVE,
# AUREON_ACCEPT_LIVE_RISK, AUREON_SELF_CODER_LIVECODE_URL, ...) is dropped.
# LIVE inside another word is kept: ALIVE (AUREON_LLM_KEEP_ALIVE), DELIVERY,
# OLIVER. The off values below are re-forced afterwards, so names such as
# AUREON_LIVE_TRADING and AUREON_FUSION_ARM_LIVE come back with their off value.
_LIVE_WORD = re.compile(r"(?<![A-Z])LIVE")

# Arming and autonomy switches. Each one is off when unset (checked against
# how it is read), so it is removed rather than given an invented off value.
# Several also match _LIVE_WORD; they are listed so the set stays explicit.
ARMING_ENV_DROP = (
    "AUREON_MAY_ACT",                   # only written by the launcher; never read as on when unset
    "AUREON_ORDER_INTENT_PUBLISH",      # getenv(..., "0")
    "AUREON_UNIFIED_ORDER_EXECUTOR",    # off unless set (launcher _live_lock sets "1")
    "LIVE",                             # getenv("LIVE", "0") == "1"
    "AUREON_LIVE",
    "LIVE_TRADING",
    "LIVE_MODE",
    "REAL_MONEY",
    "CONFIRM_LIVE",                     # must equal "yes"
    "CONFIRM_LIVE_TRADING",
    "AUREON_ACCEPT_LIVE_RISK",
    "AUREON_OPERATOR_ALLOW_LIVE",       # capability_gate: explicit true value only
    "AUREON_GO_LIVE_CLEAR",
    "AUREON_AZYRA_EXECUTE_LIVE",        # _env_bool(..., False)
    "AUREON_AUTOSTART_LIVE_RUNNER",     # truthy only
    "AUREON_DESKTOP_LIVE",
    "AUREON_DESKTOP_AUTO_ARM",
    "AUREON_LOCAL_ACTIONS_ARMED",       # _truthy
    "AUREON_SOUL_ACT",                  # _truthy
    "AUREON_QUEEN_AUTO_PUSH",           # == "1"
    "AUREON_QUEEN_SELF_REBOOT",         # == "1"
    "AUREON_FORCE_ARM",                 # == "1"
    "AUREON_BILLING_CHARGE_ENABLED",    # == "1"; hard boundary in feature_switchboard
    "AUREON_SOVEREIGN_MODE",            # hard boundary in feature_switchboard
    "AUREON_AUTO_APPROVE_LIVE_VOICE",
    "AZYRA_CURRENT_BALANCE_LIVE_APPROVED",
    "EPICENTER_LIVE",                   # must equal "YES"
    "PAPER_MODE",
    "QGITA_PAPER_TRADING",              # unset means paper
    "SIMULATION_MODE",                  # no Python reader; dropped, not forced (real-data-only rule)
    "DEMO_MODE",                        # no Python reader; dropped, not forced (real-data-only rule)
)

# Forced into every test or repair child, after the drops. These are the ones
# where unset would not mean off, or where an explicit off value is the
# contract other launch profiles use (master.PAPER_LOCK, plug_and_play):
# - AUREON_FUSION_ARM_LIVE is armed at "1" (aureon_fusion/http_service.py:39,
#   fleet_launcher.py:46); "" is the off value those profiles use.
# - AUREON_AUTONOMY_MODE unset means full (autonomy_mode.py), so guarded.
# - AUREON_CODE_AUTO_APPROVE unset follows full mode, so "0".
# - AUREON_DRY_RUN unset is read as not dry, so "1".
# - AUREON_DISABLE_LIVE_BACKGROUND_STARTUP is a safety switch the LIVE drop removes.
FORCED_OFF = {
    "PYTHON_DOTENV_DISABLED": "1",
    "AUREON_LIVE_TRADING": "0",
    "AUREON_FUSION_ARM_LIVE": "",
    "AUREON_DISABLE_REAL_ORDERS": "1",
    "AUREON_DISABLE_EXCHANGE_MUTATIONS": "1",
    "AUREON_DISABLE_LIVE_BACKGROUND_STARTUP": "1",
    "AUREON_AUTONOMY_MODE": "guarded",
    "AUREON_CODE_AUTO_APPROVE": "0",
    "AUREON_DRY_RUN": "1",
    "DRY_RUN": "1",
    # A child that imports an organ must not wake the Queen or start another
    # repair loop (aureon_baton_link.py:169 arms only at "1"; the HF guards and
    # mcp/aureon_public force "0").
    "AUREON_ACTIVATE_ON_IMPORT": "0",
    # Generic paper/testnet switches inherited from the live run, set to the
    # safe side. No Python reader parses these today; USE_TESTNET is read as
    # === '1' in scripts/traders/realMoneyTrade.ts:33. SIMULATION_MODE and
    # DEMO_MODE are dropped instead (ARMING_ENV_DROP): forcing them on would
    # run against the real-data-only rule (aureon_baton_link._REAL_DATA_ENV_DEFAULTS).
    "PAPER": "1",
    "PAPER_TRADING": "true",
    "USE_TESTNET": "1",
    # Exchange switches. The credential prefix rule drops them, and each one
    # defaults to the live endpoint when unset, so they are forced back here
    # (after the drop) to the value every reader parses as paper/testnet/dry:
    # .lower() == "true" (alpaca_client.py:161-162, binance_client.py:69-70,
    # kraken_client.py:441, kraken_adapter.py:205) and CAPITAL_DEMO == "1"
    # (capital_client.py:231, aureon_radar/capital_client.py:89).
    "ALPACA_PAPER": "true",
    "ALPACA_DRY_RUN": "true",
    "BINANCE_USE_TESTNET": "true",
    "BINANCE_TESTNET": "true",
    "BINANCE_DRY_RUN": "true",
    "KRAKEN_DRY_RUN": "true",
    "CAPITAL_DEMO": "1",
}


# The launcher's live profile (aureon_runtime_safety.LIVE_RUNTIME_ENV). Its keys
# are read at call time so the list cannot drift; these names are kept here as
# well in case that module cannot be imported. Unset is the safe side for each:
# AUREON_ORDER_AUTHORITY_MODE defaults to "runtime_only" (unified_market_trader),
# the *_ORDER_*AUTHORITY, AUREON_ORDER_TICKET_REQUIRES_EXECUTOR and
# AUREON_RELEASE_STATE names have no env reader outside release checks, and an
# unset AUREON_AUDIT_MODE reads the same as the live profile's "0".
LIVE_PROFILE_DROP = (
    "AUREON_RELEASE_STATE",
    "AUREON_AUDIT_MODE",
    "AUREON_ORDER_AUTHORITY_MODE",
    "AUREON_LLM_ORDER_AUTHORITY",
    "AUREON_COGNITIVE_ORDER_AUTHORITY",
    "AUREON_LLM_ORDER_INTENT_AUTHORITY",
    "AUREON_COGNITIVE_ORDER_INTENT_AUTHORITY",
    "AUREON_ORDER_TICKET_REQUIRES_EXECUTOR",
)


def _live_profile_names() -> frozenset[str]:
    names = set(LIVE_PROFILE_DROP)
    try:  # aureon.core.__init__ is empty and aureon_runtime_safety imports only os/typing
        from aureon.core.aureon_runtime_safety import LIVE_RUNTIME_ENV

        names.update(LIVE_RUNTIME_ENV)
    except Exception:
        pass
    return frozenset(names)


def disarm(env: dict[str, str]) -> dict[str, str]:
    """Copy of env with every arming switch dropped and the off values forced."""

    profile = _live_profile_names()
    cleaned = {
        key: value
        for key, value in env.items()
        if key not in ARMING_ENV_DROP and key not in profile and not _LIVE_WORD.search(key.upper())
    }
    cleaned.update(FORCED_OFF)
    return cleaned


def isolated_child_env(env: dict[str, str]) -> dict[str, str]:
    """Env for a test or repair child spawned from a live process.

    No parent launcher session, no workspace pointer, no credentials, and
    dotenv loading switched off so a .env on disk cannot hand them back.
    Live trading switches are forced off, even if the parent had them on.
    """

    return disarm(strip_credentials(strip_inherited_session(env)))


_UNIT_SAFE = re.compile(r"[^A-Za-z0-9_.-]")
_PROBE_SOURCE = """
import os
import sys
import time

pidfile = sys.argv[1]
child = os.fork()
if child == 0:
    os.setsid()
    payload = str(os.getpid()).encode("ascii")
    fd = os.open(pidfile, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o644)
    try:
        os.write(fd, payload)
    finally:
        os.close(fd)
    while True:
        time.sleep(3600)
while True:
    time.sleep(3600)
"""


def dotenv_disabled() -> bool:
    """True when this process must not open a dotenv file."""

    value = os.environ.get("PYTHON_DOTENV_DISABLED", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _unit_name() -> str:
    token = _UNIT_SAFE.sub("-", f"aureon-launcher-{os.getpid()}-{time.time_ns()}")
    return token[:80]


def _systemd_user_works() -> bool:
    if shutil.which("systemd-run") is None or shutil.which("systemctl") is None:
        return False
    try:
        proc = subprocess.run(
            ["systemctl", "--user", "is-system-running"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    text = f"{proc.stdout or ''} {proc.stderr or ''}"
    if "Failed to connect" in text or "No medium" in text or "not been booted" in text:
        return False
    return proc.returncode in {0, 1}


def _self_cgroup_rel() -> str:
    try:
        text = Path("/proc/self/cgroup").read_text(encoding="utf-8")
    except OSError:
        return ""
    for line in text.splitlines():
        parts = line.split(":", 2)
        if len(parts) == 3 and parts[0] == "0" and parts[1] == "":
            rel = parts[2].strip()
            if rel and not rel.startswith("/"):
                rel = "/" + rel
            return rel
    return ""


def _cgroup_path(rel: str) -> Path | None:
    if not rel.startswith("/"):
        return None
    path = Path("/sys/fs/cgroup") / rel.lstrip("/")
    if path.is_dir():
        return path
    return None


def _owned_scope_dir(path: Path) -> bool:
    """A directory this launcher created, or its systemd scope. Not the parent."""

    try:
        resolved = path.resolve()
        root = Path("/sys/fs/cgroup").resolve()
    except OSError:
        return False
    if resolved == root or root not in resolved.parents:
        return False
    return "aureon-launcher" in resolved.name


def _write_pid(path: Path, pid: int) -> bool:
    try:
        (path / "cgroup.procs").write_text(str(pid), encoding="ascii")
    except OSError:
        return False
    return True


def _try_cgroup(unit: str) -> bool:
    rel = _self_cgroup_rel()
    parent = _cgroup_path(rel) if rel else None
    if parent is None:
        return False
    procs = parent / "cgroup.procs"
    if not os.access(procs, os.W_OK):
        return False
    target = parent / unit
    try:
        target.mkdir(parents=False, exist_ok=False)
    except OSError:
        return False
    if not _write_pid(target, os.getpid()):
        try:
            target.rmdir()
        except OSError:
            pass
        return False
    now = _cgroup_path(_self_cgroup_rel())
    if now is None or now.resolve() != target.resolve():
        return False
    os.environ[CGROUP_ENV] = str(target)
    os.environ[SCOPE_ENV] = unit
    os.environ[INSIDE_ENV] = "1"
    return True


def _try_systemd_reexec(argv: list[str], unit: str) -> bool:
    if not _systemd_user_works():
        return False
    probe = f"{unit}-probe"
    try:
        proc = subprocess.run(
            ["systemd-run", "--user", "--scope", "--collect", "--quiet", f"--unit={probe}", "--", "true"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    if proc.returncode != 0:
        return False
    env = dict(os.environ)
    env[SCOPE_ENV] = unit
    env[INSIDE_ENV] = "1"
    # systemd-run --scope execs the command in place, so this pid stays the
    # session root. Stamping it lets the re-exec'd launcher prove the scope is
    # its own instead of trusting a flag inherited from another launcher.
    env[ROOT_ENV] = str(os.getpid())
    cmd = [
        "systemd-run",
        "--user",
        "--scope",
        "--collect",
        "--quiet",
        f"--unit={unit}",
        "--",
        sys.executable,
        "-m",
        "aureon.launch.master",
        *argv,
    ]
    try:
        os.execvpe(cmd[0], cmd, env)
    except OSError:
        return False
    return False


def _become_subreaper() -> None:
    """Keep exited parents' children on this tree for the pid-tree fallback."""

    try:
        import ctypes

        libc = ctypes.CDLL("libc.so.6", use_errno=True)
        libc.prctl.argtypes = [
            ctypes.c_int,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_ulong,
        ]
        libc.prctl.restype = ctypes.c_int
        libc.prctl(36, 1, 0, 0, 0)
    except Exception:
        return


def _start_setsid_probe() -> None:
    """Spawn one setsid grandchild when the self-test asks for it.

    The grandchild's process group is not the launcher's. The scope kill
    still has to reach it. Production boots leave the variable unset.
    """

    if os.environ.get(PROBE_ENV) != "1":
        return
    if os.environ.get(PROBE_STARTED_ENV) == "1":
        return
    pidfile = os.environ.get(PROBE_PID_ENV, "").strip()
    if not pidfile:
        return
    os.environ[PROBE_STARTED_ENV] = "1"
    try:
        subprocess.Popen(
            [sys.executable, "-c", _PROBE_SOURCE, pidfile],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=False,
        )
    except OSError:
        return


def _finish_inside() -> None:
    os.environ[ROOT_ENV] = str(os.getpid())
    os.environ[INSIDE_ENV] = "1"
    if not os.environ.get(CGROUP_ENV):
        rel = _self_cgroup_rel()
        path = _cgroup_path(rel) if rel else None
        if path is not None and _owned_scope_dir(path):
            os.environ[CGROUP_ENV] = str(path)
    _become_subreaper()
    _start_setsid_probe()


def _is_self_or_ancestor(pid: int) -> bool:
    """True when ``pid`` is this process or one of its parents."""

    if pid <= 1:
        return False
    current = os.getpid()
    seen: set[int] = set()
    while current > 1 and current not in seen:
        if current == pid:
            return True
        seen.add(current)
        current = _ppid(current)
    return False


def inherited_scope_is_ours() -> bool:
    """An inherited INSIDE flag counts only if its root pid is self or an ancestor.

    A launcher started by a process that merely copied another launcher's
    environment (a self-repair pytest, a smoke test) is not inside that
    launcher's scope. Trusting the flag there would publish the parent's
    cgroup, and that nested launcher's --stop could then kill the parent session.
    """

    if os.environ.get(INSIDE_ENV) != "1":
        return False
    try:
        root = int(os.environ.get(ROOT_ENV) or 0)
    except ValueError:
        return False
    return _is_self_or_ancestor(root)


def enter_session(argv: list[str]) -> None:
    """Move this process into the launcher scope. May re-exec."""

    if os.name == "nt":
        os.environ[ROOT_ENV] = str(os.getpid())
        return
    if os.environ.get(INSIDE_ENV) == "1":
        if inherited_scope_is_ours():
            _finish_inside()
            return
        # Someone else's session leaked in through the environment: drop it
        # and set up a scope of our own.
        for key in (SCOPE_ENV, CGROUP_ENV, ROOT_ENV, INSIDE_ENV, PROBE_STARTED_ENV):
            os.environ.pop(key, None)
    unit = os.environ.get(SCOPE_ENV) or _unit_name()
    if _try_systemd_reexec(argv, unit):
        return
    if _try_cgroup(unit):
        _finish_inside()
        return
    os.environ[SCOPE_ENV] = ""
    os.environ[CGROUP_ENV] = ""
    _finish_inside()


def current_session() -> dict[str, str | int]:
    root = os.environ.get(ROOT_ENV) or str(os.getpid())
    try:
        root_pid = int(root)
    except ValueError:
        root_pid = os.getpid()
    return {
        "unit": os.environ.get(SCOPE_ENV, ""),
        "cgroup": os.environ.get(CGROUP_ENV, ""),
        "root_pid": root_pid,
    }


def publish_session(repo: Path) -> None:
    from aureon.launch.master import load_state, save_state

    state = load_state(repo)
    state["session"] = current_session()
    save_state(repo, state)


def _ppid(pid: int) -> int:
    try:
        data = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    end = data.rfind(")")
    if end < 0:
        return 0
    fields = data[end + 2 :].split()
    try:
        return int(fields[1])
    except (IndexError, ValueError):
        return 0


def descendants(root: int) -> set[int]:
    """Pids whose parent chain reaches ``root``, including setsid children."""

    if root <= 1 or not Path("/proc").is_dir():
        return set()
    children: dict[int, list[int]] = {}
    try:
        entries = os.listdir("/proc")
    except OSError:
        return set()
    for entry in entries:
        if not entry.isdigit():
            continue
        pid = int(entry)
        parent = _ppid(pid)
        if parent > 0:
            children.setdefault(parent, []).append(pid)
    found: set[int] = set()
    stack = [root]
    while stack:
        current = stack.pop()
        for child in children.get(current, []):
            if child in found or child == root:
                continue
            found.add(child)
            stack.append(child)
    return found


def _cgroup_pids(path: Path) -> set[int]:
    try:
        text = (path / "cgroup.procs").read_text(encoding="ascii", errors="replace")
    except OSError:
        return set()
    found: set[int] = set()
    for line in text.splitlines():
        line = line.strip()
        if line.isdigit():
            found.add(int(line))
    return found


def _signal(pid: int, sig: int) -> None:
    if pid <= 1 or pid == os.getpid():
        return
    try:
        os.kill(pid, sig)
    except OSError:
        return


def _cgroup_kill(path: Path) -> None:
    if not _owned_scope_dir(path):
        return
    kill_file = path / "cgroup.kill"
    for _ in range(25):
        members = _cgroup_pids(path) - {os.getpid()}
        if not members:
            break
        try:
            kill_file.write_text("1\n", encoding="ascii")
        except OSError:
            for pid in members:
                _signal(pid, signal.SIGKILL)
        for pid in list(members):
            _signal(pid, signal.SIGKILL)
        time.sleep(0.05)
    if not _cgroup_pids(path):
        try:
            path.rmdir()
        except OSError:
            return


def _systemd_kill(unit: str) -> None:
    if not unit or "aureon-launcher" not in unit or not _systemd_user_works():
        return
    scope = unit if unit.endswith(".scope") else f"{unit}.scope"
    try:
        subprocess.run(
            ["systemctl", "--user", "kill", scope, "--kill-whom=all", "--signal=SIGKILL"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return


def kill_session(state: dict) -> dict[str, object]:
    """Stop the recorded scope, then signal any pid-tree stragglers."""

    session = state.get("session") if isinstance(state, dict) else None
    if not isinstance(session, dict):
        return {"methods": [], "root_pid": 0, "cgroup": ""}
    unit = str(session.get("unit") or "")
    cgroup = str(session.get("cgroup") or "")
    try:
        root = int(session.get("root_pid") or 0)
    except (TypeError, ValueError):
        root = 0
    methods: list[str] = []
    if unit and _systemd_user_works():
        _systemd_kill(unit)
        methods.append("systemd")
    cgroup_path = Path(cgroup) if cgroup else None
    if cgroup_path is not None and _owned_scope_dir(cgroup_path):
        _cgroup_kill(cgroup_path)
        methods.append("cgroup")
    pids: set[int] = set()
    if root > 1:
        pids.add(root)
        pids |= descendants(root)
    if cgroup_path is not None and cgroup_path.is_dir():
        pids |= _cgroup_pids(cgroup_path)
    if not methods:
        methods.append("pid-tree")
    elif pids:
        methods.append("pid-tree")
    for pid in pids:
        _signal(pid, signal.SIGKILL)
    return {"methods": methods, "root_pid": root, "cgroup": cgroup}
