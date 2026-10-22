#!/usr/bin/env python3
"""
Aureon Radar — Lightweight Agency Company of Agents
=====================================================
Offline consensus wrapper wired to queen_mind.

Reads the real-data volatility scanner, HNC core state, and harmonic phase,
then produces a compact consensus report that the Queen can ingest through
her battle-view senses.

Output:
  aureon_fusion/state/queen_mind/agency_company_report.json
Event:
  radar.agency_report on the organism's event spine.
"""

from __future__ import annotations

import json
import math
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Paths: this file lives in aureon_radar/; the report goes to aureon_fusion/state/queen_mind/
_RADAR_ROOT = Path(__file__).resolve().parent
_FUSION_STATE = _RADAR_ROOT.parent / "aureon_fusion" / "state"
_QUEEN_MIND_DIR = _FUSION_STATE / "queen_mind"
REPORT_PATH = _QUEEN_MIND_DIR / "agency_company_report.json"

_VOLATILITY_SCAN_PATH = _RADAR_ROOT / "state" / "volatility_scan.json"
_HNC_STATE_PATH = _FUSION_STATE / "hnc_core_state.json"
_HARMONIC_PATH = _RADAR_ROOT / "state" / "harmonic_phase.json"
_AURIS_PATH = _RADAR_ROOT / "state" / "auris_nodes.json"


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            return payload if isinstance(payload, dict) else default
    except Exception:
        pass
    return default


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _finite(v: Any) -> Optional[float]:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)) and math.isfinite(v):
        return float(v)
    return None


@dataclass
class AgentOpinion:
    agent_id: str
    role: str
    view: str  # bullish / bearish / neutral / blocked
    confidence: float
    evidence: List[str]
    blockers: List[str]


@dataclass
class ConsensusReport:
    ts: str
    ts_epoch: float
    schema_version: str
    top_target: Optional[Dict[str, Any]]
    consensus: str
    confidence: float
    agents: List[Dict[str, Any]]
    blockers: List[str]
    hnc_gamma: Optional[float]
    harmonic_phase: Optional[str]
    auris_coherence: Optional[float]
    recommended_action: str
    size_hint: Optional[float]
    expected_net_profit_after_fees_pct: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AgencyCompany:
    """Offline company of agents that votes on the radar's top target."""

    SCHEMA_VERSION = "aureon-radar-agency-v1"

    def __init__(self):
        self.volatility_scan = _read_json(_VOLATILITY_SCAN_PATH, {}) or {}
        self.hnc = _read_json(_HNC_STATE_PATH, {}) or {}
        self.harmonic = _read_json(_HARMONIC_PATH, {}) or {}
        self.auris = _read_json(_AURIS_PATH, {}) or {}

    # ------------------------------------------------------------------
    # Agent roles
    # ------------------------------------------------------------------
    def _volatility_agent(self) -> AgentOpinion:
        top = self.volatility_scan.get("top_target")
        if top is None:
            ranking = self.volatility_scan.get("ranking") or []
            top = ranking[0] if ranking else None

        if not isinstance(top, dict):
            return AgentOpinion(
                agent_id="volatility_scout",
                role="Real-data volatility ranking",
                view="neutral",
                confidence=0.0,
                evidence=["no volatility scan data available"],
                blockers=["missing_scan"],
            )

        bias = str(top.get("directional_bias") or "NEUTRAL").upper()
        view = {"LONG": "bullish", "SHORT": "bearish"}.get(bias, "neutral")
        conf = _finite(top.get("confidence")) or 0.0
        blockers = list(top.get("blockers") or [])
        evidence = [
            f"top target {top.get('symbol')}@{top.get('venue')}",
            f"volatility_score={top.get('volatility_score')}",
            f"recommended_size={top.get('recommended_size')}",
            f"net_after_fees_pct={top.get('expected_net_profit_after_fees_pct')}",
        ]
        return AgentOpinion(
            agent_id="volatility_scout",
            role="Real-data volatility ranking",
            view=view,
            confidence=conf,
            evidence=evidence,
            blockers=blockers,
        )

    def _hnc_agent(self) -> AgentOpinion:
        gamma = _finite(self.hnc.get("coherence_gamma"))
        if gamma is None:
            gamma = _finite(self.hnc.get("gamma"))
        if gamma is None:
            gamma = _finite(self.hnc.get("coherence"))
        if gamma is None:
            gamma = _finite(self.hnc.get("Γ"))

        if gamma is None:
            return AgentOpinion(
                agent_id="hnc_gate",
                role="HNC coherence gate",
                view="neutral",
                confidence=0.0,
                evidence=["no HNC gamma reading"],
                blockers=["hnc_unavailable"],
            )

        view = "bullish" if gamma >= 0.7 else "neutral" if gamma >= 0.25 else "blocked"
        evidence = [f"HNC gamma={gamma:.3f}"]
        blockers = []
        if gamma < 0.25:
            blockers.append("hnc_incoherent")
        return AgentOpinion(
            agent_id="hnc_gate",
            role="HNC coherence gate",
            view=view,
            confidence=min(1.0, gamma),
            evidence=evidence,
            blockers=blockers,
        )

    def _harmonic_agent(self) -> AgentOpinion:
        symbols = self.harmonic.get("symbols") or {}
        if not symbols:
            return AgentOpinion(
                agent_id="harmonic_reader",
                role="Harmonic phase reader",
                view="neutral",
                confidence=0.0,
                evidence=["no harmonic phase data"],
                blockers=["harmonic_unavailable"],
            )

        # Use the first symbol with a phase hint; in practice GOLD is the
        # canonical harmonic anchor for the Aureon radar.
        phase_hint = "neutral"
        coherence: Optional[float] = None
        for key, entry in symbols.items():
            if isinstance(entry, dict):
                phase_hint = str(entry.get("phase_hint") or entry.get("phase") or "neutral").lower()
                coherence = _finite(entry.get("coherence"))
                break

        view_map = {
            "crest": "bullish",
            "in_phase": "bullish",
            "rising": "bullish",
            "trough": "bearish",
            "falling": "bearish",
            "neutral": "neutral",
        }
        view = view_map.get(phase_hint, "neutral")
        conf = min(1.0, coherence) if coherence is not None else 0.5
        return AgentOpinion(
            agent_id="harmonic_reader",
            role="Harmonic phase reader",
            view=view,
            confidence=conf,
            evidence=[f"harmonic phase={phase_hint}, coherence={coherence}"],
            blockers=[],
        )

    def _auris_agent(self) -> AgentOpinion:
        nodes = self.auris.get("nodes") or {}
        if not nodes:
            return AgentOpinion(
                agent_id="auris_reader",
                role="Auris coherence reader",
                view="neutral",
                confidence=0.0,
                evidence=["no auris node data"],
                blockers=["auris_unavailable"],
            )

        coherences = []
        for key, val in nodes.items():
            if isinstance(val, dict):
                c = _finite(val.get("coherence") or val.get("score"))
                if c is not None:
                    coherences.append(c)

        if not coherences:
            return AgentOpinion(
                agent_id="auris_reader",
                role="Auris coherence reader",
                view="neutral",
                confidence=0.0,
                evidence=["auris nodes present but no coherence values"],
                blockers=["auris_unavailable"],
            )

        avg = sum(coherences) / len(coherences)
        view = "bullish" if avg >= 0.6 else "neutral" if avg >= 0.3 else "blocked"
        return AgentOpinion(
            agent_id="auris_reader",
            role="Auris coherence reader",
            view=view,
            confidence=min(1.0, avg),
            evidence=[f"auris avg coherence={avg:.3f} across {len(coherences)} nodes"],
            blockers=["auris_incoherent"] if avg < 0.25 else [],
        )

    # ------------------------------------------------------------------
    # Consensus
    # ------------------------------------------------------------------
    _SOFT_BLOCKERS = {"auris_unavailable", "harmonic_unavailable", "auris_incoherent"}

    def _consensus(self, agents: List[AgentOpinion]) -> Tuple[str, float, List[str], List[str]]:
        """Return (consensus_view, confidence, hard_blockers, evidence).

        Soft blockers (e.g., optional auris/harmonic data missing) are recorded
        but do not block consensus when the volatility and HNC gates pass.
        """
        hard_blockers: List[str] = []
        soft_blockers: List[str] = []
        evidence: List[str] = []
        for a in agents:
            for b in a.blockers:
                if b in self._SOFT_BLOCKERS:
                    soft_blockers.append(b)
                else:
                    hard_blockers.append(b)
            evidence.extend(a.evidence)

        if hard_blockers:
            return "blocked", 0.0, sorted(set(hard_blockers + soft_blockers)), evidence

        # Consensus uses only agents that are not fully blocked
        usable = [a for a in agents if not (set(a.blockers) - self._SOFT_BLOCKERS)]
        if len(usable) < 2:
            return "blocked", 0.0, sorted(set(["insufficient_agent_quorum"] + soft_blockers)), evidence

        bullish = sum(a.confidence for a in usable if a.view == "bullish")
        bearish = sum(a.confidence for a in usable if a.view == "bearish")
        neutral = sum(a.confidence for a in usable if a.view == "neutral")
        total = bullish + bearish + neutral
        if total <= 0:
            return "neutral", 0.0, sorted(set(soft_blockers)), evidence

        blockers_out = sorted(set(soft_blockers))
        if bullish > bearish and bullish > neutral:
            return "bullish", min(1.0, bullish / total), blockers_out, evidence
        if bearish > bullish and bearish > neutral:
            return "bearish", min(1.0, bearish / total), blockers_out, evidence
        return "neutral", min(1.0, neutral / total), blockers_out, evidence

    def produce_report(self) -> ConsensusReport:
        agents = [
            self._volatility_agent(),
            self._hnc_agent(),
            self._harmonic_agent(),
            self._auris_agent(),
        ]

        top = self.volatility_scan.get("top_target")
        if top is None:
            ranking = self.volatility_scan.get("ranking") or []
            top = ranking[0] if ranking else None

        consensus, confidence, blockers, evidence = self._consensus(agents)

        recommended_action = "observe"
        # Soft blockers (missing optional sense layers) do not prevent action.
        hard_blockers = set(blockers) - self._SOFT_BLOCKERS
        if not hard_blockers and confidence >= 0.55:
            recommended_action = "shadow_probe" if confidence < 0.75 else "promote_for_execution"

        size_hint = _finite(top.get("recommended_size")) if isinstance(top, dict) else None
        net_pct = _finite(top.get("expected_net_profit_after_fees_pct")) if isinstance(top, dict) else None

        gamma = (_finite(self.hnc.get("coherence_gamma"))
                 or _finite(self.hnc.get("gamma"))
                 or _finite(self.hnc.get("coherence"))
                 or _finite(self.hnc.get("Γ")))
        harmonic_symbols = self.harmonic.get("symbols") or {}
        first_harmonic = next(iter(harmonic_symbols.values()), {}) if harmonic_symbols else {}
        harmonic_phase = str(first_harmonic.get("phase_hint") or first_harmonic.get("phase") or "neutral").lower() if isinstance(first_harmonic, dict) else None

        auris_nodes = self.auris.get("nodes") or {}
        auris_coherence = None
        if auris_nodes:
            vals = [_finite(v.get("coherence") or v.get("score")) for v in auris_nodes.values() if isinstance(v, dict)]
            vals = [v for v in vals if v is not None]
            if vals:
                auris_coherence = sum(vals) / len(vals)

        return ConsensusReport(
            ts=_utc_now_iso(),
            ts_epoch=time.time(),
            schema_version=self.SCHEMA_VERSION,
            top_target=top if isinstance(top, dict) else None,
            consensus=consensus,
            confidence=round(confidence, 4),
            agents=[asdict(a) for a in agents],
            blockers=sorted(set(blockers)),
            hnc_gamma=gamma,
            harmonic_phase=harmonic_phase,
            auris_coherence=auris_coherence,
            recommended_action=recommended_action,
            size_hint=size_hint,
            expected_net_profit_after_fees_pct=net_pct,
        )

    def write_report(self) -> Path:
        report = self.produce_report()
        _QUEEN_MIND_DIR.mkdir(parents=True, exist_ok=True)
        tmp = REPORT_PATH.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2, default=str)
        tmp.replace(REPORT_PATH)
        return REPORT_PATH


def _emit_event(report: ConsensusReport) -> Optional[Dict[str, Any]]:
    """Emit radar.agency_report on the organism's event spine."""
    try:
        if str(_RADAR_ROOT.parent) not in sys.path:
            sys.path.insert(0, str(_RADAR_ROOT.parent))
        from aureon_fusion import events
        return events.publish(
            source="agency_company",
            topic="radar.agency_report",
            payload={
                "ts": report.ts,
                "consensus": report.consensus,
                "confidence": report.confidence,
                "recommended_action": report.recommended_action,
                "top_symbol": report.top_target.get("symbol") if report.top_target else None,
                "blockers": report.blockers,
            },
            priority=5,
        )
    except Exception:
        return None


def main() -> ConsensusReport:
    company = AgencyCompany()
    report = company.produce_report()
    path = company.write_report()
    _emit_event(report)
    print(f"Agency consensus: {report.consensus} (conf={report.confidence:.2f}) -> {report.recommended_action}")
    print(f"Report written: {path}")
    if report.blockers:
        print(f"Blockers: {report.blockers}")
    return report


if __name__ == "__main__":
    main()
