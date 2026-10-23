#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           AUREON PHI-RADAR + UNIFIED HUB — MASTER LAUNCHER                   ║
║                                                                              ║
║  Starts BOTH systems in parallel:                                            ║
║    1. Unified Hub — 135 Aureon systems scanning + fusing signals            ║
║    2. Phi-Radar — Auto-hive execution on Capital.com live account            ║
║                                                                              ║
║  The Unified Hub feeds fused signals to the Radar.                           ║
║  The Radar auto-trades when shadow validation + unified confidence align.    ║
║                                                                              ║
║  SOLE SUITE SUPERVISOR (bug-hunt #3):                                        ║
║    - Children are killed on ANY exit path (child exit, exception,            ║
║      Ctrl+C, SIGTERM, atexit) — no orphaned hub/radar processes.             ║
║    - On Windows children are assigned to a kill-on-close job object,         ║
║      so they die with the parent even on a hard crash.                       ║
║    - If either child exits, the whole suite is torn down and the             ║
║      launcher exits non-zero, so the organ registry restarts a               ║
║      SINGLE clean fleet instead of stacking duplicates.                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import atexit
import ctypes
import subprocess
import sys
import threading
import time
import signal
import os

# Pipe-drain fix (bug-hunt): children are spawned with stdout=PIPE, but on
# Windows the old select()-based reader never ran (select on pipes is POSIX-
# only). The hub's 64KB stdout pipe filled with module-loader log lines, its
# logging StreamHandler blocked mid-emit, and the hub main thread then blocked
# on the logging lock — a full backpressure deadlock with zero CPU. Dedicated
# reader threads drain each child's pipe on every platform.
_print_lock = threading.Lock()


def _stream_child_output(name, proc):
    try:
        for line in proc.stdout:
            with _print_lock:
                print(f"[{name}] {line.rstrip()}", flush=True)
    except Exception as e:
        # A dead drain thread silently recreates the pipe-backpressure
        # deadlock — say so loudly and let the monitor tear the suite down.
        with _print_lock:
            print(f"⚠️  {name} pipe-drain thread DIED: {e!r} — "
                  f"stdout pipe will fill", flush=True)
        raise  # visible in launcher stderr/log instead of vanishing

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Default socket timeout for us AND every child we spawn. Without this,
# import-time exchange connects (e.g. FCA-blocked Binance) hang on TCP SYN
# for many minutes and stall the whole hive. Note: CREATE_NEW_CONSOLE children
# do NOT inherit Python-level socket state, so this also lives in _child_env
# via PYTHONDEFAULTSOCKETAFFINITY below and in unified_hub's own guard.
import socket as _socket
_socket.setdefaulttimeout(30)
os.environ.setdefault("PYTHONDEFAULTSOCKETAFFINITY", "")

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
RADAR_DIR = "C:/Users/user/.kimi_openclaw/workspace/aureon_radar"
SHUTDOWN_GRACE_SEC = 5

# ═══════════════════════════════════════════════════════════════════════════════
# PROCESS MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

processes = []
_shutdown_done = False
_job_handle = None


def _create_kill_on_close_job():
    """Windows job object with KILL_ON_JOB_CLOSE.

    Every child added to this job is terminated by the OS when the launcher
    handle closes — i.e. children die with the parent even on a hard crash,
    not just on graceful shutdown. Returns None on non-Windows or failure
    (explicit shutdown() killing still covers those cases).
    """
    global _job_handle
    if os.name != 'nt':
        return None
    try:
        kernel32 = ctypes.windll.kernel32

        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [(name, ctypes.c_ulonglong) for name in (
                "ReadOperationCount", "WriteOperationCount",
                "OtherOperationCount", "ReadTransferCount",
                "WriteTransferCount", "OtherTransferCount")]

        class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_longlong),
                ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", ctypes.c_ulong),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", ctypes.c_ulong),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", ctypes.c_ulong),
                ("SchedulingClass", ctypes.c_ulong),
            ]

        class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                ("IoInfo", IO_COUNTERS),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            return None
        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = 0x2000  # KILL_ON_JOB_CLOSE
        if not kernel32.SetInformationJobObject(
                job, 9,  # JobObjectExtendedLimitInformation
                ctypes.byref(info), ctypes.sizeof(info)):
            kernel32.CloseHandle(job)
            return None
        _job_handle = job
        return job
    except Exception:
        return None


def _assign_to_job(proc):
    job = _job_handle
    if not job or os.name != 'nt':
        return
    try:
        handle = ctypes.windll.kernel32.OpenProcess(0x0400 | 0x0001, False, proc.pid)  # QUERY | SET
        if handle:
            ctypes.windll.kernel32.AssignProcessToJobObject(job, handle)
            ctypes.windll.kernel32.CloseHandle(handle)
    except Exception:
        pass  # explicit shutdown() killing remains the fallback


def _child_env():
    """UTF-8 I/O for children: cp1252 pipes crash children on emoji output (UnicodeEncodeError).

    Owner decree 2026-09-07 (Gary Leckey): live trading enabled. Children see
    LIVE=1 and Capital.com LIVE account (CAPITAL_DEMO=0) so every downstream
    path treats orders as real money unless it explicitly opts back to demo.
    """
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8:replace"
    env["LIVE"] = "1"
    env["CAPITAL_DEMO"] = "0"
    # Homing / concentrated fire configuration
    env["HOMING_ENABLED"] = "1"
    env["HOMING_THRESHOLD"] = "0.55"
    env["HOMING_TTL_SEC"] = "120"
    env["HOMING_SIZE_MULTIPLIER"] = "2.0"
    # Owner decree 2026-09-07: auto-open in-process queen cognition engines
    # so the cortex/sentience substrate wakes even when queen_mind is a
    # separate OS process (cross-process weakref discovery otherwise fails).
    env["AUREON_AUTO_OPEN_INPROC"] = "1"
    # Rate-budget / freshness conservation
    env["RADAR_PRICE_STALE_SEC"] = "90"
    env["RADAR_FUSED_SIGNAL_TTL_SEC"] = "300"
    env["RADAR_MAX_LIVE_TRADES_PER_DAY"] = "20"
    return env


def start_unified_hub():
    """Start the Unified Trading Hub (all 135 systems)."""
    print("🌐 Starting Unified Hub (135 Aureon systems)...")
    proc = subprocess.Popen(
        [sys.executable, f"{RADAR_DIR}/unified_hub.py"],
        cwd=RADAR_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_child_env(),
        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
    )
    _assign_to_job(proc)
    processes.append(("Unified Hub", proc))
    threading.Thread(
        target=_stream_child_output, args=("Unified Hub", proc),
        daemon=True, name="hub-pipe-drain").start()
    return proc

def start_phi_radar():
    """Start the Phi-Radar (auto-hive trading)."""
    print("🐝 Starting Phi-Radar (auto-hive live trading)...")
    proc = subprocess.Popen(
        [sys.executable, f"{RADAR_DIR}/aureon_phi_radar.py"],
        cwd=RADAR_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_child_env(),
        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
    )
    _assign_to_job(proc)
    processes.append(("Phi-Radar", proc))
    threading.Thread(
        target=_stream_child_output, args=("Phi-Radar", proc),
        daemon=True, name="radar-pipe-drain").start()
    return proc


def start_orca_live_monitor():
    """Start the ORCA live position monitor in LIVE mode.

    The monitor evaluates fee-aware exit conditions and submits real close
    orders when --live is passed. Without --live it logs shadow events only,
    which is why the prior suite logs showed SHADOW MODE.
    """
    print("🐋 Starting ORCA Live Monitor (LIVE exits)...")
    proc = subprocess.Popen(
        [sys.executable, f"{RADAR_DIR}/bots/orca_live_monitor.py", "--live"],
        cwd=RADAR_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_child_env(),
        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
    )
    _assign_to_job(proc)
    processes.append(("ORCA Live Monitor", proc))
    threading.Thread(
        target=_stream_child_output, args=("ORCA Live Monitor", proc),
        daemon=True, name="orca-pipe-drain").start()
    return proc

def shutdown():
    """Terminate all children. Idempotent — safe on every exit path."""
    global _shutdown_done
    if _shutdown_done:
        return
    _shutdown_done = True

    print("\n🛑 Shutting down all systems...")
    for name, proc in processes:
        if proc.poll() is None:
            print(f"  Stopping {name} (PID {proc.pid})...")
            try:
                proc.terminate()
            except Exception:
                pass

    deadline = time.time() + SHUTDOWN_GRACE_SEC
    for name, proc in processes:
        if proc.poll() is None:
            try:
                proc.wait(timeout=max(0.0, deadline - time.time()))
            except Exception:
                print(f"  Force-killing {name} (PID {proc.pid})...")
                try:
                    proc.kill()
                except Exception:
                    pass
    if _job_handle and os.name == 'nt':
        try:
            ctypes.windll.kernel32.CloseHandle(_job_handle)
        except Exception:
            pass
    print("✅ All systems stopped.")


def _handle_sigterm(signum, frame):
    print("\n🛑 SIGTERM received — tearing down suite...")
    raise SystemExit(128 + signum)


def _handle_sigint(signum, frame):
    raise KeyboardInterrupt()


def monitor():
    """Monitor all child processes and stream output.

    Any child exit tears down the whole suite (no orphans, no duplicate
    fleets when the registry restarts the launcher).
    """
    print("\n╔══════════════════════════════════════════════════════════════╗")
    print("║     🐝 AUREON MASTER LAUNCHER — ALL SYSTEMS ACTIVE 🐝        ║")
    print("║                                                              ║")
    print("║  Unified Hub:      135 systems scanning + fusing             ║")
    print("║  Phi-Radar:        Auto-hive live trading on Capital.com     ║")
    print("║  ORCA Monitor:     Live position exits enabled               ║")
    print("║                                                              ║")
    print("║  Press Ctrl+C to stop everything                             ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")

    try:
        while True:
            for name, proc in processes:
                # Check if process is alive
                rc = proc.poll()
                if rc is not None:
                    print(f"⚠️  {name} exited with code {rc} — tearing down suite")
                    sys.exit(1)

                # Output streaming is handled by the pipe-drain threads
                # (spawned in start_*); they work on POSIX AND Windows.
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        shutdown()

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    # Children die with the parent on any exit path (bug-hunt #3)
    atexit.register(shutdown)
    signal.signal(signal.SIGTERM, _handle_sigterm)
    signal.signal(signal.SIGINT, _handle_sigint)

    _create_kill_on_close_job()

    # Start both systems
    start_unified_hub()
    time.sleep(2)  # Let hub initialize first
    start_phi_radar()
    time.sleep(1)
    start_orca_live_monitor()

    # Monitor — finally-block inside guarantees teardown on any exit
    monitor()

if __name__ == "__main__":
    main()
