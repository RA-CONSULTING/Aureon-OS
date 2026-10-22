#!/usr/bin/env python3
"""
🔍 BINANCE API DIAGNOSTICS
═══════════════════════════════════════════════════════════════════════════════
Comprehensive diagnostic to verify Binance API is ready for real trading.

Tests:
  1. Environment variables are set correctly
  2. Public API (no auth required) - ticker prices
  3. Private API (requires valid keys) - account balance
  4. UK mode restrictions

Gary Leckey | Aureon Trading | January 2026
═══════════════════════════════════════════════════════════════════════════════
"""

try:
    from aureon.core.aureon_baton_link import link_system as _baton_link
    _baton_link(__name__)
except Exception:
    pass
import sys
import os

# Windows UTF-8 fix (MANDATORY)
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            return (isinstance(stream, io.TextIOWrapper) and
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        if hasattr(sys.stdout, 'buffer') and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        if hasattr(sys.stderr, 'buffer') and not _is_utf8_wrapper(sys.stderr):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

from dotenv import load_dotenv
load_dotenv()

def main():
    print()
    print("=" * 60)
    print("🔍 BINANCE API DIAGNOSTICS")
    print("=" * 60)
    
    # 1. Check environment variables
    print("\n📋 Environment Variables:")
    api_key = os.getenv("BINANCE_API_KEY", "")
    api_secret = os.getenv("BINANCE_API_SECRET", "")
    use_testnet = os.getenv("BINANCE_USE_TESTNET", "false")
    dry_run = os.getenv("BINANCE_DRY_RUN", "false")
    uk_mode = os.getenv("BINANCE_UK_MODE", "true")
    
    print(f"  BINANCE_API_KEY: {'SET' if api_key else 'NOT SET'}")
    print(f"  BINANCE_API_SECRET: {'SET' if api_secret else 'NOT SET'}")
    print(f"  BINANCE_USE_TESTNET: {use_testnet}")
    print(f"  BINANCE_DRY_RUN: {dry_run}")
    print(f"  BINANCE_UK_MODE: {uk_mode}")
    
    if not api_key or not api_secret:
        print("\n❌ ERROR: Binance API keys not set in .env file!")
        print("   Add the following to your .env file:")
        print("   BINANCE_API_KEY=your_api_key")
        print("   BINANCE_API_SECRET=your_api_secret")
        return
    
    # 2. Test client initialization
    print("\n🔗 Client Configuration:")
    try:
        from aureon.exchanges.binance_client import BinanceClient, get_binance_client
        client = get_binance_client()
        if client is None:
            print("  ❌ Client initialization failed: client unavailable")
            return
        print(f"  Dry Run: {client.dry_run}")
        print(f"  Testnet: {client.use_testnet}")
        print(f"  UK Mode: {client.uk_mode}")
        print(f"  API Key Set: {bool(client.api_key)}")
        print(f"  API Secret Set: {bool(client.api_secret)}")
        print(f"  Base URL: {client.base}")
        diag = client.diagnose_ready()
        print(f"  Network OK: {diag['network_ok']}")
        print(f"  Account OK: {diag['account_ok']}")
        print(f"  Margin Available: {diag['margin_available']}")
        if diag["init_error"]:
            print(f"  Init Error: {diag['init_error']}")
        if diag["last_error"]:
            print(f"  Last Error: {diag['last_error']}")
    except Exception as e:
        print(f"  ❌ Client initialization failed: {e}")
        return
    
    # 3. Test public API (no auth required)
    print("\n🌐 Testing Public API (no auth required):")
    try:
        import requests
        base = "https://api.binance.com"
        
        # Get BTC price
        r = requests.get(f"{base}/api/v3/ticker/price", params={"symbol": "BTCUSDT"}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            price = float(data.get('price', 0))
            print(f"  ✅ BTCUSDT Price: ${price:,.2f}")
        else:
            print(f"  ⚠️ Ticker request failed: {r.status_code}")
            
        # Get ETH price
        r = requests.get(f"{base}/api/v3/ticker/price", params={"symbol": "ETHUSDT"}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            price = float(data.get('price', 0))
            print(f"  ✅ ETHUSDT Price: ${price:,.2f}")
        else:
            print(f"  ⚠️ ETH ticker failed: {r.status_code}")
            
    except Exception as e:
        print(f"  ❌ Public API test failed: {e}")
    
    # 4. Test private API (requires valid keys)
    print("\n🔐 Testing Private API (requires valid keys):")
    try:
        # Binance uses account() method which returns balances in 'balances' array
        account_info = client.account()
        balances = account_info.get('balances', [])
        
        if account_info:
            print(f"  ✅ Account retrieved successfully!")
            total_btc = 0
            total_usdt = 0
            
            # Show non-zero balances (free + locked)
            non_zero = []
            for bal in balances:
                asset = bal.get('asset', '')
                free = float(bal.get('free', 0))
                locked = float(bal.get('locked', 0))
                total = free + locked
                if total > 0:
                    non_zero.append((asset, free, locked, total))
            
            if non_zero:
                for asset, free, locked, total in sorted(non_zero, key=lambda x: -x[3]):
                    lock_str = f" (locked: {locked:.8f})" if locked > 0 else ""
                    print(f"  💰 {asset}: {free:.8f}{lock_str}")
                    if asset == "BTC":
                        total_btc = total
                    elif asset in ["USDT", "USDC", "BUSD", "FDUSD"]:
                        total_usdt += total
                        
                # Estimate total value
                try:
                    r = requests.get(f"{base}/api/v3/ticker/price", params={"symbol": "BTCUSDT"}, timeout=5)
                    if r.status_code == 200:
                        btc_price = float(r.json().get('price', 0))
                        btc_value = total_btc * btc_price
                        total_value = btc_value + total_usdt
                        print(f"\n  💵 Estimated Total USD Value: ${total_value:,.2f}")
                except:
                    pass
            else:
                print("  ⚠️ No non-zero balances found")
                print("  This could mean:")
                print("    1. Account has no funds")
                print("    2. API key doesn't have 'read' permission")
                print("    3. Using testnet keys on mainnet or vice versa")
        else:
            print("  ⚠️ Empty account returned")
            
    except Exception as e:
        print(f"  ❌ Private API test failed: {e}")
        error_str = str(e).lower()
        if "signature" in error_str or "timestamp" in error_str:
            print("\n  💡 Signature/Timestamp error - possible causes:")
            print("     1. System clock is not synced (Windows clock drift)")
            print("     2. API key/secret mismatch")
            print("     3. Using testnet keys on mainnet")
        elif "invalid api" in error_str or "api-key" in error_str:
            print("\n  💡 Invalid API key error - check:")
            print("     1. API keys are correct and not expired")
            print("     2. IP whitelist if enabled on Binance")
        elif "permission" in error_str:
            print("\n  💡 Permission error - ensure API key has:")
            print("     1. 'Enable Reading' permission")
            print("     2. 'Enable Spot & Margin Trading' for trading")
    
    # 5. Check UK restrictions
    if uk_mode.lower() == "true":
        print("\n🇬🇧 UK Mode Restrictions:")
        print("  ℹ️ UK Mode is ENABLED - the following are restricted:")
        print("     - Leveraged tokens (BTCUP, BTCDOWN, etc.)")
        print("     - Margin trading")
        print("     - Futures/Derivatives")
        print("     - Some delisted tokens (BUSD)")
        print("  ✅ Spot trading on allowed pairs is available")
    
    # 6. Final recommendations
    print("\n📝 RECOMMENDATIONS:")
    
    issues = []
    
    if not api_key or not api_secret:
        issues.append("Set BINANCE_API_KEY and BINANCE_API_SECRET in .env")
    
    if dry_run.lower() == "true":
        issues.append("Set BINANCE_DRY_RUN=false for real trading")
    
    if use_testnet.lower() == "true":
        issues.append("Set BINANCE_USE_TESTNET=false for real trading")
    
    if issues:
        for issue in issues:
            print(f"  ⚠️ {issue}")
    else:
        try:
            if account_info and any(float(b.get('free', 0)) + float(b.get('locked', 0)) > 0 for b in balances):
                print("  ✅ Binance is ready for real trading!")
            else:
                print("  ⚠️ Binance connected but no funds available")
                print("     Deposit funds or check API permissions")
        except:
            print("  ⚠️ Could not verify trading readiness")
    
    print()

if __name__ == "__main__":
    main()
