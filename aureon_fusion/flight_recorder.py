"""✈️ Unified Flight Recorder — per-faculty freshness + truth-status audit.

One cycle reads every canonical faculty state file, computes age vs expected
TTL, classifies truth_status using the real_data_contract semantics, and
appends one JSONL record per faculty.  A bounded flight_record.jsonl plus a
single-cycle flight_health.json give the organism an honest, fail-closed view
of whether each faculty is producing fresh real data.

Run:
    python -m aureon_fusion.flight_recorder --once
    python -m aureon_fusion.flight_recorder --daemon
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    from .paths import FUSION_STATE, AUREON_RADAR, AUREON_UPSTREAM, WORKSPACE
except ImportError:
    from aureon_fusion.paths import FUSION_STATE, AUREON_RADAR, AUREON_UPSTREAM, WORKSPACE

FLIGHT_LOG = FUSION_STATE / "flight_record.jsonl"
FLIGHT_HEALTH = FUSION_STATE / "flight_health.json"

# Max JSONL size before rotation (lines).
FLIGHT_LOG_MAX_LINES = 5000
FLIGHT_LOG_KEEP_LINES = 4000

# Expected freshness TTLs (seconds).  Generous multiples of known loop cadence.
TTL_DEFAULT = 300
TTL_OVERRIDES = {
    "hnc_core": 120,              # 60s Master-Equation step
    "real_time_data": 120,        # real_time_data_feeder 60s cycle
    "schumann": 120,              # schumann_real_daemon 60s poll
    "knowledge_pulse": 180,       # knowledge_pulse_feeder default 60s
    "trading_progress": 120,      # trading_progress_monitor 60s poll
    "real_portfolio": 600,        # portfolio_writer_loop ~60s but can slow to ~9min
    "temporal_outlook": 300,      # temporal_refresh_loop 120s interval
    "prophecy_summary": 300,      # same temporal/prophecy loop
    "news_geo_digest": 1200,      # news_geo_digest 600s interval
    "heartbeat_last_results": 400,  # heartbeat_daemon 300s cycle
    "organ_registry": 600,        # registry snapshot, updated ad-hoc
}

TRUTH_DEFAULTS = {
    "hnc_core": "real_derived",
    "real_time_data": "live",
    "schumann": "live",
    "knowledge_pulse": "real_derived",
    "trading_progress": "real_derived",
    "real_portfolio": "real_derived",
    "temporal_outlook": "real_derived",
    "prophecy_summary": "real_derived",
    "news_geo_digest": "real_derived",
    "heartbeat_last_results": "real_derived",
    "organ_registry": "real_derived",
}

FACULTY_FILES: list[dict[str, Any]] = [
    {
        "name": "hnc_core",
        "path": FUSION_STATE / "hnc_core_state.json",
        "ts_keys": ("timestamp",),
        "source_id": "hnc_core",
    },
    {
        "name": "real_time_data",
        "path": WORKSPACE / "real_time_data.json",
        "ts_keys": ("timestamp",),
        "source_id": "real_time_data_feeder",
    },
    {
        "name": "schumann",
        "path": WORKSPACE / "schumann_state.json",
        "ts_keys": ("timestamp",),
        "source_id": "resonanceone_tomsk",
    },
    {
        "name": "knowledge_pulse",
        "path": FUSION_STATE / "knowledge_pulse.json",
        "ts_keys": ("timestamp",),
        "source_id": "internal_telemetry",
    },
    {
        "name": "trading_progress",
        "path": AUREON_RADAR / "state" / "trading_progress_state.json",
        "ts_keys": ("ts", "timestamp"),
        "source_id": "trading_progress_monitor",
    },
    {
        "name": "real_portfolio",
        "path": AUREON_RADAR / "real_portfolio_state.json",
        "ts_keys": ("last_update", "timestamp"),
        "source_id": "portfolio_writer_loop",
    },
    {
        "name": "temporal_outlook",
        "path": AUREON_RADAR / "state" / "temporal_outlook.json",
        "ts_keys": ("ts", "timestamp"),
        "source_id": "temporal_refresh_loop",
    },
    {
        "name": "prophecy_summary",
        "path": FUSION_STATE / "prophecy_summary.json",
        "ts_keys": ("ts", "timestamp"),
        "source_id": "multiverse_outlook",
    },
    {
        "name": "news_geo_digest",
        "path": AUREON_UPSTREAM / "aureon" / "data_feeds" / "state" / "news_geo_digest.json",
        "ts_keys": ("ts", "timestamp"),
        "source_id": "news_geo_digest",
    },
    {
        "name": "heartbeat_last_results",
        "path": FUSION_STATE / "heartbeat_last_results.json",
        "ts_keys": ("started_at", "timestamp"),
        "source_id": "heartbeat_daemon",
    },
    {
        "name": "organ_registry",
        "path": FUSION_STATE / "organ_registry.json",
        "ts_keys": (),  # use file mtime
        "source_id": "organ_registry",
    },
]


# ───────────────────────────── helpers ─────────────────────────────

def _reconfigure_stdout() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _parse_ts(value: Any) -> float | None:
    """Best-effort timestamp → epoch seconds."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        # Epoch seconds; reject clearly bogus values
        if 1_000_000_000 < value < 2_000_000_000:
            return float(value)
        if 1_000_000_000_000 <= value < 2_000_000_000_000:
            return float(value) / 1000.0
        return None
    if isinstance(value, str):
        text = value.strip().replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(text).timestamp()
        except Exception:
            pass
        # Try a few common formats
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(text[:19], fmt).replace(tzinfo=timezone.utc).timestamp()
            except Exception:
                continue
    return None


def _extract_ts(data: dict[str, Any], keys: Iterable[str]) -> float | None:
    for key in keys:
        if key in data and data[key] is not None:
            ts = _parse_ts(data[key])
            if ts is not None:
                return ts
    return None


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _scan_simulated(obj: Any, _seen: set[int] | None = None) -> list[str]:
    """Recursively scan for synthetic/truth markers that violate the real-data contract."""
    _seen = _seen or set()
    findings: list[str] = []
    obj_id = id(obj)
    if obj_id in _seen:
        return findings
    _seen.add(obj_id)

    if isinstance(obj, dict):
        for k, v in obj.items():
            key = str(k).lower()
            if key == "truth_status" and str(v).lower() in ("test_fixture", "simulated"):
                findings.append(f"truth_status={v}")
            if key == "generated_values" and bool(v):
                findings.append("generated_values=True")
            if key in ("simulation", "synthetic") and bool(v):
                findings.append(f"{key}=True")
            findings.extend(_scan_simulated(v, _seen))
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            findings.extend(_scan_simulated(item, _seen))
    return findings


def _is_explicit_test_mode(data: dict[str, Any]) -> bool:
    return bool(
        os.environ.get("AUREON_TEST_MODE")
        or os.environ.get("TEST_MODE")
        or data.get("test_mode")
        or data.get("_test_mode")
    )


def _value_summary(name: str, data: dict[str, Any]) -> str:
    """Concise, non-secret summary of a faculty's payload."""
    try:
        if name == "hnc_core":
            return (
                f"step={data.get('step')} gamma={data.get('coherence_gamma')} "
                f"psi={data.get('consciousness_psi')} level={data.get('consciousness_level')} "
                f"rung={data.get('rung')}"
            )
        if name == "real_time_data":
            s = data.get("summary", {})
            kp = s.get("kp", {})
            sw = s.get("solar_wind", {})
            xr = s.get("xray", {})
            qk = s.get("quakes", {})
            return (
                f"kp_index={kp.get('kp_index')} solar_speed={sw.get('speed')} "
                f"xray_flux={xr.get('flux')} quakes={qk.get('count')}"
            )
        if name == "schumann":
            return (
                f"freq={data.get('frequency_hz')} activity={data.get('activity_index')} "
                f"label={data.get('activity_label')} real_data={data.get('real_data')} "
                f"simulation={data.get('simulation')}"
            )
        if name == "knowledge_pulse":
            comps = list(data.get("components", {}).keys())
            return f"pulse={data.get('pulse')} components={comps}"
        if name == "trading_progress":
            summary = data.get("summary", {})
            cap = data.get("capital", {})
            return (
                f"open={summary.get('open_count')} awaiting={summary.get('awaiting_count')} "
                f"deployed={cap.get('deployed_usd')} free={cap.get('free_usd')} "
                f"positions={len(data.get('positions', []))}"
            )
        if name == "real_portfolio":
            hist = data.get("history", [])
            latest = hist[-1] if hist else {}
            return (
                f"last_update={data.get('last_update')} total_usd={latest.get('total_usd')} "
                f"realized_pnl={latest.get('realized_pnl')} entries={len(hist)}"
            )
        if name == "temporal_outlook":
            ts = data.get("temporal_sense", {})
            nonlin = ts.get("non_linear", {})
            return (
                f"regime={nonlin.get('field_regime')} positions={len(data.get('positions', []))} "
                f"candidates={len(data.get('candidates_top', []))} "
                f"seer={data.get('seer_counsel') is not None}"
            )
        if name == "prophecy_summary":
            return (
                f"open={data.get('open')} due={data.get('due_this_cycle')} "
                f"resolved={data.get('resolved_total')} hit_rate={data.get('hit_rate')} "
                f"folded={data.get('folded_into_queen_knowledge')}"
            )
        if name == "news_geo_digest":
            sp = data.get("social_pulse", {})
            fe = data.get("funding_energy", {})
            return (
                f"gdelt={data.get('gdelt_headlines') is not None} "
                f"geo_risk={data.get('geo_risk_hint') is not None} "
                f"social_tokens={sp.get('top_tokens')} "
                f"funding_flows={len(fe.get('notable_flows', []))}"
            )
        if name == "heartbeat_last_results":
            checks = data.get("checks", {})
            return f"checks={len(checks)} keys={list(checks.keys())}"
        if name == "organ_registry":
            organs = data.get("organs", {})
            running = sum(1 for v in organs.values() if v.get("pid") and not v.get("dormant"))
            dormant = sum(1 for v in organs.values() if v.get("dormant"))
            return f"total={len(organs)} running={running} dormant={dormant}"
    except Exception:
        pass
    return "summary_unavailable"


# ───────────────────────────── cycle logic ─────────────────────────────

def _build_record(now: float, faculty: dict[str, Any]) -> dict[str, Any]:
    name = faculty["name"]
    path: Path = faculty["path"]
    ttl = TTL_OVERRIDES.get(name, TTL_DEFAULT)
    source_id = faculty.get("source_id", name)

    data = _load_json(path)

    if data is None:
        return {
            "ts": datetime.now(timezone.utc).isoformat(),
            "faculty": name,
            "status": "missing",
            "age_s": None,
            "ttl_s": ttl,
            "truth_status": "no_data",
            "source_id": source_id,
            "value_summary": f"file_missing:{path.name}",
            "simulated": False,
        }

    ts_keys = faculty.get("ts_keys", ())
    ts = _extract_ts(data, ts_keys)
    if ts is None and not ts_keys:
        # organ_registry: fall back to file mtime
        try:
            ts = path.stat().st_mtime
        except Exception:
            ts = None

    if ts is None:
        age_s = None
        status = "missing"
    else:
        age_s = max(0.0, now - ts)
        status = "fresh" if age_s <= ttl else "stale"

    simulated_flags = _scan_simulated(data)
    explicit_test = _is_explicit_test_mode(data)
    truth_status = TRUTH_DEFAULTS.get(name, "real_derived")
    if simulated_flags and not explicit_test:
        truth_status = "test_fixture"

    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "faculty": name,
        "status": status,
        "age_s": round(age_s, 3) if age_s is not None else None,
        "ttl_s": ttl,
        "truth_status": truth_status,
        "source_id": data.get("source") or source_id,
        "value_summary": _value_summary(name, data),
        "simulated": False,
    }
    # Preserve the finding for health aggregation even though the line schema says false.
    record["_simulated_flags"] = simulated_flags
    record["_explicit_test"] = explicit_test
    return record


def _append_records(records: list[dict[str, Any]]) -> None:
    FUSION_STATE.mkdir(parents=True, exist_ok=True)
    # Strip internal-only keys before writing.
    lines = [json.dumps({k: v for k, v in r.items() if not k.startswith("_")},
                        ensure_ascii=False, default=str) + "\n"
             for r in records]

    # Rotation: keep the log bounded.
    if FLIGHT_LOG.exists():
        try:
            with open(FLIGHT_LOG, "r", encoding="utf-8", errors="replace") as f:
                existing = f.readlines()
            if len(existing) >= FLIGHT_LOG_MAX_LINES:
                keep = existing[-FLIGHT_LOG_KEEP_LINES:]
                tmp = FLIGHT_LOG.with_suffix(".jsonl.tmp")
                with open(tmp, "w", encoding="utf-8") as f:
                    f.writelines(keep)
                os.replace(tmp, FLIGHT_LOG)
        except Exception:
            pass

    with open(FLIGHT_LOG, "a", encoding="utf-8") as f:
        f.writelines(lines)
        f.flush()
        try:
            os.fsync(f.fileno())
        except Exception:
            pass


def _write_health(records: list[dict[str, Any]]) -> dict[str, Any]:
    stale_list: list[str] = []
    simulated_detected: list[str] = []
    fresh_count = 0
    for r in records:
        if r["status"] != "fresh":
            stale_list.append(r["faculty"])
        else:
            fresh_count += 1
        flags = r.get("_simulated_flags", [])
        if flags and not r.get("_explicit_test"):
            simulated_detected.append(r["faculty"])

    health = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "all_fresh": len(stale_list) == 0,
        "stale_list": stale_list,
        "simulated_detected": simulated_detected,
        "faculties_count": len(records),
        "fresh_count": fresh_count,
    }
    tmp = FLIGHT_HEALTH.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(health, f, indent=2, ensure_ascii=False, default=str)
        f.flush()
        try:
            os.fsync(f.fileno())
        except Exception:
            pass
    os.replace(tmp, FLIGHT_HEALTH)
    return health


def record_cycle(*, silent: bool = False) -> dict[str, Any]:
    """Run one flight-recorder cycle: read, classify, append, write health."""
    now = time.time()
    records = [_build_record(now, f) for f in FACULTY_FILES]
    _append_records(records)
    health = _write_health(records)
    if not silent:
        _reconfigure_stdout()
        print("═" * 72)
        print("✈️  FLIGHT RECORDER — one cycle")
        print("═" * 72)
        for r in records:
            print(json.dumps({k: v for k, v in r.items() if not k.startswith("_")},
                             ensure_ascii=False, default=str))
        print("─" * 72)
        print("flight_health:", json.dumps(health, ensure_ascii=False, default=str))
        print("═" * 72)
    return {"records": records, "health": health}


# ───────────────────────────── CLI ─────────────────────────────

def main(argv: list[str] | None = None) -> int:
    _reconfigure_stdout()
    parser = argparse.ArgumentParser(
        description="Unified flight recorder for Aureon faculty freshness.")
    parser.add_argument("--once", action="store_true",
                        help="Record one cycle and exit.")
    parser.add_argument("--daemon", action="store_true",
                        help="Run a cycle every 60 seconds.")
    args = parser.parse_args(argv)

    if not (args.once or args.daemon):
        parser.print_help()
        return 2

    if args.once:
        record_cycle(silent=False)
        return 0

    # daemon mode
    print("[flight_recorder] daemon starting; cadence 60s (Ctrl-C to stop)", flush=True)
    while True:
        try:
            record_cycle(silent=True)
        except Exception as e:
            print(f"[flight_recorder] cycle error: {e}", flush=True)
        try:
            time.sleep(60)
        except KeyboardInterrupt:
            print("[flight_recorder] stopping on interrupt", flush=True)
            return 0


if __name__ == "__main__":
    sys.exit(main())
