"""
Aureon Trade Ledger & Audit System

Tracks the full lifecycle:
  SHADOW HIT -> ORDER SENT -> CAPITAL CONFIRMED -> POSITION OPEN -> POSITION CLOSED

Validates every trade against Capital.com positions API.
Writes immutable audit log to trade_ledger.jsonl.

Gary Leckey | 2026 | Trust but verify
"""

import json
import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

LEDGER_FILE = Path(__file__).parent / "trade_ledger.jsonl"


@dataclass
class TradeAuditRecord:
    audit_id: str
    timestamp: str
    stage: str  # SHADOW_HIT | ORDER_SENT | CAPITAL_CONFIRMED | POSITION_OPEN | POSITION_CLOSED | ORDER_FAILED
    symbol: str
    direction: str
    size: float
    entry_price: float
    target_price: float
    deal_id: Optional[str]
    capital_position_id: Optional[str]
    capital_confirmed: bool
    pnl: Optional[float]
    error: Optional[str]
    source: str
    rung: int


class TradeLedger:
    """
    Immutable audit trail for every Honey Ladder trade.
    Validates against Capital.com positions API.
    """
    
    def __init__(self, capital_connector=None):
        self.capital = capital_connector
        self._audit_counter = 0
        self._ensure_file()
    
    def _ensure_file(self):
        if not LEDGER_FILE.exists():
            LEDGER_FILE.touch()
    
    def _next_id(self) -> str:
        self._audit_counter += 1
        return f"AUD-{int(time.time())}-{self._audit_counter:04d}"
    
    def _write(self, record: TradeAuditRecord):
        """Append immutable record to ledger."""
        with open(LEDGER_FILE, 'a') as f:
            f.write(json.dumps(asdict(record)) + '\n')
    
    def shadow_hit(self, symbol: str, direction: str, entry_price: float, 
                   target_price: float, source: str, rung: int) -> str:
        """Log when a shadow hits its target."""
        audit_id = self._next_id()
        record = TradeAuditRecord(
            audit_id=audit_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            stage="SHADOW_HIT",
            symbol=symbol,
            direction=direction,
            size=0.0,
            entry_price=entry_price,
            target_price=target_price,
            deal_id=None,
            capital_position_id=None,
            capital_confirmed=False,
            pnl=None,
            error=None,
            source=source,
            rung=rung
        )
        self._write(record)
        logger.info(f"[LEDGER] {audit_id} SHADOW_HIT {symbol} {direction} @ {entry_price}")
        return audit_id
    
    def order_sent(self, audit_id: str, symbol: str, direction: str, size: float,
                   entry_price: float, target_price: float, source: str, rung: int) -> str:
        """Log when order is sent to Capital.com."""
        record = TradeAuditRecord(
            audit_id=audit_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            stage="ORDER_SENT",
            symbol=symbol,
            direction=direction,
            size=size,
            entry_price=entry_price,
            target_price=target_price,
            deal_id=None,
            capital_position_id=None,
            capital_confirmed=False,
            pnl=None,
            error=None,
            source=source,
            rung=rung
        )
        self._write(record)
        logger.info(f"[LEDGER] {audit_id} ORDER_SENT {symbol} {direction} size={size}")
        return audit_id
    
    def capital_confirmed(self, audit_id: str, deal_id: str, 
                          capital_response: dict) -> bool:
        """Log Capital.com confirmation. Validate with positions API."""
        confirmed = False
        position_id = None
        error = None
        
        try:
            if self.capital:
                # Wait a moment for position to appear
                time.sleep(1)
                positions = self.capital.get_positions()
                
                # Match by dealId
                for pos in positions:
                    pos_deal = pos.get('position', {}).get('dealId', '')
                    if pos_deal == deal_id:
                        confirmed = True
                        position_id = pos_deal
                        break
                
                if not confirmed:
                    error = f"dealId {deal_id} not found in Capital.com positions"
        except Exception as e:
            error = str(e)
        
        record = TradeAuditRecord(
            audit_id=audit_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            stage="CAPITAL_CONFIRMED" if confirmed else "ORDER_FAILED",
            symbol="",  # Will be filled from previous record
            direction="",
            size=0.0,
            entry_price=0.0,
            target_price=0.0,
            deal_id=deal_id,
            capital_position_id=position_id,
            capital_confirmed=confirmed,
            pnl=None,
            error=error,
            source="",
            rung=0
        )
        self._write(record)
        
        if confirmed:
            logger.info(f"[LEDGER] {audit_id} CAPITAL_CONFIRMED dealId={deal_id}")
        else:
            logger.error(f"[LEDGER] {audit_id} ORDER_FAILED dealId={deal_id} error={error}")
        
        return confirmed
    
    def position_closed(self, audit_id: str, deal_id: str, pnl: float):
        """Log when a position is closed (target hit or manual)."""
        record = TradeAuditRecord(
            audit_id=audit_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            stage="POSITION_CLOSED",
            symbol="",
            direction="",
            size=0.0,
            entry_price=0.0,
            target_price=0.0,
            deal_id=deal_id,
            capital_position_id=None,
            capital_confirmed=True,
            pnl=pnl,
            error=None,
            source="",
            rung=0
        )
        self._write(record)
        logger.info(f"[LEDGER] {audit_id} POSITION_CLOSED dealId={deal_id} PnL={pnl:.2f}")
    
    def get_audit_trail(self, audit_id: str) -> List[dict]:
        """Get full lifecycle for an audit ID."""
        trail = []
        if LEDGER_FILE.exists():
            with open(LEDGER_FILE, 'r') as f:
                for line in f:
                    try:
                        record = json.loads(line.strip())
                        if record.get('audit_id') == audit_id:
                            trail.append(record)
                    except:
                        pass
        return trail
    
    def get_summary(self) -> dict:
        """Get summary stats from ledger."""
        stats = {
            'total_shadow_hits': 0,
            'total_orders_sent': 0,
            'total_confirmed': 0,
            'total_failed': 0,
            'total_closed': 0,
            'total_pnl': 0.0,
            'unconfirmed_orders': 0,
        }
        
        if not LEDGER_FILE.exists():
            return stats
        
        with open(LEDGER_FILE, 'r') as f:
            for line in f:
                try:
                    record = json.loads(line.strip())
                    stage = record.get('stage', '')
                    if stage == 'SHADOW_HIT':
                        stats['total_shadow_hits'] += 1
                    elif stage == 'ORDER_SENT':
                        stats['total_orders_sent'] += 1
                    elif stage == 'CAPITAL_CONFIRMED':
                        stats['total_confirmed'] += 1
                    elif stage == 'ORDER_FAILED':
                        stats['total_failed'] += 1
                    elif stage == 'POSITION_CLOSED':
                        stats['total_closed'] += 1
                        pnl = record.get('pnl', 0)
                        if pnl:
                            stats['total_pnl'] += pnl
                except:
                    pass
        
        stats['unconfirmed_orders'] = stats['total_orders_sent'] - stats['total_confirmed'] - stats['total_failed']
        return stats
    
    def print_summary(self):
        """Print human-readable summary."""
        stats = self.get_summary()
        print("="*60)
        print("AUREON TRADE LEDGER SUMMARY")
        print("="*60)
        print(f"  Shadow hits:       {stats['total_shadow_hits']}")
        print(f"  Orders sent:       {stats['total_orders_sent']}")
        print(f"  Confirmed by Cap:  {stats['total_confirmed']}")
        print(f"  Failed:            {stats['total_failed']}")
        print(f"  Unconfirmed:       {stats['unconfirmed_orders']}")
        print(f"  Positions closed:  {stats['total_closed']}")
        print(f"  Total PnL:         £{stats['total_pnl']:.2f}")
        print("="*60)


if __name__ == "__main__":
    ledger = TradeLedger()
    ledger.print_summary()
