#!/usr/bin/env python3
"""
🇬🇧 BINANCE UK ALLOWED PAIRS GENERATOR
=====================================

Fetches and saves the list of trading pairs allowed for UK Binance accounts.
This is based on the account's TRD_GRP_ permissions (Trade Groups).

Run this script to regenerate: binance_uk_allowed_pairs.json

Usage:
    python binance_uk_allowed_pairs.py
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import json
import time
from typing import Set, Dict, List, Any

# UK Restricted tokens that are banned regardless of Trade Groups
UK_RESTRICTED_TOKENS = {
    # Derivatives/Leveraged tokens (banned for UK retail)
    "BTCDOWN", "BTCUP", "ETHDOWN", "ETHUP", "BNBDOWN", "BNBUP",
    "XRPDOWN", "XRPUP", "DOTDOWN", "DOTUP", "EOSDOWN", "EOSUP",
    "TRXDOWN", "TRXUP", "LINKDOWN", "LINKUP", "ADAUP", "ADADOWN",
    "SXPDOWN", "SXPUP", "UNIDOWN", "UNIUP", "FILDOWN", "FILUP",
    "AAVEDOWN", "AAVEUP", "SUSHIDOWN", "SUSHIUP", "1INCHDOWN", "1INCHUP",
    # Stock tokens (delisted for UK)
    "TSLA", "COIN", "AAPL", "MSFT", "GOOGL", "AMZN", "MSTR",
    # Deprecated stablecoins
    "BUSD",
}


def fetch_uk_allowed_pairs() -> Dict[str, Any]:
    """Fetch all allowed pairs for UK Binance accounts."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except:
        pass
    
    try:
        from aureon.exchanges.binance_client import BinanceClient, get_binance_client
        client = get_binance_client()
    except Exception as e:
        print(f"❌ Failed to create Binance client: {e}")
        return {"error": str(e)}
    
    result = {
        "timestamp": time.time(),
        "timestamp_readable": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "uk_mode": client.uk_mode,
        "trade_groups": [],
        "allowed_pairs": [],
        "allowed_base_assets": set(),
        "allowed_quote_assets": set(),
        "pairs_by_quote": {},
        "total_pairs": 0,
        "restricted_tokens": list(UK_RESTRICTED_TOKENS),
    }
    
    if not client.uk_mode:
        print("⚠️  UK mode is disabled - all pairs allowed")
        result["note"] = "UK mode disabled - no restrictions applied"
        return result
    
    print("🇬🇧 Fetching UK allowed pairs...")
    
    try:
        # Get account info for trade groups
        account = client.account()
        permissions = account.get('permissions', [])
        trade_groups = {p for p in permissions if p.startswith('TRD_GRP_')}
        result["trade_groups"] = sorted(list(trade_groups))
        
        print(f"   Account Type: {account.get('accountType', 'Unknown')}")
        print(f"   Can Trade: {account.get('canTrade')}")
        print(f"   Trade Groups: {', '.join(sorted(trade_groups)) if trade_groups else 'NONE'}")
        
        if not trade_groups:
            print("❌ No TRD_GRP permissions found - trading may be disabled")
            result["error"] = "No trade group permissions"
            return result
        
        # Get exchange info
        info = client.exchange_info()
        symbols = info.get('symbols', [])
        print(f"   Total exchange symbols: {len(symbols)}")
        
        allowed_pairs = []
        allowed_base = set()
        allowed_quote = set()
        pairs_by_quote: Dict[str, List[str]] = {}
        
        for sym in symbols:
            if sym.get('status') != 'TRADING':
                continue
            if not sym.get('isSpotTradingAllowed', False):
                continue
            
            symbol_name = sym.get('symbol', '')
            base_asset = sym.get('baseAsset', '')
            quote_asset = sym.get('quoteAsset', '')
            
            # Check restricted tokens
            is_restricted = False
            for token in UK_RESTRICTED_TOKENS:
                if token in symbol_name.upper():
                    is_restricted = True
                    break
            
            if is_restricted:
                continue
            
            # Check trade groups match
            permission_sets = sym.get('permissionSets') or []
            matched = False
            for perm_set in permission_sets:
                perm_groups = {p for p in perm_set if p.startswith('TRD_GRP_')}
                if trade_groups.intersection(perm_groups):
                    matched = True
                    break
            
            if matched:
                allowed_pairs.append(symbol_name)
                allowed_base.add(base_asset)
                allowed_quote.add(quote_asset)
                
                if quote_asset not in pairs_by_quote:
                    pairs_by_quote[quote_asset] = []
                pairs_by_quote[quote_asset].append(symbol_name)
        
        result["allowed_pairs"] = sorted(allowed_pairs)
        result["allowed_base_assets"] = sorted(list(allowed_base))
        result["allowed_quote_assets"] = sorted(list(allowed_quote))
        result["pairs_by_quote"] = {k: sorted(v) for k, v in pairs_by_quote.items()}
        result["total_pairs"] = len(allowed_pairs)
        
        print(f"\n✅ Found {len(allowed_pairs)} allowed pairs for UK account")
        print(f"   Base assets: {len(allowed_base)}")
        print(f"   Quote assets: {len(allowed_quote)}")
        
        # Show breakdown by quote
        print("\n   Pairs by quote currency:")
        for quote in ['USDT', 'BTC', 'ETH', 'BNB', 'EUR', 'GBP', 'USDC']:
            count = len(pairs_by_quote.get(quote, []))
            if count > 0:
                print(f"      {quote}: {count} pairs")
        
    except Exception as e:
        print(f"❌ Error fetching pairs: {e}")
        import traceback
        traceback.print_exc()
        result["error"] = str(e)
    
    return result


def save_allowed_pairs(data: Dict[str, Any], filename: str = "binance_uk_allowed_pairs.json"):
    """Save the allowed pairs to a JSON file."""
    # Convert sets to lists for JSON serialization
    data_serializable = {}
    for key, value in data.items():
        if isinstance(value, set):
            data_serializable[key] = sorted(list(value))
        else:
            data_serializable[key] = value
    
    with open(filename, 'w') as f:
        json.dump(data_serializable, f, indent=2)
    
    print(f"\n💾 Saved to {filename}")


def load_allowed_pairs(filename: str = "binance_uk_allowed_pairs.json") -> Dict[str, Any]:
    """Load allowed pairs from JSON file."""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return {}


def is_pair_allowed_uk(pair: str, allowed_data: Dict[str, Any] = None) -> bool:
    """Check if a trading pair is allowed for UK accounts.
    
    Args:
        pair: Trading pair symbol (e.g., 'BTCUSDT')
        allowed_data: Pre-loaded allowed pairs data, or None to load from file
    
    Returns:
        True if pair is allowed, False otherwise
    """
    if allowed_data is None:
        allowed_data = load_allowed_pairs()
    
    if not allowed_data:
        return True  # No restriction data, assume allowed
    
    if allowed_data.get("uk_mode") == False:
        return True  # UK mode disabled
    
    allowed_pairs = set(allowed_data.get("allowed_pairs", []))
    return pair.upper() in allowed_pairs


def get_allowed_base_assets(allowed_data: Dict[str, Any] = None) -> Set[str]:
    """Get set of base assets that can be traded."""
    if allowed_data is None:
        allowed_data = load_allowed_pairs()
    return set(allowed_data.get("allowed_base_assets", []))


def get_allowed_quote_assets(allowed_data: Dict[str, Any] = None) -> Set[str]:
    """Get set of quote assets available."""
    if allowed_data is None:
        allowed_data = load_allowed_pairs()
    return set(allowed_data.get("allowed_quote_assets", []))


if __name__ == "__main__":
    print("=" * 60)
    print("🇬🇧 BINANCE UK ALLOWED PAIRS GENERATOR")
    print("=" * 60)
    
    data = fetch_uk_allowed_pairs()
    
    if "error" not in data:
        save_allowed_pairs(data)
        
        # Show some sample pairs
        print("\n📋 Sample allowed pairs:")
        for quote in ['USDT', 'BTC', 'EUR', 'GBP']:
            pairs = data.get("pairs_by_quote", {}).get(quote, [])[:5]
            if pairs:
                print(f"   {quote}: {', '.join(pairs)}")
    else:
        print(f"\n❌ Failed to fetch pairs: {data.get('error')}")
    
    print("\n" + "=" * 60)
