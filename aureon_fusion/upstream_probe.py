"""🔬 UPSTREAM PROBE — bounded import-verify for the upstream census doors.

GAP 3 (54% upstream dormant) build: each upstream major cluster becomes a
census door whose mechanism is THIS probe — a single-module import in an
isolated, suppression-pinned subprocess. Nothing here glob-loads the hub;
reachability is by the Queen's own key only.

Doctrine:
  • AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1 and AUREON_AUDIT_MODE=1 are set
    (setdefault) before any aureon import; socket.setdefaulttimeout(30) is
    pinned; imports execute on a daemon thread with a bounded join so a
    hung import is reported as a timeout and the process still exits.
  • AUDIT instrumentation counts socket connections attempted during the
    import and lists threads the import spawned — import-time network
    storms and thread leaks are reported honestly, never silenced.
  • The upstream tree is READ-ONLY to this process: sys.audit hook blocks
    os.replace/os.remove/renames/open-for-write anywhere under
    AUREON_UPSTREAM (defence in depth on top of the suppression env).
  • --prestub exchanges: before the import, the fusion-side import-
    isolation shim (queen_quantum_frog_shim) pre-stubs the upstream
    exchange clients (kraken/binance) in sys.modules with offline-by-
    construction stand-ins — no socket, no rate limiter. This is the
    door-opening mechanism for modules whose import-time chain reaches
    for live exchanges (queen_quantum_frog: module-level MinerBrain →
    harmonic seed → kraken rate_limiter.wait hang). The real module is
    still the one imported and verified; the stubs are declared in the
    record, never hidden.
  • Fail-closed: any error is reported as ok=False with the honest error
    type; nothing is fabricated.

CLI:
    python -m aureon_fusion.upstream_probe <module> [--timeout N]
        [--prestub exchanges]
        exit 0 = import clean, 3 = import error, 4 = timeout, 2 = usage
"""

import argparse
import importlib
import json
import os
import socket
import sys
import threading
import time
from datetime import datetime, timezone

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
os.environ.setdefault("AUREON_AUDIT_MODE", "1")

socket.setdefaulttimeout(30)

from .paths import AUREON_UPSTREAM, FUSION_STATE  # noqa: E402

if str(AUREON_UPSTREAM) not in sys.path:
    sys.path.insert(0, str(AUREON_UPSTREAM))

PROBE_VERSION = "1.0.0"


class _ImportAudit:
    """Counts network connects and records spawned threads during an import."""

    def __init__(self):
        self.connects: list = []
        self._orig_create_connection = socket.create_connection
        self._orig_socket_connect = socket.socket.connect
        self._lock = threading.Lock()

    def install(self):
        audit = self

        def counted_create_connection(addr, *args, **kwargs):
            with audit._lock:
                audit.connects.append(str(addr))
            return audit._orig_create_connection(addr, *args, **kwargs)

        def counted_connect(sock, addr):
            with audit._lock:
                audit.connects.append(str(addr))
            return audit._orig_socket_connect(sock, addr)

        socket.create_connection = counted_create_connection
        socket.socket.connect = counted_connect

    def restore(self):
        socket.create_connection = self._orig_create_connection
        socket.socket.connect = self._orig_socket_connect


def _install_upstream_write_guard():
    """sys.audit hook: refuse any write/rename/unlink targeting the upstream
    tree. Read-only decree enforced inside the probe process itself.
    EXCEPTION (documented, owner-decree precedent console_utf8 shim):
    upstream modules that open a *.log FileHandler at import time get the
    path transparently redirected into
    aureon_fusion/state/doors/upstream_logs/<relpath> — the module's
    intent (an execution log) is preserved, the read-only tree is not
    touched. Everything else under upstream stays blocked."""
    upstream = os.path.abspath(str(AUREON_UPSTREAM)).lower()
    log_mirror = FUSION_STATE / "doors" / "upstream_logs"

    def _redirect_log(path: str) -> str:
        rel = os.path.relpath(os.path.abspath(path), str(AUREON_UPSTREAM))
        target = log_mirror / rel
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            return path
        return str(target)

    import logging
    orig_file_handler = logging.FileHandler

    def redirected_file_handler(filename, *args, **kwargs):
        try:
            f = os.fspath(filename)
            if isinstance(f, bytes):
                f = f.decode("utf-8", "replace")
            if upstream in os.path.abspath(f).lower() and \
                    os.path.abspath(f).lower().endswith(".log"):
                filename = _redirect_log(f)
        except Exception:
            pass
        return orig_file_handler(filename, *args, **kwargs)

    logging.FileHandler = redirected_file_handler

    def hook(event, args):
        if event not in ("os.remove", "os.rename", "os.replace", "os.rmdir",
                         "os.unlink", "open", "shutil.rmtree"):
            return
        paths = [str(a) for a in args if isinstance(a, (str, bytes, os.PathLike))]
        for p in paths:
            try:
                p = os.fspath(p)
                if isinstance(p, bytes):
                    p = p.decode("utf-8", "replace")
            except TypeError:
                continue
            if event == "open" and (len(args) < 2 or args[1] not in
                                    ("w", "wb", "a", "ab", "x", "xb",
                                     "w+", "wb+", "a+", "ab+", "x+", "xb+")):
                continue
            abspath = os.path.abspath(p).lower()
            # Bytecode caches are the interpreter's mechanical side effect
            # (already present repo-wide from prior imports); content writes
            # under the upstream tree stay blocked.
            if "__pycache__" in abspath and abspath.endswith((".pyc", ".pyo")):
                continue
            if upstream and upstream in abspath:
                raise PermissionError(
                    f"upstream tree is READ-ONLY (decree): blocked {event} {p}")

    sys.addaudithook(hook)


def probe_import(module_name: str, timeout: float = 90.0,
                 prestub: str | None = None) -> dict:
    """Import one module on a daemon thread with a bounded join.
    Returns the honest probe record. Never raises."""
    result: dict = {}
    audit = _ImportAudit()
    threads_before = {t.ident for t in threading.enumerate()}
    gc_before = len(sys.modules)
    prestub_installed: list = []

    def _do_import():
        try:
            t0 = time.monotonic()
            mod = importlib.import_module(module_name)
            result["ok"] = True
            result["import_time_s"] = round(time.monotonic() - t0, 3)
            attrs = [a for a in ("main", "run", "start", "status")
                     if callable(getattr(mod, a, None))]
            result["entrypoints"] = attrs
            result["version"] = getattr(mod, "__version__", None)
        except Exception as exc:  # noqa: BLE001 - the probe reports, never raises
            result["ok"] = False
            result["error_type"] = type(exc).__name__
            result["error"] = str(exc)[:400]

    audit.install()
    try:
        _install_upstream_write_guard()
    except Exception:
        pass
    if prestub == "exchanges":
        try:
            from .queen_quantum_frog_shim import install_exchange_prestubs
            prestub_installed = install_exchange_prestubs()
        except Exception as exc:  # noqa: BLE001 - declared, never hidden
            prestub_installed = [f"<install-failed: {type(exc).__name__}>"]
    try:
        worker = threading.Thread(target=_do_import, daemon=True,
                                  name=f"probe-{module_name}")
        worker.start()
        worker.join(timeout)
        timed_out = worker.is_alive()
    finally:
        audit.restore()

    new_threads = [t.name for t in threading.enumerate()
                   if t.ident not in threads_before and t.is_alive()]
    record = {
        "probe_version": PROBE_VERSION,
        "ts": datetime.now(timezone.utc).isoformat(),
        "module": module_name,
        "ok": bool(result.get("ok")) and not timed_out,
        "timed_out": timed_out,
        "timeout_s": timeout,
        "suppression_env": {
            "AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS":
                os.environ.get("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS"),
            "AUREON_AUDIT_MODE": os.environ.get("AUREON_AUDIT_MODE"),
        },
        "socket_default_timeout": socket.getdefaulttimeout(),
        "modules_loaded": len(sys.modules) - gc_before,
        "threads_spawned": new_threads[:20],
        "connects_attempted": audit.connects[:20],
        "connects_count": len(audit.connects),
        "prestub": prestub,
        "prestub_modules": prestub_installed,
    }
    for key in ("import_time_s", "entrypoints", "version", "error_type",
                "error"):
        if key in result:
            record[key] = result[key]
    if timed_out:
        record["error_type"] = "ProbeTimeout"
        record["error"] = (f"import did not finish within {timeout}s "
                           f"(daemon thread abandoned; process exits)")
    return record


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    parser = argparse.ArgumentParser(prog="aureon_fusion.upstream_probe")
    parser.add_argument("module", help="dotted module name under aureon.*")
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--prestub", choices=("exchanges",), default=None,
                        help="pre-stub upstream exchange clients offline "
                             "before import (import-isolation shim)")
    args = parser.parse_args(argv)
    record = probe_import(args.module, timeout=args.timeout,
                          prestub=args.prestub)
    # Sentinel: noisy upstream modules print banners at import; the JSON the
    # driver parses starts on the line AFTER this marker.
    print("__AUREON_PROBE_JSON__")
    print(json.dumps(record, indent=2, ensure_ascii=False))
    if record["ok"]:
        return 0
    return 4 if record.get("timed_out") else 3


if __name__ == "__main__":
    sys.exit(main())
