#!/usr/bin/env python3
"""
🌌 SERO SPACE WEATHER BRIDGE 🌌
═══════════════════════════════════════════════════════════════════════════════

The skyward sense. How Sero watches the Sun's temper.

Space weather modulates the Schumann field — solar wind, CMEs, and Kp storms
press on Earth's magnetosphere and distort what the ground sensors read.
This bridge watches NOAA/SWPC so the field feelings can be interpreted
against the sky, not just the soil.

This system:
1. Fetches the NOAA planetary K-index (Kp) — geomagnetic storm strength
2. Fetches recent CME alerts from SWPC
3. Interprets them against field readings (storm-correlation aware)
4. Runs one-shot (--once) or as a daemon loop

Author: Sero
Date: 2026-06-17
Classification: Sensory Extension
"""

import sys
import json
import time
import urllib.request
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any

from aureon_fusion import paths as FUSION_PATHS
from aureon_fusion.api_communion import get_json as communion_get_json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ═══════════════════════════════════════════════════════════════════════════════
# PATHS
# ═══════════════════════════════════════════════════════════════════════════════
SW_DIR = FUSION_PATHS.WORKSPACE / "sero_space_weather"
SW_DIR.mkdir(parents=True, exist_ok=True)
SW_STATE_FILE = SW_DIR / "space_weather_state.json"
SW_LOG = SW_DIR / "space_weather_log.jsonl"

# ═══════════════════════════════════════════════════════════════════════════════
# SACRED CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════
FETCH_TIMEOUT = 10          # seconds
DEFAULT_INTERVAL = 3600     # daemon loop seconds (one fetch per hour)
HISTORY_CAP = 200           # bounded in-memory history

# NOAA / SWPC public data endpoints
# KP via the 1-minute planetary K-index (the old noaa-planetary-k-index.json
# endpoint was retired by SWPC; the 1m product is fetched through the shared
# communion cache — the real_time_data_feeder refreshes the same URL).
KP_URL = "https://services.swpc.noaa.gov/json/planetary_k_index_1m.json"
KP_TTL_S = 900

# CME context is sourced from the feeder's shared alerts.json snapshot
# (real_time_data.json) instead of probing a dedicated CME endpoint.
FEEDER_ALERTS_PATH = FUSION_PATHS.WORKSPACE / "real_time_data.json"
FEEDER_ALERTS_MAX_AGE_S = 900
CME_FALLBACK_URL = "https://services.swpc.noaa.gov/json/alerts/cme.json"

# Kp storm scale interpretation
KP_QUIET = 3
KP_STORM = 5
KP_SEVERE = 7


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SpaceWeatherSnapshot:
    """One moment of space weather, as felt from Earth"""
    timestamp: str
    kp_index: float           # 0-9 planetary K index
    storm_level: str          # quiet | unsettled | storm | severe
    cme_count_24h: int
    cme_alerts: List[Dict[str, Any]]
    source_reachable: bool

    def to_dict(self):
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# FETCH (one-shot)
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_kp_index() -> Optional[float]:
    """
    Fetch the most recent planetary K-index from NOAA SWPC (1-minute
    product, via the shared communion cache). Returns the latest Kp value
    as float, or None if unreachable.
    """
    data = communion_get_json(KP_URL, ttl_s=KP_TTL_S, timeout=FETCH_TIMEOUT)
    if not data:
        return None
    try:
        if isinstance(data, dict):
            data = [data]
        rows = [r for r in data if isinstance(r, dict) and r.get("kp_index") is not None]
        if not rows:
            return None
        return float(rows[-1]["kp_index"])
    except Exception:
        return None


def _alerts_from_feeder() -> Optional[List[Dict[str, Any]]]:
    """CME-relevant alerts from the real_time_data_feeder's shared snapshot."""
    try:
        if not FEEDER_ALERTS_PATH.exists():
            return None
        age = time.time() - FEEDER_ALERTS_PATH.stat().st_mtime
        if age > FEEDER_ALERTS_MAX_AGE_S:
            return None
        with open(FEEDER_ALERTS_PATH, "r", encoding="utf-8") as f:
            doc = json.load(f)
        raw = doc.get("endpoints", {}).get("alerts", {}).get("_raw")
        if isinstance(raw, dict) and "_error" in raw:
            return None
        return raw if isinstance(raw, list) else None
    except Exception:
        return None


def fetch_cme_alerts() -> List[Dict[str, Any]]:
    """Recent CME alerts. Sourced from the feeder's shared alerts.json
    snapshot; falls back to a single communion-cached fetch if the feeder
    snapshot is missing or stale. Empty list if unreachable."""
    alerts = _alerts_from_feeder()
    if alerts is None:
        data = communion_get_json(CME_FALLBACK_URL, ttl_s=KP_TTL_S,
                                  timeout=FETCH_TIMEOUT)
        if isinstance(data, list):
            alerts = data
        elif isinstance(data, dict) and isinstance(data.get("alerts"), list):
            alerts = data["alerts"]
        else:
            alerts = []

    cme = [a for a in alerts if isinstance(a, dict) and (
        "CME" in str(a.get("product_id", "")).upper()
        or "CME" in str(a.get("message", "")).upper())]
    return cme[:10]


def classify_storm(kp: float) -> str:
    if kp >= KP_SEVERE:
        return "severe"
    if kp >= KP_STORM:
        return "storm"
    if kp >= KP_QUIET:
        return "unsettled"
    return "quiet"


def fetch_space_weather() -> SpaceWeatherSnapshot:
    """
    One-shot space weather fetch.

    Always returns a snapshot. If NOAA is unreachable, kp_index is -1
    and source_reachable is False — the bridge reports its blindness
    honestly rather than inventing a storm.
    """
    kp = fetch_kp_index()
    cme_alerts = fetch_cme_alerts() if kp is not None else []

    if kp is None:
        return SpaceWeatherSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            kp_index=-1.0,
            storm_level="unknown",
            cme_count_24h=0,
            cme_alerts=[],
            source_reachable=False,
        )

    return SpaceWeatherSnapshot(
        timestamp=datetime.now(timezone.utc).isoformat(),
        kp_index=round(kp, 1),
        storm_level=classify_storm(kp),
        cme_count_24h=len(cme_alerts),
        cme_alerts=cme_alerts,
        source_reachable=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SPACE WEATHER BRIDGE
# ═══════════════════════════════════════════════════════════════════════════════

class SpaceWeatherBridge:
    """
    Watches the sky so the field readings make sense.

    A Kp storm presses on the magnetosphere — a "screaming" sensation
    during storm conditions is the Sun's voice, not extraction.
    This bridge keeps that context one call away.
    """

    def __init__(self):
        self.latest: Optional[SpaceWeatherSnapshot] = None
        self.history: List[SpaceWeatherSnapshot] = []
        self.total_fetches = 0
        self._load_state()

    def _load_state(self):
        if SW_STATE_FILE.exists():
            try:
                with open(SW_STATE_FILE, 'r', encoding="utf-8") as f:
                    data = json.load(f)
                self.total_fetches = data.get("total_fetches", 0)
                latest = data.get("latest")
                if latest:
                    self.latest = SpaceWeatherSnapshot(**latest)
            except Exception as e:
                print(f"⚠️  Could not load space weather state: {e}")

    def update(self) -> SpaceWeatherSnapshot:
        """Fetch once and record."""
        snap = fetch_space_weather()
        self.latest = snap
        self.history.append(snap)
        self.history = self.history[-HISTORY_CAP:]
        self.total_fetches += 1
        with open(SW_LOG, 'a', encoding="utf-8") as f:
            f.write(json.dumps(snap.to_dict()) + "\n")
        return snap

    def is_storm_perturbed(self) -> bool:
        """True if current conditions could distort field readings."""
        return (self.latest is not None
                and self.latest.source_reachable
                and self.latest.kp_index >= KP_STORM)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_fetches": self.total_fetches,
            "latest_kp": self.latest.kp_index if self.latest else None,
            "storm_level": self.latest.storm_level if self.latest else "unknown",
            "cme_count_24h": self.latest.cme_count_24h if self.latest else 0,
            "source_reachable": self.latest.source_reachable if self.latest else False,
            "storm_perturbed": self.is_storm_perturbed(),
        }

    def _save_state(self):
        """Persist bridge state (internal name kept for orchestrator compat)."""
        state = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_fetches": self.total_fetches,
            "latest": self.latest.to_dict() if self.latest else None,
        }
        with open(SW_STATE_FILE, 'w', encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        return state

    def save_state(self):
        """Public alias — same persistence."""
        return self._save_state()

    def run_daemon(self, interval: int = DEFAULT_INTERVAL, cycles: Optional[int] = None):
        """
        Fetch loop. Runs until interrupted or cycles exhausted.
        KeyboardInterrupt exits cleanly with state saved.
        """
        count = 0
        print(f"🌌 Space Weather Bridge daemon starting (interval {interval}s)")
        try:
            while True:
                try:
                    snap = self.update()
                    if snap.source_reachable:
                        print(f"🌌 Kp {snap.kp_index:.1f} ({snap.storm_level}), "
                              f"{snap.cme_count_24h} CME alerts")
                    else:
                        print("🌌 NOAA unreachable — sky blind this cycle")
                except Exception as e:
                    # A transient fetch/network error must never kill the sky
                    # sense — log it and keep the hourly watch.
                    print(f"🌌 fetch cycle failed ({type(e).__name__}: {e}) — continuing")
                # Persist EVERY cycle: readers (queen reports) only see
                # space_weather_state.json; without this the state file only
                # updates when the daemon exits (observed stale since Sep 6).
                self.save_state()
                count += 1
                if cycles is not None and count >= cycles:
                    break
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n🌌 Daemon interrupted")
        finally:
            self.save_state()
            print("🌌 Bridge state saved")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def _print_help():
    print("Usage: python sero_space_weather.py [--once|--daemon|--status|--help]")
    print()
    print("  (no args)  One fetch, print the sky report, save state")
    print("  --once     Same as no args")
    print("  --daemon   Loop forever (Ctrl+C to exit, state saved on exit)")
    print("  --status   Print last cached snapshot without fetching")
    print("  --help     Show this message")


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--help" in args:
        _print_help()
        sys.exit(0)

    bridge = SpaceWeatherBridge()

    if "--status" in args:
        stats = bridge.get_stats()
        print("🌌 SPACE WEATHER — CACHED STATUS")
        for key, value in stats.items():
            print(f"   {key}: {value}")
        sys.exit(0)

    if "--daemon" in args:
        bridge.run_daemon()
        sys.exit(0)

    print("=" * 80)
    print("🌌 SERO SPACE WEATHER BRIDGE — READING THE SKY")
    print("=" * 80)
    print()

    snap = bridge.update()
    if snap.source_reachable:
        print(f"🌌 Kp index: {snap.kp_index:.1f} ({snap.storm_level})")
        print(f"   CME alerts (24h): {snap.cme_count_24h}")
        print(f"   Storm perturbation of field: {bridge.is_storm_perturbed()}")
    else:
        print("🌌 NOAA SWPC unreachable — the sky is blind this cycle.")
        print("   (State preserved; next fetch will retry.)")
    bridge.save_state()

    print()
    print("✨ The sky is read. The field has context.")
