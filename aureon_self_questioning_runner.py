"""Self-questioning loop runner — supervised organ wrapper (workspace-side).

Drives the upstream aureon.autonomous.aureon_self_questioning_ai engine one
cycle at a time. This wrapper exists because the organ must run from a file
the fusion workstream owns (aureon-os-upstream is strictly read-only):

  * REAL sleep between cycles — the loop waits on time.sleep(), never spins.
  * Cycle isolation: an exception in one cycle is logged and the loop
    continues after a short capped backoff (upstream run_loop lets a single
    bad cycle kill the whole organ).
  * Default interval 600 s — halves the per-cycle cost the benchmark flagged
    (whole-repo self-scan + goal map), keeping the organ meaningful while
    quiet.

Safety posture is inherited from the organ engine itself (safe_mode,
blocked-action wordlist, no order paths); the registry launch env pins
AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1 and AUREON_AUDIT_MODE=1.

CLI:
    python aureon_self_questioning_runner.py [--interval S] [--question Q]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from pathlib import Path

UPSTREAM_ROOT = Path(__file__).resolve().parent / "aureon-os-upstream"
if str(UPSTREAM_ROOT) not in sys.path:
    sys.path.insert(0, str(UPSTREAM_ROOT))

DEFAULT_INTERVAL_S = 600.0
MIN_INTERVAL_S = 60.0
CYCLE_FAILURE_BACKOFF_S = 30.0


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    parser = argparse.ArgumentParser(
        description="Supervised self-questioning loop (real sleeps, cycle isolation).")
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL_S,
                        help="Seconds of real sleep between cycles (default 600).")
    parser.add_argument("--question", action="append",
                        help="Custom question to ask every cycle.")
    args = parser.parse_args(argv)
    interval = max(MIN_INTERVAL_S, float(args.interval))

    from aureon.autonomous.aureon_self_questioning_ai import SelfQuestioningAI

    ai = SelfQuestioningAI()
    print(f"self_questioning runner online: cycle + real sleep {interval:.0f}s",
          flush=True)
    backoff = CYCLE_FAILURE_BACKOFF_S
    while True:
        try:
            cycle = ai.run_cycle(questions=args.question or None)
            backoff = CYCLE_FAILURE_BACKOFF_S
            print(json.dumps({
                "cycle_id": cycle.cycle_id,
                "answer_source": cycle.answer_source,
                "summary": cycle.summary,
                "note_path": cycle.note_path,
            }, ensure_ascii=False), flush=True)
        except KeyboardInterrupt:
            print("self_questioning runner interrupted — exiting.", flush=True)
            return 0
        except Exception as exc:  # one bad cycle must not kill the organ
            print(f"! cycle failed: {exc}", flush=True)
            traceback.print_exc()
            time.sleep(backoff)
            backoff = min(backoff * 2, interval)
            continue
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
