#!/usr/bin/env python3
"""
headless_watch.py — Boots ICS headlessly for 330s, logs everything to watch_log.txt.
"""
import os
import sys
import threading
import time
import logging

os.environ["AUREON_VOICE_BACKEND"]    = "brain"
os.environ["AUREON_LLM_PROBE_TIMEOUT_S"] = "3"
os.environ["AUREON_LLM_HEALTH_TIMEOUT_S"] = "2"
os.environ["PYTHONIOENCODING"]        = "utf-8"

# Patch initialize_queen_autonomy BEFORE importing ICS so the sentient loop
# never blocks the boot sequence on exchange connections.
# Must save the original reference first to avoid recursive call.
try:
    import aureon.autonomous.aureon_queen_full_autonomy_enablement as _aqfa
    _orig_init_autonomy = _aqfa.initialize_queen_autonomy

    def _nonblocking_autonomy():
        done = threading.Event()
        def _run():
            try:
                _orig_init_autonomy()
            except Exception:
                pass
            finally:
                done.set()
        t = threading.Thread(target=_run, daemon=True, name="autonomy-init")
        t.start()
        done.wait(timeout=10.0)

    _aqfa.initialize_queen_autonomy = _nonblocking_autonomy
    print("[headless_watch] autonomy-init patched (10s cap)", flush=True)
except Exception as e:
    print(f"[headless_watch] autonomy patch failed (non-fatal): {e}", flush=True)

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)

from aureon.core.integrated_cognitive_system import IntegratedCognitiveSystem

DURATION = 330

def main():
    print("[headless_watch] Booting ICS organism...", flush=True)
    ics = IntegratedCognitiveSystem()

    t_boot = time.time()
    status = ics.boot()
    boot_elapsed = time.time() - t_boot

    alive = sum(1 for v in status.values() if v == "alive")
    total = len(status)
    print(f"[headless_watch] Boot complete in {boot_elapsed:.1f}s: {alive}/{total} subsystems alive.", flush=True)
    for name, st in status.items():
        marker = "+" if st == "alive" else "-"
        if st != "alive":
            print(f"  [{marker}] {name}: {st[:80]}", flush=True)

    ics._start_tick_thread()
    print(f"[headless_watch] Organism running. Observing for {DURATION}s...", flush=True)

    start = time.time()
    while time.time() - start < DURATION:
        elapsed = int(time.time() - start)
        if elapsed % 30 == 0 and elapsed > 0:
            try:
                sl = ics.sentient_loop
                if sl is not None:
                    st = sl.get_status()
                    mood  = st.get("last_mood", "—")
                    cycle = st.get("cycle_count", 0)
                    thots = st.get("thoughts_generated", 0)
                    print(f"[headless_watch] T+{elapsed:03d}s  cycle={cycle}  thoughts={thots}  mood={mood}", flush=True)
            except Exception:
                print(f"[headless_watch] T+{elapsed:03d}s  (alive)", flush=True)
        time.sleep(1)

    print("[headless_watch] 5min window complete — shutting down.", flush=True)
    ics.shutdown()

if __name__ == "__main__":
    main()
