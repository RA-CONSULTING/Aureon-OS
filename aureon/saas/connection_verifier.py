"""
Aureon SaaS — connection verifier.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"Is the SaaS working and is every connection wired?" — made repeatable and honest.

Two checks, both read-only (they boot the operator app in-process and probe it; they never mutate state,
place trades, or move money):

  * ``verify_surface``  — enumerate every registered route and GET each parameter-free GET endpoint,
    classifying it as ``ok`` (200 + JSON), ``honest_unavailable`` (a self-declared 503 / ``available:
    false`` — a configured-off feature, not a bug), or ``fault`` (500 / crash / HTML where JSON is due).
  * ``verify_frontend_parity`` — cross-check the endpoint paths the React console calls (both the current
    ``frontend/src/shell/`` console and the legacy trading console) against the routes the operator
    actually registers, so a page fetching a path the backend doesn't serve is caught as ``missing``.

A ``fault`` or a ``missing`` endpoint is a real problem; an ``honest_unavailable`` is the no-fake-data
policy working as intended. The CLI (``python -m aureon.saas.connection_verifier``) prints the table and
exits non-zero only on faults / missing endpoints.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("aureon.saas.connection_verifier")

# GET routes we deliberately do not probe: streaming (would block) and the text metrics endpoint.
_SKIP_SUBSTR = ("/stream", "/metrics")

# ── the endpoints the React console calls, cross-checked against registered routes ───────────────
# Path templates use ``<param>`` to match Flask rule variables. Sourced from a frontend audit of
# ``frontend/src/shell/`` (current console) and ``frontend/src/`` App/components (legacy console).
_SHELL_ENDPOINTS: List[str] = [
    "/api/pulse", "/api/status", "/api/billing/status", "/api/organism", "/api/automation",
    "/api/defense", "/api/org", "/api/company", "/api/pursuit", "/api/approvals",
    "/api/approvals/<item_id>", "/api/metacognition", "/api/switchboard", "/api/switchboard/<flag_id>",
    "/api/providers", "/api/providers/<provider_id>", "/api/providers/<provider_id>/test",
    "/api/affect", "/api/soul", "/api/inner-work", "/api/consciousness", "/api/connections",
    "/api/connections/readiness", "/api/connections/<conn_id>", "/api/connections/<conn_id>/test",
    "/api/cognition", "/api/cognition/reason", "/healthz", "/readyz",
]
_LEGACY_ENDPOINTS: List[str] = [
    "/api/bots", "/api/trades", "/api/terminal-state", "/api/flight-test", "/api/reboot-advice",
    "/api/env-credentials", "/api/notifications/telegram",
]


@dataclass
class EndpointStatus:
    path: str
    status: str          # "ok" | "honest_unavailable" | "fault"
    code: int
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SurfaceReport:
    checked: int = 0
    ok: int = 0
    honest_unavailable: int = 0
    faults: int = 0
    endpoints: List[EndpointStatus] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["endpoints"] = [e.to_dict() for e in self.endpoints]
        return d


def _build_app() -> Any:
    """Boot the operator app in-process (offline-safe). Raises on failure — the caller decides."""
    from aureon.operator.operator_server import create_app

    return create_app()


def _classify(code: int, payload: Any) -> tuple[str, str]:
    """Map an HTTP response to (status, reason). A self-declared 503 / available:false is honest."""
    if code == 200:
        if isinstance(payload, (dict, list)):
            return "ok", ""
        return "fault", "200 but non-JSON body"
    if code == 503:
        reason = ""
        if isinstance(payload, dict):
            reason = str(payload.get("reason")
                         or (payload.get("error", {}) or {}).get("message")
                         if isinstance(payload.get("error"), dict) else payload.get("error", ""))
        return "honest_unavailable", reason or "self-declared 503"
    if isinstance(payload, dict) and payload.get("available") is False:
        return "honest_unavailable", str(payload.get("reason") or payload.get("error") or "available:false")
    return "fault", f"HTTP {code}"


def verify_surface(app: Any = None) -> SurfaceReport:
    """GET every parameter-free GET route and classify each. Read-only; never raises on a bad route."""
    app = app or _build_app()
    client = app.test_client()
    report = SurfaceReport()

    rules = sorted(app.url_map.iter_rules(), key=lambda r: str(r))
    for rule in rules:
        path = str(rule)
        if "GET" not in rule.methods or "<" in path:
            continue
        if any(s in path for s in _SKIP_SUBSTR):
            continue
        if path in ("/", "/watch", "/watch/") or path.startswith("/static"):
            continue  # HTML/asset routes — not JSON connections
        try:
            resp = client.get(path)
            payload = resp.get_json(silent=True)
            status, reason = _classify(resp.status_code, payload)
            code = resp.status_code
        except Exception as exc:  # noqa: BLE001 - a crash IS a fault, recorded not raised
            status, reason, code = "fault", f"exception: {exc}"[:200], 0
        report.endpoints.append(EndpointStatus(path=path, status=status, code=code, reason=reason))
        report.checked += 1
        if status == "ok":
            report.ok += 1
        elif status == "honest_unavailable":
            report.honest_unavailable += 1
        else:
            report.faults += 1
    return report


def _registered_paths(app: Any) -> set[str]:
    return {str(r) for r in app.url_map.iter_rules()}


def verify_frontend_parity(app: Any = None) -> Dict[str, Any]:
    """Cross-check every endpoint the console calls against the registered routes."""
    app = app or _build_app()
    registered = _registered_paths(app)
    expected = [(p, "shell") for p in _SHELL_ENDPOINTS] + [(p, "legacy") for p in _LEGACY_ENDPOINTS]
    served: List[Dict[str, str]] = []
    missing: List[Dict[str, str]] = []
    for path, origin in expected:
        (served if path in registered else missing).append({"path": path, "origin": origin})
    return {
        "expected": len(expected),
        "served": served,
        "missing": missing,
        "all_served": not missing,
    }


def verify_all(app: Any = None) -> Dict[str, Any]:
    """Both checks over one booted app."""
    app = app or _build_app()
    surface = verify_surface(app)
    parity = verify_frontend_parity(app)
    healthy = surface.faults == 0 and parity["all_served"]
    return {"surface": surface.to_dict(), "parity": parity, "healthy": healthy}


def write_connection_report(result: Dict[str, Any], out_md: str | Path,
                            out_json: str | Path | None = None) -> str:
    """Write the verification as a durable evidence artifact (markdown [+ JSON])."""
    surface = result["surface"]
    parity = result["parity"]
    lines: List[str] = []
    lines.append("# SaaS connection verification")
    lines.append("")
    lines.append("Generated by `python -m aureon.saas.connection_verifier --report <OUT.md>` — boots the "
                 "operator app in-process, GETs every registered JSON route, and cross-checks the console's "
                 "expected endpoints against the registered routes. Read-only; nothing is armed.")
    lines.append("")
    lines.append(f"**Healthy: {result['healthy']}** · surface {surface['ok']} ok / "
                 f"{surface['honest_unavailable']} honest-unavailable / {surface['faults']} faults "
                 f"(of {surface['checked']}) · parity {len(parity['served'])}/{parity['expected']} served, "
                 f"{len(parity['missing'])} missing")
    lines.append("")
    lines.append("## Surface — every registered JSON GET route")
    lines.append("")
    lines.append("| endpoint | status | code | note |")
    lines.append("|:---|:---:|:---:|:---|")
    for e in surface["endpoints"]:
        lines.append(f"| `{e['path']}` | {e['status']} | {e['code']} | {e['reason']} |")
    lines.append("")
    lines.append("## Frontend ↔ backend parity")
    lines.append("")
    if parity["missing"]:
        lines.append("**Missing (console calls it, operator does not serve it):**")
        for m in parity["missing"]:
            lines.append(f"- `{m['path']}` ({m['origin']})")
    else:
        lines.append("Every endpoint the console calls (shell + legacy) is served by the operator.")
    lines.append("")
    md = "\n".join(lines) + "\n"

    out_md_path = Path(out_md)
    out_md_path.write_text(md, encoding="utf-8")
    if out_json is not None:
        Path(out_json).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return str(out_md_path)


def main(argv: List[str] | None = None) -> int:
    """CLI: verify the SaaS surface + frontend parity. Exit 0 iff no faults and nothing missing."""
    import argparse

    parser = argparse.ArgumentParser(description="Verify the Aureon SaaS surface and every console connection.")
    parser.add_argument("--report", metavar="OUT.md", help="write the table as a markdown evidence artifact")
    parser.add_argument("--report-json", metavar="OUT.json", help="also write the JSON record")
    parser.add_argument("--json", action="store_true", help="print the raw JSON result and exit")
    args = parser.parse_args(argv)

    result = verify_all()
    surface = result["surface"]
    parity = result["parity"]

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["healthy"] else 1

    print("SaaS connection verification")
    print(f"  surface: {surface['ok']} ok · {surface['honest_unavailable']} honest-unavailable · "
          f"{surface['faults']} faults  (of {surface['checked']})")
    print(f"  parity : {len(parity['served'])}/{parity['expected']} served · {len(parity['missing'])} missing")
    for e in surface["endpoints"]:
        if e["status"] != "ok":
            print(f"    [{e['status']}] {e['path']}  ({e['code']}) {e['reason']}")
    for m in parity["missing"]:
        print(f"    [missing] {m['path']}  ({m['origin']})")

    if args.report:
        path = write_connection_report(result, args.report, args.report_json)
        print(f"  report written: {path}")

    print(f"  healthy: {result['healthy']}")
    return 0 if result["healthy"] else 1


__all__ = [
    "EndpointStatus", "SurfaceReport",
    "verify_surface", "verify_frontend_parity", "verify_all",
    "write_connection_report", "main",
]


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())
