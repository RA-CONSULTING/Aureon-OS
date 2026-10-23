#!/usr/bin/env python3
"""
MARGIN GOAL RECORDER
====================
Records every entry-selection scan (all candidates + goal scores) and
the final trade outcome.  Proves that higher goal_score → faster profit.

Two record types stored in margin_goal_proof.jsonl:
  {"type": "scan", ...}     — written by find_best_target() every scan
  {"type": "outcome", ...}  — written by close_position() when trade ends

The check_goal_proof.py script reads the file and correlates them.
"""

import json
import time
import threading
from datetime import datetime
from typing import Optional

PROOF_FILE = "margin_goal_proof.jsonl"

_lock = threading.Lock()


def _append(record: dict):
    """Append one JSON line to the proof file (thread-safe)."""
    record["_written"] = datetime.now().isoformat()
    with _lock:
        with open(PROOF_FILE, "a") as f:
            f.write(json.dumps(record) + "\n")


class MarginGoalRecorder:
    """
    Drop-in recorder for KrakenMarginArmyTrader.

    Usage inside the trader:
        self._goal_recorder = MarginGoalRecorder()

    In find_best_target():
        scan_id = self._goal_recorder.record_scan(candidates_raw, winner_pair, winner_side)
        self._pending_scan_id = scan_id

    After open_position() returns trade:
        self._goal_recorder.link_order(self._pending_scan_id, trade.order_id)

    In close_position() after completed dict is built:
        self._goal_recorder.record_outcome(trade.order_id, completed)
    """

    def __init__(self):
        # order_id → scan_id  (set after open)
        self._order_to_scan: dict = {}
        # scan_id → scan record (kept in memory for fast linking)
        self._pending: dict = {}

    # ------------------------------------------------------------------ #
    #  SCAN — called from find_best_target() after sorting candidates      #
    # ------------------------------------------------------------------ #
    def record_scan(self, candidates_raw: list, winner_pair: str, winner_side: str) -> str:
        """
        Record all scored candidates and which one was selected.
        Returns a unique scan_id to link with the eventual trade outcome.

        candidates_raw is the sorted list of tuples:
          (info, side, vol, trade_val, max_lev, total_score,
           required_move_pct, round_trip_fee, goal_score, eta_minutes,
           optional route_to_profit)
        """
        scan_id = f"scan_{int(time.time() * 1000)}"
        ts = datetime.now().isoformat()

        rows = []
        for rank, item in enumerate(candidates_raw[:10]):  # top 10 only
            info, side, vol, trade_val, max_lev, total_score, req_pct, fees, goal_score, eta_min, *rest = item
            route_to_profit = rest[0] if rest else None
            rows.append({
                "rank":            rank + 1,
                "pair":            info.pair,
                "side":            side,
                "leverage":        max_lev,
                "momentum_pct":    round(info.momentum, 4),
                "spread_pct":      round(info.spread_pct, 4),
                "volume_24h":      round(info.volume_24h, 0),
                "notional_usd":    round(trade_val, 2),
                "required_move_pct": round(req_pct, 4),
                "round_trip_fees": round(fees, 4),
                "goal_score":      round(goal_score, 4),
                "eta_minutes":     round(eta_min, 1) if eta_min < 9999 else None,
                "route_to_profit":  round(route_to_profit, 4) if route_to_profit is not None else None,
                "total_score":     round(total_score, 4),
                "selected":        (info.pair == winner_pair and side == winner_side),
            })

        record = {
            "type":        "scan",
            "scan_id":     scan_id,
            "timestamp":   ts,
            "winner_pair": winner_pair,
            "winner_side": winner_side,
            "n_candidates": len(candidates_raw),
            "candidates":  rows,
        }
        self._pending[scan_id] = record
        _append(record)
        return scan_id

    # ------------------------------------------------------------------ #
    #  LINK — called after open_position() returns the order_id           #
    # ------------------------------------------------------------------ #
    def link_order(self, scan_id: str, order_id: str):
        """Associate the open order_id with the scan that chose it."""
        if not scan_id or not order_id:
            return
        self._order_to_scan[order_id] = scan_id
        link = {
            "type":     "link",
            "scan_id":  scan_id,
            "order_id": order_id,
            "timestamp": datetime.now().isoformat(),
        }
        _append(link)

    # ------------------------------------------------------------------ #
    #  OUTCOME — called from close_position() with completed trade dict   #
    # ------------------------------------------------------------------ #
    def record_outcome(self, order_id: str, completed: dict):
        """
        Record actual trade result and marry it to the original scan.
        completed is the dict built inside close_position().
        """
        scan_id = self._order_to_scan.get(order_id, "unknown")

        # Pull the winner's goal_score from the pending scan (if still in memory)
        goal_score_selected  = None
        eta_predicted_min    = None
        n_candidates         = None
        scan_candidates      = None

        if scan_id in self._pending:
            sc = self._pending[scan_id]
            n_candidates = sc.get("n_candidates")
            for row in sc.get("candidates", []):
                if row.get("selected"):
                    goal_score_selected = row["goal_score"]
                    eta_predicted_min   = row["eta_minutes"]
                    break
            scan_candidates = sc.get("candidates")

        hold_sec  = completed.get("hold_seconds", 0)
        net_pnl   = completed.get("net_pnl", 0)
        hold_min  = round(hold_sec / 60, 2)

        # Did we beat the goal?
        goal_hit = (
            net_pnl >= completed.get("entry_fee", 0) + 0.01  # net profit > 0
            and eta_predicted_min is not None
            and hold_min <= eta_predicted_min * 2  # within 2× predicted ETA
        )

        record = {
            "type":               "outcome",
            "scan_id":            scan_id,
            "order_id":           order_id,
            "close_order_id":     completed.get("close_order_id"),
            "pair":               completed.get("pair"),
            "side":               completed.get("side"),
            "leverage":           completed.get("leverage"),
            "entry_price":        completed.get("entry_price"),
            "exit_price":         completed.get("exit_price"),
            "net_pnl":            round(net_pnl, 4),
            "gross_pnl":          round(completed.get("gross_pnl", 0), 4),
            "total_fees":         round(completed.get("total_fees", 0), 4),
            "hold_seconds":       round(hold_sec, 1),
            "hold_minutes":       hold_min,
            "close_reason":       completed.get("reason"),
            "goal_score_selected": goal_score_selected,
            "eta_predicted_min":  eta_predicted_min,
            "n_candidates":       n_candidates,
            "goal_hit":           goal_hit,
            "timestamp":          datetime.now().isoformat(),
            # Full candidate snapshot for deep analysis
            "scan_candidates":    scan_candidates,
        }
        _append(record)

        # Clean up memory
        self._pending.pop(scan_id, None)
        self._order_to_scan.pop(order_id, None)
