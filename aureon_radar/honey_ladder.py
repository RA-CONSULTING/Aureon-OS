#!/usr/bin/env python3
"""
THE HONEY LADDER SYSTEM
=======================
One trade at a time. Penny profit. Shadow proves, live executes.

Philosophy:
- The bee doesn't fly into 38 flowers at once. It visits ONE, collects the nectar, moves on.
- Shadow trades in ALL sectors, ALL the time, proving which signals are PHI-worthy.
- When a shadow trade hits the track record threshold (PHI win rate), it graduates to live.
- Live executes ONE trade at a time, captures the penny, closes, moves to next.
- No stacking. No piling. ONE. Then NEXT.

Components:
1. Shadow Ladder: Multiple sectors, continuous shadow validation
2. Honey Pot: The single live position
3. PHI Track Record: Signal source scoring
4. Frequency Analyzer: Who's trading what, how often
5. Sector Rotator: Which sector has the sweetest nectar right now
"""

import os
import sys
import json
import time
import math
import logging
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List, Tuple
from collections import deque, defaultdict

logger = logging.getLogger(__name__)

# Owner capture floor (Gary Leckey, 2026-09-06): every shadow/ladder TP
# target is clamped UPWARD to the floor (state/capture_floor.json, 1.0%).
# Read at call time; an absent/corrupt file or import failure means the
# floor is absent and targets keep their prior values. Upward-only.
try:
    _EX_ADAPTERS_DIR = str(Path(__file__).resolve().parent / "exchange_adapters")
    if _EX_ADAPTERS_DIR not in sys.path:
        sys.path.insert(0, _EX_ADAPTERS_DIR)
    from capture_floor import load_capture_floor, apply_floor_to_target
except Exception:  # pragma: no cover - floor module unavailable => floor absent
    load_capture_floor = None
    apply_floor_to_target = None

def _chirp_close_failed(payload: dict):
    """Urgency-9 chirp when a broker-side close fails. Never raises."""
    try:
        root = str(Path(__file__).resolve().parent.parent)
        if root not in sys.path:
            sys.path.insert(0, root)
        from aureon_fusion import events
        events.chirp("honey_ladder", "honey_pot_close_failed", 9, payload)
    except Exception:
        pass  # event spine unavailable — failure already logged

# ─── PHI CONSTANTS ────────────────────────────────────────────────────────────
PHI = 1.618033988749895
PHI_INV = 1 / PHI
PHI_SQUARED = PHI ** 2

# ─── DATA STRUCTURES ──────────────────────────────────────────────────────────
@dataclass
class ShadowLadderRun:
    """A single rung on the shadow ladder"""
    signal_id: str
    timestamp: str
    symbol: str
    sector: str  # 'crypto', 'tech', 'commodity', 'forex'
    direction: str
    entry_price: float
    target_price: float  # Penny profit target
    status: str  # 'OPEN', 'HIT', 'MISS', 'EXPIRED'
    pnl: float  # Actual pnl when closed
    source: str  # Which signal source generated this
    phi_score: float  # PHI-based performance score
    ladder_rung: int  # Which rung this graduated from

@dataclass
class SignalSourceRecord:
    """Track record for a signal source"""
    source: str
    total_shadows: int
    hits: int
    misses: int
    phi_win_rate: float  # Weighted by PHI decay
    last_hit_time: float
    current_ladder_rung: int  # 0=unproven, 1=initiate, 2=novice, 3=adept, 4=master, 5=PHI
    sector_specialty: str  # Which sector this source performs best in

@dataclass
class HoneyPot:
    """The single live position"""
    active: bool
    deal_id: str
    symbol: str
    sector: str
    direction: str
    entry_price: float
    target_price: float
    size: float
    source: str  # Which graduated shadow source
    opened_at: float  # timestamp
    max_hold_seconds: int  # Force close if too long

@dataclass
class SectorHeat:
    """How hot a sector is right now"""
    sector: str
    momentum_score: float  # -1 to 1
    volume_surge: float  # multiplier
    shadow_hit_rate: float  # Recent shadow success
    sweet_spot: bool  # Is this the best sector right now

# ─── HONEY LADDER ENGINE ──────────────────────────────────────────────────────
class HoneyLadder:
    """
    The core engine.
    
    Rule 1: ONE live trade at a time. No exceptions.
    Rule 2: Shadow trades run continuously across ALL sectors.
    Rule 3: A shadow must prove itself on PHI rungs before graduating.
    Rule 4: When honey pot is empty, the highest PHI shadow gets promoted.
    Rule 5: Penny profit target. In and out. Quick.
    """
    
    def __init__(self):
        self.shadow_runs: List[ShadowLadderRun] = []
        self.source_records: Dict[str, SignalSourceRecord] = {}
        self.honey_pot: Optional[HoneyPot] = None
        self.sector_heat: Dict[str, SectorHeat] = {}
        
        # Ladder configuration
        self.rung_thresholds = {
            0: 0.0,      # Unproven - any signal starts here
            1: 0.50,     # Initiate - 50% win rate
            2: 0.55,     # Novice - 55% win rate
            3: 0.60,     # Adept - 60% win rate (can graduate to live)
            4: 0.65,     # Master - 65% win rate
            5: 0.70,     # PHI - 70% win rate (highest priority)
        }
        
        self.penny_target_pct = 0.00001  # 0.001% = ~1p/1c net target, overridden per shadow
        self.max_shadows_per_sector = 5
        self.max_hold_seconds = 600  # 10 minutes max hold
        # Bounded growth (bug-hunt MEDIUM): never keep more than this many
        # shadow runs in memory; oldest terminal runs are pruned first.
        # OPEN runs are never pruned.
        try:
            self.max_shadow_runs = int(os.getenv("RADAR_MAX_SHADOW_RUNS", "500"))
        except Exception:
            self.max_shadow_runs = 500
        
        # Frequency analyzer
        self.trade_frequency = defaultdict(lambda: deque(maxlen=100))  # symbol -> timestamps
        self.sector_rotation = deque(["commodity", "tech", "crypto", "forex"], maxlen=4)
    
    def _phi_decay_weight(self, age_seconds: float) -> float:
        """PHI-based time decay - recent trades matter more"""
        return PHI_INV ** (age_seconds / 3600)  # Decay over hours
    
    def _calculate_phi_win_rate(self, source: str) -> float:
        """Calculate PHI-weighted win rate for a source.

        Denominator is HIT + MISS terminal runs only. EXPIRED (capacity
        eviction, never given market time) is excluded; anything that had a
        chance to hit and failed is recorded as MISS by update paths, so a
        source with no losses can no longer read 1.0 by omission.
        """
        now = time.time()
        relevant_runs = [r for r in self.shadow_runs
                        if r.source == source and r.status in ('HIT', 'MISS')]

        if not relevant_runs:
            return 0.0

        weighted_hits = 0.0
        weighted_total = 0.0

        for run in relevant_runs:
            age = max(0.0, now - self._shadow_timestamp(run))
            weight = self._phi_decay_weight(age)
            weighted_total += weight
            if run.status == 'HIT':
                weighted_hits += weight

        return weighted_hits / weighted_total if weighted_total > 0 else 0.0
    
    def _update_source_record(self, source: str):
        """Update the track record for a signal source"""
        if source not in self.source_records:
            self.source_records[source] = SignalSourceRecord(
                source=source,
                total_shadows=0,
                hits=0,
                misses=0,
                phi_win_rate=0.0,
                last_hit_time=0.0,
                current_ladder_rung=0,
                sector_specialty=""
            )
        
        record = self.source_records[source]
        record.phi_win_rate = self._calculate_phi_win_rate(source)
        
        # Determine ladder rung
        for rung in sorted(self.rung_thresholds.keys(), reverse=True):
            if record.phi_win_rate >= self.rung_thresholds[rung]:
                record.current_ladder_rung = rung
                break
        
        # Count hits/misses
        record.hits = sum(1 for r in self.shadow_runs if r.source == source and r.status == 'HIT')
        record.misses = sum(1 for r in self.shadow_runs if r.source == source and r.status == 'MISS')
        record.total_shadows = record.hits + record.misses
    
    def add_shadow(self, symbol: str, sector: str, direction: str, 
                   entry_price: float, source: str, target_price: float = None) -> ShadowLadderRun:
        """Add a new shadow trade to the ladder.
        
        Args:
            target_price: Optional explicit target (for micro-scalping 1-tick)
        """
        
        # Check if we have too many shadows in this sector
        sector_shadows = sum(1 for r in self.shadow_runs 
                            if r.sector == sector and r.status == 'OPEN')
        if sector_shadows >= self.max_shadows_per_sector:
            # Close oldest shadow in this sector
            oldest = min((r for r in self.shadow_runs 
                         if r.sector == sector and r.status == 'OPEN'),
                        key=lambda x: x.timestamp, default=None)
            if oldest:
                # Capacity eviction: the rung was never given market time, so
                # this is not a win or a loss — EXPIRED stays out of the
                # win-rate denominator (only HIT/MISS count).
                oldest.status = 'EXPIRED'
                oldest.pnl = 0.0
        
        # Calculate penny target (or use provided micro-scalp target)
        if target_price is not None:
            target = target_price
        else:
            target = entry_price * (1 + self.penny_target_pct) if direction == 'LONG' else entry_price * (1 - self.penny_target_pct)

        # Owner decree 2026-09-06: TP target = max(computed, capture floor).
        # Upward-only clamp at call time; a floor above the target raises it,
        # a target already beyond the floor is untouched. Missing/corrupt
        # decree file => floor absent, target unchanged (prior behavior).
        if load_capture_floor is not None and apply_floor_to_target is not None:
            _floor = load_capture_floor()
            if _floor is not None:
                _floored = apply_floor_to_target(direction, entry_price, target, _floor)
                if _floored != target:
                    logger.info(f"[FLOOR] shadow target raised to capture floor "
                                f"{_floor * 100:.1f}%: {symbol} {direction} "
                                f"{target} -> {_floored} (owner decree 2026-09-06)")
                    target = _floored
        
        run = ShadowLadderRun(
            signal_id=f"shadow_{int(time.time() * 1000)}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            symbol=symbol,
            sector=sector,
            direction=direction,
            entry_price=entry_price,
            target_price=target,
            status='OPEN',
            pnl=0.0,
            source=source,
            phi_score=0.0,
            ladder_rung=self.source_records.get(source, SignalSourceRecord(
                source=source, total_shadows=0, hits=0, misses=0,
                phi_win_rate=0.0, last_hit_time=0.0, current_ladder_rung=0,
                sector_specialty=""
            )).current_ladder_rung
        )
        
        self.shadow_runs.append(run)
        self._prune_shadow_runs()
        return run

    def _shadow_timestamp(self, run) -> float:
        """Parse a shadow timestamp (ISO str or epoch) → epoch seconds."""
        ts = run.timestamp
        if isinstance(ts, (int, float)):
            return float(ts)
        try:
            return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
        except Exception:
            return 0.0

    def _prune_shadow_runs(self):
        """Bound shadow growth (bug-hunt MEDIUM): drop the oldest terminal
        (non-OPEN) runs when over the cap. OPEN runs are never pruned."""
        excess = len(self.shadow_runs) - self.max_shadow_runs
        if excess <= 0:
            return
        terminals = sorted(
            (r for r in self.shadow_runs if r.status != 'OPEN'),
            key=self._shadow_timestamp,
        )
        drop_ids = {id(r) for r in terminals[:excess]}
        if drop_ids:
            self.shadow_runs = [r for r in self.shadow_runs if id(r) not in drop_ids]
    
    def expire_stale_shadows(self):
        """Fail-closed sweep: an OPEN shadow past max_hold_seconds is a MISS.

        A shadow that never reaches its penny target before max hold is a
        losing run for this system — it must enter the win-rate denominator.
        Without this sweep, a shadow whose symbol stops quoting stays OPEN
        forever and the metric silently keeps only winners (structural 1.0).
        A run whose timestamp cannot be parsed is treated as stale —
        indeterminate outcomes are never defaulted to WIN.
        """
        now = time.time()
        for run in self.shadow_runs:
            if run.status != 'OPEN':
                continue
            if now - self._shadow_timestamp(run) > self.max_hold_seconds:
                run.status = 'MISS'
                run.pnl = 0.0
                self._update_source_record(run.source)
                print(f"[HONEY] SHADOW MISS: {run.symbol} {run.direction} "
                      f"(stale expiry, no target within {self.max_hold_seconds}s)")

    def update_shadow(self, symbol: str, current_price: float):
        """Update all open shadows for a symbol, check for hits/misses"""
        # Expire stale runs first so every past-deadline run is a MISS even
        # when its symbol no longer produces price ticks.
        self.expire_stale_shadows()

        for run in self.shadow_runs:
            if run.symbol != symbol or run.status != 'OPEN':
                continue

            # Check for hit (reached penny target)
            if run.direction == 'LONG' and current_price >= run.target_price:
                run.status = 'HIT'
                run.pnl = (current_price - run.entry_price) / run.entry_price
                self._update_source_record(run.source)
                print(f"[HONEY] SHADOW HIT: {run.symbol} {run.direction} @ {current_price} "
                      f"(target: {run.target_price:.2f}) source: {run.source}")

            elif run.direction == 'SHORT' and current_price <= run.target_price:
                run.status = 'HIT'
                run.pnl = (run.entry_price - current_price) / run.entry_price
                self._update_source_record(run.source)
                print(f"[HONEY] SHADOW HIT: {run.symbol} {run.direction} @ {current_price} "
                      f"(target: {run.target_price:.2f}) source: {run.source}")
    
    def get_graduation_candidate(self) -> Optional[ShadowLadderRun]:
        """Find the highest PHI shadow ready to graduate to live.

        GRADUATION RULE: Any shadow that has HIT its target can graduate.
        No minimum rung. No minimum win rate. Hit = proven = live.

        Owner decree 2026-09-07: the single honey-pot gate is relaxed so the
        radar can hold multiple concurrent live positions. This method no
        longer returns None just because a honey pot is active.
        """
        # Find shadows that have HIT (status=HIT) and are ready to graduate
        candidates = [r for r in self.shadow_runs
                     if r.status == 'HIT']

        if not candidates:
            return None
        
        # Sort by ladder rung (higher = more proven), then by recency.
        # Bug-hunt MEDIUM: recency scoring used to be dead code — the ISO
        # timestamp string was never parsed, so every shadow got age=now.
        now = time.time()
        def score(run):
            record = self.source_records.get(run.source)
            wr = record.phi_win_rate if record else 0.0
            age = max(0.0, now - self._shadow_timestamp(run))
            recency = math.exp(-age / 300)  # 5-minute decay
            return run.ladder_rung * PHI + wr * recency
        
        candidates.sort(key=score, reverse=True)
        return candidates[0]
    
    def open_honey_pot(self, shadow: ShadowLadderRun, deal_id: str, size: float):
        """Promote a shadow trade to live honey pot"""
        self.honey_pot = HoneyPot(
            active=True,
            deal_id=deal_id,
            symbol=shadow.symbol,
            sector=shadow.sector,
            direction=shadow.direction,
            entry_price=shadow.entry_price,
            target_price=shadow.target_price,
            size=size,
            source=shadow.source,
            opened_at=time.time(),
            max_hold_seconds=self.max_hold_seconds
        )
        # Carry audit_id for ledger tracking
        if hasattr(shadow, '_audit_id'):
            self.honey_pot._audit_id = shadow._audit_id
        print(f"[HONEY] HONEY POT OPEN: {shadow.symbol} {shadow.direction} "
              f"size={size} target={shadow.target_price:.2f} "
              f"source={shadow.source} (rung {shadow.ladder_rung})")
    
    def _close_broker_position(self, connector, pot: HoneyPot) -> bool:
        """Close the live position server-side and VERIFY the close.

        Reuses the DualCapitalConnector pattern (authenticate → DELETE
        /positions/{dealId} → re-fetch /positions to confirm the dealId is
        gone). Returns True only when the close is confirmed server-side.
        """
        try:
            if not getattr(connector, "authenticated", False):
                if not connector.authenticate():
                    logger.error(f"[HONEY] Broker close FAILED for {pot.deal_id}: "
                                 f"Capital.com not authenticated")
                    return False

            result = connector.close_live_position(pot.deal_id)
            if not (isinstance(result, dict) and result.get("success")):
                logger.error(f"[HONEY] Broker close FAILED for {pot.deal_id}: "
                             f"{result.get('error', result) if isinstance(result, dict) else result}")
                return False

            # Verify server-side: the dealId must be gone from open positions
            positions = connector.get_live_positions()
            for pos in positions:
                deal = pos.get("position", {}).get("dealId", "")
                if deal == pot.deal_id:
                    logger.error(f"[HONEY] Broker close UNCONFIRMED for {pot.deal_id}: "
                                 f"position still open server-side")
                    return False
            return True
        except Exception as e:
            logger.error(f"[HONEY] Broker close exception for {pot.deal_id}: {e}")
            return False

    def close_honey_pot(self, pnl: float):
        """Close the honey pot, record the result.

        FAIL-CLOSED (owner decree 2026-09-04): when a live broker connector
        is attached (radar sets `honey_ladder.connector`), the position is
        closed on the broker FIRST and the close verified server-side. Only
        then is local state cleared. If the close fails or cannot be
        verified, local state stays OPEN, an urgency-9 chirp fires, and the
        failure is logged — the position is never silently orphaned.
        """
        if not self.honey_pot:
            return

        pot = self.honey_pot
        connector = getattr(self, "connector", None)

        if connector is not None and getattr(pot, "deal_id", None):
            if not self._close_broker_position(connector, pot):
                # Keep local state OPEN; chirp urgency 9 + log
                logger.error(f"[HONEY] HONEY POT CLOSE REFUSED: {pot.symbol} "
                             f"dealId={pot.deal_id} — broker close failed/unconfirmed; "
                             f"local state kept OPEN")
                _chirp_close_failed({
                    "symbol": pot.symbol,
                    "direction": pot.direction,
                    "deal_id": pot.deal_id,
                    "reason": "broker close failed or unconfirmed",
                    "held_seconds": int(time.time() - pot.opened_at),
                })
                return

        self.honey_pot = None

        print(f"[HONEY] HONEY POT CLOSED: {pot.symbol} PnL={pnl:+.4f} "
              f"(held {time.time() - pot.opened_at:.0f}s)")

        # Update source record
        if pot.source in self.source_records:
            record = self.source_records[pot.source]
            if pnl > 0:
                record.last_hit_time = time.time()
    
    def check_honey_pot(self, current_price: float) -> bool:
        """Check if honey pot should be closed. Returns True if closed."""
        if not self.honey_pot or not self.honey_pot.active:
            return False
        
        pot = self.honey_pot
        age = time.time() - pot.opened_at
        
        # Check target hit
        if pot.direction == 'LONG' and current_price >= pot.target_price:
            pnl = (current_price - pot.entry_price) / pot.entry_price
            self.close_honey_pot(pnl)
            # True only if the pot actually closed (broker close may refuse)
            return self.honey_pot is None
        elif pot.direction == 'SHORT' and current_price <= pot.target_price:
            pnl = (pot.entry_price - current_price) / pot.entry_price
            self.close_honey_pot(pnl)
            return self.honey_pot is None
        
        # Check max hold time
        if age > pot.max_hold_seconds:
            pnl = (current_price - pot.entry_price) / pot.entry_price if pot.direction == 'LONG' else (pot.entry_price - current_price) / pot.entry_price
            self.close_honey_pot(pnl)
            return self.honey_pot is None
        
        return False
    
    def get_sector_heat(self) -> Dict[str, SectorHeat]:
        """Calculate which sectors are hottest right now"""
        sectors = ['commodity', 'tech', 'crypto', 'forex']
        heat_map = {}
        
        for sector in sectors:
            # Recent shadow performance in this sector
            recent = [r for r in self.shadow_runs 
                     if r.sector == sector 
                     and r.status in ('HIT', 'MISS')
                     and time.time() - datetime.fromisoformat(r.timestamp).timestamp() < 3600]
            
            hits = sum(1 for r in recent if r.status == 'HIT')
            total = len(recent)
            hit_rate = hits / total if total > 0 else 0.0
            
            # Volume surge (how many shadows running)
            active = sum(1 for r in self.shadow_runs if r.sector == sector and r.status == 'OPEN')
            
            heat_map[sector] = SectorHeat(
                sector=sector,
                momentum_score=hit_rate * 2 - 1,  # -1 to 1
                volume_surge=active / self.max_shadows_per_sector,
                shadow_hit_rate=hit_rate,
                sweet_spot=hit_rate > 0.6 and active > 0
            )
        
        self.sector_heat = heat_map
        return heat_map
    
    def get_frequency_report(self) -> Dict:
        """Analyze trading frequency patterns"""
        now = time.time()
        
        # Symbol frequency
        symbol_freq = {}
        for symbol, timestamps in self.trade_frequency.items():
            recent = [t for t in timestamps if now - t < 3600]
            symbol_freq[symbol] = len(recent)
        
        # Source frequency
        source_freq = defaultdict(int)
        for run in self.shadow_runs:
            if run.status == 'HIT':
                source_freq[run.source] += 1
        
        # Sector frequency
        sector_freq = defaultdict(int)
        for run in self.shadow_runs:
            if run.status == 'HIT':
                sector_freq[run.sector] += 1
        
        return {
            'symbol_frequency': dict(symbol_freq),
            'source_frequency': dict(source_freq),
            'sector_frequency': dict(sector_freq),
            'total_shadows': len(self.shadow_runs),
            'open_shadows': sum(1 for r in self.shadow_runs if r.status == 'OPEN'),
            'honey_pot_active': self.honey_pot.active if self.honey_pot else False
        }
    
    def get_status(self) -> Dict:
        """Get full ladder status"""
        return {
            'honey_pot': {
                'active': self.honey_pot.active if self.honey_pot else False,
                'symbol': self.honey_pot.symbol if self.honey_pot else None,
                'sector': self.honey_pot.sector if self.honey_pot else None,
                'direction': self.honey_pot.direction if self.honey_pot else None,
                'held_seconds': time.time() - self.honey_pot.opened_at if self.honey_pot else 0
            },
            'shadow_stats': {
                'total': len(self.shadow_runs),
                'open': sum(1 for r in self.shadow_runs if r.status == 'OPEN'),
                'hits': sum(1 for r in self.shadow_runs if r.status == 'HIT'),
                'misses': sum(1 for r in self.shadow_runs if r.status == 'MISS'),
                'expired': sum(1 for r in self.shadow_runs if r.status == 'EXPIRED')
            },
            'source_records': {
                source: {
                    'ladder_rung': record.current_ladder_rung,
                    'phi_win_rate': round(record.phi_win_rate, 3),
                    'total': record.total_shadows,
                    'hits': record.hits,
                    'specialty': record.sector_specialty
                }
                for source, record in self.source_records.items()
            },
            'sector_heat': {
                sector: {
                    'hit_rate': round(heat.shadow_hit_rate, 3),
                    'sweet_spot': heat.sweet_spot
                }
                for sector, heat in self.get_sector_heat().items()
            }
        }


# ─── EXAMPLE USAGE / TEST (SIMULATED PRICES — NOT LIVE DATA) ──────────────────
if __name__ == "__main__":
    ladder = HoneyLadder()
    
    print("=" * 60)
    print("HONEY LADDER SYSTEM TEST — SIMULATED PRICES ONLY")
    print("=" * 60)
    
    # Simulate some shadow trades with fabricated prices for unit testing.
    sources = ['scanner', 'ollama', 'planetary', 'crypto_corr', 'stock_corr']
    sectors = ['commodity', 'tech', 'crypto', 'forex']
    
    for i in range(20):
        source = sources[i % len(sources)]
        sector = sectors[i % len(sectors)]
        symbol = f"SYM{i}"
        direction = 'LONG' if i % 2 == 0 else 'SHORT'
        price = 100.0 + i  # SIMULATED test price, not a market quote
        
        run = ladder.add_shadow(symbol, sector, direction, price, source)

        # Simulate price movement
        if i < 10:
            # First 10 hit
            ladder.update_shadow(symbol, price * 1.01)
        else:
            # Rest miss: price never reaches the target and the run goes
            # past max hold — backdate it so the expiry sweep records MISS.
            backdated = time.time() - ladder.max_hold_seconds - 1
            run.timestamp = datetime.fromtimestamp(
                backdated, tz=timezone.utc).isoformat()
            ladder.update_shadow(symbol, price * 0.99)
    
    print("\nStatus after 20 shadows:")
    status = ladder.get_status()
    print(json.dumps(status, indent=2))
    
    # Try to graduate
    candidate = ladder.get_graduation_candidate()
    if candidate:
        print(f"\n[GRADUATION] CANDIDATE: {candidate.symbol} from {candidate.source}")
        ladder.open_honey_pot(candidate, "deal_123", 0.01)
        
        # Simulate price hitting target
        ladder.check_honey_pot(candidate.target_price * 1.001)
    
    print("\nFinal status:")
    print(json.dumps(ladder.get_status(), indent=2))
