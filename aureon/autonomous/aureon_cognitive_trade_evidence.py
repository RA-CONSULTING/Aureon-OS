"""Cognitive trade evidence and reward ledger.

This module turns trading outcomes into operational learning evidence. It does
not claim consciousness or feelings; it records affect-like labels as feedback
signals so the rest of Aureon can see whether trading action is strengthening
or weakening the current signal stack.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence


SCHEMA_VERSION = "aureon-cognitive-trade-evidence-v1"
REPO_ROOT = Path(__file__).resolve().parents[2]
STATE_ROOT = REPO_ROOT / "state"
EVIDENCE_JSONL = STATE_ROOT / "cognitive_trade_evidence.jsonl"
RUNTIME_STATUS_PATH = STATE_ROOT / "unified_runtime_status.json"
MARGIN_GOAL_PROOF_PATH = REPO_ROOT / "margin_goal_proof.jsonl"
ADAPTIVE_HISTORY_PATH = REPO_ROOT / "adaptive_learning_history.json"
BRAIN_PREDICTIONS_PATH = REPO_ROOT / "brain_predictions_history.json"
DEFAULT_OUTPUT_JSON = REPO_ROOT / "docs/audits/aureon_cognitive_trade_evidence.json"
DEFAULT_PUBLIC_JSON = REPO_ROOT / "frontend/public/aureon_cognitive_trade_evidence.json"

try:
    from aureon.trading.order_lifecycle import append_event as append_order_lifecycle_event, lifecycle_for_deal
except Exception:
    append_order_lifecycle_event = None  # type: ignore[assignment]
    lifecycle_for_deal = None  # type: ignore[assignment]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        if math.isfinite(number):
            return number
    except Exception:
        pass
    return default


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _read_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _tail_jsonl(path: Path, limit: int = 2000) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except Exception:
                    continue
                if isinstance(item, dict):
                    rows.append(item)
                    if len(rows) > limit:
                        rows = rows[-limit:]
    except Exception:
        return rows[-limit:]
    return rows[-limit:]


def _event_id(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8", errors="replace")
    return "cte_" + hashlib.sha256(raw).hexdigest()[:16]


def _runtime_snapshot(root: Path = REPO_ROOT) -> dict[str, Any]:
    data = _read_json(root / "state/unified_runtime_status.json", {})
    return data if isinstance(data, dict) else {}


def reward_from_trade(trade: dict[str, Any], runtime_snapshot: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    runtime = runtime_snapshot if isinstance(runtime_snapshot, dict) else {}
    net_pnl = _as_float(trade.get("net_pnl", trade.get("pnl_gbp", trade.get("realized_pnl", 0.0))))
    gross_pnl = _as_float(trade.get("gross_pnl", net_pnl))
    total_fees = abs(_as_float(trade.get("total_fees", trade.get("fees", 0.0))))
    hold_seconds = _as_float(trade.get("hold_seconds", trade.get("hold_time_seconds", 0.0)))
    stale = bool(runtime.get("stale") or runtime.get("runtime_watchdog", {}).get("tick_stale"))
    data_ready = bool(runtime.get("data_ready", True))
    trading_ready = bool(runtime.get("trading_ready", True))

    pnl_scale = max(0.1, _as_float(os.getenv("AUREON_COGNITIVE_REWARD_PNL_SCALE_GBP"), 5.0))
    profit_component = _clamp((net_pnl / pnl_scale + 1.0) / 2.0)
    fee_drag = _clamp(total_fees / max(abs(gross_pnl), abs(net_pnl), 1.0))
    duration_drag = _clamp(hold_seconds / max(1.0, _as_float(os.getenv("AUREON_COGNITIVE_REWARD_LONG_HOLD_SEC"), 3600.0)))
    readiness_bonus = 0.08 if trading_ready and data_ready and not stale else 0.0
    stale_penalty = 0.25 if stale else 0.0
    reward = _clamp((0.15 + 0.75 * profit_component + readiness_bonus) - (0.16 * fee_drag) - (0.08 * duration_drag) - stale_penalty)

    if net_pnl > 0 and reward >= 0.65:
        affect_label = "gratitude_reinforcement"
        next_action = "increase_weight_for_verified_profitable_signal_without_raising_risk_limits"
    elif net_pnl < 0:
        affect_label = "resolve_to_learn"
        next_action = "reduce_weight_for_losing_signal_and_recheck_costs_timing_and_entry_context"
    elif stale:
        affect_label = "protective_caution"
        next_action = "preserve_position_monitoring_and_restore_fresh_tick_before_new_action"
    else:
        affect_label = "disciplined_neutral"
        next_action = "keep_observing_until_reward_signal_is_clear"

    return {
        "net_pnl": round(net_pnl, 6),
        "gross_pnl": round(gross_pnl, 6),
        "total_fees": round(total_fees, 6),
        "hold_seconds": round(hold_seconds, 3),
        "profit_component": round(profit_component, 6),
        "fee_drag": round(fee_drag, 6),
        "duration_drag": round(duration_drag, 6),
        "readiness_bonus": round(readiness_bonus, 6),
        "stale_penalty": round(stale_penalty, 6),
        "learning_reward": round(reward, 6),
        "outcome": "win" if net_pnl > 0 else "loss" if net_pnl < 0 else "flat",
        "operational_affect_label": affect_label,
        "affect_note": "feedback label only; not a sentience or feeling claim",
        "next_action": next_action,
    }


def append_trade_evidence(
    trade: dict[str, Any],
    *,
    source: str = "unknown",
    runtime_snapshot: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    runtime = runtime_snapshot if isinstance(runtime_snapshot, dict) else _runtime_snapshot()
    reward = reward_from_trade(trade, runtime)
    event = {
        "schema_version": SCHEMA_VERSION,
        "type": "trade_cognitive_reward",
        "event_time": utc_now(),
        "source": source,
        "who": "aureon_unified_trading_runtime",
        "what": "trade outcome converted into cognitive reward evidence",
        "where": str(EVIDENCE_JSONL),
        "how": "risk-adjusted pnl, fee drag, hold time, runtime freshness, and data readiness",
        "trade": dict(trade or {}),
        "reward": reward,
        "runtime_guard": {
            "trading_ready": bool(runtime.get("trading_ready")),
            "data_ready": bool(runtime.get("data_ready")),
            "stale": bool(runtime.get("stale")),
            "stale_reason": runtime.get("stale_reason"),
            "open_positions": runtime.get("combined", {}).get("open_positions") if isinstance(runtime.get("combined"), dict) else None,
        },
    }
    event["event_id"] = _event_id(event)
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    with EVIDENCE_JSONL.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True, default=str) + "\n")
    lifecycle_id = str(trade.get("lifecycle_id") or "")
    if not lifecycle_id and lifecycle_for_deal is not None:
        try:
            lifecycle_id = str(lifecycle_for_deal(str(trade.get("deal_id") or trade.get("dealId") or "")) or "")
        except Exception:
            lifecycle_id = ""
    if lifecycle_id and append_order_lifecycle_event is not None:
        try:
            append_order_lifecycle_event(
                event_type="cognitive_trade_evidence",
                status="outcome_recorded",
                lifecycle_id=lifecycle_id,
                deal_id=trade.get("deal_id") or trade.get("dealId"),
                route_key=trade.get("route_key"),
                symbol=trade.get("symbol") or trade.get("pair"),
                side=trade.get("direction") or trade.get("side"),
                net_pnl=reward.get("net_pnl"),
                outcome=reward.get("outcome"),
                evidence_event_id=event.get("event_id"),
                source=source,
            )
        except Exception:
            pass
    return event


def _outcome_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("type") in {"outcome", "trade_cognitive_reward"}]


def _recent_reward_rows(root: Path) -> list[dict[str, Any]]:
    evidence = _tail_jsonl(root / "state/cognitive_trade_evidence.jsonl", 1000)
    outcomes = _tail_jsonl(root / "margin_goal_proof.jsonl", 2000)
    rows: list[dict[str, Any]] = []
    for item in evidence:
        reward = item.get("reward") if isinstance(item.get("reward"), dict) else {}
        rows.append(
            {
                "source": item.get("source", "cognitive_trade_evidence"),
                "event_time": item.get("event_time"),
                "symbol": item.get("trade", {}).get("pair") or item.get("trade", {}).get("symbol"),
                "net_pnl": _as_float(reward.get("net_pnl")),
                "learning_reward": _as_float(reward.get("learning_reward")),
                "outcome": reward.get("outcome"),
                "affect_label": reward.get("operational_affect_label"),
                "next_action": reward.get("next_action"),
            }
        )
    for item in outcomes:
        if item.get("type") != "outcome":
            continue
        reward = reward_from_trade(item, {})
        rows.append(
            {
                "source": "margin_goal_proof",
                "event_time": item.get("timestamp") or item.get("_written"),
                "symbol": item.get("pair"),
                "net_pnl": _as_float(item.get("net_pnl")),
                "learning_reward": _as_float(reward.get("learning_reward")),
                "outcome": reward.get("outcome"),
                "affect_label": reward.get("operational_affect_label"),
                "next_action": reward.get("next_action"),
                "goal_hit": item.get("goal_hit"),
            }
        )
    return rows[-250:]


def build_cognitive_trade_state(root: Optional[Path] = None) -> dict[str, Any]:
    root = (root or REPO_ROOT).resolve()
    runtime = _read_json(root / "state/unified_runtime_status.json", {})
    if not isinstance(runtime, dict):
        runtime = {}
    rows = _recent_reward_rows(root)
    rewards = [_as_float(row.get("learning_reward")) for row in rows]
    wins = sum(1 for row in rows if row.get("outcome") == "win")
    losses = sum(1 for row in rows if row.get("outcome") == "loss")
    net_pnl = sum(_as_float(row.get("net_pnl")) for row in rows)
    avg_reward = sum(rewards) / len(rewards) if rewards else 0.0
    runtime_stale = bool(runtime.get("stale") or runtime.get("runtime_watchdog", {}).get("tick_stale"))
    open_positions = runtime.get("combined", {}).get("open_positions") if isinstance(runtime.get("combined"), dict) else None
    signal_quality = _clamp(avg_reward - (0.2 if runtime_stale else 0.0) + (0.05 if wins > losses else 0.0))
    action_mode = (
        "rewarded_action_ready"
        if signal_quality >= 0.65 and not runtime_stale
        else "learn_and_recover"
        if runtime_stale
        else "observe_and_refine"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "status": "cognitive_trade_evidence_ready",
        "summary": {
            "evidence_count": len(rows),
            "wins": wins,
            "losses": losses,
            "win_rate": round(wins / max(1, wins + losses), 6),
            "net_pnl": round(net_pnl, 6),
            "average_learning_reward": round(avg_reward, 6),
            "signal_quality": round(signal_quality, 6),
            "action_mode": action_mode,
            "runtime_stale": runtime_stale,
            "open_positions": open_positions,
        },
        "contract": {
            "trade_as_cognition": "closed-loop evidence: signal -> action -> outcome -> reward -> next signal",
            "profit_is_not_enough": "profit counts strongest when runtime is fresh, fees are controlled, and risk gates stayed intact",
            "operational_affect": "gratitude/happiness labels are reinforcement signals, not sentience claims",
            "loop": ["who", "what", "where", "when", "why", "how", "act", "verify", "record", "repeat"],
        },
        "runtime_watchdog": runtime.get("runtime_watchdog") if isinstance(runtime.get("runtime_watchdog"), dict) else {},
        "recent_evidence": rows[-40:],
    }


def write_cognitive_trade_state(
    state: dict[str, Any],
    output_json: Path = DEFAULT_OUTPUT_JSON,
    public_json: Path = DEFAULT_PUBLIC_JSON,
) -> tuple[Path, Path]:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    public_json.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(state, indent=2, sort_keys=True, default=str)
    output_json.write_text(data, encoding="utf-8")
    public_json.write_text(data, encoding="utf-8")
    return output_json, public_json


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Aureon's cognitive trade evidence manifest.")
    parser.add_argument("--repo-root", default="", help="Repo root; defaults to current Aureon repo.")
    parser.add_argument("--json", default=str(DEFAULT_OUTPUT_JSON), help="Audit JSON path.")
    parser.add_argument("--public-json", default=str(DEFAULT_PUBLIC_JSON), help="Frontend public JSON path.")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else REPO_ROOT
    state = build_cognitive_trade_state(root)
    output, public = write_cognitive_trade_state(state, Path(args.json), Path(args.public_json))
    print(json.dumps({"json": str(output), "public_json": str(public), "summary": state["summary"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
