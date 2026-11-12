#!/usr/bin/env python3
"""
🧹 DUST CONVERTER - Sweep Small Holdings to Stablecoins
════════════════════════════════════════════════════════════════════════════
Converts any asset worth less than £1 (~$1.27) to stablecoins, but ONLY if:
1. The sale covers trading fees (net profitable)
2. The exchange supports the conversion pair
3. We're above minimum order size for the exchange
════════════════════════════════════════════════════════════════════════════
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Any


@dataclass
class DustCandidate:
    """A small balance candidate for dust conversion."""
    asset: str
    exchange: str
    amount: float
    value_usd: float
    value_gbp: float
    sell_fee_usd: float
    net_proceeds_usd: float
    target_stable: str  # Where to convert (USD, USDC, ZUSD)
    is_profitable: bool  # True if net_proceeds > 0


class DustConverter:
    """
    🧹 DUST CONVERTER - Smart Portfolio Cleanup
    
    "Don't let pennies become lost pennies. Sweep them up!"
    
    Purpose:
    - Find all assets worth less than £1 (~$1.27 USD)
    - Convert them to stablecoins IF profitable after fees
    - Work across all exchanges (Kraken, Binance, Alpaca)
    
    Each exchange has different:
    - Minimum order sizes
    - Fee structures  
    - Available stablecoins (USD, USDC, ZUSD, etc.)
    """
    
    # £1 threshold in USD (approximate, updates with forex)
    GBP_THRESHOLD = 1.00  # £1
    USD_TO_GBP = 0.79  # $1 = £0.79 roughly
    DUST_THRESHOLD_USD = GBP_THRESHOLD / USD_TO_GBP  # ~$1.27
    
    # Exchange-specific configurations
    EXCHANGE_CONFIG = {
        'kraken': {
            'min_order_usd': 1.50,  # Kraken minimum ~$1.50
            'fee_pct': 0.0026,      # 0.26% taker fee
            'target_stable': 'ZUSD',  # Kraken's USD equivalent
            'alt_stables': ['USDC', 'USDT'],
        },
        'binance': {
            'min_order_usd': 5.00,  # Binance minimum ~$5
            'fee_pct': 0.0010,      # 0.10% with BNB
            'target_stable': 'USDC',  # Binance UK prefers USDC
            'alt_stables': ['USDT', 'FDUSD'],
        },
        'alpaca': {
            'min_order_usd': 1.00,  # Alpaca minimum ~$1
            'fee_pct': 0.0015,      # 0.15% crypto fee
            'target_stable': 'USD',  # Alpaca native USD
            'alt_stables': ['USDC'],
        },
    }
    
    # Assets we should NEVER sell (even if dust)
    PROTECTED_ASSETS = {
        'USD', 'USDC', 'USDT', 'ZUSD', 'TUSD', 'DAI', 'FDUSD',  # Stablecoins
        'GBP', 'EUR',  # Fiat
    }
    
    def __init__(self):
        self.dust_swept = 0
        self.total_swept_usd = 0.0
        self.failed_sweeps = 0
        self.last_sweep_time = 0.0
        self.sweep_history: List[Dict] = []
        
        # Cooldown between sweeps (avoid spam)
        self.SWEEP_COOLDOWN_SECONDS = 300  # 5 minutes
    
    def find_dust_candidates(
        self,
        exchange: str,
        balances: Dict[str, float],
        prices: Dict[str, float],
    ) -> List[DustCandidate]:
        """
        Find all dust positions on an exchange.
        
        Returns list of DustCandidate objects sorted by profitability.
        """
        candidates = []
        config = self.EXCHANGE_CONFIG.get(exchange, self.EXCHANGE_CONFIG['alpaca'])
        
        for asset, amount in balances.items():
            # Skip protected assets (stablecoins, fiat)
            if asset.upper() in self.PROTECTED_ASSETS:
                continue
            
            # Skip zero balances
            if amount <= 0:
                continue
            
            # Get price
            price = prices.get(asset, prices.get(asset.upper(), 0))
            if price <= 0:
                continue
            
            # Calculate value
            value_usd = amount * price
            value_gbp = value_usd * self.USD_TO_GBP
            
            # Only consider dust (< £1)
            if value_gbp >= self.GBP_THRESHOLD:
                continue
            
            # Check minimum order size
            if value_usd < config['min_order_usd']:
                # Too small even for dust sweep
                continue
            
            # Calculate fees
            fee_pct = config['fee_pct']
            sell_fee_usd = value_usd * fee_pct
            
            # Net proceeds
            net_proceeds_usd = value_usd - sell_fee_usd
            
            # Is it profitable? (Must recover something after fees)
            is_profitable = net_proceeds_usd > 0.001  # At least $0.001 net
            
            candidates.append(DustCandidate(
                asset=asset,
                exchange=exchange,
                amount=amount,
                value_usd=value_usd,
                value_gbp=value_gbp,
                sell_fee_usd=sell_fee_usd,
                net_proceeds_usd=net_proceeds_usd,
                target_stable=config['target_stable'],
                is_profitable=is_profitable,
            ))
        
        # Sort by profitability (highest net proceeds first)
        candidates.sort(key=lambda x: x.net_proceeds_usd, reverse=True)
        
        return candidates
    
    def find_all_dust(
        self,
        all_balances: Dict[str, Dict[str, float]],  # exchange -> asset -> amount
        prices: Dict[str, float],
    ) -> Dict[str, List[DustCandidate]]:
        """
        Find dust across ALL exchanges.
        
        Returns: {exchange: [DustCandidate, ...]}
        """
        all_dust = {}
        
        for exchange in ['kraken', 'binance', 'alpaca']:
            balances = all_balances.get(exchange, {})
            if balances:
                candidates = self.find_dust_candidates(exchange, balances, prices)
                if candidates:
                    all_dust[exchange] = candidates
        
        return all_dust
    
    def get_profitable_sweeps(
        self,
        all_dust: Dict[str, List[DustCandidate]],
    ) -> List[DustCandidate]:
        """
        Filter to only profitable dust sweeps.
        
        Returns flat list of all profitable dust candidates.
        """
        profitable = []
        
        for exchange, candidates in all_dust.items():
            for candidate in candidates:
                if candidate.is_profitable:
                    profitable.append(candidate)
        
        return profitable
    
    def format_dust_report(
        self,
        all_dust: Dict[str, List[DustCandidate]],
    ) -> str:
        """Generate a formatted report of all dust positions."""
        lines = [
            "",
            "   ╔══════════════════════════════════════════════════════════════╗",
            "   ║          🧹 DUST CONVERTER - PORTFOLIO CLEANUP               ║",
            "   ╠══════════════════════════════════════════════════════════════╣",
        ]
        
        total_dust_usd = 0.0
        total_recoverable = 0.0
        total_fees = 0.0
        
        for exchange, candidates in all_dust.items():
            if not candidates:
                continue
            
            exchange_icon = {'kraken': '🐙', 'binance': '🔶', 'alpaca': '🦙'}.get(exchange, '📊')
            lines.append(f"   ║  {exchange_icon} {exchange.upper():10}                                       ║")
            lines.append(f"   ║  ─────────────────────────────────────────────────────────  ║")
            
            for c in candidates[:5]:  # Show top 5 per exchange
                status = "✅" if c.is_profitable else "❌"
                lines.append(
                    f"   ║  {status} {c.asset:6} £{c.value_gbp:.4f} → {c.target_stable} "
                    f"(net ${c.net_proceeds_usd:.4f})        ║"
                )
                total_dust_usd += c.value_usd
                if c.is_profitable:
                    total_recoverable += c.net_proceeds_usd
                total_fees += c.sell_fee_usd
            
            if len(candidates) > 5:
                lines.append(f"   ║  ... and {len(candidates) - 5} more dust positions            ║")
        
        if not any(all_dust.values()):
            lines.append("   ║  ✨ No dust positions found - portfolio is clean!            ║")
        
        lines.extend([
            "   ╠══════════════════════════════════════════════════════════════╣",
            f"   ║  📊 TOTAL DUST VALUE:    ${total_dust_usd:.4f}                        ║",
            f"   ║  📉 ESTIMATED FEES:      ${total_fees:.4f}                        ║",
            f"   ║  💰 RECOVERABLE (NET):   ${total_recoverable:.4f}                        ║",
            "   ╚══════════════════════════════════════════════════════════════╝",
        ])
        
        return "\n".join(lines)
    
    def should_sweep_now(self) -> bool:
        """Check if enough time has passed since last sweep."""
        return time.time() - self.last_sweep_time >= self.SWEEP_COOLDOWN_SECONDS
    
    def record_sweep(self, candidate: DustCandidate, success: bool):
        """Record a sweep attempt."""
        self.last_sweep_time = time.time()
        
        if success:
            self.dust_swept += 1
            self.total_swept_usd += candidate.net_proceeds_usd
            self.sweep_history.append({
                'timestamp': time.time(),
                'asset': candidate.asset,
                'exchange': candidate.exchange,
                'amount': candidate.amount,
                'value_usd': candidate.value_usd,
                'net_proceeds': candidate.net_proceeds_usd,
                'target': candidate.target_stable,
                'success': True,
            })
        else:
            self.failed_sweeps += 1
            self.sweep_history.append({
                'timestamp': time.time(),
                'asset': candidate.asset,
                'exchange': candidate.exchange,
                'success': False,
            })
    
    def get_status(self) -> Dict:
        """Get converter status for monitoring."""
        return {
            'dust_swept': self.dust_swept,
            'total_swept_usd': self.total_swept_usd,
            'failed_sweeps': self.failed_sweeps,
            'last_sweep': self.last_sweep_time,
            'cooldown_remaining': max(0, self.SWEEP_COOLDOWN_SECONDS - (time.time() - self.last_sweep_time)),
        }


# ════════════════════════════════════════════════════════════════════════════
# 🧪 QUICK TEST
# ════════════════════════════════════════════════════════════════════════════

_dust_converter_instance: Optional["DustConverter"] = None


def get_dust_converter() -> "DustConverter":
    """Shared DustConverter instance.

    The converter only finds and reports dust candidates; it never places
    orders. Any sweep is executed (and governed) by its caller.
    """
    global _dust_converter_instance
    if _dust_converter_instance is None:
        _dust_converter_instance = DustConverter()
    return _dust_converter_instance


if __name__ == "__main__":
    # Test the dust converter with sample data
    converter = DustConverter()
    
    # Sample balances (simulating small holdings closer to threshold)
    test_balances = {
        'kraken': {
            'ETH': 0.0004,     # ~$1.20 @ $3000
            'SOL': 0.008,      # ~$1.28 @ $160 
            'DOGE': 8.0,       # ~$1.20 @ $0.15
            'XRP': 2.0,        # ~$1.20 @ $0.60
            'ZUSD': 25.0,      # Protected - won't sweep
        },
        'binance': {
            # Binance has $5 min - harder to hit dust threshold
            'PEPE': 625000,    # ~$5.00 @ $0.000008 (at min, but above £1)
            'USDC': 10.0,      # Protected
        },
        'alpaca': {
            'ETH': 0.0004,     # ~$1.20 @ $3000
            'SOL': 0.007,      # ~$1.12 @ $160
            'USD': 16.03,      # Protected
        },
    }
    
    # Sample prices
    test_prices = {
        'ETH': 3000.0,
        'BTC': 100000.0,
        'SOL': 160.0,
        'DOGE': 0.15,
        'XRP': 0.60,
        'PEPE': 0.000008,
        'SHIB': 0.000012,
    }
    
    print("🧹 DUST CONVERTER TEST")
    print("=" * 60)
    
    # Find all dust
    all_dust = converter.find_all_dust(test_balances, test_prices)
    
    # Print report
    print(converter.format_dust_report(all_dust))
    
    # Get profitable sweeps
    profitable = converter.get_profitable_sweeps(all_dust)
    
    print(f"\n✅ Found {len(profitable)} profitable dust sweeps")
    for p in profitable:
        print(f"   - {p.exchange}: {p.asset} £{p.value_gbp:.4f} → {p.target_stable} (net ${p.net_proceeds_usd:.4f})")
