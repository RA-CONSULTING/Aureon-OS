"""Model-backed fix step for the Queen's repair loop, wired to her own coding organs.

When the rule-based repair (``aureon_sandbox_self_repair._attempt``) runs out of
proven edits for a failing test, this step asks Aureon's own code-authoring organ
for a minimal unified diff, applies it in the repair checkout behind the same
write guard, and proves it through the same benchmark gate and the no-regression
rule. The originally-red test is the red/green witness: it was red in the baseline
run and must be green after the patch, with no previously-green test turning red.

Honest note on the backend (see HONEST_BACKEND below): Aureon's deterministic
coder is the rule-based ``_attempt`` and the template authors in
``queen_benchmark_gate`` / ``code_architect`` — those write code with no model.
Her organs that author *arbitrary* diffs (``aureon_internal_self_coder`` /
``aureon_internal_patch_loop``) author through her agent-company brain fabric,
whose backend is the local Ollama model she already runs. This step keeps that
local model only as the organ's existing backend; it adds no separate LLM call
and sends nothing off-box. If the organ holds (model not pulled, brain fabric or
HNC forge not ready, no truth-authority bundle) this step skips gracefully.

Off unless AUREON_QUEEN_REPAIR_CODER=1.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

from aureon.autonomous.self_repair_guard import (
    _live_arm_text,
    append_review,
    block_reason_for_patch,
    is_protected_path,
    paths_from_patch,
)

CODER_ENV = "AUREON_QUEEN_REPAIR_CODER"
ATTEMPTS_LOG = Path("state/queen_repair_attempts.jsonl")
MAX_RECORDS = 3
PER_FIX_TIMEOUT_S = 180.0
MAX_DIFF_BYTES = 32 * 1024
HONEST_BACKEND = "aureon_internal_self_coder via her agent-company brain fabric (local Ollama backend)"


def coder_enabled() -> bool:
    return os.environ.get(CODER_ENV, "").strip() == "1"


# ── the diff a candidate fix must respect ───────────────────────────────────
def refuse_reason(root: Path, patch_text: str, targets: list[str]) -> str | None:
    """Refuse a candidate diff. Live-trading flag files are refused in every mode
    (her App.tsx guard stays), as are tests/queen_benchmarks, .env and credentials."""
    all_targets = list(dict.fromkeys([*targets, *paths_from_patch(patch_text)]))
    if not all_targets:
        return "no_target"
    for raw in all_targets:
        rel = raw[2:] if raw.startswith(("a/", "b/")) else raw
        if rel.startswith("tests/queen_benchmarks"):
            return "benchmark_seed_protected"
        name = rel.rsplit("/", 1)[-1]
        if name == ".env" or name.startswith(".env"):
            return "env_file_protected"
        if is_protected_path(rel):
            return "credential_path"
    added = "\n".join(line[1:] for line in patch_text.splitlines()
                      if line.startswith("+") and not line.startswith("+++"))
    if _live_arm_text(added):  # refuse live-trading flags even in full autonomy mode
        return "live_trading_flag"
    return block_reason_for_patch(root, patch_text, all_targets)


# ── her own organ, used only to author a candidate diff ─────────────────────
def build_goal(record: dict[str, Any], research_summary: str = "") -> str:
    goal = (f"Fix the failing test {record.get('test_id','')}. "
            f"Error: {record.get('error','')[:300]}. "
            f"Suspected file: {record.get('suspected_file','')}. "
            "Change only the implementation; keep unrelated behaviour; add no network calls, "
            "secrets, economic actions, deployment, or live-trading flags.")
    if research_summary:
        goal += f" Research notes: {research_summary[:400]}"
    return goal


def source_excerpt(root: Path, rel: str, max_lines: int = 400) -> str:
    try:
        text = (root / rel).read_text(encoding="utf-8")
    except OSError:
        return ""
    lines = text.splitlines()
    return "\n".join(lines[:max_lines])


def _organ_author(root: Path, record: dict[str, Any], goal: str, source: str) -> dict[str, Any]:
    """Ask Aureon's internal self-coder organ for a unified diff. Any hold => skipped."""
    target = record.get("suspected_file", "")
    if not target or not target.endswith(".py"):
        return {"skipped": "no_python_target"}
    test_file = str(record.get("test_id", "")).split("::", 1)[0]
    commands = ((_py(), "-m", "pytest", "-q", "-p", "no:cacheprovider", test_file),) if test_file else ()
    suffix = f"{os.getpid()}_{int(time.time()*1000)}"
    try:
        from aureon.autonomous.aureon_internal_self_coder import (
            InternalSelfCoderHold,
            run_autonomous_self_coding,
        )
    except Exception as exc:  # organ not importable in this runtime
        return {"skipped": f"organ_unavailable:{type(exc).__name__}"}
    try:
        result = run_autonomous_self_coding(
            root=root,
            goal=goal,
            target_path=target,
            test_commands=commands,
            ledger_path=Path(f"state/queen_coder_ledger_{suffix}.json"),
            proposal_path=Path(f"state/queen_coder_proposal_{suffix}.json"),
            evidence_path=Path(f"state/queen_coder_evidence_{suffix}.json"),
        )
    except InternalSelfCoderHold as exc:
        return {"skipped": f"organ_hold:{exc}"}
    except Exception as exc:
        return {"skipped": f"organ_error:{type(exc).__name__}:{exc}"[:200]}
    diff = _extract_proposal_diff(root, Path(f"state/queen_coder_proposal_{suffix}.json")) or result.get("patch_text", "")
    if not diff:
        return {"skipped": "organ_authored_no_diff", "organ_status": result.get("status")}
    return {"diff": diff, "organ_status": result.get("status")}


def _extract_proposal_diff(root: Path, proposal_rel: Path) -> str:
    try:
        data = json.loads((root / proposal_rel).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    items = data if isinstance(data, list) else data.get("pending_proposals") or data.get("proposals") or []
    for item in items if isinstance(items, list) else []:
        patch = (item or {}).get("patch_text") or (item or {}).get("diff")
        if patch and str(patch).strip():
            return str(patch)
    return ""


def _py() -> str:
    import sys
    return sys.executable


# ── logging + bus ───────────────────────────────────────────────────────────
_SECRET_KEYS = {"secret", "token", "authorization", "api_key", "api_secret"}


def log_attempt(root: Path, payload: dict[str, Any]) -> None:
    path = root / ATTEMPTS_LOG
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"ts": time.time(), **{k: v for k, v in payload.items() if k.lower() not in _SECRET_KEYS}}
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, default=str)[:8000] + "\n")


def relay_attempt(summary: dict[str, Any]) -> None:
    try:
        from aureon.core.aureon_baton_link import relay_state
        relay_state("queen.self_repair", "attempt", summary)
    except Exception:
        pass


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, timeout=60)


# ── orchestration: author → guard → apply → gate + no-regression → commit ────
def attempt_model_fixes(
    root: Path,
    records: list[dict[str, Any]],
    *,
    gate: Any,
    architect: Any,
    pytest_fn: Callable[[Path], subprocess.CompletedProcess[str]],
    census_before: dict[str, dict[str, int]],
    red_before: set[str],
    branch: str,
    findings_by_test: dict[str, str] | None = None,
    coder: Callable[[Path, dict[str, Any], str, str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Try the model-backed coder on the top failing records. Returns a report delta.

    ``status`` is 'repaired' with a 'commit' when a diff passes the gate and leaves no
    regression; otherwise 'held' with a reason. Every candidate is logged and relayed.
    """
    coder = coder or _organ_author
    findings_by_test = findings_by_test or {}
    deadline = time.monotonic() + PER_FIX_TIMEOUT_S * MAX_RECORDS
    tried = 0
    for record in records:
        if tried >= MAX_RECORDS or time.monotonic() > deadline:
            break
        test_id = str(record.get("test_id", ""))
        if test_id and test_id not in red_before:
            continue  # only witness-provable targets (red in the baseline run)
        target = record.get("suspected_file", "")
        if not target:
            continue
        tried += 1
        goal = build_goal(record, findings_by_test.get(test_id, ""))
        source = source_excerpt(root, target)
        proposal = coder(root, record, goal, source)
        base = {"test_id": test_id, "target": target, "backend": HONEST_BACKEND, "goal": goal[:300]}
        if "diff" not in proposal:
            entry = {**base, "outcome": "skipped", "reason": proposal.get("skipped", "no_diff")}
            log_attempt(root, entry)
            relay_attempt({**base, "outcome": "skipped", "reason": entry["reason"]})
            continue
        diff = proposal["diff"]
        if len(diff.encode("utf-8", "replace")) > MAX_DIFF_BYTES:
            entry = {**base, "outcome": "refused", "reason": "diff_too_large"}
            log_attempt(root, entry); relay_attempt(entry); continue
        targets = [p[2:] if p.startswith(("a/", "b/")) else p for p in paths_from_patch(diff)]
        refuse = refuse_reason(root, diff, targets)
        if refuse:
            entry = {**base, "outcome": "refused", "reason": refuse, "targets": targets,
                     "diff": diff[:4000], "human_review": True}
            log_attempt(root, entry)
            append_review(root, "human_review_required", reason=refuse, branch=branch,
                          path=",".join(targets), human_review=True, source="queen_repair_coder")
            relay_attempt({**base, "outcome": "refused", "reason": refuse})
            continue
        verdict = _apply_and_prove(root, diff, targets, record, gate=gate, architect=architect,
                                   pytest_fn=pytest_fn, census_before=census_before,
                                   red_before=red_before, branch=branch)
        entry = {**base, "outcome": verdict["outcome"], "reason": verdict.get("reason"),
                 "targets": targets, "diff": diff[:4000],
                 "witness_test": test_id, "regressions": verdict.get("regressions", []),
                 "commit": verdict.get("commit"), "seed_ok": verdict.get("seed_ok")}
        log_attempt(root, entry)
        relay_attempt({**base, "outcome": verdict["outcome"], "reason": verdict.get("reason"),
                       "commit": verdict.get("commit"), "regressions": verdict.get("regressions", [])})
        if verdict["outcome"] == "repaired":
            return {"status": "repaired", "reason": "model_fix_gate_verified", "commit": verdict["commit"],
                    "paths": targets, "path": targets[0] if len(targets) == 1 else "",
                    "witness_test": test_id, "gate": verdict["gate"], "regressions": [],
                    "coder_backend": HONEST_BACKEND}
    return {"status": "held", "reason": "no_model_fix", "coder_backend": HONEST_BACKEND}


def _apply_and_prove(root, diff, targets, record, *, gate, architect, pytest_fn,
                     census_before, red_before, branch) -> dict[str, Any]:
    normalized = diff.rstrip("\n") + "\n"
    with tempfile.NamedTemporaryFile("w", suffix=".patch", delete=False, encoding="utf-8", newline="\n") as fh:
        fh.write(normalized)
        patch_path = fh.name
    try:
        if _git(root, "apply", "--whitespace=nowarn", "--check", patch_path).returncode != 0:
            return {"outcome": "held", "reason": "git_apply_check_failed"}
        if _git(root, "apply", "--whitespace=nowarn", patch_path).returncode != 0:
            return {"outcome": "held", "reason": "git_apply_failed"}
    finally:
        Path(patch_path).unlink(missing_ok=True)

    def revert():
        _git(root, "checkout", "--", *targets)

    after = pytest_fn(root)
    failed_after = gate.failed_nodeids(after.stdout or "")
    regressions = sorted(failed_after - red_before)
    if regressions:
        revert()
        return {"outcome": "held", "reason": "regression", "regressions": regressions}
    witness = str(record.get("test_id", ""))
    if witness in failed_after:  # the target test is still red => not proven
        revert()
        return {"outcome": "held", "reason": "witness_still_red"}
    seed = gate.run_seed_benchmarks(root)
    weak = gate.weakened(census_before, gate.census_tests(root))
    if not seed.get("ok"):
        revert(); return {"outcome": "held", "reason": "seed_benchmarks_failed", "seed_ok": False}
    if weak:
        revert(); return {"outcome": "held", "reason": "test_weakened"}
    _git(root, "add", *targets)
    commit = _git(root, "commit", "-m", "self-repair (model, gate-verified, no regressions): " + ", ".join(targets))
    head = _git(root, "rev-parse", "--short", "HEAD")
    gate_verdict = {"verified": True, "seed_benchmarks": seed, "weakened": [],
                    "witness_red_before": witness in red_before, "witness_green_after": True,
                    "reasons": []}
    append_review(root, "repair_committed", reason="model_fix_gate_verified", branch=branch,
                  path=",".join(targets), commit=(head.stdout or "").strip(), tests_passed=True,
                  verified=True, witness_test=witness, seed_benchmarks=seed, source="queen_repair_coder")
    return {"outcome": "repaired", "commit": (head.stdout or "").strip(), "regressions": [],
            "seed_ok": True, "gate": gate_verdict}
