"""Read-only health monitor for the local Aureon OS stack.

The monitor checks the launcher's recorded processes, the HTTP seats, log
freshness, ThoughtBus traffic, the generated system registry, and free disk.
It writes ``state/monitor/health.json`` plus a bounded JSONL history and never
publishes to the bus or starts a component.

Run once::

    .venv\\Scripts\\python.exe scripts\\monitor\\aureon_health_monitor.py

Watch (singleton, writes its own pid file)::

    .venv\\Scripts\\python.exe scripts\\monitor\\aureon_health_monitor.py --watch
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state"
MONITOR_DIR = STATE / "monitor"
LAUNCHER_DIR = STATE / "launcher"
LAUNCHER_LOGS = LAUNCHER_DIR / "logs"
FUSION_STATE = ROOT / "aureon_fusion" / "state"
THOUGHTS = ROOT / "thoughts.jsonl"
UNIFIED_BUS = FUSION_STATE / "unified_bus.jsonl"
BRIDGE_LOG = FUSION_STATE / "bus_bridge.log"
REGISTRY = ROOT / "aureon_system_registry.json"
HNC_TRACE = STATE / "hnc_live_trace.jsonl"
HEALTH_JSON = MONITOR_DIR / "health.json"
HISTORY_JSONL = MONITOR_DIR / "monitor.jsonl"
PID_FILE = MONITOR_DIR / "monitor.pid"
CORE_ONLY_FLAG = LAUNCHER_DIR / "core-only"

BUS_WINDOW_SECONDS = 300
TAIL_BYTES = 512 * 1024
HISTORY_MAX_BYTES = 2 * 1024 * 1024
HISTORY_BACKUPS = 2

PAPER_ENV = {
    "AUREON_LIVE_TRADING": "0",
    "AUREON_DISABLE_REAL_ORDERS": "1",
    "AUREON_DISABLE_EXCHANGE_MUTATIONS": "1",
    "AUREON_ORDER_INTENT_PUBLISH": "0",
    "AUREON_UNIFIED_ORDER_EXECUTOR": "0",
    "AUREON_DRY_RUN": "1",
    "AUREON_PLUG_AND_PLAY": "0",
    "AUREON_THOUGHT_BUS_MAX_BYTES": "8388608",
    "AUREON_THOUGHT_BUS_BACKUPS": "2",
    "AUREON_UNIFIED_BUS_MAX_BYTES": "8388608",
}

# name -> (module fragment, URL, log freshness seconds or None)
COMPONENTS: dict[str, tuple[str, str | None, int | None]] = {
    "organ/organism_circulation": ("aureon.core.organism_circulation", "http://127.0.0.1:8799/healthz", None),
    "organ/operator_gateway": ("aureon.operator.operator_server", "http://127.0.0.1:8790/readyz", 900),
    "organ/frontend_vite": ("vite.js", "http://127.0.0.1:5173/", None),
    "organ/unified_market_status": (
        "aureon.exchanges.unified_market_status_server",
        "http://127.0.0.1:8791/api/terminal-state",
        None,
    ),
    "organ/mind_thought_action_hub": (
        "aureon.autonomous.aureon_mind_thought_action_hub",
        "http://127.0.0.1:13002/api/thoughts",
        None,
    ),
    "organ/hnc_core": ("aureon_fusion.hnc_core", None, 300),
    "organ/hnc_live_daemon": ("aureon.core.hnc_live_daemon", None, 900),
    "organ/bus_bridge": ("aureon_fusion.bus_bridge", None, 120),
}

OPTIONAL_COMPONENTS = {"organ/frontend_vite", "organ/mind_thought_action_hub"}


@dataclass
class ComponentCheck:
    name: str
    process: str
    http: str
    log: str
    status: str
    detail: str
    pid: int = 0


@dataclass
class Report:
    generated_at: str
    overall: str
    connectivity: str
    components: list[ComponentCheck] = field(default_factory=list)
    bus: dict[str, Any] = field(default_factory=dict)
    registry: dict[str, Any] = field(default_factory=dict)
    hnc: dict[str, Any] = field(default_factory=dict)
    disk: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    environment: dict[str, str] = field(default_factory=dict)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_pids() -> dict[str, Any]:
    try:
        payload = json.loads((LAUNCHER_DIR / "pids.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _psutil():
    try:
        import psutil  # type: ignore
    except Exception:
        return None
    return psutil


def _check_process(name: str, module: str, record: dict[str, Any]) -> tuple[str, str, int]:
    pid = int(record.get("pid") or 0)
    if pid <= 0:
        return "down", "no recorded pid", 0
    psutil = _psutil()
    if psutil is None:
        return "down", "psutil unavailable", pid
    try:
        process = psutil.Process(pid)
        cmdline = " ".join(process.cmdline())
        cwd = str(Path(process.cwd()).resolve()).casefold()
    except Exception as exc:
        return "down", f"pid {pid} not running ({exc.__class__.__name__})", pid
    recorded_cwd = str(Path(str(record.get("cwd") or ROOT)).resolve()).casefold()
    recorded_repo = str(Path(str(record.get("repo") or ROOT)).resolve()).casefold()
    if module.casefold() not in cmdline.casefold():
        return "down", f"pid {pid} is not {module}", pid
    if recorded_repo != str(ROOT.resolve()).casefold():
        return "down", f"pid {pid} recorded from another checkout", pid
    if cwd != recorded_cwd:
        return "down", f"pid {pid} cwd changed", pid
    return "up", f"pid {pid}", pid


def _http(url: str, timeout: float = 10.0) -> tuple[int, bytes]:
    request = Request(url, headers={"User-Agent": "aureon-health-monitor/1"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return int(response.status), response.read(262144)
    except HTTPError as exc:
        try:
            body = exc.read(262144)
        except Exception:
            body = b""
        return int(exc.code), body
    except (URLError, OSError, TimeoutError) as exc:
        return 0, str(exc).encode("utf-8", "replace")


def _port_open(host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _json_body(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def _check_circulation(code: int, body: dict[str, Any]) -> tuple[str, str]:
    if code != 200:
        return "down", f"HTTP {code}"
    if not body.get("ok") or not body.get("listening"):
        return "down", "seat is not listening"
    connectors = body.get("connectors") or {}
    off = sorted(str(key) for key, value in connectors.items() if not value)
    loops = body.get("loops") or {}
    heard = [key for key, value in loops.items() if value in {"heard", "bound"}]
    if off:
        return "degraded", f"connectors off: {', '.join(off[:4])}"
    if len(heard) < 8:
        return "degraded", f"only {len(heard)} loops heard"
    return "ok", f"{len(heard)} loops heard, {len(connectors)} connectors"


def _check_operator(code: int, body: dict[str, Any]) -> tuple[str, str]:
    if code not in (200, 503):
        return "down", f"HTTP {code}"
    if body.get("ready") is True:
        return "ok", "ready"
    checks = body.get("checks") or {}
    failed = sorted(str(key) for key, value in checks.items() if value is False)
    reason = ", ".join(failed) if failed else "readiness not reported"
    return "degraded", f"not ready: {reason}"


def _check_market(code: int, body: dict[str, Any]) -> tuple[str, str]:
    if code != 200:
        return "down", f"HTTP {code}"
    if not body.get("ok"):
        return "down", "status server not ok"
    if body.get("stale") or not body.get("trading_ready"):
        return "degraded", "trader booting or stale (expected without exchange keys)"
    return "ok", "trader ready"


def _check_mind(code: int, body: dict[str, Any]) -> tuple[str, str]:
    if code != 200:
        return "down", f"HTTP {code}"
    status = str(body.get("status") or "")
    if status != "ready" or not body.get("initialized"):
        return "degraded", f"status={status or 'unknown'} initializing={body.get('initializing')}"
    thoughts = body.get("thoughts") or []
    return "ok", f"ready, {len(thoughts)} recent thoughts"


def _http_status(name: str, url: str) -> tuple[str, str]:
    if name.endswith("frontend_vite"):
        # The dev server can take minutes on a cold or memory-starved host.
        # A bound port with a slow first response is degraded, not down.
        code, raw = _http(url, timeout=20.0)
        if code == 200 and raw:
            return "ok", "HTTP 200"
        if _port_open("127.0.0.1", 5173):
            return "degraded", f"port 5173 listening; HTTP {code or 'timeout'}"
        return "down", f"HTTP {code}" if code else "no answer"
    code, raw = _http(url)
    body = _json_body(raw)
    if name.endswith("organism_circulation"):
        return _check_circulation(code, body)
    if name.endswith("operator_gateway"):
        if code == 404:
            # Older operator processes serve /healthz before /readyz is mounted.
            health_code, health_raw = _http("http://127.0.0.1:8790/healthz")
            if health_code == 200 and _json_body(health_raw).get("ok"):
                return "degraded", "readyz not mounted; healthz ok"
        return _check_operator(code, body)
    if name.endswith("unified_market_status"):
        return _check_market(code, body)
    if name.endswith("mind_thought_action_hub"):
        return _check_mind(code, body)
    return ("ok" if code == 200 else "down"), f"HTTP {code}"


def _log_freshness(name: str, max_age: int | None) -> tuple[str, str]:
    if max_age is None:
        return "skip", "-"
    path = LAUNCHER_LOGS / f"{name.replace('/', '_')}.log"
    try:
        age = max(0.0, time.time() - path.stat().st_mtime)
    except OSError:
        return "stale", "log missing"
    if age > max_age:
        return "stale", f"last line {int(age)}s ago"
    return "fresh", f"{int(age)}s ago"


def _tail_lines(path: Path, max_bytes: int = TAIL_BYTES) -> list[str]:
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - max_bytes))
            raw = handle.read()
    except OSError:
        return []
    lines = raw.decode("utf-8", "replace").splitlines()
    if size > max_bytes and lines:
        lines = lines[1:]
    return lines


def _record_timestamp(record: dict[str, Any]) -> float | None:
    for key in ("ts", "timestamp"):
        value = record.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    raw = record.get("ingress_timestamp") or record.get("generated_at")
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None
    return None


def _bus_file_stats(path: Path, now: float) -> dict[str, Any]:
    records = 0
    recent = 0
    sources: set[str] = set()
    last_ts: float | None = None
    bad = 0
    for line in _tail_lines(path):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except ValueError:
            bad += 1
            continue
        if not isinstance(record, dict):
            continue
        records += 1
        stamp = _record_timestamp(record)
        if stamp is not None:
            if stamp >= now - BUS_WINDOW_SECONDS:
                recent += 1
            if last_ts is None or stamp > last_ts:
                last_ts = stamp
        source = record.get("source") or (record.get("event") or {}).get("source")
        if source:
            sources.add(str(source))
    age = None if last_ts is None else max(0.0, now - last_ts)
    return {
        "records": records,
        "recent": recent,
        "sources": sorted(sources),
        "last_age_seconds": None if age is None else int(age),
        "bad_lines": bad,
    }


def _bus_report(now: float) -> dict[str, Any]:
    thoughts = _bus_file_stats(THOUGHTS, now)
    unified = _bus_file_stats(UNIFIED_BUS, now)
    try:
        bridge_age = max(0.0, now - BRIDGE_LOG.stat().st_mtime)
    except OSError:
        bridge_age = None
    recent = thoughts["recent"] + unified["recent"]
    sources = sorted(set(thoughts["sources"]) | set(unified["sources"]))
    if bridge_age is None or bridge_age > 120:
        status = "down"
        reason = "bus bridge log is missing or stale"
    elif recent == 0:
        status = "degraded"
        reason = f"no bus records in the last {BUS_WINDOW_SECONDS}s"
    elif len(sources) < 2:
        status = "degraded"
        reason = f"only {len(sources)} bus source(s) active"
    else:
        status = "ok"
        reason = "bridge fresh and traffic flowing"
    return {
        "status": status,
        "reason": reason,
        "window_seconds": BUS_WINDOW_SECONDS,
        "recent": recent,
        "sources": sources,
        "thoughts": thoughts,
        "unified": unified,
        "bridge_log_age_seconds": None if bridge_age is None else int(bridge_age),
    }


def _registry_report(now: float) -> dict[str, Any]:
    try:
        payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"status": "degraded", "systems": 0, "reason": "registry missing"}
    except (OSError, ValueError) as exc:
        return {"status": "degraded", "systems": 0, "reason": f"registry unreadable: {exc.__class__.__name__}"}
    total = int(payload.get("total_systems") or 0)
    if not total:
        categories = payload.get("categories") or {}
        total = sum(len((item or {}).get("systems") or []) for item in categories.values())
    try:
        age_days = max(0.0, now - REGISTRY.stat().st_mtime) / 86400
    except OSError:
        age_days = 0.0
    if total < 100:
        return {"status": "degraded", "systems": total, "reason": "registry has too few systems"}
    if age_days > 14:
        return {
            "status": "degraded",
            "systems": total,
            "age_days": round(age_days, 1),
            "reason": "registry is stale",
        }
    return {"status": "ok", "systems": total, "age_days": round(age_days, 2)}


def _hnc_report(now: float) -> dict[str, Any]:
    lines = _tail_lines(HNC_TRACE, 262144)
    for line in reversed(lines):
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if not isinstance(record, dict):
            continue
        stamp = _record_timestamp(record)
        age = None if stamp is None else max(0.0, now - stamp)
        fresh = bool(record.get("freshness_status") == "fresh")
        live = bool(record.get("data_status") == "live")
        status = "ok" if (fresh and live and (age is None or age < 900)) else "degraded"
        return {
            "status": status,
            "data_status": record.get("data_status"),
            "truth_status": record.get("truth_status"),
            "freshness_status": record.get("freshness_status"),
            "age_seconds": None if age is None else int(age),
        }
    return {"status": "degraded", "reason": "no HNC trace record"}


def _disk_report() -> dict[str, Any]:
    usage = shutil.disk_usage(ROOT)
    free_gb = round(usage.free / (1024**3), 2)
    if usage.free < 512 * 1024 * 1024:
        status = "down"
    elif usage.free < 1536 * 1024 * 1024:
        status = "degraded"
    else:
        status = "ok"
    return {"status": status, "free_gb": free_gb, "total_gb": round(usage.total / (1024**3), 1)}


def _append_history(record: dict[str, Any]) -> None:
    MONITOR_DIR.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
    try:
        size = HISTORY_JSONL.stat().st_size
    except OSError:
        size = 0
    if size >= HISTORY_MAX_BYTES:
        for index in range(HISTORY_BACKUPS - 1, 0, -1):
            source = HISTORY_JSONL.with_name(f"{HISTORY_JSONL.name}.{index}")
            target = HISTORY_JSONL.with_name(f"{HISTORY_JSONL.name}.{index + 1}")
            if source.exists():
                try:
                    os.replace(source, target)
                except OSError:
                    pass
        try:
            os.replace(HISTORY_JSONL, HISTORY_JSONL.with_name(f"{HISTORY_JSONL.name}.1"))
        except OSError:
            pass
    with HISTORY_JSONL.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(line)


def _write_report(report: Report) -> None:
    MONITOR_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(asdict(report), indent=2, sort_keys=True) + "\n"
    temporary = HEALTH_JSON.with_name(HEALTH_JSON.name + ".tmp")
    temporary.write_text(payload, encoding="utf-8", newline="\n")
    os.replace(temporary, HEALTH_JSON)
    _append_history(
        {
            "generated_at": report.generated_at,
            "overall": report.overall,
            "connectivity": report.connectivity,
            "components": {item.name: item.status for item in report.components},
            "bus_recent": report.bus.get("recent"),
            "bus_sources": report.bus.get("sources"),
            "free_gb": report.disk.get("free_gb"),
            "warnings": report.warnings,
        }
    )


def _overall_status(
    connectivity: str,
    bus: dict[str, Any],
    registry: dict[str, Any],
    hnc: dict[str, Any],
    disk: dict[str, Any],
    warnings: list[str],
) -> str:
    critical = connectivity == "down" or any(
        item.get("status") == "down" for item in (bus, registry, hnc, disk)
    )
    if critical:
        return "down"
    return "degraded" if warnings else "ok"


def _collect() -> Report:
    now = time.time()
    pids = _load_pids().get("pids") or {}
    components: list[ComponentCheck] = []
    warnings: list[str] = []
    core_only = CORE_ONLY_FLAG.exists()
    for name, (module, url, max_log_age) in COMPONENTS.items():
        if core_only and name in OPTIONAL_COMPONENTS:
            components.append(
                ComponentCheck(
                    name=name,
                    process="skip",
                    http="skip",
                    log="skip",
                    status="skipped",
                    detail="not in core-only profile",
                    pid=None,
                )
            )
            continue
        record = pids.get(name) or {}
        process_state, process_detail, pid = _check_process(name, module, record)
        http_state, http_detail = ("skip", "-")
        if url:
            http_state, http_detail = _http_status(name, url)
        log_state, log_detail = _log_freshness(name, max_log_age)
        if name.endswith("operator_gateway") and log_state == "stale" and http_state in {"ok", "degraded"}:
            # The gateway answers health probes without writing a log line, so
            # a quiet log is not evidence of a fault while HTTP is responsive.
            log_state = "idle"
        status = "ok"
        reasons: list[str] = []
        if process_state != "up":
            status = "down"
            reasons.append(process_detail)
        if http_state == "down":
            status = "down"
            reasons.append(http_detail)
        elif http_state == "degraded" and status != "down":
            status = "degraded"
            reasons.append(http_detail)
        if log_state == "stale" and status != "down":
            status = "degraded"
            reasons.append(f"log {log_detail}")
        detail_parts = [part for part in (process_detail, http_detail, log_detail) if part != "-"]
        detail = "; ".join(detail_parts)
        if not reasons:
            reasons.append(detail)
        if status != "ok":
            warnings.append(f"{name}: {reasons[0]}")
        components.append(
            ComponentCheck(
                name=name,
                process=process_state,
                http=http_state,
                log=log_state,
                status=status,
                detail=detail[:180],
                pid=pid,
            )
        )

    bus = _bus_report(now)
    registry = _registry_report(now)
    hnc = _hnc_report(now)
    disk = _disk_report()
    if bus["status"] != "ok":
        warnings.append(f"bus: {bus['reason']}")
    if registry["status"] != "ok":
        warnings.append(f"registry: {registry.get('reason', 'not ready')}")
    if hnc["status"] != "ok":
        warnings.append(f"hnc: {hnc.get('reason', 'not fresh')}")
    if disk["status"] != "ok":
        warnings.append(f"disk: {disk['free_gb']} GB free")

    active = [item for item in components if item.process != "skip"]
    connectivity = "down" if any(item.process != "up" or item.http == "down" for item in active) else "ok"
    overall = _overall_status(connectivity, bus, registry, hnc, disk, warnings)
    return Report(
        generated_at=_utc_now(),
        overall=overall,
        connectivity=connectivity,
        components=components,
        bus=bus,
        registry=registry,
        hnc=hnc,
        disk=disk,
        warnings=warnings,
        environment={key: os.environ.get(key, "") for key in PAPER_ENV if key in os.environ},
    )


def _short(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 1] + "…"


def _print_report(report: Report, compact: bool = False) -> None:
    active = [item for item in report.components if item.process != "skip"]
    up = sum(1 for item in active if item.process == "up")
    print(f"AUREON HEALTH {report.generated_at}")
    print(
        f"overall={report.overall} connectivity={report.connectivity} "
        f"processes={up}/{len(active)} active disk={report.disk.get('free_gb')}GB free"
    )
    skipped = len(report.components) - len(active)
    if skipped:
        print(f"optional components not selected: {skipped}")
    if not compact:
        print(f"{'component':38s} {'proc':5s} {'http':6s} {'log':7s} {'status':9s} detail")
        print("-" * 112)
        for item in report.components:
            print(
                f"{item.name:38s} {item.process:5s} {item.http:6s} {item.log:7s} "
                f"{item.status:9s} {_short(item.detail, 48)}"
            )
    print(
        f"bus: {report.bus.get('recent', 0)} msgs/{report.bus.get('window_seconds', BUS_WINDOW_SECONDS)}s "
        f"from {len(report.bus.get('sources') or [])} sources; "
        f"bridge_age={report.bus.get('bridge_log_age_seconds')}s"
    )
    print(
        f"registry: {report.registry.get('systems', 0)} systems ({report.registry.get('status')}); "
        f"hnc: {report.hnc.get('status')} data={report.hnc.get('data_status')} "
        f"fresh={report.hnc.get('freshness_status')}"
    )
    if report.warnings:
        print("warnings:")
        for warning in report.warnings:
            print(f"  - {_short(warning, 110)}")
    if report.overall == "ok" and not compact:
        print("all recorded components are connected and interacting.")


def _existing_watch_pid() -> int:
    try:
        pid = int(PID_FILE.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return 0
    if pid <= 0:
        return 0
    psutil = _psutil()
    if psutil is None:
        return pid
    try:
        process = psutil.Process(pid)
        cmdline = " ".join(process.cmdline())
    except Exception:
        return 0
    if "aureon_health_monitor.py" in cmdline and "--watch" in cmdline:
        return pid
    return 0


def run_once(*, write: bool = True, emit_json: bool = False) -> int:
    report = _collect()
    if write:
        _write_report(report)
    if emit_json:
        print(json.dumps(asdict(report), indent=2, sort_keys=True))
    else:
        _print_report(report)
    return 0 if report.overall != "down" else 1


def watch(interval: int, *, quiet: bool = False) -> int:
    existing = _existing_watch_pid()
    if existing:
        print(f"monitor already running as pid {existing}")
        return 0
    MONITOR_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
    try:
        while True:
            report = _collect()
            _write_report(report)
            if not quiet:
                _print_report(report, compact=True)
                sys.stdout.flush()
            time.sleep(max(10, interval))
    except KeyboardInterrupt:
        return 0
    finally:
        try:
            if PID_FILE.read_text(encoding="utf-8").strip() == str(os.getpid()):
                PID_FILE.unlink()
        except OSError:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watch", action="store_true", help="run continuously")
    parser.add_argument("--interval", type=int, default=60, help="seconds between checks in watch mode")
    parser.add_argument("--json", action="store_true", help="print the full report as JSON")
    parser.add_argument("--no-write", action="store_true", help="do not write state/monitor files")
    parser.add_argument("--quiet", action="store_true", help="suppress per-cycle output in watch mode")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if args.watch:
        return watch(args.interval, quiet=args.quiet)
    return run_once(write=not args.no_write, emit_json=args.json)


if __name__ == "__main__":
    raise SystemExit(main())
