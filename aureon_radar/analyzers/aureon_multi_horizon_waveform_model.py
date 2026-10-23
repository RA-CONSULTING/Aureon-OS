"""Multi-horizon historical waveform models for financial assets.

The model builder is deliberately evidence-first: it reads persisted market
bars from the global history database and overlays live CentralBeat points.
When a horizon has insufficient history, the horizon is emitted with a blocker
instead of pretending that the system has a one-year memory.
"""

from __future__ import annotations

import math
import sqlite3
import statistics
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


HORIZONS: Dict[str, int] = {
    "1h": 60 * 60,
    "4h": 4 * 60 * 60,
    "12h": 12 * 60 * 60,
    "1d": 24 * 60 * 60,
    "3d": 3 * 24 * 60 * 60,
    "1w": 7 * 24 * 60 * 60,
    "1m": 30 * 24 * 60 * 60,
    "3m": 90 * 24 * 60 * 60,
    "6m": 180 * 24 * 60 * 60,
    "1y": 365 * 24 * 60 * 60,
}


@dataclass(frozen=True)
class WaveformObservation:
    symbol: str
    ts_ms: int
    close: float
    high: float = 0.0
    low: float = 0.0
    volume: float = 0.0
    source: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "ts_ms": self.ts_ms,
            "close": self.close,
            "high": self.high,
            "low": self.low,
            "volume": self.volume,
            "source": self.source,
        }


def normalize_symbol(symbol: Any) -> str:
    raw = str(symbol or "").upper().strip()
    alnum = "".join(ch for ch in raw if ch.isalnum())
    aliases = {
        "XBTUSD": "BTCUSD",
        "XXBTZUSD": "BTCUSD",
        "BTCUSDT": "BTCUSD",
        "XETHZUSD": "ETHUSD",
        "ETHUSDT": "ETHUSD",
        "SOLUSDT": "SOLUSD",
        "XRPUSDT": "XRPUSD",
        "DOGEUSDT": "DOGEUSD",
    }
    return aliases.get(alnum, alnum)


def _clamp01(value: Any, default: float = 0.0) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except Exception:
        return max(0.0, min(1.0, float(default)))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
        if math.isfinite(result):
            return result
    except Exception:
        pass
    return default


def _coerce_observation(row: Any, source: str = "live") -> Optional[WaveformObservation]:
    if isinstance(row, WaveformObservation):
        return row
    if not isinstance(row, dict):
        return None
    symbol = normalize_symbol(row.get("symbol") or row.get("raw_symbol") or row.get("symbol_id"))
    close = _safe_float(row.get("close", row.get("price", row.get("reference_price", 0.0))))
    if not symbol or close <= 0:
        return None
    ts_raw = row.get("ts_ms") or row.get("timestamp_ms") or row.get("time_start_ms")
    if ts_raw is None:
        ts_raw = row.get("timestamp") or row.get("generated_at")
    ts_ms = _timestamp_to_ms(ts_raw) or int(time.time() * 1000)
    high = _safe_float(row.get("high"), close)
    low = _safe_float(row.get("low"), close)
    if high <= 0:
        high = close
    if low <= 0:
        low = close
    if low > high:
        low, high = high, low
    return WaveformObservation(
        symbol=symbol,
        ts_ms=int(ts_ms),
        close=close,
        high=high,
        low=low,
        volume=_safe_float(row.get("volume", row.get("volume_24h", 0.0))),
        source=str(row.get("source") or source or "live"),
    )


def _timestamp_to_ms(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            number = float(value)
            if number > 1_000_000_000_000:
                return int(number)
            if number > 1_000_000_000:
                return int(number * 1000)
            return int(number)
        if isinstance(value, datetime):
            return int(value.timestamp() * 1000)
        text = str(value).strip()
        if not text:
            return None
        if text.isdigit():
            return _timestamp_to_ms(float(text))
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return int(parsed.timestamp() * 1000)
    except Exception:
        return None


def _dedupe_sort(observations: Iterable[WaveformObservation]) -> List[WaveformObservation]:
    by_key: Dict[tuple[str, int], WaveformObservation] = {}
    for obs in observations:
        if obs.close <= 0 or obs.ts_ms <= 0:
            continue
        key = (normalize_symbol(obs.symbol), int(obs.ts_ms))
        current = by_key.get(key)
        if current is None or (obs.source != "live" and current.source == "live"):
            by_key[key] = obs
    return sorted(by_key.values(), key=lambda item: item.ts_ms)


def _query_history_bars(
    *,
    symbols: Sequence[str],
    since_ms: int,
    db_path: str | Path | None = None,
) -> Dict[str, List[WaveformObservation]]:
    if not symbols:
        return {}
    try:
        from aureon.core.aureon_global_history_db import connect

        conn = connect(str(db_path) if db_path else None, check_same_thread=False)
    except Exception:
        return {}
    try:
        result: Dict[str, List[WaveformObservation]] = {symbol: [] for symbol in symbols}
        for symbol in symbols:
            rows = conn.execute(
                """
                SELECT symbol, symbol_id, time_start_ms, time_end_ms, open, high, low, close, volume, provider, venue
                FROM market_bars
                WHERE time_start_ms >= ?
                  AND (
                    UPPER(REPLACE(REPLACE(REPLACE(COALESCE(symbol, ''), '/', ''), '-', ''), '_', '')) = ?
                    OR UPPER(REPLACE(REPLACE(REPLACE(COALESCE(symbol_id, ''), '/', ''), '-', ''), '_', '')) LIKE ?
                  )
                ORDER BY time_start_ms ASC
                """,
                (int(since_ms), symbol, f"%{symbol}%"),
            ).fetchall()
            for row in rows:
                close = _safe_float(row["close"], _safe_float(row["open"], 0.0))
                if close <= 0:
                    continue
                result.setdefault(symbol, []).append(
                    WaveformObservation(
                        symbol=symbol,
                        ts_ms=int(row["time_start_ms"]),
                        close=close,
                        high=_safe_float(row["high"], close),
                        low=_safe_float(row["low"], close),
                        volume=_safe_float(row["volume"], 0.0),
                        source=f"{row['provider'] or 'history'}:{row['venue'] or ''}".strip(":"),
                    )
                )
        return result
    except sqlite3.Error:
        return {}
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _max_drawdown_pct(closes: Sequence[float]) -> float:
    peak = closes[0] if closes else 0.0
    max_drawdown = 0.0
    for close in closes:
        peak = max(peak, close)
        if peak > 0:
            max_drawdown = min(max_drawdown, (close - peak) / peak * 100.0)
    return abs(max_drawdown)


def _horizon_model(label: str, horizon_sec: int, observations: Sequence[WaveformObservation], now_ms: int) -> Dict[str, Any]:
    cutoff = now_ms - horizon_sec * 1000
    points = [obs for obs in observations if obs.ts_ms >= cutoff]
    if not points:
        return {
            "horizon": label,
            "horizon_sec": horizon_sec,
            "point_count": 0,
            "usable": False,
            "blocker": "no_history_points",
        }
    first = points[0]
    last = points[-1]
    closes = [obs.close for obs in points if obs.close > 0]
    highs = [obs.high or obs.close for obs in points if obs.close > 0]
    lows = [obs.low or obs.close for obs in points if obs.close > 0]
    duration_sec = max(0.0, (last.ts_ms - first.ts_ms) / 1000.0)
    coverage_ratio = _clamp01(duration_sec / max(1.0, float(horizon_sec)))
    returns: List[float] = []
    for before, after in zip(closes, closes[1:]):
        if before > 0:
            returns.append((after - before) / before * 100.0)
    return_pct = ((last.close - first.close) / first.close * 100.0) if first.close > 0 else 0.0
    high = max(highs) if highs else last.close
    low = min(lows) if lows else last.close
    amplitude_pct = ((high - low) / last.close * 100.0) if last.close > 0 else 0.0
    volatility_pct = statistics.pstdev(returns) if len(returns) > 1 else 0.0
    drawdown_pct = _max_drawdown_pct(closes)
    close_position = ((last.close - low) / (high - low)) if high > low else 0.5
    if close_position >= 0.78 and return_pct >= 0:
        phase = "cresting"
    elif close_position <= 0.22 and return_pct <= 0:
        phase = "troughing"
    elif return_pct > 0:
        phase = "rising"
    elif return_pct < 0:
        phase = "falling"
    else:
        phase = "flat"
    trend_strength = _clamp01(abs(return_pct) / max(amplitude_pct, 0.01))
    fresh_sec = max(0.0, (now_ms - last.ts_ms) / 1000.0)
    fresh_score = _clamp01(1.0 - (fresh_sec / max(60.0, min(float(horizon_sec), 24 * 60 * 60))))
    coverage_quality = _clamp01(coverage_ratio / 0.80)
    point_quality = _clamp01(len(points) / 12.0)
    usable = len(points) >= 2 and (coverage_ratio >= 0.01 or horizon_sec <= 4 * 60 * 60)
    blocker = "" if usable else "insufficient_points_or_coverage"
    quality_score = _clamp01((coverage_quality * 0.35) + (point_quality * 0.35) + (fresh_score * 0.30))
    return {
        "horizon": label,
        "horizon_sec": horizon_sec,
        "point_count": len(points),
        "first_ts_ms": first.ts_ms,
        "last_ts_ms": last.ts_ms,
        "duration_sec": round(duration_sec, 3),
        "coverage_ratio": round(coverage_ratio, 6),
        "fresh_age_sec": round(fresh_sec, 3),
        "open_close_return_pct": round(return_pct, 6),
        "amplitude_pct": round(amplitude_pct, 6),
        "volatility_pct": round(volatility_pct, 6),
        "max_drawdown_pct": round(drawdown_pct, 6),
        "close_position": round(close_position, 6),
        "wave_phase": phase,
        "trend_strength": round(trend_strength, 6),
        "quality_score": round(quality_score, 6),
        "usable": usable,
        "blocker": blocker,
    }


def _symbol_model(symbol: str, observations: Sequence[WaveformObservation], now_ms: int) -> Dict[str, Any]:
    observations = _dedupe_sort(observations)
    horizons = {
        label: _horizon_model(label, seconds, observations, now_ms)
        for label, seconds in HORIZONS.items()
    }
    usable = [row for row in horizons.values() if row.get("usable")]
    weighted_return = 0.0
    weight_sum = 0.0
    for label, row in horizons.items():
        if not row.get("usable"):
            continue
        horizon_weight = {
            "1h": 1.8,
            "4h": 1.55,
            "12h": 1.35,
            "1d": 1.2,
            "3d": 1.0,
            "1w": 0.85,
            "1m": 0.65,
            "3m": 0.50,
            "6m": 0.40,
            "1y": 0.30,
        }.get(label, 0.5)
        quality = _safe_float(row.get("quality_score"), 0.0)
        weight = horizon_weight * max(0.1, quality)
        weighted_return += _safe_float(row.get("open_close_return_pct"), 0.0) * weight
        weight_sum += weight
    directional_return = weighted_return / weight_sum if weight_sum > 0 else 0.0
    side = "BUY" if directional_return > 0 else "SELL" if directional_return < 0 else "NEUTRAL"
    avg_quality = sum(_safe_float(row.get("quality_score"), 0.0) for row in usable) / max(1, len(usable))
    horizon_coverage = len(usable) / max(1, len(HORIZONS))
    confidence = _clamp01((avg_quality * 0.60) + (horizon_coverage * 0.25) + (_clamp01(abs(directional_return) / 5.0) * 0.15))
    blockers = {
        label: row.get("blocker")
        for label, row in horizons.items()
        if not row.get("usable") and row.get("blocker")
    }
    return {
        "symbol": symbol,
        "observation_count": len(observations),
        "first_ts_ms": observations[0].ts_ms if observations else None,
        "last_ts_ms": observations[-1].ts_ms if observations else None,
        "usable_horizon_count": len(usable),
        "total_horizon_count": len(HORIZONS),
        "fast_memory_ready": bool(horizons.get("1h", {}).get("usable")),
        "long_memory_ready": bool(
            horizons.get("1m", {}).get("usable")
            or horizons.get("3m", {}).get("usable")
            or horizons.get("1y", {}).get("usable")
        ),
        "dominant_direction": side,
        "directional_return_score": round(directional_return, 6),
        "waveform_confidence": round(confidence, 6),
        "usable_for_decision": bool(usable),
        "blockers": blockers,
        "horizons": horizons,
    }


def build_multi_horizon_waveform_report(
    *,
    symbols: Sequence[str],
    live_observations: Sequence[Dict[str, Any] | WaveformObservation] | None = None,
    db_path: str | Path | None = None,
    now_ms: int | None = None,
    max_symbols: int = 24,
) -> Dict[str, Any]:
    now_ms = int(now_ms or time.time() * 1000)
    normalized_symbols = []
    for symbol in symbols:
        normalized = normalize_symbol(symbol)
        if normalized and normalized not in normalized_symbols:
            normalized_symbols.append(normalized)
    normalized_symbols = normalized_symbols[: max(1, int(max_symbols or 24))]
    since_ms = now_ms - max(HORIZONS.values()) * 1000
    history_by_symbol = _query_history_bars(symbols=normalized_symbols, since_ms=since_ms, db_path=db_path)
    live_by_symbol: Dict[str, List[WaveformObservation]] = {symbol: [] for symbol in normalized_symbols}
    for raw in live_observations or []:
        obs = _coerce_observation(raw, source="live")
        if obs is None:
            continue
        normalized = normalize_symbol(obs.symbol)
        if normalized not in live_by_symbol:
            live_by_symbol[normalized] = []
            if normalized not in normalized_symbols:
                normalized_symbols.append(normalized)
        live_by_symbol[normalized].append(obs)
    symbol_models: Dict[str, Dict[str, Any]] = {}
    for symbol in normalized_symbols:
        observations = list(history_by_symbol.get(symbol, [])) + list(live_by_symbol.get(symbol, []))
        symbol_models[symbol] = _symbol_model(symbol, observations, now_ms)
    decision_symbols: Dict[str, Dict[str, Any]] = {}
    for symbol, model in symbol_models.items():
        if not model.get("usable_for_decision"):
            continue
        confidence = _clamp01(model.get("waveform_confidence", 0.0))
        if confidence <= 0:
            continue
        side = str(model.get("dominant_direction") or "NEUTRAL")
        if side not in {"BUY", "SELL"}:
            continue
        decision_symbols[symbol] = {
            "symbol": symbol,
            "confidence": confidence,
            "side": side,
            "reason": "multi_horizon_historical_waveform",
            "downstream_stage": "hnc_proof",
            "usable_horizon_count": model.get("usable_horizon_count", 0),
            "fast_memory_ready": model.get("fast_memory_ready", False),
            "long_memory_ready": model.get("long_memory_ready", False),
            "directional_return_score": model.get("directional_return_score", 0.0),
        }
    usable_symbols = sum(1 for model in symbol_models.values() if model.get("usable_for_decision"))
    long_ready = sum(1 for model in symbol_models.values() if model.get("long_memory_ready"))
    return {
        "schema_version": 1,
        "generated_at": datetime.fromtimestamp(now_ms / 1000.0).isoformat(),
        "mode": "multi_horizon_asset_waveform_models",
        "horizon_labels": list(HORIZONS.keys()),
        "horizon_seconds": dict(HORIZONS),
        "symbol_count": len(symbol_models),
        "usable_symbol_count": usable_symbols,
        "long_memory_ready_count": long_ready,
        "decision_symbol_count": len(decision_symbols),
        "fed_to_decision_logic": bool(decision_symbols),
        "source_summary": {
            "history_db": str(db_path) if db_path else "state/aureon_global_history.sqlite",
            "live_observation_count": len(live_observations or []),
            "history_points_loaded": sum(len(value) for value in history_by_symbol.values()),
        },
        "decision_symbols": decision_symbols,
        "symbol_models": symbol_models,
    }
