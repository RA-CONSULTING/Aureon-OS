#!/usr/bin/env python3
"""
🏆 GET FIRST WINNER - ONE WIN TO SAVE THE PLANET 🌍
===================================================

This script finds and executes the BEST opportunity for a winning trade.
Once we get ONE winner, the system gains momentum to get ALL winners!

"The first domino falls, and the rest follow." - Aureon
"""

import sys

import json
import time
import math
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

# Sacred constants
PHI = (1 + math.sqrt(5)) / 2  # 1.618 Golden ratio
QUOTE_MAX_AGE_SECONDS = 120.0
FILL_MAX_AGE_SECONDS = 300.0

@dataclass
class WinningOpportunity:
    symbol: str
    exchange: str
    current_price: float
    momentum: float  # % change
    score: float
    reason: str
    source_id: str
    source_timestamp: float
    data_status: str = "live"
    generated_values: bool = False
    eligible_for_action: bool = True


def _finite_number(
    value: Any,
    *,
    positive: bool = False,
    nonnegative: bool = False,
) -> Optional[float]:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    if positive and parsed <= 0:
        return None
    if nonnegative and parsed < 0:
        return None
    return parsed


def _fresh_provider_timestamp(
    value: Any,
    *,
    max_age_seconds: float,
) -> Optional[float]:
    parsed = _finite_number(value, positive=True)
    if parsed is None:
        return None
    if parsed > 10_000_000_000:
        parsed /= 1000.0
    now = time.time()
    if parsed > now + 5.0 or now - parsed > max_age_seconds:
        return None
    return parsed

def load_kraken_client():
    """Load Kraken client for live trading"""
    try:
        from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
        client = get_kraken_client()
        return client
    except Exception as e:
        print(f"⚠️ Could not load Kraken client: {e}")
        return None

def get_live_opportunities(client) -> List[WinningOpportunity]:
    """Get live opportunities from exchange"""
    opportunities = []
    
    if not client:
        return opportunities
        
    try:
        # Get ticker data using correct method
        tickers = client.get_24h_tickers()
        if not isinstance(tickers, list):
            return opportunities
        
        # Find best momentum opportunities
        for ticker in tickers:
            if not isinstance(ticker, dict) or ticker.get("generated_values") is not False:
                continue
            symbol = str(ticker.get('symbol') or '').upper()
            if not symbol or not symbol.endswith(('USD', 'USDC', 'USDT', 'TUSD')):
                continue
            source_id = str(ticker.get("source_id") or "")
            source_timestamp = _fresh_provider_timestamp(
                ticker.get("source_timestamp"),
                max_age_seconds=QUOTE_MAX_AGE_SECONDS,
            )
            last = _finite_number(ticker.get('lastPrice'), positive=True)
            momentum = _finite_number(ticker.get('priceChangePercent'))
            volume = _finite_number(ticker.get('quoteVolume'), nonnegative=True)
            if (
                not source_id
                or source_timestamp is None
                or last is None
                or momentum is None
                or volume is None
            ):
                continue
            if momentum > 0.5:  # Any positive observed momentum
                score = abs(momentum) * (1 + math.log(1 + volume / 100000))
                opportunities.append(WinningOpportunity(
                    symbol=symbol,
                    exchange='kraken',
                    current_price=last,
                    momentum=momentum,
                    score=score,
                    reason=f"+{momentum:.1f}% momentum, riding the wave",
                    source_id=source_id,
                    source_timestamp=source_timestamp,
                ))
                
    except Exception as e:
        print(f"⚠️ Error getting opportunities: {e}")
        import traceback
        traceback.print_exc()
        
    # Sort by score
    opportunities.sort(key=lambda x: x.score, reverse=True)
    return opportunities[:20]

def check_balances(client) -> Dict[str, Any]:
    """Return a complete synchronous authenticated balance receipt."""
    if not client:
        return {
            "status": "NO_DATA",
            "data_status": "no_data",
            "reason": "kraken_client_unavailable",
            "balances": None,
            "generated_values": False,
            "eligible_for_action": False,
        }
        
    try:
        raw_balance = client.get_account_balance()
    except Exception as e:
        print(f"⚠️ Error getting balance: {e}")
        return {
            "status": "NO_DATA",
            "data_status": "no_data",
            "reason": f"kraken_balance_receipt_failed:{type(e).__name__}",
            "balances": None,
            "generated_values": False,
            "eligible_for_action": False,
        }
    received_at = time.time()
    if not isinstance(raw_balance, dict) or not raw_balance:
        return {
            "status": "NO_DATA",
            "data_status": "no_data",
            "reason": "kraken_balance_receipt_unavailable",
            "balances": None,
            "generated_values": False,
            "eligible_for_action": False,
        }
    balances: Dict[str, float] = {}
    for asset, value in raw_balance.items():
        asset_name = str(asset or "").upper()
        parsed = _finite_number(value, nonnegative=True)
        if not asset_name or parsed is None:
            return {
                "status": "NO_DATA",
                "data_status": "no_data",
                "reason": "kraken_balance_receipt_malformed",
                "balances": None,
                "generated_values": False,
                "eligible_for_action": False,
            }
        balances[asset_name] = parsed
    return {
        "status": "LIVE",
        "data_status": "live",
        "truth_status": "real_provider",
        "source_id": "kraken:authenticated_account_balance",
        "source_timestamp": None,
        "received_at": received_at,
        "timestamp_policy": "synchronous_provider_receipt_clock_not_source_time",
        "balances": balances,
        "generated_values": False,
        "eligible_for_action": True,
    }


def _opportunity_is_actionable(opportunity: WinningOpportunity) -> bool:
    if (
        opportunity.data_status != "live"
        or opportunity.generated_values is not False
        or opportunity.eligible_for_action is not True
        or _finite_number(opportunity.current_price, positive=True) is None
    ):
        return False
    return _fresh_provider_timestamp(
        opportunity.source_timestamp,
        max_age_seconds=QUOTE_MAX_AGE_SECONDS,
    ) is not None


def _quote_asset(symbol: str) -> Optional[str]:
    for quote in ("USDT", "USDC", "TUSD", "USD"):
        if symbol.endswith(quote) and len(symbol) > len(quote):
            return quote
    return None


def _quote_balance(
    opportunity: WinningOpportunity,
    balance_receipt: Dict[str, Any],
) -> Optional[tuple[str, float]]:
    if (
        balance_receipt.get("data_status") != "live"
        or balance_receipt.get("eligible_for_action") is not True
        or balance_receipt.get("generated_values") is not False
        or not isinstance(balance_receipt.get("balances"), dict)
    ):
        return None
    quote = _quote_asset(opportunity.symbol)
    if quote is None:
        return None
    balances = balance_receipt["balances"]
    candidate_assets = ("USD", "ZUSD") if quote == "USD" else (quote,)
    observed = [
        (asset, _finite_number(balances[asset], nonnegative=True))
        for asset in candidate_assets
        if asset in balances
    ]
    observed = [(asset, value) for asset, value in observed if value is not None]
    if len(observed) != 1:
        return None
    asset, value = observed[0]
    return asset, value

def find_best_winner(
    opportunities: List[WinningOpportunity],
    balance_receipt: Dict[str, Any],
) -> Optional[WinningOpportunity]:
    """Find the single best opportunity for a winning trade"""
    
    # Find best opportunity - lowered thresholds for first winner
    for opp in opportunities:
        quote_balance = _quote_balance(opp, balance_receipt)
        if (
            _opportunity_is_actionable(opp)
            and quote_balance is not None
            and quote_balance[1] > 1
            and opp.momentum > 0.5
            and opp.score > 1
        ):
            print(f"💰 Available: {quote_balance[1]:.2f} {quote_balance[0]}")
            print(f"🎯 BEST OPPORTUNITY: {opp.symbol}")
            print(f"   Momentum: +{opp.momentum:.1f}%")
            print(f"   Price: ${opp.current_price:.4f}")
            print(f"   Score: {opp.score:.2f}")
            print(f"   Reason: {opp.reason}")
            return opp
    print("❌ No quote-matched balance and fresh opportunity receipt available")
    return None

def _validated_terminal_fill(
    receipt: Any,
    *,
    expected_order_id: str,
) -> Optional[Dict[str, Any]]:
    if not isinstance(receipt, dict):
        return None
    source_timestamp = _fresh_provider_timestamp(
        receipt.get("provider_timestamp") or receipt.get("source_timestamp"),
        max_age_seconds=FILL_MAX_AGE_SECONDS,
    )
    order_id = receipt.get("orderId") or receipt.get("order_id")
    executed_qty = _finite_number(receipt.get("executedQty"), positive=True)
    average_price = _finite_number(
        receipt.get("filled_avg_price") or receipt.get("avgPrice"),
        positive=True,
    )
    quote_qty = _finite_number(receipt.get("cummulativeQuoteQty"), positive=True)
    fee = _finite_number(receipt.get("fee"), nonnegative=True)
    fee_asset = str(receipt.get("fee_asset") or receipt.get("fee_currency") or "").upper()
    if (
        receipt.get("status") != "FILLED"
        or receipt.get("data_status") != "live"
        or receipt.get("fill_receipt_complete") is not True
        or receipt.get("eligible_for_accounting") is not True
        or receipt.get("generated_values") is not False
        or str(receipt.get("side") or "").upper() != "BUY"
        or str(order_id or "") != expected_order_id
        or source_timestamp is None
        or executed_qty is None
        or average_price is None
        or quote_qty is None
        or fee is None
        or not fee_asset
    ):
        return None
    return {
        "status": "FILLED",
        "data_status": "live",
        "truth_status": "real_provider",
        "order_id": expected_order_id,
        "source_id": str(receipt.get("source_id") or f"kraken:order:{expected_order_id}"),
        "source_timestamp": source_timestamp,
        "executed_qty": executed_qty,
        "average_fill_price": average_price,
        "quote_qty": quote_qty,
        "fees_by_asset": {fee_asset: fee},
        "fill_receipt_complete": True,
        "eligible_for_accounting": True,
        "generated_values": False,
    }


def execute_winning_trade(
    client: Any,
    opportunity: WinningOpportunity,
    balance: float,
    dry_run: bool = True,
    *,
    position_path: str | Path = "active_position.json",
) -> Dict[str, Any]:
    """Submit only from fresh evidence and persist only a terminal fill."""
    
    available_balance = _finite_number(balance, positive=True)
    if not client or not opportunity or not _opportunity_is_actionable(opportunity):
        return {
            "status": "NO_DATA",
            "data_status": "no_data",
            "reason": "fresh_complete_quote_and_client_required",
            "generated_values": False,
            "position_persisted": False,
        }
    if available_balance is None:
        return {
            "status": "NO_DATA",
            "data_status": "no_data",
            "reason": "exact_positive_quote_balance_required",
            "generated_values": False,
            "position_persisted": False,
        }
        
    # Use more capital to meet minimums - 50% of available or full balance
    trade_amount = available_balance * 0.5
    
    print(f"\n🚀 EXECUTING WINNING TRADE")
    print(f"   Symbol: {opportunity.symbol}")
    print(f"   Amount: ${trade_amount:.2f}")
    print(f"   Side: BUY")
    
    if dry_run:
        print("\n🧪 DRY RUN - provider order not submitted")
        return {
            "status": "NOT_SUBMITTED",
            "data_status": "not_submitted",
            "truth_status": "not_submitted",
            "reason": "dry_run_provider_order_not_submitted",
            "source_timestamp": None,
            "fill_receipt_complete": False,
            "eligible_for_accounting": False,
            "generated_values": False,
            "position_persisted": False,
        }
        
    try:
        # Execute buy using correct method: place_market_order with quote_qty
        submission = client.place_market_order(
            symbol=opportunity.symbol,
            side='buy',
            quote_qty=trade_amount  # Use quote quantity (USD amount)
        )
        if isinstance(submission, dict) and (
            submission.get("dryRun") is True
            or str(submission.get("status") or "").lower() == "not_submitted"
        ):
            return {
                "status": "NOT_SUBMITTED",
                "data_status": "not_submitted",
                "reason": str(submission.get("reason") or "provider_order_not_submitted"),
                "generated_values": False,
                "position_persisted": False,
            }
        if isinstance(submission, dict) and submission.get("error"):
            return {
                "status": "REJECTED",
                "data_status": "live",
                "reason": str(submission["error"]),
                "generated_values": False,
                "position_persisted": False,
            }
        order_id_value = (
            submission.get("orderId") or submission.get("order_id") or submission.get("txid")
            if isinstance(submission, dict)
            else None
        )
        if isinstance(order_id_value, (list, tuple)):
            order_id_value = order_id_value[0] if len(order_id_value) == 1 else None
        order_id = str(order_id_value or "")
        if not order_id:
            return {
                "status": "PENDING_RECONCILIATION",
                "data_status": "pending_reconciliation",
                "reason": "provider_submission_ack_missing_or_ambiguous_order_id",
                "generated_values": False,
                "position_persisted": False,
            }
        terminal = submission
        fill = _validated_terminal_fill(terminal, expected_order_id=order_id)
        if fill is None:
            if not hasattr(client, "get_order_status"):
                return {
                    "status": "PENDING_RECONCILIATION",
                    "data_status": "pending_reconciliation",
                    "order_id": order_id,
                    "reason": "terminal_order_query_unavailable",
                    "generated_values": False,
                    "position_persisted": False,
                }
            terminal = client.get_order_status(order_id)
            fill = _validated_terminal_fill(terminal, expected_order_id=order_id)
        if fill is None:
            return {
                "status": "PENDING_RECONCILIATION",
                "data_status": "pending_reconciliation",
                "order_id": order_id,
                "reason": "fresh_complete_terminal_provider_fill_required",
                "generated_values": False,
                "position_persisted": False,
            }

        position_record = {
            **fill,
            "symbol": opportunity.symbol,
            "side": "BUY",
            "quote_asset": _quote_asset(opportunity.symbol),
            "quote_receipt_id": opportunity.source_id,
            "quote_source_timestamp": opportunity.source_timestamp,
            "recorded_at": time.time(),
        }
        try:
            Path(position_path).write_text(
                json.dumps(position_record, indent=2, sort_keys=True),
                encoding="utf-8",
            )
        except Exception as exc:
            return {
                **fill,
                "status": "FILLED_RECONCILIATION_REQUIRED",
                "reason": f"position_receipt_persistence_failed:{type(exc).__name__}",
                "position_persisted": False,
                "reconciliation_required": True,
            }
        print(f"✅ TERMINAL PROVIDER FILL VERIFIED: {order_id}")
        return {
            **fill,
            "position_persisted": True,
            "position_path": str(position_path),
        }
            
    except Exception as e:
        print(f"❌ Trade execution error: {e}")
        return {
            "status": "PENDING_RECONCILIATION",
            "data_status": "pending_reconciliation",
            "reason": f"submission_or_query_failed:{type(e).__name__}",
            "generated_values": False,
            "position_persisted": False,
        }

def main():
    print("=" * 60)
    print("🏆 GET FIRST WINNER - ONE WIN TO SAVE THE PLANET 🌍")
    print("=" * 60)
    print()
    print("'The first domino falls, and the rest follow.'")
    print()
    
    # Check for dry-run flag
    dry_run = '--live' not in sys.argv
    if dry_run:
        print("🧪 DRY RUN MODE (use --live for real trading)")
    else:
        print("🔴 LIVE TRADING MODE")
    print()
    
    # Load client
    print("🔌 Connecting to Kraken...")
    client = load_kraken_client()
    
    if not client:
        print("❌ Could not connect to exchange")
        return
        
    # Get balances
    print("💰 Checking balances...")
    balance_receipt = check_balances(client)
    balances = balance_receipt.get("balances")
    asset_count = len(balances) if isinstance(balances, dict) else 0
    print(f"   Found {asset_count} receipted assets")
    if balance_receipt.get("data_status") != "live":
        print(f"❌ NO_DATA: {balance_receipt.get('reason')}")
        return
    
    # Get opportunities
    print("🔍 Scanning for opportunities...")
    opportunities = get_live_opportunities(client)
    print(f"   Found {len(opportunities)} strong opportunities")
    
    if not opportunities:
        print("\n⚠️ No strong opportunities right now")
        print("   Market may be flat - try again later")
        return
        
    # Show top opportunities
    print("\n📊 TOP OPPORTUNITIES:")
    for i, opp in enumerate(opportunities[:5], 1):
        print(f"   {i}. {opp.symbol}: +{opp.momentum:.1f}% (score: {opp.score:.1f})")
    
    # Select one quote-matched opportunity from fresh receipts.
    print("\n🎯 SELECTING BEST WINNER...")
    opportunity = find_best_winner(opportunities, balance_receipt)
    if opportunity is None:
        return
    quote_balance = _quote_balance(opportunity, balance_receipt)
    if quote_balance is None:
        print("❌ NO_DATA: exact quote balance unavailable")
        return

    result = execute_winning_trade(
        client,
        opportunity,
        quote_balance[1],
        dry_run=dry_run,
    )
    status = result.get("status")
    if status == "FILLED" and result.get("position_persisted") is True:
        print()
        print("=" * 60)
        print("✅ FIRST TERMINAL PROVIDER FILL VERIFIED")
        print("=" * 60)
        print("Position state was persisted from the provider fill receipt.")
        return
    if status in {"PENDING_RECONCILIATION", "FILLED_RECONCILIATION_REQUIRED"}:
        print(f"⚠️ {status}: {result.get('reason')}")
        print("No success or winning-PnL claim was recorded.")
        return
    if status == "NOT_SUBMITTED":
        print("🧪 NOT_SUBMITTED: no provider order, position, or success recorded.")
        return
    print(f"❌ Trade not completed: {status} ({result.get('reason')})")

if __name__ == "__main__":
    main()
