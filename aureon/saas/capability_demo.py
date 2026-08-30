"""
Aureon OS — capability demonstration ("prove it in one command").
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

One command that lets an end-user / investor / researcher verify the whole system works — not by
reading a stack of markdown, but by booting the real operator app once and exercising the full
capability surface in front of them, then rolling every existing self-test into one honest artifact.

What it does, in one booted ``create_app()`` (offline-safe, read-only, nothing armed):

  * **Live capability exercises** through the app's test client, grouped into investor-legible classes —
    Reasoning (``POST /api/cognition/reason``), Operator + conscience (``POST /api/operator/respond``),
    MCP boundary end-to-end (``GET /mcp/tools`` → ``POST /mcp/call`` with a read-only tool),
    Connections / providers (``POST …/test`` probes), the full SaaS telemetry GET surface, and the
    frontend↔backend parity check. Each exercise is classified ``ok`` / ``honest_unavailable`` (a
    configured-off feature, not a bug) / ``fault`` (500 / crash / HTML where JSON is due).
  * **Rolled-up self-tests** — the SaaS compliance audit (provenance + truth_status + catalog + the
    money-gate), the MCP transport membrane self-test (laminar / tamper-detected), the repo-wide
    coverage audit (every ``aureon/`` package covered), and the 45 Tier-A architectural invariants.

Honest by construction: an offline / unconfigured capability reports ``honest_unavailable`` with a
declared reason — never a fabricated value and never a silent ``fault``. Read-only by construction: the
harness only GETs and issues safe POSTs that are themselves read-only or dry by design; it never flips a
flag, records an approval, arms a local action, moves money, or places a trade. The report is
byte-identical on rerun (no wall-clock in the artifact).

CLI: ``python -m aureon.saas.capability_demo [--report OUT.md] [--report-json OUT.json] [--json]
[--fast]`` — exit 0 iff every capability class is proven, every rolled-up suite is green, coverage is
complete, and all 45 Tier-A invariants pass. ``--fast`` reads the committed Tier-A ``report.json`` instead
of re-running the 45 benchmarks live.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

import importlib.util
import json
import logging
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

from aureon.saas.connection_verifier import _classify, verify_frontend_parity, verify_surface

logger = logging.getLogger("aureon.saas.capability_demo")

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Small classes list every exercise; large sweeps (the SaaS surface) summarise counts + list only the
# non-ok rows, so the artifact stays readable.
_DETAIL_MAX = 6


def _build_app() -> Any:
    """Boot the operator app in-process (offline-safe). Raises on failure — the caller decides."""
    from aureon.operator.operator_server import create_app

    return create_app()


def _exercise(client: Any, method: str, path: str,
              json_body: Dict[str, Any] | None = None) -> Tuple[Dict[str, Any], Any]:
    """Issue one request and classify it. Returns (row, payload); a crash IS a fault, recorded not raised."""
    try:
        resp = client.open(path, method=method, json=json_body)
        payload = resp.get_json(silent=True)
        status, reason = _classify(resp.status_code, payload)
        row = {"path": path, "method": method, "status": status, "code": resp.status_code, "reason": reason}
        return row, payload
    except Exception as exc:  # noqa: BLE001 - a crash IS a fault, recorded not raised
        row = {"path": path, "method": method, "status": "fault", "code": 0,
               "reason": f"exception: {exc}"[:200]}
        return row, None


def _class(name: str, exercised: List[Dict[str, Any]], proven: bool,
           summary: str = "") -> Dict[str, Any]:
    return {"name": name, "exercised": exercised, "proven": bool(proven), "summary": summary}


def _no_fault(rows: List[Dict[str, Any]]) -> bool:
    return all(r["status"] != "fault" for r in rows)


# ── Live capability exercises ─────────────────────────────────────────────────────────────────────

def _exercise_reasoning(client: Any) -> Dict[str, Any]:
    """Grounded cognition round-trip: the system reasons about a prompt and returns a structured answer."""
    row, payload = _exercise(client, "POST", "/api/cognition/reason",
                             {"prompt": "In one line, what does Aureon OS do?"})
    if row["status"] == "ok" and isinstance(payload, dict):
        row["reason"] = "returned a structured reasoning result"
    return _class("Reasoning", [row], row["status"] in ("ok", "honest_unavailable"),
                  "grounded cognition answers a prompt (POST /api/cognition/reason)")


def _exercise_operator(client: Any) -> Dict[str, Any]:
    """Operator + conscience: a one-shot answer that carries the veto / reply-containment envelope."""
    row, payload = _exercise(client, "POST", "/api/operator/respond",
                             {"prompt": "Give me a one-line status."})
    proven = row["status"] in ("ok", "honest_unavailable")
    if row["status"] == "ok" and isinstance(payload, dict):
        has_envelope = "conscience_message" in payload or "reply_contained" in payload
        row["reason"] = ("answer carries the conscience/veto envelope"
                         if has_envelope else "answer returned (no envelope field)")
    return _class("Operator + conscience", [row], proven,
                  "operator answers with the conscience/veto envelope (POST /api/operator/respond)")


def _exercise_mcp(client: Any) -> Dict[str, Any]:
    """MCP boundary end-to-end: list the read-only tools, then call one through the live membrane route.

    Proven requires the sealed result be ``laminar`` — the four-part isolation contract (read-only
    surface, ingress screened, interior unchanged, egress verified) held across the real Flask route,
    not just the in-process self-test.
    """
    tools_row, tools_payload = _exercise(client, "GET", "/mcp/tools")
    call_row, call_payload = _exercise(client, "POST", "/mcp/call",
                                       {"name": "read_state", "arguments": {}})
    laminar = bool(isinstance(call_payload, dict) and call_payload.get("laminar"))
    if isinstance(call_payload, dict):
        call_row["reason"] = (f"read_state sealed + laminar={laminar}"
                              if laminar else f"call returned laminar={laminar}")
    tools_count = len(tools_payload.get("tools", [])) if isinstance(tools_payload, dict) else 0
    if tools_row["status"] == "ok":
        tools_row["reason"] = f"{tools_count} read-only tool(s) advertised"
    rows = [tools_row, call_row]
    proven = _no_fault(rows) and laminar
    return _class("MCP boundary (end-to-end)", rows, proven,
                  "read-only MCP call crosses the membrane laminarly (GET /mcp/tools → POST /mcp/call)")


def _exercise_probes(client: Any) -> Dict[str, Any]:
    """Connections / providers: real test probes. Offline they return an honest 'unconfigured' verdict —
    classified as a working capability, never a fault, never a fabricated success."""
    rows: List[Dict[str, Any]] = []
    provider_id = None
    _, providers_payload = _exercise(client, "GET", "/api/providers")
    if isinstance(providers_payload, dict):
        provs = providers_payload.get("providers") or []
        if provs and isinstance(provs[0], dict):
            provider_id = provs[0].get("id")

    if not provider_id:
        row = {"path": "/api/providers", "method": "GET", "status": "honest_unavailable",
               "code": 200, "reason": "no provider registered to probe"}
        return _class("Connections / providers", [row], True,
                      "connection test probes return an honest verdict")

    for path in (f"/api/providers/{provider_id}/test", f"/api/connections/{provider_id}/test"):
        row, payload = _exercise(client, "POST", path, {})
        if isinstance(payload, dict) and "ok" in payload:
            verdict = "reachable" if payload.get("ok") else "honest 'unconfigured/unreachable' verdict"
            row["reason"] = f"{provider_id}: {verdict}"
        rows.append(row)
    return _class("Connections / providers", rows, _no_fault(rows),
                  f"provider + connection test probes on '{provider_id}' return honest verdicts")


def _surface_class(surface: Dict[str, Any]) -> Dict[str, Any]:
    """The full SaaS telemetry GET surface, via the reused connection verifier."""
    rows = [{"path": e["path"], "method": "GET", "status": e["status"], "code": e["code"],
             "reason": e["reason"]} for e in surface["endpoints"]]
    summary = (f"{surface['ok']} ok · {surface['honest_unavailable']} honest-unavailable · "
               f"{surface['faults']} fault(s) across {surface['checked']} GET routes")
    return _class("SaaS telemetry surface", rows, surface["faults"] == 0, summary)


def _parity_class(parity: Dict[str, Any]) -> Dict[str, Any]:
    """Every endpoint the React console calls (shell + legacy) is served by the operator."""
    rows = [{"path": m["path"], "method": "GET", "status": "fault", "code": 404,
             "reason": f"console calls it ({m['origin']}), operator does not serve it"}
            for m in parity["missing"]]
    summary = f"{len(parity['served'])}/{parity['expected']} console endpoints served"
    return _class("Frontend ↔ backend parity", rows, parity["all_served"], summary)


# ── Rolled-up self-test suites ──────────────────────────────────────────────────────────────────

def _rollup_suites() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """The four existing self-tests, each reduced to one ok/detail row. Returns (suites, coverage_audit)."""
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))  # so `scripts.validation.*` imports in a standalone run

    suites: List[Dict[str, Any]] = []

    try:
        from scripts.validation.audit_saas_compliance import build_report, run_audit

        rep = build_report(run_audit())
        s = rep["summary"]
        suites.append({"name": "SaaS compliance audit", "ok": s["compliance_status"] == "compliant",
                       "detail": f"{s['passed']}/{s['check_count']} checks · {s['failed_required']} "
                                 f"required failure(s)"})
    except Exception as exc:  # noqa: BLE001
        suites.append({"name": "SaaS compliance audit", "ok": False, "detail": f"unavailable: {exc}"[:120]})

    try:
        from aureon.bio.mcp_transport import compute_mcp_transport

        m = compute_mcp_transport()
        suites.append({"name": "MCP transport membrane", "ok": bool(m.all_ok),
                       "detail": f"tools={m.tools_listed} · benign laminar={m.benign_laminar} · "
                                 f"tamper detected={m.tamper_detected}"})
    except Exception as exc:  # noqa: BLE001
        suites.append({"name": "MCP transport membrane", "ok": False, "detail": f"unavailable: {exc}"[:120]})

    coverage: Dict[str, Any] = {}
    try:
        from aureon.saas.coverage import build_coverage_audit

        coverage = build_coverage_audit()
        suites.append({"name": "Repo-wide coverage", "ok": bool(coverage.get("all_covered")),
                       "detail": f"{len(coverage.get('covered', []))}/{coverage.get('fs_package_count')} "
                                 f"packages · {coverage.get('uncovered', []) and 'gaps' or 'no gaps'}"})
    except Exception as exc:  # noqa: BLE001
        suites.append({"name": "Repo-wide coverage", "ok": False, "detail": f"unavailable: {exc}"[:120]})

    return suites, coverage


def _load_benchmark_module() -> Any:
    """Load the Tier-A benchmark runner by file path (tests/ is not an importable package)."""
    path = _REPO_ROOT / "tests" / "benchmarks" / "benchmark_aureon_scope.py"
    spec = importlib.util.spec_from_file_location("aureon_benchmark_scope", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load benchmark runner at {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run_tier_a(fast: bool = False) -> Dict[str, Any]:
    """Run (or read) the 45 Tier-A architectural invariants. Live by default; ``fast`` reads report.json."""
    if fast:
        report_path = _REPO_ROOT / "tests" / "benchmarks" / "report.json"
        try:
            data = json.loads(report_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            return {"passed": 0, "total": 0, "failures": [f"report.json unavailable: {exc}"[:120]],
                    "mode": "committed_report"}
        tier_a = data.get("tier_a", [])
        passed = sum(1 for r in tier_a if r.get("passed"))
        failures = [str(r.get("name")) for r in tier_a if not r.get("passed")]
        return {"passed": passed, "total": len(tier_a), "failures": failures, "mode": "committed_report"}

    mod = _load_benchmark_module()
    benchmarks: List[Tuple[str, Any]] = list(mod.TIER_A)
    passed = 0
    failures = []
    with tempfile.TemporaryDirectory(prefix="aureon-capdemo-") as tmp:
        root = Path(tmp)
        for idx, (label, fn) in enumerate(benchmarks, start=1):
            sub = root / f"a{idx}"
            sub.mkdir(parents=True, exist_ok=True)
            try:
                result = fn(sub)
                if result.get("passed"):
                    passed += 1
                else:
                    failures.append(str(label))
            except Exception as exc:  # noqa: BLE001 - a raising benchmark is a failure, not a crash
                failures.append(f"{label}: {type(exc).__name__}")
    return {"passed": passed, "total": len(benchmarks), "failures": failures, "mode": "live"}


# ── Orchestration ──────────────────────────────────────────────────────────────────────────────

def demonstrate(app: Any = None, *, fast: bool = False, run_tier_a: bool = True) -> Dict[str, Any]:
    """Boot the operator app once, exercise the full capability surface, and roll up every self-test.

    Returns one aggregated result. ``healthy`` is True iff every capability class is proven (no faults,
    parity all-served), every rolled-up suite is green, coverage is complete, and all Tier-A invariants
    pass. Read-only; never raises on a bad exercise (a crash is recorded as a fault).
    """
    app = app or _build_app()
    client = app.test_client()

    classes: List[Dict[str, Any]] = [
        _exercise_reasoning(client),
        _exercise_operator(client),
        _exercise_mcp(client),
        _exercise_probes(client),
        _surface_class(verify_surface(app).to_dict()),
        _parity_class(verify_frontend_parity(app)),
    ]

    suites, coverage = _rollup_suites()
    # Annotated so the skipped-run literal joins the live return as one dict type; without it
    # the comparisons below widen to `object` and mypy cannot check them.
    tier_a: Dict[str, Any] = _run_tier_a(fast=fast) if run_tier_a else {
        "passed": 0, "total": 0, "failures": [], "mode": "skipped"}

    all_proven = all(c["proven"] for c in classes)
    suites_ok = all(s["ok"] for s in suites)
    coverage_ok = bool(coverage.get("all_covered"))
    tier_ok = tier_a["total"] > 0 and tier_a["passed"] == tier_a["total"]
    if tier_a["mode"] == "skipped":
        tier_ok = True  # explicitly not gating on Tier-A this run
    healthy = all_proven and suites_ok and coverage_ok and tier_ok

    proven_classes = sum(1 for c in classes if c["proven"])
    green_suites = sum(1 for s in suites if s["ok"])
    return {
        "capability_classes": classes,
        "suites": suites,
        "tier_a": tier_a,
        "coverage_complete": coverage_ok,
        "healthy": healthy,
        "totals": {
            "classes_proven": proven_classes,
            "classes_total": len(classes),
            "suites_green": green_suites,
            "suites_total": len(suites),
        },
        "note": "Boots the operator app once and exercises the live capability surface, then rolls up "
                "every existing self-test. Read-only; nothing armed; no fabricated data — an offline "
                "capability reports honest_unavailable, never a fault.",
    }


# ── Evidence artifact ──────────────────────────────────────────────────────────────────────────

def write_capability_report(result: Dict[str, Any], out_md: str | Path,
                            out_json: str | Path | None = None) -> str:
    """Write the demonstration as a durable, byte-identical evidence artifact (markdown [+ JSON])."""
    t = result["totals"]
    tier = result["tier_a"]
    lines: List[str] = []
    lines.append("# Aureon OS — capability demonstration")
    lines.append("")
    lines.append("Generated by `python -m aureon.saas.capability_demo --report <OUT.md>` — boots the "
                 "operator app in-process, exercises the full live capability surface (reasoning, "
                 "operator, MCP boundary, connection probes, the SaaS telemetry surface, and "
                 "frontend↔backend parity), then rolls up every existing self-test. Read-only; nothing "
                 "is armed; no fabricated data.")
    lines.append("")
    lines.append(
        f"**Healthy: {result['healthy']}** · {t['classes_proven']}/{t['classes_total']} capability "
        f"classes proven · {t['suites_green']}/{t['suites_total']} self-test suites green · Tier-A "
        f"{tier['passed']}/{tier['total']} architectural invariants ({tier['mode']}) · coverage "
        f"complete {result['coverage_complete']}")
    lines.append("")

    lines.append("## Capability classes (exercised live)")
    lines.append("")
    lines.append("| capability | result | what was exercised |")
    lines.append("|:---|:---:|:---|")
    for c in result["capability_classes"]:
        mark = "proven" if c["proven"] else "FAULT"
        lines.append(f"| {c['name']} | {mark} | {c['summary']} |")
    lines.append("")

    # Per-exercise detail: small classes list every row; large sweeps show only non-ok rows.
    for c in result["capability_classes"]:
        rows = c["exercised"]
        show = rows if len(rows) <= _DETAIL_MAX else [r for r in rows if r["status"] != "ok"]
        if not show:
            continue
        lines.append(f"### {c['name']}")
        lines.append("")
        lines.append("| endpoint | method | status | code | note |")
        lines.append("|:---|:---:|:---:|:---:|:---|")
        for r in show:
            lines.append(f"| `{r['path']}` | {r['method']} | {r['status']} | {r['code']} | "
                         f"{r.get('reason', '')} |")
        if len(rows) > _DETAIL_MAX:
            ok_n = sum(1 for r in rows if r["status"] == "ok")
            lines.append(f"| … | | | | {ok_n} further route(s) ok |")
        lines.append("")

    lines.append("## Rolled-up self-tests")
    lines.append("")
    lines.append("| suite | result | detail |")
    lines.append("|:---|:---:|:---|")
    for s in result["suites"]:
        lines.append(f"| {s['name']} | {'green' if s['ok'] else 'RED'} | {s['detail']} |")
    lines.append(f"| Tier-A architectural invariants | "
                 f"{'green' if tier['passed'] == tier['total'] and tier['total'] else 'RED'} | "
                 f"{tier['passed']}/{tier['total']} passed ({tier['mode']}) |")
    lines.append("")
    if tier["failures"]:
        lines.append("**Tier-A failures:** " + ", ".join(tier["failures"]))
        lines.append("")

    lines.append("## Reproduce")
    lines.append("")
    lines.append("```bash")
    lines.append("AUREON_LLM_OFFLINE=1 AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1 \\")
    lines.append("  python -m aureon.saas.capability_demo --report docs/reports/CAPABILITY_DEMO.md")
    lines.append("```")
    lines.append("")
    lines.append(f"_{result['note']}_")
    lines.append("")
    md = "\n".join(lines) + "\n"

    out_md_path = Path(out_md)
    out_md_path.write_text(md, encoding="utf-8")
    if out_json is not None:
        Path(out_json).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return str(out_md_path)


def main(argv: List[str] | None = None) -> int:
    """CLI: demonstrate the full capability surface. Exit 0 iff healthy."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Prove Aureon OS works: exercise the full capability surface + roll up every self-test.")
    parser.add_argument("--report", metavar="OUT.md", help="write the demonstration as a markdown artifact")
    parser.add_argument("--report-json", metavar="OUT.json", help="also write the JSON record")
    parser.add_argument("--json", action="store_true", help="print the raw JSON result and exit")
    parser.add_argument("--fast", action="store_true",
                        help="read the committed Tier-A report.json instead of re-running the 45 benchmarks")
    args = parser.parse_args(argv)

    result = demonstrate(fast=args.fast)
    t = result["totals"]
    tier = result["tier_a"]

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["healthy"] else 1

    print("Aureon OS — capability demonstration")
    print(f"  capability classes : {t['classes_proven']}/{t['classes_total']} proven")
    for c in result["capability_classes"]:
        mark = "  ok " if c["proven"] else "FAULT"
        print(f"    [{mark}] {c['name']:26} {c['summary']}")
    print(f"  self-test suites   : {t['suites_green']}/{t['suites_total']} green")
    for s in result["suites"]:
        print(f"    [{'green' if s['ok'] else ' RED '}] {s['name']:26} {s['detail']}")
    print(f"  Tier-A invariants  : {tier['passed']}/{tier['total']} passed ({tier['mode']})")
    for f in tier["failures"]:
        print(f"    [fail] {f}")

    if args.report:
        path = write_capability_report(result, args.report, args.report_json)
        print(f"  report written: {path}")

    print(f"  healthy: {result['healthy']}")
    return 0 if result["healthy"] else 1


__all__ = ["demonstrate", "write_capability_report", "main"]


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())
