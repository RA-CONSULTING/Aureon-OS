#!/usr/bin/env python3
"""
🇮🇪🎯 SNIPER KILL VALIDATOR - THE DOUBLE-CHECK BEFORE THE SHOT 🎯🇮🇪
====================================================================

This module validates the kill BEFORE execution:
1. Calculate exact target price for profit
2. Validate current market still supports the kill
3. Echo back: "YES - KILL CONFIRMED" or "NO - REASON WHY"

"We don't pull the trigger until we KNOW we have the kill."

Gary Leckey | December 2025
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Tuple, Optional

# =============================================================================
# KILL VALIDATION RESULT
# =============================================================================

@dataclass
class KillValidation:
    """The result of validating a kill shot."""
    is_valid: bool              # Can we take the shot?
    reason: str                 # Why yes or why no
    
    # The math
    entry_price: float          # What we bought at
    entry_qty: float            # How much we have
    entry_cost: float           # Total cost (price * qty)
    entry_fee: float            # Fee paid on entry
    
    target_price: float         # Price we need to hit
    current_price: float        # Current market price
    
    # P&L breakdown
    gross_pnl: float            # Current unrealized P&L
    exit_fee: float             # Estimated exit fee
    net_pnl: float              # Net P&L after fees
    
    # Gap
    price_gap: float            # How far from target (negative = still waiting)
    price_gap_pct: float        # Gap as percentage
    
    # Timing
    eta_seconds: Optional[float] # Estimated time to kill (if momentum data available)
    
    def __str__(self) -> str:
        if self.is_valid:
            return f"""
╔══════════════════════════════════════════════════════════════╗
║  🇮🇪🎯 KILL VALIDATED - TAKE THE SHOT! 🎯🇮🇪                    ║
╠══════════════════════════════════════════════════════════════╣
║  Entry:        {self.entry_price:.6f} x {self.entry_qty:.2f} = ${self.entry_cost:.4f}
║  Current:      {self.current_price:.6f}
║  Target:       {self.target_price:.6f} ✅ CLEARED
║  ──────────────────────────────────────────────────────────  ║
║  Gross P&L:    ${self.gross_pnl:+.4f}
║  Exit Fee:     -${self.exit_fee:.4f}
║  NET PROFIT:   ${self.net_pnl:+.4f} 💰
║  ──────────────────────────────────────────────────────────  ║
║  ✅ {self.reason}
╚══════════════════════════════════════════════════════════════╝"""
        else:
            return f"""
╔══════════════════════════════════════════════════════════════╗
║  ⏳ KILL NOT READY - HOLD POSITION ⏳                        ║
╠══════════════════════════════════════════════════════════════╣
║  Entry:        {self.entry_price:.6f} x {self.entry_qty:.2f} = ${self.entry_cost:.4f}
║  Current:      {self.current_price:.6f}
║  Target:       {self.target_price:.6f} ❌ NOT YET
║  Gap:          {self.price_gap_pct:+.3f}% (need +{abs(self.price_gap):.6f})
║  ──────────────────────────────────────────────────────────  ║
║  Gross P&L:    ${self.gross_pnl:+.4f}
║  Exit Fee:     -${self.exit_fee:.4f} (estimated)
║  Net if exit:  ${self.net_pnl:+.4f} ❌ LOSS
║  ──────────────────────────────────────────────────────────  ║
║  ❌ {self.reason}
╚══════════════════════════════════════════════════════════════╝"""


# =============================================================================
# THE KILL VALIDATOR
# =============================================================================

class SniperKillValidator:
    """
    The double-check before the kill.
    
    "The sniper never shoots without confirming the target."
    """
    
    # Default fee assumptions (conservative)
    DEFAULT_FEE_RATE = 0.001      # 0.1% per trade (Binance standard)
    DEFAULT_SLIPPAGE = 0.001      # 0.1% slippage buffer
    MIN_NET_PROFIT = 0.01         # $0.01 minimum net profit required
    
    def __init__(self, fee_rate: float = None, slippage: float = None, min_net: float = None):
        self.fee_rate = fee_rate or self.DEFAULT_FEE_RATE
        self.slippage = slippage or self.DEFAULT_SLIPPAGE
        self.min_net_profit = min_net or self.MIN_NET_PROFIT
        self.total_cost_rate = self.fee_rate * 2 + self.slippage  # Entry + Exit + Slippage
    
    def calculate_target_price(
        self,
        entry_price: float,
        entry_qty: float,
        entry_fee: float = None
    ) -> Tuple[float, Dict]:
        """
        Calculate the exact price needed for a profitable kill.
        
        Returns: (target_price, breakdown_dict)
        """
        entry_cost = entry_price * entry_qty
        
        # Entry fee (actual or estimated)
        if entry_fee is None:
            entry_fee = entry_cost * self.fee_rate
        
        # Total cost basis
        total_cost_basis = entry_cost + entry_fee
        
        # What we need to receive to cover:
        # 1. Original cost
        # 2. Entry fee (already paid)
        # 3. Exit fee (estimated)
        # 4. Min profit ($0.01)
        
        # Exit value needed = cost_basis + exit_fee + min_profit
        # Exit value = exit_price * qty
        # exit_fee = exit_value * fee_rate
        # So: exit_value = cost_basis + (exit_value * fee_rate) + min_profit
        # exit_value * (1 - fee_rate) = cost_basis + min_profit
        # exit_value = (cost_basis + min_profit) / (1 - fee_rate)
        
        required_exit_value = (total_cost_basis + self.min_net_profit) / (1 - self.fee_rate)
        target_price = required_exit_value / entry_qty
        
        breakdown = {
            'entry_price': entry_price,
            'entry_qty': entry_qty,
            'entry_cost': entry_cost,
            'entry_fee': entry_fee,
            'total_cost_basis': total_cost_basis,
            'required_exit_value': required_exit_value,
            'target_price': target_price,
            'price_increase_needed': target_price - entry_price,
            'price_increase_pct': (target_price / entry_price - 1) * 100,
            'min_net_profit': self.min_net_profit,
            'fee_rate': self.fee_rate
        }
        
        return target_price, breakdown
    
    def validate_kill(
        self,
        entry_price: float,
        entry_qty: float,
        current_price: float,
        entry_fee: float = None
    ) -> KillValidation:
        """
        🎯 THE DOUBLE-CHECK - Validate if we can take the kill shot.
        
        Returns a KillValidation with YES/NO and full reasoning.
        """
        # Calculate what we need
        target_price, breakdown = self.calculate_target_price(entry_price, entry_qty, entry_fee)
        
        entry_cost = breakdown['entry_cost']
        entry_fee_used = breakdown['entry_fee']
        
        # Current value
        current_value = current_price * entry_qty
        gross_pnl = current_value - entry_cost
        
        # Estimated exit fee
        exit_fee = current_value * self.fee_rate
        
        # Net P&L
        net_pnl = gross_pnl - entry_fee_used - exit_fee
        
        # Price gap
        price_gap = current_price - target_price
        price_gap_pct = (current_price / target_price - 1) * 100
        
        # THE VALIDATION
        is_valid = current_price >= target_price and net_pnl >= self.min_net_profit
        
        if is_valid:
            reason = f"DOUBLE-CHECK PASSED: Net ${net_pnl:.4f} >= ${self.min_net_profit:.2f} target"
        else:
            if current_price < target_price:
                reason = f"Price {current_price:.6f} < Target {target_price:.6f} - Need +{price_gap_pct:.3f}%"
            else:
                reason = f"Net ${net_pnl:.4f} < ${self.min_net_profit:.2f} minimum - Fees eating profit"
        
        return KillValidation(
            is_valid=is_valid,
            reason=reason,
            entry_price=entry_price,
            entry_qty=entry_qty,
            entry_cost=entry_cost,
            entry_fee=entry_fee_used,
            target_price=target_price,
            current_price=current_price,
            gross_pnl=gross_pnl,
            exit_fee=exit_fee,
            net_pnl=net_pnl,
            price_gap=price_gap,
            price_gap_pct=price_gap_pct,
            eta_seconds=None
        )
    
    def validate_with_eta(
        self,
        entry_price: float,
        entry_qty: float,
        current_price: float,
        pnl_velocity: float,
        momentum_score: float = 0.0,
        cascade_factor: float = 1.0,
        entry_fee: float = None,
        symbol: str = "UNKNOWN",
        exchange: str = "binance"
    ) -> KillValidation:
        """
        🎯⏱️ VALIDATE WITH ETA VERIFICATION - Track predictions!
        
        Like validate_kill but also:
        - Registers ETA prediction with verification system
        - Applies learned corrections to ETA
        - Returns corrected ETA confidence
        """
        validation = self.validate_kill(entry_price, entry_qty, current_price, entry_fee)
        
        # Calculate raw ETA
        gap_value = abs(validation.price_gap * entry_qty)
        raw_eta = gap_value / pnl_velocity if pnl_velocity > 0 else float('inf')
        
        # Try to get corrected ETA from verification system
        try:
            from aureon.analytics.eta_verification_system import get_eta_verifier
            verifier = get_eta_verifier()
            
            proximity = 1.0 - abs(validation.price_gap_pct) / 100 if validation.price_gap_pct < 0 else 1.0
            confidence = verifier.get_prediction_confidence(
                momentum_score, pnl_velocity, proximity, cascade_factor
            )
            
            corrected_eta = verifier.get_corrected_eta(
                raw_eta, momentum_score, pnl_velocity, confidence
            )
            
            # Register prediction
            if corrected_eta < float('inf') and corrected_eta > 0:
                verifier.register_eta_prediction(
                    symbol=symbol,
                    exchange=exchange,
                    eta_seconds=corrected_eta,
                    current_pnl=validation.net_pnl,
                    target_pnl=self.min_net_profit,
                    pnl_velocity=pnl_velocity,
                    momentum_score=momentum_score,
                    cascade_factor=cascade_factor,
                    confidence=confidence
                )
            
            validation.eta_seconds = corrected_eta
            
        except ImportError:
            validation.eta_seconds = raw_eta
        except Exception:
            validation.eta_seconds = raw_eta
        
        return validation
    
    def echo_status(
        self,
        entry_price: float,
        entry_qty: float,
        current_price: float,
        entry_fee: float = None,
        symbol: str = "UNKNOWN"
    ) -> str:
        """
        Echo the kill validation status for the sniper.
        
        This is the "ARE WE STILL GOOD?" check.
        """
        validation = self.validate_kill(entry_price, entry_qty, current_price, entry_fee)
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        if validation.is_valid:
            return f"""
🇮🇪🎯 [{timestamp}] {symbol} - KILL AUTHORIZED 🎯🇮🇪
   ✅ Current: {current_price:.6f} >= Target: {validation.target_price:.6f}
   ✅ Net P&L: ${validation.net_pnl:+.4f} >= ${self.min_net_profit:.2f}
   >>> EXECUTE THE KILL <<<
"""
        else:
            eta_str = f"ETA: {validation.eta_seconds:.0f}s" if validation.eta_seconds and validation.eta_seconds < float('inf') else "ETA: Unknown"
            return f"""
⏳ [{timestamp}] {symbol} - HOLD POSITION ⏳
   ❌ Current: {current_price:.6f} | Target: {validation.target_price:.6f}
   ❌ Gap: {validation.price_gap_pct:+.3f}% | Need: +${abs(validation.price_gap * entry_qty):.4f}
   ❌ Net if exit now: ${validation.net_pnl:+.4f} (LOSS)
   ⏱️ {eta_str}
   >>> WAIT FOR TARGET <<<
"""


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def validate_kill_shot(
    entry_price: float,
    entry_qty: float,
    current_price: float,
    entry_fee: float = None,
    fee_rate: float = 0.001
) -> KillValidation:
    """Quick validation check."""
    validator = SniperKillValidator(fee_rate=fee_rate)
    return validator.validate_kill(entry_price, entry_qty, current_price, entry_fee)


def get_target_price(
    entry_price: float,
    entry_qty: float,
    fee_rate: float = 0.001,
    min_profit: float = 0.01
) -> float:
    """Get the target price for a kill."""
    validator = SniperKillValidator(fee_rate=fee_rate, min_net=min_profit)
    target, _ = validator.calculate_target_price(entry_price, entry_qty)
    return target


# =============================================================================
# MAIN - DEMO WITH CURRENT CHZ TRADE
# =============================================================================

if __name__ == "__main__":
    print("🇮🇪🎯 SNIPER KILL VALIDATOR - DOUBLE-CHECK DEMO 🎯🇮🇪")
    print("=" * 60)
    
    # Current CHZ position (from the live check)
    ENTRY_PRICE = 0.04481
    ENTRY_QTY = 535.0
    CURRENT_PRICE = 0.04488  # From last check
    ENTRY_FEE = 0.50825  # CHZ fee paid (need to convert to USDC value)
    
    # Since fee was paid in CHZ, convert to USDC value
    entry_fee_usdc = ENTRY_FEE * ENTRY_PRICE
    
    # Create validator with Binance fee rate
    validator = SniperKillValidator(fee_rate=0.001)  # 0.1% Binance fee
    
    # Calculate target
    target_price, breakdown = validator.calculate_target_price(ENTRY_PRICE, ENTRY_QTY, entry_fee_usdc)
    
    print(f"\n📊 KILL TARGET CALCULATION:")
    print(f"   Entry:          {ENTRY_PRICE:.6f} x {ENTRY_QTY:.0f} = ${breakdown['entry_cost']:.4f}")
    print(f"   Entry Fee:      ${breakdown['entry_fee']:.4f}")
    print(f"   Cost Basis:     ${breakdown['total_cost_basis']:.4f}")
    print(f"   Min Net Profit: ${breakdown['min_net_profit']:.2f}")
    print(f"   ────────────────────────────────────────")
    print(f"   🎯 TARGET PRICE: {target_price:.6f}")
    print(f"   🎯 PRICE MOVE:   +{breakdown['price_increase_pct']:.3f}%")
    
    # Validate current situation
    validation = validator.validate_kill(ENTRY_PRICE, ENTRY_QTY, CURRENT_PRICE, entry_fee_usdc)
    print(validation)
    
    # Echo status
    print("\n📡 SNIPER ECHO CHECK:")
    print(validator.echo_status(ENTRY_PRICE, ENTRY_QTY, CURRENT_PRICE, entry_fee_usdc, "CHZUSDC"))
    
    # What if price was higher?
    print("\n🔮 SIMULATION - What if price hits target?")
    simulated_price = target_price + 0.0001
    sim_validation = validator.validate_kill(ENTRY_PRICE, ENTRY_QTY, simulated_price, entry_fee_usdc)
    print(validator.echo_status(ENTRY_PRICE, ENTRY_QTY, simulated_price, entry_fee_usdc, "CHZUSDC"))
