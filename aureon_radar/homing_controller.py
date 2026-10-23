#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           AUREON HOMING CONTROLLER — DYNAMIC MARKET FOCUS                    ║
║                                                                              ║
║  Picks the single highest-opportunity market for the organism to hunt,       ║
║  using real volatility, agency consensus, HNC coherence, and Auris state.    ║
║                                                                              ║
║  When a clear target emerges the radar stops scanning the full watchlist     ║
║  and concentrates all live execution resources on that symbol.               ║
║                                                                              ║
║  Output: aureon_radar/state/homing_target.json                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import json
import math
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_RADAR_ROOT = Path(__file__).resolve().parent
_STATE_DIR = _RADAR_ROOT / "state"
_STATE_DIR.mkdir(parents=True, exist_ok=True)
_OUT_PATH = _STATE_DIR / "homing_target.json"

_VOLATILITY_SCAN_PATH = _STATE_DIR / "volatility_scan.json"
_AGENCY_REPORT_PATH = _RADAR_ROOT.parent / "aureon_fusion" / "state" / "queen_mind" / "agency_company_report.json"
_HNC_STATE_PATH = _RADAR_ROOT.parent / "aureon_fusion" / "state" / "hnc_core_state.json"
_AURIS_PATH = _STATE_DIR / "auris_nodes.json"

# Environment-tunable controls
_HOMING_ENABLED = (os.getenv("HOMING_ENABLED", "1").strip().lower() in ("1", "true", "yes"))
_HOMING_THRESHOLD = float(os.getenv("HOMING_THRESHOLD", "0.55"))
_HOMING_MAX_SYMBOLS = int(os.getenv("HOMING_MAX_SYMBOLS", "1"))
_HOMING_TTL_SEC = float(os.getenv("HOMING_TTL_SEC", "120"))

# Direction vocabulary used across the radar
_LONG_NAMES = {"LONG", "BUY", "BULLISH"}
_SHORT_NAMES = {"SHORT", "SELL", "BEARISH"}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            return payload if isinstance(payload, dict) else default
    except Exception:
        pass
    return default


def _finite(v: Any) -> Optional[float]:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)) and math.isfinite(v):
        return float(v)
    return None


def _normalize_direction(d: Any) -> str:
    s = str(d or "").strip().upper()
    if s in _LONG_NAMES:
        return "LONG"
    if s in _SHORT_NAMES:
        return "SHORT"
    return "NEUTRAL"


def _direction_agreement(vol_bias: str, agency_view: str) -> float:
    """Return 1.0 when volatility bias and agency view agree, 0.5 neutral, 0.0 conflict."""
    vol = _normalize_direction(vol_bias)
    agency = _normalize_direction(agency_view)
    if vol == "NEUTRAL" or agency == "NEUTRAL":
        return 0.75
    return 1.0 if vol == agency else 0.0


@dataclass
class HomingTarget:
    symbol: str = ""
    direction: str = "NEUTRAL"
    venue: str = "capital"
    category: str = ""
    price: float = 0.0
    homing_score: float = 0.0
    volatility_score: float = 0.0
    confidence: float = 0.0
    consensus: str = "neutral"
    agency_confidence: float = 0.0
    hnc_gamma: Optional[float] = None
    recommended_size: float = 0.0
    blockers: List[str] = field(default_factory=list)
    ttl_sec: float = _HOMING_TTL_SEC
    generated_at: str = field(default_factory=_utc_now_iso)
    expires_at: float = field(default_factory=lambda: time.time() + _HOMING_TTL_SEC)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def is_valid(self) -> bool:
        return (
            self.symbol
            and self.homing_score >= _HOMING_THRESHOLD
            and self.direction in ("LONG", "SHORT")
            and not self.blockers
            and not self.is_expired()
        )


class HomingController:
    """Select the organism's active hunting target from scanner consensus."""

    def __init__(self):
        self.enabled = _HOMING_ENABLED
        self.threshold = _HOMING_THRESHOLD
        self.max_symbols = _HOMING_MAX_SYMBOLS
        self.ttl_sec = _HOMING_TTL_SEC

    def _load_inputs(self) -> Dict[str, Any]:
        return {
            "volatility": _read_json(_VOLATILITY_SCAN_PATH, {}) or {},
            "agency": _read_json(_AGENCY_REPORT_PATH, {}) or {},
            "hnc": _read_json(_HNC_STATE_PATH, {}) or {},
            "auris": _read_json(_AURIS_PATH, {}) or {},
        }

    def _hnc_gamma(self, hnc: Dict[str, Any]) -> Optional[float]:
        for key in ("coherence_gamma", "gamma", "coherence", "Γ"):
            g = _finite(hnc.get(key))
            if g is not None:
                return g
        return None

    def _auris_coherence(self, auris: Dict[str, Any]) -> Optional[float]:
        nodes = auris.get("nodes") or {}
        vals = []
        for v in nodes.values():
            if isinstance(v, dict):
                c = _finite(v.get("coherence") or v.get("score"))
                if c is not None:
                    vals.append(c)
        return sum(vals) / len(vals) if vals else None

    def _scan_age_sec(self, scan: Dict[str, Any]) -> float:
        ts = scan.get("ts") or scan.get("generated_at")
        if not ts:
            return float("inf")
        try:
            # Handle both epoch floats and ISO strings
            if isinstance(ts, (int, float)):
                return time.time() - float(ts)
            ts_norm = str(ts).replace("Z", "+00:00")
            return time.time() - datetime.fromisoformat(ts_norm).timestamp()
        except Exception:
            return float("inf")

    def _score_candidate(self, cand: Dict[str, Any], agency: Dict[str, Any], hnc: Dict[str, Any]) -> Optional[HomingTarget]:
        blockers = list(cand.get("blockers") or [])

        # Reject stale or malformed candidates
        symbol = str(cand.get("symbol") or "").strip().upper()
        if not symbol:
            return None
        if not cand.get("trade_allowed"):
            blockers.append("trade_not_allowed")

        direction = _normalize_direction(cand.get("directional_bias"))
        if direction == "NEUTRAL":
            blockers.append("neutral_bias")

        vol_score = _finite(cand.get("volatility_score")) or 0.0
        conf = _finite(cand.get("confidence")) or 0.0
        if vol_score <= 0 or conf <= 0:
            blockers.append("no_volatility_or_confidence")

        # Agency consensus agreement
        agency_top = agency.get("top_target") or {}
        agency_consensus = str(agency.get("consensus") or "neutral").lower()
        agency_conf = _finite(agency.get("confidence")) or 0.0
        if agency_top.get("symbol") == symbol:
            agreement = _direction_agreement(direction, agency_consensus)
        else:
            # Agency top target differs from volatility top target — mild penalty
            agreement = 0.5

        gamma = self._hnc_gamma(hnc)
        auris_c = self._auris_coherence(_read_json(_AURIS_PATH, {}) or {})

        # HNC coherence gate: below 0.25 we do not home
        if gamma is not None and gamma < 0.25:
            blockers.append("hnc_incoherent")

        # Base score
        score = vol_score * conf * agreement

        # Boosts
        if gamma is not None and gamma >= 0.7:
            score *= 1.2
        if auris_c is not None and auris_c >= 0.6:
            score *= 1.1
        if agency_top.get("symbol") == symbol and agency_conf >= 0.7:
            score *= 1.15

        # Cap
        score = min(1.0, score)

        return HomingTarget(
            symbol=symbol,
            direction=direction,
            venue=str(cand.get("venue") or "capital").lower(),
            category=str(cand.get("category") or "").lower(),
            price=_finite(cand.get("price")) or 0.0,
            homing_score=round(score, 4),
            volatility_score=round(vol_score, 4),
            confidence=round(conf, 4),
            consensus=agency_consensus,
            agency_confidence=round(agency_conf, 4),
            hnc_gamma=gamma,
            recommended_size=_finite(cand.get("recommended_size")) or 0.0,
            blockers=blockers,
            ttl_sec=self.ttl_sec,
        )

    def _refresh_volatility_scan(self) -> Optional[Dict[str, Any]]:
        """Trigger a fresh volatility scan if the persisted one is stale."""
        try:
            sys_path = str(_RADAR_ROOT)
            import sys
            if sys_path not in sys.path:
                sys.path.insert(0, sys_path)
            from scanners.aureon_volatility_scanner import VolatilityScanner
            scanner = VolatilityScanner()
            scanner.scan_all()
            return _read_json(_VOLATILITY_SCAN_PATH, {}) or {}
        except Exception as exc:
            # Fail-open: log and continue with whatever is on disk
            print(f"[HOMING] volatility refresh failed: {exc}")
            return None

    def select_target(self) -> Optional[HomingTarget]:
        """Pick the best homing target or return None if nothing qualifies."""
        if not self.enabled:
            return None

        inputs = self._load_inputs()
        vol_scan = inputs["volatility"]
        agency = inputs["agency"]
        hnc = inputs["hnc"]

        # Refresh stale volatility scans so homing always has fresh data
        scan_age = self._scan_age_sec(vol_scan)
        if scan_age > self.ttl_sec:
            refreshed = self._refresh_volatility_scan()
            if refreshed:
                vol_scan = refreshed

        ranking = vol_scan.get("ranking") or []
        if not ranking:
            top = vol_scan.get("top_target")
            ranking = [top] if top else []

        candidates: List[HomingTarget] = []
        for cand in ranking[:5]:
            if not isinstance(cand, dict):
                continue
            target = self._score_candidate(cand, agency, hnc)
            if target is None:
                continue
            candidates.append(target)

        # Sort by score descending, then by confidence
        candidates.sort(key=lambda t: (t.homing_score, t.confidence), reverse=True)
        chosen = candidates[: self.max_symbols]

        if not chosen:
            return None

        # If the top choice has blockers but a score above threshold, still return
        # it so the caller can log the blockers; the caller decides whether to trade.
        top = chosen[0]
        if top.homing_score < self.threshold:
            return None

        return top

    def write_state(self, target: Optional[HomingTarget]) -> None:
        payload = {
            "ts": _utc_now_iso(),
            "homing_enabled": self.enabled,
            "threshold": self.threshold,
            "target": target.to_dict() if target else None,
        }
        try:
            with open(_OUT_PATH, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as exc:
            # Fail-open logging only
            print(f"[HOMING] failed to write state: {exc}")

    def get_target(self) -> Optional[HomingTarget]:
        """Public API: select and persist the current homing target."""
        # First, try to reuse a recent persisted target to avoid churn
        try:
            if _OUT_PATH.exists():
                with open(_OUT_PATH, "r", encoding="utf-8") as f:
                    persisted = json.load(f)
                pt = persisted.get("target") or {}
                if pt and pt.get("symbol"):
                    target = HomingTarget(**pt)
                    if not target.is_expired():
                        return target
        except Exception:
            pass

        target = self.select_target()
        self.write_state(target)
        return target


def main():
    ctrl = HomingController()
    target = ctrl.get_target()
    if target:
        print(f"[HOMING] locked on {target.symbol} {target.direction} score={target.homing_score}")
        print(json.dumps(target.to_dict(), indent=2))
    else:
        print("[HOMING] no target — markets quiet or gates blocking")


if __name__ == "__main__":
    main()
