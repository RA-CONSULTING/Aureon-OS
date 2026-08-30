"""Source-neutral HNC evidence-control graph generator.

The generator turns a controlled local contract and the current public-claim
register into a small semantic HTML/CSS/JavaScript component bundle.  It writes
only below ``artifacts/website-components`` and never edits ``website/`` or a
staged candidate.  A separately source-bound work order is required before a
human-approved bundle can be transplanted into a candidate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any, Mapping, Sequence

from aureon.operator.public_claim_evidence import audit_public_claim_evidence_file

CONTRACT_SCHEMA = "aureon.hnc-evidence-graph-contract.v1"
AUDIT_SCHEMA = "aureon.hnc-evidence-graph-audit.v1"
BUNDLE_SCHEMA = "aureon.hnc-evidence-graph-bundle.v1"
DEFAULT_CONTRACT_PATH = Path("data/website_operator/hnc_evidence_graph.v1.json")
DEFAULT_CLAIM_REGISTER_PATH = Path("data/website_operator/public_claim_evidence_register.v1.json")
DEFAULT_COMPONENT_ROOT = Path("artifacts/website-components")

NON_AUTHORITATIVE_AUTHORITY = {
    "scope": "source-neutral local HNC evidence-control component only",
    "canonical_website_mutation": "never",
    "candidate_mutation": "never",
    "release_eligible": False,
    "package_authority": "none",
    "deployment_authority": "none",
    "credential_access": "none",
    "network_access": "none",
    "human_visual_acceptance": "required before candidate transplant",
}

_CONTRACT_FIELDS = frozenset(
    {
        "schema",
        "component_id",
        "issued_at",
        "authority",
        "route",
        "placement",
        "claim_register",
        "claim_ids",
        "process_steps",
        "motion",
        "budgets",
    }
)
_BINDING_FIELDS = frozenset({"path", "sha256"})
_STEP_FIELDS = frozenset({"step_id", "index", "label", "state_label", "body", "claim_id"})
_MOTION_FIELDS = frozenset(
    {
        "trigger_ratio",
        "phase_interval_ms",
        "settled_by_ms",
        "maximum_displacement_px",
        "minimum_content_opacity",
        "repeats",
        "reduced_motion",
    }
)
_BUDGET_FIELDS = frozenset(
    {
        "html_bytes",
        "css_bytes",
        "javascript_bytes",
        "additional_requests",
        "binary_bytes",
    }
)
_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9-]{2,127}$")
_SHA256 = re.compile(r"^[A-F0-9]{64}$")
_EXPECTED_CLAIM_IDS = (
    "hnc-research-framework",
    "aureon-os-evidence-system",
)
_EXPECTED_STEPS = (
    ("research-record", "01", "Research record", "Research proposition"),
    ("source-claim-state", "02", "Source + claim state", "Control state"),
    ("aureon-os-control", "03", "Aureon OS control", "Company-built"),
    ("human-gate", "04", "Human gate", "Authority gate"),
    ("bounded-decision", "05", "Bounded decision", "Retained decision"),
)


class HNCEvidenceGraphError(ValueError):
    """The graph contract, claim binding, or artifact target is unsafe."""


def _find_repo_root(start: Path | None = None) -> Path:
    candidate = (start or Path.cwd()).resolve()
    for root in (candidate, *candidate.parents):
        if (root / "aureon").is_dir() and (root / "website").is_dir():
            return root
    raise HNCEvidenceGraphError("Could not locate the Aureon repository root.")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _bytes_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def _json_sha256(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def _relative_to_repo(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise HNCEvidenceGraphError("Graph input escapes the repository.") from exc


def _mapping(value: object, *, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise HNCEvidenceGraphError(f"{label} must be one object.")
    return dict(value)


def _exact_fields(value: Mapping[str, Any], expected: frozenset[str], *, label: str) -> None:
    actual = frozenset(str(key) for key in value)
    if actual != expected:
        raise HNCEvidenceGraphError(
            f"{label} fields do not match; "
            f"missing={sorted(expected - actual)}, unknown={sorted(actual - expected)}."
        )


def _text(value: object, *, label: str, maximum: int = 600) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HNCEvidenceGraphError(f"{label} must be non-empty text.")
    cleaned = value.strip()
    if len(cleaned) > maximum:
        raise HNCEvidenceGraphError(f"{label} exceeds {maximum} characters.")
    return cleaned


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HNCEvidenceGraphError(f"{label} is not valid JSON: {path}") from exc
    return _mapping(parsed, label=label)


def _claim_index(register: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    rows = register.get("claims")
    if not isinstance(rows, list):
        raise HNCEvidenceGraphError("Claim register did not retain claim records.")
    index: dict[str, dict[str, Any]] = {}
    for raw in rows:
        claim = _mapping(raw, label="claim audit row")
        claim_id = str(claim.get("id") or "")
        if claim_id:
            index[claim_id] = claim
    return index


def _contract_and_claims(
    contract: Mapping[str, Any],
    *,
    contract_path: Path,
    repo_root: Path,
    as_of: datetime,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]]:
    _exact_fields(contract, _CONTRACT_FIELDS, label="HNC graph contract")
    if contract.get("schema") != CONTRACT_SCHEMA:
        raise HNCEvidenceGraphError("HNC graph contract schema is unsupported.")
    component_id = _text(contract.get("component_id"), label="component_id", maximum=128)
    if not _IDENTIFIER.fullmatch(component_id):
        raise HNCEvidenceGraphError("component_id must be a stable lowercase identifier.")
    if contract.get("authority") != NON_AUTHORITATIVE_AUTHORITY:
        raise HNCEvidenceGraphError("HNC graph authority changed.")
    if contract.get("route") != "/":
        raise HNCEvidenceGraphError("HNC graph v1 is bounded to the homepage route.")
    if contract.get("placement") != "after-homepage-proof-rail":
        raise HNCEvidenceGraphError("HNC graph placement is not source-neutral.")

    binding = _mapping(contract.get("claim_register"), label="claim_register")
    _exact_fields(binding, _BINDING_FIELDS, label="claim_register")
    if binding.get("path") != DEFAULT_CLAIM_REGISTER_PATH.as_posix():
        raise HNCEvidenceGraphError("HNC graph must bind the canonical claim register.")
    if not isinstance(binding.get("sha256"), str) or not _SHA256.fullmatch(str(binding.get("sha256"))):
        raise HNCEvidenceGraphError("Claim-register SHA-256 is invalid.")
    register_path = (repo_root / DEFAULT_CLAIM_REGISTER_PATH).resolve()
    if binding["sha256"] != _sha256(register_path):
        raise HNCEvidenceGraphError("Claim register changed after the graph contract.")

    claim_ids = contract.get("claim_ids")
    if not isinstance(claim_ids, list) or tuple(claim_ids) != _EXPECTED_CLAIM_IDS:
        raise HNCEvidenceGraphError("Homepage graph claim identifiers are not exact.")
    claim_receipt = audit_public_claim_evidence_file(
        register_path,
        repo_root=repo_root,
        as_of=as_of.date(),
    )
    if claim_receipt.get("passed") is not True:
        raise HNCEvidenceGraphError("Canonical public-claim register does not pass.")
    claims = _claim_index(_read_json(register_path, label="public claim register"))
    for claim_id in _EXPECTED_CLAIM_IDS:
        claim = claims.get(claim_id)
        if claim is None or "/" not in set(claim.get("public_routes") or []):
            raise HNCEvidenceGraphError(
                f"Claim '{claim_id}' is unavailable or not authorised for the homepage."
            )

    raw_steps = contract.get("process_steps")
    if not isinstance(raw_steps, list) or len(raw_steps) != len(_EXPECTED_STEPS):
        raise HNCEvidenceGraphError("HNC graph needs exactly five ordered steps.")
    steps: list[dict[str, Any]] = []
    for raw, expected in zip(raw_steps, _EXPECTED_STEPS, strict=True):
        step = _mapping(raw, label="process step")
        _exact_fields(step, _STEP_FIELDS, label="process step")
        actual = (
            step.get("step_id"),
            step.get("index"),
            step.get("label"),
            step.get("state_label"),
        )
        if actual != expected:
            raise HNCEvidenceGraphError("HNC graph step identity or order changed.")
        body = _text(step.get("body"), label=f"{expected[0]} body")
        step_claim_id = step.get("claim_id")
        if step_claim_id is not None and step_claim_id not in _EXPECTED_CLAIM_IDS:
            raise HNCEvidenceGraphError("HNC graph contains an unauthorised claim id.")
        if step_claim_id is not None and body != claims[str(step_claim_id)]["claim"]:
            raise HNCEvidenceGraphError(
                f"Step '{expected[0]}' does not use the exact permitted claim wording."
            )
        steps.append({**step, "body": body})
    if [step["claim_id"] for step in steps if step["claim_id"]] != list(_EXPECTED_CLAIM_IDS):
        raise HNCEvidenceGraphError("HNC graph claim bindings are incomplete.")

    motion = _mapping(contract.get("motion"), label="motion")
    _exact_fields(motion, _MOTION_FIELDS, label="motion")
    if motion != {
        "trigger_ratio": 0.35,
        "phase_interval_ms": 180,
        "settled_by_ms": 900,
        "maximum_displacement_px": 6,
        "minimum_content_opacity": 0.72,
        "repeats": False,
        "reduced_motion": "static-complete",
    }:
        raise HNCEvidenceGraphError("HNC graph motion contract changed.")

    budgets = _mapping(contract.get("budgets"), label="budgets")
    _exact_fields(budgets, _BUDGET_FIELDS, label="budgets")
    if budgets != {
        "html_bytes": 2500,
        "css_bytes": 5500,
        "javascript_bytes": 1800,
        "additional_requests": 0,
        "binary_bytes": 0,
    }:
        raise HNCEvidenceGraphError("HNC graph performance budgets changed.")
    return steps, claims, claim_receipt


def render_hnc_evidence_graph_html(
    steps: Sequence[Mapping[str, Any]],
    claims: Mapping[str, Mapping[str, Any]],
) -> str:
    """Render complete first-paint semantic markup with exact claim boundaries."""

    items: list[str] = []
    for step in steps:
        claim_attr = f' data-claim-id="{escape(str(step["claim_id"]))}"' if step.get("claim_id") else ""
        items.append(
            f"<li{claim_attr}>"
            f'<span class="hnc-evidence-graph__index">{escape(str(step["index"]))}</span>'
            f'<span class="hnc-evidence-graph__state">{escape(str(step["state_label"]))}</span>'
            f"<h3>{escape(str(step['label']))}</h3>"
            f"<p>{escape(str(step['body']))}</p></li>"
        )
    hnc = claims["hnc-research-framework"]
    os_claim = claims["aureon-os-evidence-system"]
    return (
        '<section class="hnc-evidence-graph" id="evidence-path" '
        'data-hnc-evidence-graph data-motion="static" '
        'aria-labelledby="hnc-evidence-graph-title"><div class="wrap">'
        '<div class="hnc-evidence-graph__head">'
        '<p class="institutional-kicker">HNC evidence-control graph</p>'
        '<h2 id="hnc-evidence-graph-title">From question to accountable decision.</h2>'
        "<p>One trace carries purpose, provenance, evidence state, human authority "
        "and the final receipt forward. Every stop remains visible.</p></div>"
        '<ol class="hnc-evidence-graph__rail" '
        'aria-label="Research-to-decision evidence flow">'
        + "".join(items)
        + '</ol><div class="hnc-evidence-graph__boundaries" '
        'aria-label="Claim boundaries">'
        f"<p><strong>HNC boundary</strong>{escape(str(hnc['boundary']))}</p>"
        f"<p><strong>Aureon OS boundary</strong>{escape(str(os_claim['boundary']))}</p>"
        "</div></div></section>\n"
    )


def render_hnc_evidence_graph_css() -> str:
    """Render a restrained institutional rail with a static complete fallback."""

    return """.hnc-evidence-graph {
  --hnc-trace: 1;
  padding-block: clamp(76px, 9vw, 126px);
  color: var(--ivory-50, #f7f2e7);
  background: var(--ink-950, #06111e);
}
.hnc-evidence-graph__head { display:grid; grid-template-columns:minmax(0,.84fr) minmax(280px,.52fr); gap:clamp(28px,6vw,88px); align-items:end; }
.hnc-evidence-graph__head h2 { grid-column:1; max-width:760px; margin:0; font-family:"Source Serif 4",serif; font-size:clamp(2.3rem,4.8vw,4.7rem); line-height:.98; }
.hnc-evidence-graph__head > p:last-child { grid-column:2; grid-row:1/3; align-self:end; margin:0; color:#bdcad4; line-height:1.7; }
.hnc-evidence-graph__rail { position:relative; display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:clamp(18px,2.5vw,34px); margin:clamp(48px,7vw,78px) 0 0; padding:34px 0 0; list-style:none; }
.hnc-evidence-graph__rail::before,
.hnc-evidence-graph__rail::after { position:absolute; top:8px; right:0; left:0; height:1px; content:""; transform-origin:left center; }
.hnc-evidence-graph__rail::before { background:rgba(247,242,231,.24); }
.hnc-evidence-graph__rail::after { background:var(--orientation-gold,#efc76f); transform:scaleX(var(--hnc-trace)); transition:transform 180ms linear; }
.hnc-evidence-graph__rail li { position:relative; min-width:0; opacity:1; transform:none; transition:opacity 180ms ease,transform 180ms ease; }
.hnc-evidence-graph__rail li::before { position:absolute; top:-31px; left:0; width:9px; height:9px; border:2px solid var(--ink-950,#06111e); border-radius:50%; background:var(--orientation-gold,#efc76f); box-shadow:0 0 0 1px rgba(239,199,111,.68); content:""; }
.hnc-evidence-graph__index,
.hnc-evidence-graph__state { display:block; font-family:"IBM Plex Mono",monospace; font-size:.7rem; font-weight:650; letter-spacing:.09em; text-transform:uppercase; }
.hnc-evidence-graph__index { color:#8397a8; }
.hnc-evidence-graph__state { min-height:2.4em; margin-top:12px; color:var(--orientation-gold,#efc76f); }
.hnc-evidence-graph__rail li:nth-child(2) .hnc-evidence-graph__state { color:var(--state-source,#8fc9f4); }
.hnc-evidence-graph__rail li:nth-child(3) .hnc-evidence-graph__state { color:var(--state-company,#c9a8ff); }
.hnc-evidence-graph__rail li:nth-child(4) { padding-left:14px; border-left:2px solid var(--state-open,#f19a87); }
.hnc-evidence-graph__rail li:nth-child(4) .hnc-evidence-graph__state { color:var(--state-open,#f19a87); }
.hnc-evidence-graph__rail h3 { margin:15px 0 11px; font-size:clamp(1.03rem,1.45vw,1.3rem); }
.hnc-evidence-graph__rail p { margin:0; color:#aebdca; font-size:.89rem; line-height:1.64; }
.hnc-evidence-graph__boundaries { display:grid; grid-template-columns:1fr 1fr; gap:1px; margin-top:clamp(42px,6vw,66px); border:1px solid rgba(247,242,231,.16); background:rgba(247,242,231,.12); }
.hnc-evidence-graph__boundaries p { margin:0; padding:22px 24px; color:#aebdca; background:var(--ink-950,#06111e); font-size:.78rem; line-height:1.62; }
.hnc-evidence-graph__boundaries strong { display:block; margin-bottom:8px; color:#f7f2e7; font-family:"IBM Plex Mono",monospace; font-size:.67rem; letter-spacing:.09em; text-transform:uppercase; }
.hnc-evidence-graph[data-motion="tracing"] { --hnc-trace:0; }
.hnc-evidence-graph[data-motion="tracing"] .hnc-evidence-graph__rail li { opacity:.72; transform:translateY(6px); }
.hnc-evidence-graph[data-phase="1"] { --hnc-trace:.2; }
.hnc-evidence-graph[data-phase="2"] { --hnc-trace:.4; }
.hnc-evidence-graph[data-phase="3"] { --hnc-trace:.6; }
.hnc-evidence-graph[data-phase="4"] { --hnc-trace:.8; }
.hnc-evidence-graph[data-phase="5"],
.hnc-evidence-graph[data-motion="complete"] { --hnc-trace:1; }
.hnc-evidence-graph[data-phase="1"] li:nth-child(1),
.hnc-evidence-graph[data-phase="2"] li:nth-child(-n+2),
.hnc-evidence-graph[data-phase="3"] li:nth-child(-n+3),
.hnc-evidence-graph[data-phase="4"] li:nth-child(-n+4),
.hnc-evidence-graph[data-phase="5"] li { opacity:1; transform:none; }
@media (max-width:819px) {
  .hnc-evidence-graph__head,.hnc-evidence-graph__boundaries { grid-template-columns:1fr; }
  .hnc-evidence-graph__head h2,.hnc-evidence-graph__head > p:last-child { grid-column:1; grid-row:auto; }
  .hnc-evidence-graph__rail { display:grid; grid-template-columns:1fr; gap:30px; padding:0 0 0 28px; }
  .hnc-evidence-graph__rail::before,.hnc-evidence-graph__rail::after { top:0; right:auto; bottom:0; left:6px; width:1px; height:auto; transform-origin:center top; transform:scaleY(var(--hnc-trace)); }
  .hnc-evidence-graph__rail li::before { top:4px; left:-26px; }
  .hnc-evidence-graph__state { min-height:0; }
}
@media (max-width:390px) {
  .hnc-evidence-graph__rail p { font-size:.875rem; }
  .hnc-evidence-graph__boundaries p { padding:18px; font-size:.875rem; }
}
@media (prefers-reduced-motion:reduce) {
  .hnc-evidence-graph { --hnc-trace:1!important; }
  .hnc-evidence-graph__rail::after,.hnc-evidence-graph__rail li { transition:none!important; opacity:1!important; transform:none!important; }
}
@media print {
  .hnc-evidence-graph { color:#000; background:#fff; }
  .hnc-evidence-graph__rail::after { display:none; }
  .hnc-evidence-graph__rail p,.hnc-evidence-graph__boundaries p { color:#222; background:#fff; }
}
@media (forced-colors:active) {
  .hnc-evidence-graph__rail::before,.hnc-evidence-graph__rail::after { background:CanvasText; }
  .hnc-evidence-graph__rail li::before { border-color:Canvas; background:CanvasText; box-shadow:none; }
}
"""


def render_hnc_evidence_graph_javascript() -> str:
    """Render one-shot explanatory motion with a complete no-JS fallback."""

    return """(() => {
  const reduce = matchMedia("(prefers-reduced-motion: reduce)");
  document.querySelectorAll("[data-hnc-evidence-graph]").forEach((root) => {
    let observer;
    let timers = [];
    let started = false;
    const clear = () => { timers.forEach(clearTimeout); timers = []; observer?.disconnect(); };
    const complete = () => {
      clear();
      root.dataset.motion = "complete";
      root.dataset.phase = "5";
      reduce.removeEventListener?.("change", onMotionChange);
    };
    const onMotionChange = (event) => { if (event.matches) complete(); };
    const start = () => {
      if (started) return;
      started = true;
      root.dataset.motion = "tracing";
      root.dataset.phase = "0";
      for (let phase = 1; phase <= 5; phase += 1) {
        timers.push(setTimeout(() => {
          root.dataset.phase = String(phase);
          if (phase === 5) complete();
        }, phase * 180));
      }
    };
    if (reduce.matches || !("IntersectionObserver" in window)) {
      complete();
      return;
    }
    reduce.addEventListener?.("change", onMotionChange);
    observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting && entry.intersectionRatio >= .35)) {
        observer.disconnect();
        start();
      }
    }, { threshold: [.35] });
    observer.observe(root);
  });
})();
"""


def audit_hnc_evidence_graph_contract(
    contract: Mapping[str, Any],
    *,
    contract_path: Path,
    repo_root: Path | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    root = _find_repo_root(repo_root)
    resolved_contract = contract_path.resolve()
    _relative_to_repo(root, resolved_contract)
    observed_at = (as_of or datetime.now(UTC)).astimezone(UTC)
    steps, claims, claim_receipt = _contract_and_claims(
        contract,
        contract_path=resolved_contract,
        repo_root=root,
        as_of=observed_at,
    )
    html = render_hnc_evidence_graph_html(steps, claims)
    css = render_hnc_evidence_graph_css()
    javascript = render_hnc_evidence_graph_javascript()
    budgets = _mapping(contract["budgets"], label="budgets")
    outputs = {
        "component.html": html,
        "component.css": css,
        "component.js": javascript,
    }
    sizes = {name: len(value.encode("utf-8")) for name, value in outputs.items()}
    checks = [
        {
            "id": "html-budget",
            "passed": sizes["component.html"] <= budgets["html_bytes"],
            "actual_bytes": sizes["component.html"],
            "maximum_bytes": budgets["html_bytes"],
        },
        {
            "id": "css-budget",
            "passed": sizes["component.css"] <= budgets["css_bytes"],
            "actual_bytes": sizes["component.css"],
            "maximum_bytes": budgets["css_bytes"],
        },
        {
            "id": "javascript-budget",
            "passed": sizes["component.js"] <= budgets["javascript_bytes"],
            "actual_bytes": sizes["component.js"],
            "maximum_bytes": budgets["javascript_bytes"],
        },
        {
            "id": "zero-new-resources",
            "passed": not re.search(
                r"<(?:img|picture|svg|canvas|video|iframe)\b|https?://|data:|blob:",
                html,
                re.IGNORECASE,
            ),
        },
        {
            "id": "semantic-ordered-list",
            "passed": html.count("<ol ") == 1
            and len(re.findall(r"<li(?:\s|>)", html)) == 5
            and 'aria-labelledby="hnc-evidence-graph-title"' in html,
        },
        {
            "id": "exact-claim-bindings",
            "passed": all(
                html.count(f'data-claim-id="{claim_id}"') == 1
                and escape(str(claims[claim_id]["claim"])) in html
                and escape(str(claims[claim_id]["boundary"])) in html
                for claim_id in _EXPECTED_CLAIM_IDS
            ),
        },
        {
            "id": "static-first-paint",
            "passed": 'data-motion="static"' in html
            and " hidden" not in html.casefold()
            and ".hnc-evidence-graph__rail li{display:none" not in css.replace(" ", "").casefold(),
        },
        {
            "id": "motion-boundary",
            "passed": "setInterval" not in javascript
            and "requestAnimationFrame" not in javascript
            and "@keyframes" not in css
            and "animation:" not in css,
        },
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "schema": AUDIT_SCHEMA,
        "audited_at": observed_at.isoformat().replace("+00:00", "Z"),
        "state": "pass" if passed else "blocked",
        "passed": passed,
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "authority": NON_AUTHORITATIVE_AUTHORITY,
        "contract": {
            "component_id": contract["component_id"],
            "path": _relative_to_repo(root, resolved_contract),
            "sha256": _sha256(resolved_contract),
        },
        "claim_register": {
            "path": DEFAULT_CLAIM_REGISTER_PATH.as_posix(),
            "sha256": contract["claim_register"]["sha256"],
            "audit_schema": claim_receipt["schema"],
            "passed": claim_receipt["passed"],
            "claim_ids": list(_EXPECTED_CLAIM_IDS),
        },
        "outputs": {
            name: {
                "bytes": sizes[name],
                "sha256": _bytes_sha256(value),
            }
            for name, value in outputs.items()
        },
        "checks": checks,
        "bundle_sha256": _json_sha256(
            {
                name: {
                    "bytes": sizes[name],
                    "sha256": _bytes_sha256(value),
                }
                for name, value in outputs.items()
            }
        ),
        "next_gate": (
            "Select and back up the live source, then bind these exact outputs to a "
            "fresh candidate work order and named human visual acceptance."
        ),
    }


def audit_hnc_evidence_graph_contract_file(
    contract_path: Path | None = None,
    *,
    repo_root: Path | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    root = _find_repo_root(repo_root)
    source = contract_path or DEFAULT_CONTRACT_PATH
    resolved = source if source.is_absolute() else root / source
    resolved = resolved.resolve()
    _relative_to_repo(root, resolved)
    if not resolved.is_file() or resolved.is_symlink():
        raise HNCEvidenceGraphError("HNC graph contract must be one regular file.")
    return audit_hnc_evidence_graph_contract(
        _read_json(resolved, label="HNC graph contract"),
        contract_path=resolved,
        repo_root=root,
        as_of=as_of,
    )


def write_hnc_evidence_graph_bundle(
    contract_path: Path | None = None,
    *,
    repo_root: Path | None = None,
    as_of: datetime | None = None,
) -> Path:
    """Write one immutable source-neutral bundle below the component artifact root."""

    root = _find_repo_root(repo_root)
    source = contract_path or DEFAULT_CONTRACT_PATH
    resolved = source if source.is_absolute() else root / source
    resolved = resolved.resolve()
    contract = _read_json(resolved, label="HNC graph contract")
    receipt = audit_hnc_evidence_graph_contract(contract, contract_path=resolved, repo_root=root, as_of=as_of)
    if receipt["passed"] is not True:
        raise HNCEvidenceGraphError("Blocked HNC graph contract cannot write a bundle.")
    target = (root / DEFAULT_COMPONENT_ROOT / str(contract["component_id"])).resolve()
    allowed = (root / DEFAULT_COMPONENT_ROOT).resolve()
    try:
        target.relative_to(allowed)
    except ValueError as exc:
        raise HNCEvidenceGraphError("HNC graph artifact target escapes its root.") from exc
    if target.exists():
        raise HNCEvidenceGraphError("HNC graph artifact bundle already exists.")
    target.mkdir(parents=True)
    steps, claims, _claim_receipt = _contract_and_claims(
        contract,
        contract_path=resolved,
        repo_root=root,
        as_of=(as_of or datetime.now(UTC)).astimezone(UTC),
    )
    outputs = {
        "component.html": render_hnc_evidence_graph_html(steps, claims),
        "component.css": render_hnc_evidence_graph_css(),
        "component.js": render_hnc_evidence_graph_javascript(),
    }
    for name, value in outputs.items():
        (target / name).write_text(value, encoding="utf-8", newline="\n")
    bundle = {
        "schema": BUNDLE_SCHEMA,
        "component_id": contract["component_id"],
        "authority": NON_AUTHORITATIVE_AUTHORITY,
        "contract": receipt["contract"],
        "claim_register": receipt["claim_register"],
        "outputs": receipt["outputs"],
        "bundle_sha256": receipt["bundle_sha256"],
        "checks": receipt["checks"],
        "next_gate": receipt["next_gate"],
    }
    (target / "bundle.v1.json").write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return target


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit or write the source-neutral HNC evidence graph bundle."
    )
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--write-bundle", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.write_bundle:
        path = write_hnc_evidence_graph_bundle(args.contract, repo_root=args.repo_root)
        print(path)
        return 0
    receipt = audit_hnc_evidence_graph_contract_file(args.contract, repo_root=args.repo_root)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if receipt["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
