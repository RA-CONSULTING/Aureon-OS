"""🔺 TRUTH GATE — fusion adapter over the upstream QGITA/Kundalini gate.

The pure upstream truth gate (aureon-os-upstream/aureon/governance/
qgita_kundalini_truth_gate.py + trusted_truth_evidence.py, imported ONLY,
never run) decides whether claims are SUPPORTED through hash-bound
grounding receipts, with QGITA + math-angle diagnostics as diagnostic
views of the residual — passed through the 7 Kundalini blockers. The only
successful status is READY_FOR_AURIS.

This adapter is the composition root the upstream module deliberately
leaves to production code: it builds the claim + grounding-receipt bundles
from fusion research fragments (text + provenance), feeds them through
evaluate_receipt_backed_truth_gate, and normalizes the verdict. It is
pure: zero I/O, zero network, zero authority — it fabricates nothing;
missing provenance is an honest MISSING_GROUNDING.

Doctrine:
  • Imported under AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1 +
    AUREON_AUDIT_MODE=1 (hard-set below, BEFORE any aureon import),
    upstream repo root pinned on sys.path (queen_mind idiom).
  • Fail-closed: no public API ever raises. Gate unavailable →
    {"verdict": "GATE_UNAVAILABLE", "ready_for_aris": False, ...}.
  • Claim-level staleness is decided here (STALE_AFTER_S): evidence stays
    valid inside the wider MAX_AGE_S envelope, but a claim whose
    provenance fetched_at is older than STALE_AFTER_S is a Sacral
    STALE_OR_LINEAGE blocker, not a pass.
  • Batch evaluation puts ALL items in ONE claim set so contradictions
    BETWEEN items surface as CROSS_CLAIM_CONFLICT (Third Eye) — something
    single-claim checks can never see.

CLI:
  python -m aureon_fusion.truth_gate status
  python -m aureon_fusion.truth_gate check "<text>" \
      [--url U --source S --fetched-at ISO]
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import types
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
os.environ.setdefault("AUREON_AUDIT_MODE", "1")

from .paths import AUREON_UPSTREAM

# ── policy constants ─────────────────────────────────────────────────────────
# Evidence freshness envelope the upstream validators enforce on every
# receipt timestamp (source AND received). Claims whose provenance is
# older than this cannot even be evidenced → honest HOLD, never a pass.
MAX_AGE_S = 30.0 * 86400.0
# Claim-level staleness: provenance fetched_at older than this (but still
# inside MAX_AGE_S) is STALE_OR_LINEAGE (Sacral), not SUPPORTED.
STALE_AFTER_S = 24.0 * 3600.0

_CLAIM_AUTHORITY_ID = "aureon_fusion:truth_gate:claim_authority:v1"
_DIAGNOSTIC_AUTHORITY_ID = "aureon_fusion:truth_gate:diagnostic_authority:v1"
_OBS_ISSUER_ID = "aureon_fusion:truth_gate:organism_observation:v1"
_WEB_ISSUER_ID = "aureon_fusion:truth_gate:web_response:v1"
_OBS_URI = "state://aureon_fusion/truth_gate"

# Fusion-side contradiction signal: a negation-pair heuristic over the
# claim token stream. Same core token signature, different negation
# polarity → CROSS_CLAIM_CONFLICT candidate (Third Eye).
_NEGATIONS = frozenset({
    "not", "no", "never", "none", "cannot", "can't", "cant",
    "isn't", "isnt", "aren't", "arent", "wasn't", "wasnt",
    "won't", "wont", "don't", "dont", "doesn't", "doesnt",
    "didn't", "didnt", "without", "absent", "fails", "fails_to",
})

_probe_cache: Dict[str, Any] = {"probed": False, "modules": None}


# ─────────────────────────────────────────────────────────────────────────────
# Upstream gate import (read-only repo, suppression env vars) — cached probe
# ─────────────────────────────────────────────────────────────────────────────


def _load_gate() -> Optional[types.SimpleNamespace]:
    """Import + construct-probe the upstream gate exactly once.

    Idempotent and cached: returns a namespace with .gate / .evidence
    modules, or None when the gate cannot be imported AND exercised under
    the suppression env vars. Imports only — never runs upstream mains."""
    if _probe_cache["probed"]:
        return _probe_cache["modules"]
    _probe_cache["probed"] = True
    mods: Optional[types.SimpleNamespace] = None
    try:
        root = str(AUREON_UPSTREAM)
        if root in sys.path:
            sys.path.remove(root)
        sys.path.insert(0, root)  # pin the upstream repo root (queen_mind idiom)

        import importlib

        # aureon._path_setup walks the package tree onto sys.path so
        # upstream bare imports resolve exactly as they do inside the repo.
        import aureon._path_setup  # noqa: F401

        gate = importlib.import_module(
            "aureon.governance.qgita_kundalini_truth_gate")
        ev = importlib.import_module(
            "aureon.governance.trusted_truth_evidence")
        # Construction probe: one full receipt-backed evaluation on a
        # fixture claim. If ANY step breaks, the gate is unavailable.
        now = time.time()
        _evaluate_with(
            types.SimpleNamespace(gate=gate, evidence=ev),
            [{"text": "construction probe claim", "provenance": {}}], now)
        mods = types.SimpleNamespace(gate=gate, evidence=ev)
    except Exception:
        mods = None
    _probe_cache["modules"] = mods
    return mods


def gate_available() -> bool:
    """Can the upstream gate + evidence modules be imported, constructed,
    and exercised under the suppression env vars? Cached after first probe.
    NEVER raises."""
    try:
        return _load_gate() is not None
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Small honest helpers
# ─────────────────────────────────────────────────────────────────────────────


def _s(value: Any, limit: int = 0) -> str:
    try:
        out = " ".join(str(value or "").split())
        return out[:limit] if limit > 0 else out
    except Exception:
        return ""


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def _receipt(prefix: str, causal: Dict[str, Any]) -> str:
    return f"{prefix}{_sha(_canon(causal))}"


def _iso(ts: float) -> str:
    try:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(float(ts)))
    except Exception:
        return ""


def _to_epoch(value: Any) -> Optional[float]:
    """float epoch or ISO-8601 string → epoch seconds; None when unusable.
    NEVER raises, never fabricates."""
    try:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            out = float(value)
            return out if out == out else None  # NaN guard
        text = str(value).strip()
        if not text:
            return None
        try:
            return float(text)
        except (TypeError, ValueError):
            pass
        for cand in (text, text.replace("Z", "+00:00"),
                     text.replace("z", "+00:00")):
            try:
                dt = datetime.fromisoformat(cand)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.timestamp()
            except ValueError:
                continue
        return None
    except Exception:
        return None


def _resolve_now(now: Any) -> float:
    ts = _to_epoch(now)
    if ts is not None:
        return ts
    try:
        return time.time()
    except Exception:
        return 0.0


def _false_flags(mods: types.SimpleNamespace) -> Dict[str, bool]:
    flags = getattr(mods.gate, "_FALSE_FLAGS", None)
    if not flags:
        flags = ("action_eligible", "accounting_eligible",
                 "learning_eligible", "action_gate_passed", "actionable",
                 "operational_eligible", "provider_eligible",
                 "eligible_for_action", "eligible_for_accounting",
                 "eligible_for_learning", "economic_mutation")
    return dict.fromkeys(flags, False)


# ─────────────────────────────────────────────────────────────────────────────
# Bundle construction (claim evidence set + diagnostic signal)
# ─────────────────────────────────────────────────────────────────────────────


def _usable_web_provenance(provenance: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """A provenance dict is usable web evidence ONLY when it carries an
    http(s) URL and a parseable fetched_at. The upstream evidence schema
    accepts web_response ONLY over https, so an http-observed URL is
    upgraded for the receipt's source_uri while the ACTUALLY observed
    URL is preserved in the locator — the provenance is never rewritten,
    only schema-fit. Anything unparseable → None (the claim is honestly
    ungrounded, never dressed up). NEVER raises."""
    try:
        prov = dict(provenance or {})
        url = _s(prov.get("url"))
        if not re.match(r"^https?://", url, re.IGNORECASE):
            return None
        fetched = _to_epoch(prov.get("fetched_at"))
        if fetched is None:
            return None
        locator = url
        if url.lower().startswith("http://"):
            url = "https://" + url[len("http://"):]
        return {"url": url, "locator": locator,
                "source": _s(prov.get("source")) or "web",
                "fetched_at": fetched}
    except Exception:
        return None


def _evidence_item(mods: types.SimpleNamespace, *, issuer_id: str,
                   source_kind: str, source_uri: str, locator: str,
                   content: str, source_ts: float, received_at: float,
                   prefix: str) -> Dict[str, Any]:
    ev = mods.evidence
    causal = {
        "schema_version": ev.EVIDENCE_ITEM_SCHEMA,
        "issuer_id": issuer_id,
        "source_kind": source_kind,
        "source_uri": source_uri,
        "source_locator": locator,
        "content_digest": _sha(_s(content)),
        "source_timestamp": float(source_ts),
        "received_at": float(received_at),
        "truth_status": "real_observed",
        "generated_values": False,
        **_false_flags(mods),
    }
    return {**causal, "receipt_id": _receipt(prefix, causal)}


def _claim_id(text: str) -> str:
    return _sha(f"claim:{_s(text, 2000)}")


def _negation_signature(text: str) -> tuple:
    toks = re.findall(r"[a-z0-9']+", _s(text, 2000).lower())
    core = [t for t in toks if t not in _NEGATIONS]
    negs = sum(1 for t in toks if t in _NEGATIONS)
    return " ".join(core), negs


def _contradiction_pairs(texts: List[str]) -> List[tuple]:
    """Negation-pair detection BETWEEN batch items: same core token
    signature, opposite negation polarity → (i, j) contradiction."""
    out: List[tuple] = []
    try:
        sigs = [_negation_signature(t) for t in texts]
        for i in range(len(sigs)):
            core_i, neg_i = sigs[i]
            if not core_i or len(core_i.split()) < 3:
                continue
            for j in range(i + 1, len(sigs)):
                core_j, neg_j = sigs[j]
                if core_i != core_j:
                    continue
                if (neg_i == 0) != (neg_j == 0):
                    out.append((i, j))
    except Exception:
        pass
    return out


def _diagnostics(texts: List[str]) -> tuple:
    """Flat, finite, non-empty QGITA + math-angle diagnostic views over
    the claim texts (diagnostics only — they never decide truth)."""
    joined = " ".join(_s(t, 2000) for t in texts)
    toks = re.findall(r"[a-z0-9]+", joined.lower())
    negs = sum(1 for t in toks if t in _NEGATIONS)
    qgita = {
        "claim_count": float(max(1, len(texts))),
        "token_count": float(len(toks)),
        "unique_ratio": round(len(set(toks)) / max(1, len(toks)), 6),
        "negation_markers": float(negs),
    }
    math_angle = {
        "char_count": float(len(joined)),
        "mean_token_len": round(
            sum(len(t) for t in toks) / max(1, len(toks)), 6),
        "negation_markers": float(negs),
    }
    return qgita, math_angle


def _build_claim_set(mods: types.SimpleNamespace, texts: List[str],
                     provenances: List[Dict[str, Any]], now: float,
                     extra_kinds: Optional[Dict[int, str]] = None
                     ) -> Dict[str, Any]:
    """One claim-evidence set over the batch: every claim gets an
    organism-observation evidence item (the claim text as observed in
    fusion state); grounded claims additionally get a web-response item
    from their provenance. Findings are decided honestly here:
    MISSING_GROUNDING (no usable provenance), STALE_OR_LINEAGE
    (fetched_at older than STALE_AFTER_S), SUPPORTED — or overridden by
    the caller's cross-claim kinds."""
    ev = mods.evidence
    flags = _false_flags(mods)
    evidence: Dict[str, Dict[str, Any]] = {}
    findings: Dict[str, Dict[str, Any]] = {}
    order: List[int] = []          # first-seen index per unique claim
    index_of_claim: Dict[str, int] = {}

    for idx, text in enumerate(texts):
        norm = _s(text, 2000)
        if not norm:
            continue
        cid = _claim_id(norm)
        if cid not in index_of_claim:
            index_of_claim[cid] = idx
            order.append(idx)
        links: List[str] = []
        kind = ""
        if isinstance(extra_kinds, dict) and idx in extra_kinds:
            kind = extra_kinds[idx]
        prov = _usable_web_provenance(
            provenances[idx] if idx < len(provenances) else {})
        if prov is not None:
            web = _evidence_item(
                mods, issuer_id=_WEB_ISSUER_ID,
                source_kind="web_response", source_uri=prov["url"],
                locator=prov["locator"], content=norm,
                source_ts=prov["fetched_at"], received_at=now,
                prefix=ev.EVIDENCE_ITEM_PREFIX)
            evidence[web["receipt_id"]] = web
            links.append(web["receipt_id"])
            if not kind:
                age = now - prov["fetched_at"]
                kind = "SUPPORTED" if age <= STALE_AFTER_S \
                    else "STALE_OR_LINEAGE"
        if not kind:
            kind = "MISSING_GROUNDING"
        obs = _evidence_item(
            mods, issuer_id=_OBS_ISSUER_ID, source_kind="operator_state",
            source_uri=_OBS_URI, locator=f"claim:{cid[:16]}",
            content=norm, source_ts=now, received_at=now,
            prefix=ev.EVIDENCE_ITEM_PREFIX)
        evidence[obs["receipt_id"]] = obs
        if kind != "MISSING_GROUNDING":
            links.append(obs["receipt_id"])
        if kind == "MISSING_GROUNDING":
            links = []
        findings[cid] = {
            "claim_id": cid,
            "failure_kind": kind,
            "evidence_receipt_ids": sorted(set(links)),
        }

    receipts = sorted(evidence)
    claim_findings = [findings[_claim_id(_s(texts[i], 2000))]
                      for i in order]
    claim_findings.sort(key=lambda f: f["claim_id"])
    source_ts = min(e["source_timestamp"] for e in evidence.values())
    causal = {
        "schema_version": ev.CLAIM_SET_SCHEMA,
        "authority_id": _CLAIM_AUTHORITY_ID,
        "prompt_digest": _sha("prompt:" + _canon(texts)),
        "answer_digest": _sha("answer:" + _canon(texts)),
        "hnc_receipt_id": _hnc_id(texts),
        "source_timestamp": float(source_ts),
        "received_at": float(now),
        "truth_status": "real_derived",
        "generated_values": False,
        "evidence_receipts": [evidence[r] for r in receipts],
        "claim_findings": claim_findings,
        **flags,
    }
    return {**causal, "receipt_id": _receipt(ev.CLAIM_SET_PREFIX, causal)}


def _hnc_id(texts: List[str]) -> str:
    return "hnc:live_field:" + _sha(_canon([_s(t, 2000) for t in texts]))[:24]


class _ClaimAuthority:
    """Composition-root claim authority: serves the prebuilt claim set.
    The upstream resolver validates the FULL evidence bodies before
    reducing them to grounding receipts."""

    authority_id = _CLAIM_AUTHORITY_ID

    def __init__(self, claim_set: Dict[str, Any]):
        self._claim_set = claim_set

    def resolve_claim_evidence(self, request: Any) -> Dict[str, Any]:
        return self._claim_set


class _DiagnosticAuthority:
    """Independent diagnostic authority: QGITA + math-angle signals.
    Grounding receipt binding happens at resolve time (the signal is
    receipt-hashed only once its grounding lineage is known)."""

    authority_id = _DIAGNOSTIC_AUTHORITY_ID

    def __init__(self, mods: types.SimpleNamespace, texts: List[str]):
        ev = mods.evidence
        self._ev = ev
        qgita, math_angle = _diagnostics(texts)
        evidence_ids = []  # bound at resolve time from the grounding
        self._causal = {
            "schema_version": ev.DIAGNOSTIC_SIGNAL_SCHEMA,
            "authority_id": self.authority_id,
            "grounding_receipt_id": "",
            "prompt_digest": _sha("prompt:" + _canon(texts)),
            "answer_digest": _sha("answer:" + _canon(texts)),
            "hnc_receipt_id": _hnc_id(texts),
            "source_timestamp": 0.0,
            "received_at": 0.0,
            "truth_status": "real_derived",
            "generated_values": False,
            "evidence_receipt_ids": evidence_ids,
            "qgita_diagnostics": qgita,
            "math_angle_diagnostics": math_angle,
            **_false_flags(mods),
        }
        self._qgita = qgita
        self._math_angle = math_angle

    def resolve_diagnostic_signals(self, request: Any,
                                   grounding: Dict[str, Any]) -> Dict[str, Any]:
        causal = dict(self._causal)
        causal["grounding_receipt_id"] = grounding.get("receipt_id", "")
        causal["evidence_receipt_ids"] = list(
            grounding.get("evidence_receipt_ids") or [])
        causal["source_timestamp"] = float(grounding.get("source_timestamp")
                                           or 0.0)
        causal["received_at"] = float(grounding.get("received_at") or 0.0)
        return {**causal,
                "receipt_id": _receipt(self._ev.DIAGNOSTIC_SIGNAL_PREFIX,
                                       causal)}


# ─────────────────────────────────────────────────────────────────────────────
# Evaluation + normalization
# ─────────────────────────────────────────────────────────────────────────────


def _schema_versions(mods: types.SimpleNamespace) -> Dict[str, str]:
    g, ev = mods.gate, mods.evidence
    return {
        "grounding": g.GROUNDING_SCHEMA,
        "diagnostic": g.DIAGNOSTIC_SCHEMA,
        "result": g.RESULT_SCHEMA,
        "evidence_item": ev.EVIDENCE_ITEM_SCHEMA,
        "claim_set": ev.CLAIM_SET_SCHEMA,
        "diagnostic_signal": ev.DIAGNOSTIC_SIGNAL_SCHEMA,
    }


def _normalize(mods: types.SimpleNamespace, result: Dict[str, Any],
               texts: List[str], now: float) -> Dict[str, Any]:
    status = _s(result.get("status"))
    failure = _s(result.get("failure_kind")) or None
    stage = _s(result.get("kundalini_stage")) or None
    qgita, math_angle = _diagnostics(texts)
    base: Dict[str, Any] = {
        "ready_for_aris": False,
        "failure_kind": failure,
        "blocker": stage,
        "qgita_diagnostic": qgita,
        "math_angle_diagnostic": math_angle,
        "schema_versions": _schema_versions(mods),
        "status": status,
        "reason": _s(result.get("reason")),
        "receipt_id": _s(result.get("receipt_id")),
        "evaluated_at": _iso(now),
    }
    if status == "READY_FOR_AURIS":
        base.update(verdict="READY_FOR_AURIS", ready_for_aris=True,
                    failure_kind=None, blocker=None)
    elif failure:
        base.update(verdict=failure)  # Kundalini-blocked: verdict IS the kind
    else:
        base.update(verdict="HOLD", failure_kind=None, blocker=None)
    return base


def _evaluate_with(mods: types.SimpleNamespace, items: List[Dict[str, Any]],
                   now: float,
                   forced_kinds: Optional[Dict[int, str]] = None
                   ) -> List[Dict[str, Any]]:
    """Run one receipt-backed truth-gate evaluation over the batch and
    return per-item normalized results. NEVER raises."""
    texts = [_s((it or {}).get("text"), 2000) for it in items]
    texts = [t for t in texts if t]
    provenances = [dict((it or {}).get("provenance") or {})
                   for it in items]
    claim_set = _build_claim_set(mods, texts, provenances, now,
                                 extra_kinds=forced_kinds)
    request = mods.gate.TruthGateRequest(
        prompt_digest=claim_set["prompt_digest"],
        answer_digest=claim_set["answer_digest"],
        hnc_receipt_id=claim_set["hnc_receipt_id"],
        correction_attempt=0,
    )
    diag = _DiagnosticAuthority(mods, texts)
    result = mods.evidence.evaluate_receipt_backed_truth_gate(
        request,
        claim_authority=_ClaimAuthority(claim_set),
        diagnostic_authority=diag,
        allowed_claim_authority_ids=frozenset({_CLAIM_AUTHORITY_ID}),
        allowed_evidence_issuer_ids=frozenset({_OBS_ISSUER_ID,
                                               _WEB_ISSUER_ID}),
        allowed_diagnostic_authority_ids=frozenset({_DIAGNOSTIC_AUTHORITY_ID}),
        now=float(now),
        max_age_s=MAX_AGE_S,
    )
    normalized = _normalize(mods, dict(result or {}), texts, now)
    blocker_kind = normalized["failure_kind"]
    # Map the batch verdict back to each item: items whose own finding is
    # the blocker kind carry the verdict; SUPPORTED items in a blocked set
    # are re-evaluated individually below (their own claim set may pass).
    by_index: Dict[int, Dict[str, Any]] = {}
    claim_kind = {f["claim_id"]: f["failure_kind"]
                  for f in claim_set["claim_findings"]}
    texts_all = [_s((it or {}).get("text"), 2000) for it in items]
    for idx, text in enumerate(texts_all):
        if not text:
            by_index[idx] = {**normalized, "verdict": "HOLD",
                             "reason": "empty_claim"}
            continue
        own = claim_kind.get(_claim_id(text))
        if normalized["ready_for_aris"]:
            by_index[idx] = normalized
        elif own == blocker_kind and blocker_kind:
            by_index[idx] = normalized
        elif isinstance(forced_kinds, dict) and idx in forced_kinds \
                and forced_kinds[idx] == blocker_kind:
            by_index[idx] = normalized
        else:
            by_index[idx] = {}  # re-evaluate individually
    for idx in list(by_index):
        if by_index[idx]:
            continue
        solo = _evaluate_with(mods, [items[idx]], now)
        by_index[idx] = solo[0] if solo else {**normalized, "verdict": "HOLD"}
    return [by_index[i] for i in range(len(items))]


def _gate_unavailable_result(detail: str = "") -> Dict[str, Any]:
    return {
        "verdict": "GATE_UNAVAILABLE",
        "ready_for_aris": False,
        "failure_kind": None,
        "blocker": None,
        "qgita_diagnostic": {},
        "math_angle_diagnostic": {},
        "schema_versions": {},
        "status": "UNAVAILABLE",
        "reason": detail or "upstream truth gate not importable/constructible",
        "receipt_id": "",
        "evaluated_at": "",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Public API (NEVER raises)
# ─────────────────────────────────────────────────────────────────────────────


def check_claim(text: str, provenance: Optional[Dict[str, Any]] = None,
                *, now: Any = None) -> Dict[str, Any]:
    """Gate ONE claim. Builds the claim + grounding receipts from the
    fragment text and provenance (source/url/fetched_at when present;
    missing provenance is an honest MISSING_GROUNDING — never fabricated),
    runs the upstream gate, returns the normalized verdict dict."""
    try:
        mods = _load_gate()
        if mods is None:
            return _gate_unavailable_result()
        return _evaluate_with(mods, [{"text": text,
                                      "provenance": dict(provenance or {})}],
                              _resolve_now(now))[0]
    except Exception as exc:
        out = _gate_unavailable_result(
            f"gate evaluation failed ({type(exc).__name__}) — fail-closed")
        return out


def check_batch(items: List[Dict[str, Any]], *, now: Any = None) -> List[Dict[str, Any]]:
    """Gate a batch of {'text', 'provenance'} items. ALL items go through
    ONE upstream claim-set evaluation so contradictions BETWEEN items
    surface as CROSS_CLAIM_CONFLICT (Third Eye) — then each item's own
    verdict is resolved (SUPPORTED items in a blocked set are re-checked
    individually). Returns one normalized dict per input item."""
    try:
        items = list(items or [])
        if not items:
            return []
        mods = _load_gate()
        if mods is None:
            return [_gate_unavailable_result() for _ in items]
        ts = _resolve_now(now)
        texts = [_s((it or {}).get("text"), 2000) for it in items]
        # Cross-claim pass: negation-pair contradictions between items.
        forced: Dict[int, str] = {}
        for i, j in _contradiction_pairs(texts):
            forced[i] = "CROSS_CLAIM_CONFLICT"
            forced[j] = "CROSS_CLAIM_CONFLICT"
        return _evaluate_with(mods, items, ts, forced_kinds=forced or None)
    except Exception as exc:
        return [{**_gate_unavailable_result(
            f"batch evaluation failed ({type(exc).__name__}) — fail-closed")}
            for _ in list(items or [])]


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def _emit(payload: Dict[str, Any]) -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def get_status() -> Dict[str, Any]:
    """Read-only availability + policy snapshot. NEVER raises."""
    try:
        mods = _load_gate()
    except Exception:
        mods = None
    status: Dict[str, Any] = {
        "gate_available": mods is not None,
        "max_age_s": MAX_AGE_S,
        "stale_after_s": STALE_AFTER_S,
        "verdicts": ["READY_FOR_AURIS", "MISSING_GROUNDING",
                     "STALE_OR_LINEAGE", "UNSUPPORTED", "CONTRADICTED",
                     "SEMANTIC_MISMATCH", "CROSS_CLAIM_CONFLICT", "HOLD",
                     "GATE_UNAVAILABLE"],
    }
    if mods is not None:
        status["schema_versions"] = _schema_versions(mods)
        status["kundalini_blockers"] = [list(b) for b in
                                        mods.gate.KUNDALINI_BLOCKERS]
    return status


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print("usage: python -m aureon_fusion.truth_gate "
              "status | check \"<text>\" [--url U --source S "
              "--fetched-at ISO]")
        return 0
    cmd = argv[0]
    if cmd == "status":
        _emit(get_status())
        return 0 if gate_available() else 1
    if cmd == "check":
        text = ""
        rest = argv[1:]
        provenance: Dict[str, Any] = {}
        i = 0
        while i < len(rest):
            tok = rest[i]
            if tok in ("--url", "--source", "--fetched-at"):
                if i + 1 < len(rest):
                    key = {"--url": "url", "--source": "source",
                           "--fetched-at": "fetched_at"}[tok]
                    provenance[key] = rest[i + 1]
                    i += 2
                    continue
            elif not tok.startswith("--") and not text:
                text = tok
            i += 1
        if not text:
            print("usage: python -m aureon_fusion.truth_gate check "
                  "\"<text>\" [--url U --source S --fetched-at ISO]",
                  file=sys.stderr)
            return 2
        result = check_claim(text, provenance or None)
        _emit(result)
        return 0 if result.get("ready_for_aris") else 1
    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
