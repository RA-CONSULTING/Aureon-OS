"""One honest pass over the 11 flight-recorder faculties.

Public measurements are fetched and stored. A faculty that cannot be fed
from a real source is written ``blocked`` with the reason. No synthetic
frequency, balance, headline, or prophecy is substituted.
"""

from __future__ import annotations

import errno
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .flight_recorder import FACULTY_FILES, record_cycle

Fetch = Callable[[str], Any]

NOAA_KP = "https://services.swpc.noaa.gov/json/planetary_k_index_1m.json"
NOAA_XRAY = "https://services.swpc.noaa.gov/json/goes/primary/xrays-6-hour.json"
USGS_QUAKES = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
GDELT = "https://api.gdeltproject.org/api/v2/doc/doc?query=markets&mode=artlist&maxrecords=5&format=json"
HN = "https://hn.algolia.com/api/v1/search_by_date?query=markets&tags=story&hitsPerPage=5"
SCHUMANN_STATION = "http://sosrff.tsu.ru/"

PATHS = {item["name"]: Path(item["path"]) for item in FACULTY_FILES}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _measured_pulse_component(component: Any) -> bool:
    """A first-observation 0.5 baseline is not a measurement."""
    if not isinstance(component, dict) or not component.get("available"):
        return False
    if component.get("baseline_established") and "delta_vs_prior" not in component:
        subs = component.get("subsignals")
        if not isinstance(subs, dict):
            return False
        measured = [
            key
            for key, sub_value in subs.items()
            if sub_value is not None and key != "db_growth"
        ]
        return bool(measured)
    return True


def _pid_alive(pid: int) -> bool:
    """True when the process exists. Permission to signal it is not required."""
    if pid <= 0:
        return False
    if Path(f"/proc/{pid}").exists():
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError as exc:
        return exc.errno == errno.EPERM
    return True


def _write(name: str, payload: dict[str, Any]) -> None:
    path = PATHS[name]
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
    os.replace(tmp, path)


def _blocked(name: str, reason: str, source: str) -> dict[str, Any]:
    payload = {
        "timestamp": _now(),
        "ts": _now(),
        "blocked": True,
        "blocked_reason": reason,
        "truth_status": "blocked",
        "source": source,
        "simulation": False,
        "live_trading": False,
        "may_act": False,
    }
    _write(name, payload)
    return payload


def default_fetch(url: str, timeout: float = 8.0) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "AureonSelfHost/1.0", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            content_type = response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        return {"_error": f"HTTP {exc.code}", "_url": url}
    except Exception as exc:
        return {"_error": f"{type(exc).__name__}: {exc}", "_url": url}
    if "json" in content_type or raw[:1] in (b"{", b"["):
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {"_error": "invalid json", "_url": url}
    return {"_error": "not json", "_url": url, "_content_type": content_type}


def _latest_kp(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, list) or not payload or not isinstance(payload[-1], dict):
        return None
    latest = payload[-1]
    if latest.get("kp_index") is None and latest.get("estimated_kp") is None:
        return None
    return {
        "timestamp": latest.get("time_tag"),
        "kp_index": latest.get("kp_index"),
        "estimated_kp": latest.get("estimated_kp"),
        "kp": latest.get("kp"),
    }


def _latest_xray(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, list) or not payload or not isinstance(payload[-1], dict):
        return None
    latest = payload[-1]
    if latest.get("flux") is None:
        return None
    return {"time_tag": latest.get("time_tag"), "flux": latest.get("flux"), "energy": latest.get("energy")}


def _quakes(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict) or not isinstance(payload.get("features"), list):
        return None
    features = payload["features"]
    latest = None
    if features and isinstance(features[0], dict):
        props = features[0].get("properties") or {}
        latest = {"mag": props.get("mag"), "place": props.get("place"), "time": props.get("time")}
    return {"count": len(features), "latest": latest}


def _step_hnc(kp_index: float) -> dict[str, Any]:
    os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
    os.environ.setdefault("AUREON_AUDIT_MODE", "1")
    from aureon.core.aureon_lambda_engine import LambdaEngine, SubsystemReading

    value = max(0.0, min(1.0, float(kp_index) / 9.0))
    reading = SubsystemReading(name="noaa_kp", value=value, confidence=1.0, state="measured")
    state = LambdaEngine().step(readings=[reading], auto_persist=False)
    payload = state.to_dict()
    payload["timestamp"] = _now()
    payload["source"] = "hnc_core"
    payload["truth_status"] = "real_derived"
    payload["input_kp_index"] = kp_index
    payload["simulation"] = False
    payload["live_trading"] = False
    return payload


def _regime(kp_index: float) -> str:
    if kp_index >= 5:
        return "disturbed"
    if kp_index >= 4:
        return "elevated"
    return "calm"


def _paper_scan() -> dict[str, Any]:
    roots = [PATHS["trading_progress"].parent, PATHS["real_portfolio"].parent]
    found = []
    for root in roots:
        if not root.is_dir():
            continue
        for name in ("paper_orders.json", "open_orders.json"):
            path = root / name
            if path.is_file():
                found.append(str(path))
    return {
        "ts": datetime.now(timezone.utc).timestamp(),
        "timestamp": _now(),
        "source": "trading_progress_monitor",
        "truth_status": "real_derived",
        "paper": True,
        "live_trading": False,
        "may_act": False,
        "summary": {"open_count": 0, "awaiting_count": 0},
        "capital": {"deployed_usd": None, "free_usd": None},
        "positions": [],
        "scan": {
            "files_found": len(found),
            "files": found,
            "note": "paper book scanned; no open paper orders were on disk" if not found else "paper order files present; open rows were not promoted without a fill ledger",
        },
        "simulation": False,
    }


def refresh(
    fetch: Fetch | None = None,
    *,
    organ_pids: dict[str, int] | None = None,
    hnc_step: Callable[[float], dict[str, Any]] | None = None,
    pulse: Callable[[], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Write every faculty file, then record one flight-recorder cycle."""

    getter = fetch or default_fetch
    kp_payload = getter(NOAA_KP)
    xray_payload = getter(NOAA_XRAY)
    quake_payload = getter(USGS_QUAKES)
    kp = _latest_kp(kp_payload)
    xray = _latest_xray(xray_payload)
    quakes = _quakes(quake_payload)
    if kp is None or xray is None or quakes is None:
        _blocked(
            "real_time_data",
            "NOAA or USGS payload was missing a measured field",
            "real_time_data_feeder",
        )
    else:
        _write(
            "real_time_data",
            {
                "timestamp": _now(),
                "source": "real_time_data_feeder",
                "truth_status": "live",
                "data_policy": "REAL_ONLY_NO_SYNTHETIC",
                "simulation": False,
                "live_trading": False,
                "summary": {"kp": kp, "xray": xray, "quakes": quakes, "solar_wind": None},
                "endpoints": {
                    "kp_index": {"_url": NOAA_KP},
                    "xray_flux": {"_url": NOAA_XRAY},
                    "quakes": {"_url": USGS_QUAKES},
                },
            },
        )

    station = getter(SCHUMANN_STATION)
    if isinstance(station, dict) and station.get("frequency_hz") is not None and not station.get("_error"):
        _write(
            "schumann",
            {
                "timestamp": _now(),
                "source": "resonanceone_tomsk",
                "truth_status": "live",
                "frequency_hz": station["frequency_hz"],
                "real_data": True,
                "simulation": False,
            },
        )
    else:
        reason = "no direct Schumann station reading"
        if isinstance(station, dict) and station.get("_error"):
            reason = f"no direct Schumann station reading ({station['_error']})"
        reason += "; a Kp-derived frequency was not substituted"
        _blocked("schumann", reason, "resonanceone_tomsk")

    if pulse is not None:
        try:
            _write("knowledge_pulse", pulse())
        except Exception as exc:
            _blocked("knowledge_pulse", f"knowledge pulse feeder failed: {type(exc).__name__}", "internal_telemetry")
    else:
        try:
            from .knowledge_pulse_feeder import compute_pulse

            value, components = compute_pulse()
            available = [
                name
                for name, component in components.items()
                if _measured_pulse_component(component)
            ]
            if not available:
                _blocked(
                    "knowledge_pulse",
                    "no internal telemetry files were readable; a neutral 0.5 pulse was not substituted",
                    "internal_telemetry",
                )
            else:
                _write(
                    "knowledge_pulse",
                    {
                        "timestamp": _now(),
                        "source": "internal_telemetry",
                        "truth_status": "real_derived",
                        "simulation": False,
                        "pulse": value,
                        "components": components,
                    },
                )
        except Exception as exc:
            _blocked("knowledge_pulse", f"knowledge pulse feeder failed: {type(exc).__name__}", "internal_telemetry")

    paper = _paper_scan()
    _write("trading_progress", paper)

    _blocked(
        "real_portfolio",
        "no read-only exchange credentials; venue balances were not fetched",
        "portfolio_writer_loop",
    )

    if kp is None or kp.get("kp_index") is None:
        _blocked("temporal_outlook", "no fresh NOAA Kp measurement", "temporal_refresh_loop")
        _blocked("hnc_core", "no fresh NOAA Kp measurement for the master-equation step", "hnc_core")
    else:
        kp_index = float(kp["kp_index"])
        _write(
            "temporal_outlook",
            {
                "ts": _now(),
                "timestamp": _now(),
                "source": "temporal_refresh_loop",
                "truth_status": "real_derived",
                "simulation": False,
                "live_trading": False,
                "temporal_sense": {
                    "non_linear": {
                        "field_regime": _regime(kp_index),
                        "rule": "kp>=5 disturbed; kp>=4 elevated; else calm",
                        "kp_index": kp_index,
                    }
                },
                "positions": [],
                "candidates_top": [],
                "seer_counsel": None,
            },
        )
        stepper = hnc_step or _step_hnc
        try:
            _write("hnc_core", stepper(kp_index))
        except Exception as exc:
            _blocked("hnc_core", f"lambda engine step failed: {type(exc).__name__}", "hnc_core")

    ledger = PATHS["prophecy_summary"].with_name("prophecy_ledger.jsonl")
    if ledger.is_file() and ledger.stat().st_size > 0:
        _blocked(
            "prophecy_summary",
            "prophecy ledger exists but this pass does not score outcomes it did not recompute",
            "multiverse_outlook",
        )
    else:
        _blocked(
            "prophecy_summary",
            "no prophecy ledger with resolved outcomes; forecasts were not invented",
            "multiverse_outlook",
        )

    gdelt = getter(GDELT)
    hn = getter(HN)
    headlines = None
    if isinstance(gdelt, dict) and isinstance(gdelt.get("articles"), list) and gdelt["articles"]:
        headlines = [
            {"title": item.get("title"), "url": item.get("url"), "source": "gdelt"}
            for item in gdelt["articles"][:5]
            if isinstance(item, dict) and item.get("title")
        ]
    hits = hn.get("hits") if isinstance(hn, dict) else None
    tokens = []
    if isinstance(hits, list):
        tokens = [item.get("title") for item in hits if isinstance(item, dict) and item.get("title")]
    if not headlines and not tokens:
        gdelt_error = gdelt.get("_error") if isinstance(gdelt, dict) else "unavailable"
        hn_error = hn.get("_error") if isinstance(hn, dict) else "unavailable"
        _blocked(
            "news_geo_digest",
            f"GDELT {gdelt_error}; Hacker News {hn_error}",
            "news_geo_digest",
        )
    else:
        _write(
            "news_geo_digest",
            {
                "ts": _now(),
                "timestamp": _now(),
                "source": "news_geo_digest",
                "truth_status": "real_derived",
                "simulation": False,
                "gdelt_headlines": headlines,
                "gdelt_error": None if headlines else (gdelt.get("_error") if isinstance(gdelt, dict) else "unavailable"),
                "geo_risk_hint": None,
                "social_pulse": {"top_tokens": tokens, "source": "hn_algolia" if tokens else None},
                "funding_energy": {"notable_flows": [], "error": "DefiLlama was not called this pass"},
            },
        )

    _write(
        "heartbeat_last_results",
        {
            "started_at": _now(),
            "timestamp": _now(),
            "finished_at": _now(),
            "source": "heartbeat_daemon",
            "truth_status": "real_derived",
            "simulation": False,
            "live_trading": False,
            "may_act": False,
            "checks": {
                "live_trading_off": {"ok": os.environ.get("AUREON_LIVE_TRADING", "0") != "1"},
                "may_act_false": {"ok": True, "may_act": False},
                "paper_orders": paper["scan"],
            },
        },
    )

    organs: dict[str, Any] = {}
    if not organ_pids:
        _blocked("organ_registry", "no running organ supervisor reported pids", "organ_registry")
    else:
        for name, pid in organ_pids.items():
            alive = _pid_alive(int(pid))
            organs[name] = {
                "pid": int(pid) if alive else None,
                "dormant": not alive,
                "blocked_reason": "" if alive else "pid is not alive",
                "mode": "self-hosted paper",
            }
        if not any(item.get("pid") for item in organs.values()):
            _blocked("organ_registry", "reported pids were not alive", "organ_registry")
        else:
            _write(
                "organ_registry",
                {
                    "timestamp": _now(),
                    "source": "organ_registry",
                    "truth_status": "real_derived",
                    "simulation": False,
                    "live_trading": False,
                    "may_act": False,
                    "organs": organs,
                },
            )

    cycle = record_cycle(silent=True)
    rows = []
    for record in cycle["records"]:
        rows.append(
            {
                "faculty": record["faculty"],
                "status": record["status"],
                "truth_status": record["truth_status"],
                "blocked_reason": record.get("blocked_reason") or "",
                "source_id": record.get("source_id"),
            }
        )
    return {"rows": rows, "health": cycle["health"]}
