#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           CHAIN-LINK SHADOW TRADING SYSTEM                                    ║
║                                                                              ║
║  Shadow trades form a validation chain:                                       ║
║    Trade N validates Trade N+1                                               ║
║    A trade is only promoted to live if previous 3 shadows were profitable    ║
║                                                                              ║
║  FORCE-ARMED MODE:                                                           ║
║    Hive is ARMED (executes live) but continues shadow validation            ║
║    Every live trade is shadow-validated by the chain behind it              ║
║    If chain breaks (3 losses in a row), auto-disarm                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import time
import math
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict

RADAR_DIR = Path("C:/Users/user/.kimi_openclaw/workspace/aureon_radar")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(RADAR_DIR / "chain_link.log")
    ]
)
logger = logging.getLogger('CHAIN_LINK')

# ═══════════════════════════════════════════════════════════════════════════════
# CHAIN-LINK SHADOW SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ChainLink:
    link_id: str
    timestamp: str
    symbol: str
    direction: str
    entry: float
    target: float
    stop: float
    status: str  # OPEN, PROFIT, LOSS, EXPIRED
    pnl: float
    validates: Optional[str] = None  # ID of next link this one validates
    validated_by: Optional[str] = None  # ID of previous link that validates this one

class ChainLinkShadowSystem:
    """
    Chain-link shadow validation.
    
    Each shadow trade forms a link in a chain.
    A link validates the NEXT link.
    Live execution requires 3 consecutive profitable links.
    """
    
    def __init__(self):
        self.links: List[ChainLink] = []
        self.chain_file = RADAR_DIR / "chain_link_shadows.jsonl"
        self.min_chain_length = 3  # Need 3 profitable links to promote
        self.consecutive_losses = 0
        self.max_consecutive_losses = 3  # Auto-disarm after 3 losses
        self._load_chain()
        
    def _load_chain(self):
        if self.chain_file.exists():
            with open(self.chain_file) as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        self.links.append(ChainLink(**data))
                    except:
                        pass
            logger.info(f"Loaded chain: {len(self.links)} links")
    
    def _save_link(self, link: ChainLink):
        with open(self.chain_file, 'a') as f:
            f.write(json.dumps(asdict(link)) + '\n')
    
    def open_link(self, symbol: str, direction: str, entry: float, target: float, stop: float) -> ChainLink:
        """Open a new chain link (shadow trade)."""
        link_id = f"link_{int(time.time() * 1000)}_{symbol}"
        
        # Find previous open link to chain to
        prev_link = None
        for link in reversed(self.links):
            if link.status == "OPEN" and link.symbol == symbol:
                prev_link = link
                break
        
        link = ChainLink(
            link_id=link_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            symbol=symbol,
            direction=direction,
            entry=entry,
            target=target,
            stop=stop,
            status="OPEN",
            pnl=0.0,
            validated_by=prev_link.link_id if prev_link else None
        )
        
        # Update previous link to validate this one
        if prev_link:
            prev_link.validates = link_id
        
        self.links.append(link)
        self._save_link(link)
        
        logger.info(f"CHAIN OPEN: {link_id} {symbol} {direction} @ {entry}")
        if prev_link:
            logger.info(f"  ↳ Validated by: {prev_link.link_id}")
        
        return link
    
    def close_link(self, link_id: str, exit_price: float):
        """Close a chain link and calculate PnL."""
        for link in self.links:
            if link.link_id == link_id and link.status == "OPEN":
                if link.direction == "LONG":
                    link.pnl = (exit_price - link.entry) / link.entry
                else:
                    link.pnl = (link.entry - exit_price) / link.entry
                
                if link.pnl > 0:
                    link.status = "PROFIT"
                    self.consecutive_losses = 0
                    logger.info(f"CHAIN PROFIT: {link_id} +{link.pnl:.4f}")
                else:
                    link.status = "LOSS"
                    self.consecutive_losses += 1
                    logger.info(f"CHAIN LOSS: {link_id} {link.pnl:.4f}")
                
                self._save_link(link)
                return link
        
        return None
    
    def is_chain_valid(self, symbol: str) -> bool:
        """Check if the chain for a symbol has 3 consecutive profitable links."""
        symbol_links = [l for l in self.links if l.symbol == symbol]
        if len(symbol_links) < self.min_chain_length:
            return False
        
        # Check last 3 closed links
        closed = [l for l in symbol_links if l.status in ("PROFIT", "LOSS")]
        if len(closed) < self.min_chain_length:
            return False
        
        last_three = closed[-self.min_chain_length:]
        return all(l.status == "PROFIT" for l in last_three)
    
    def should_disarm(self) -> bool:
        """Check if we should disarm due to broken chain."""
        return self.consecutive_losses >= self.max_consecutive_losses
    
    def get_chain_stats(self) -> Dict:
        """Get chain statistics."""
        closed = [l for l in self.links if l.status in ("PROFIT", "LOSS")]
        profits = len([l for l in closed if l.status == "PROFIT"])
        losses = len([l for l in closed if l.status == "LOSS"])
        total = profits + losses
        
        return {
            "total_links": len(self.links),
            "closed_links": total,
            "profits": profits,
            "losses": losses,
            "win_rate": profits / total if total else 0,
            "consecutive_losses": self.consecutive_losses,
            "chain_valid": self.is_chain_valid("USDJPY")  # Example
        }

# ═══════════════════════════════════════════════════════════════════════════════
# FORCE-ARMED HIVE WITH CHAIN-LINK VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

class ForceArmedHive:
    """
    The hive is FORCE-ARMED (live trading active) but uses chain-link
    shadow validation for every trade.
    
    If chain breaks (3 consecutive losses), auto-disarm.
    """
    
    def __init__(self):
        self.chain = ChainLinkShadowSystem()
        self.armed = True  # FORCE ARMED
        self.state_file = RADAR_DIR / "hive_state.json"
        self._save_state()
        
    def _save_state(self):
        with open(self.state_file, 'w') as f:
            json.dump({
                "armed": self.armed,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "mode": "FORCE_ARMED_CHAIN_LINK",
                "chain_stats": self.chain.get_chain_stats()
            }, f, indent=2)
    
    def process_signal(self, symbol: str, direction: str, price: float, target: float, stop: float):
        """Process a trading signal with chain-link validation."""
        
        # Step 1: Open shadow link
        link = self.chain.open_link(symbol, direction, price, target, stop)
        
        # Step 2: Check if chain is valid for live execution
        chain_valid = self.chain.is_chain_valid(symbol)
        
        if self.armed and chain_valid:
            # Step 3: Execute LIVE
            logger.info(f"🐝 LIVE EXECUTE: {symbol} {direction} @ {price} (chain validated)")
            self._execute_live(symbol, direction, price, target, stop)
            return "LIVE"
        elif self.armed and not chain_valid:
            # Step 4: Shadow only until chain builds
            logger.info(f"🎭 SHADOW ONLY: {symbol} {direction} @ {price} (building chain)")
            return "SHADOW"
        else:
            logger.info(f"🔒 DISARMED: {symbol} {direction} (chain broken)")
            return "BLOCKED"
    
    def _execute_live(self, symbol: str, direction: str, price: float, target: float, stop: float):
        """Execute a live trade on Capital.com."""
        # This would call Capital.com API
        # For now, log it
        live_file = RADAR_DIR / "live_trades.jsonl"
        with open(live_file, 'a') as f:
            f.write(json.dumps({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "symbol": symbol,
                "direction": direction,
                "entry": price,
                "target": target,
                "stop": stop,
                "source": "chain_link_validated",
                "status": "EXECUTED"
            }) + '\n')
    
    def check_disarm(self):
        """Check if we should disarm due to broken chain."""
        if self.chain.should_disarm():
            self.armed = False
            logger.error("🚨 AUTO-DISARM: 3 consecutive losses, chain broken")
            self._save_state()
            return True
        return False
    
    def force_rearm(self):
        """Manually rearm the hive."""
        self.armed = True
        self.chain.consecutive_losses = 0
        logger.info("🐝 FORCE RE-ARMED: Hive active, chain reset")
        self._save_state()

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    hive = ForceArmedHive()
    
    print("=" * 70)
    print("     FORCE-ARMED HIVE WITH CHAIN-LINK VALIDATION")
    print("=" * 70)
    print(f"Mode: FORCE ARMED")
    print(f"Chain links: {len(hive.chain.links)}")
    print(f"Stats: {json.dumps(hive.chain.get_chain_stats(), indent=2)}")
    print("=" * 70)
    
    # Example: Process a signal
    result = hive.process_signal("USDJPY", "LONG", 160.0, 160.5, 159.5)
    print(f"\nSignal result: {result}")

if __name__ == "__main__":
    main()
