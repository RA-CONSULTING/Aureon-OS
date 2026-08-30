from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import time
import sys
import logging
import json
import asyncio
import math
from datetime import datetime, timedelta, timezone

EXECUTION_RECEIPT_MAX_AGE_SECONDS = 300.0
EXECUTION_RECEIPT_FUTURE_SKEW_SECONDS = 30.0
ACTION_EVIDENCE_MAX_AGE_SECONDS = 300.0
ACTION_EVIDENCE_FUTURE_SKEW_SECONDS = 30.0


def _finite_provider_number(value, *, positive=False, nonnegative=False):
    """Parse an observed provider number without substituting a default."""
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(parsed):
        return None
    if positive and parsed <= 0:
        return None
    if nonnegative and parsed < 0:
        return None
    return parsed


def _parse_provider_timestamp(value):
    """Return a provider timestamp in seconds, or None when it is unproven."""
    if value is None or isinstance(value, bool):
        return None
    parsed = None
    if isinstance(value, (int, float)):
        parsed = _finite_provider_number(value, positive=True)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        parsed = _finite_provider_number(text, positive=True)
        if parsed is None:
            try:
                normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
                observed = datetime.fromisoformat(normalized)
                if observed.tzinfo is None:
                    return None
                parsed = observed.timestamp()
            except (TypeError, ValueError, OverflowError):
                return None
    if parsed is None:
        return None
    while parsed > 100_000_000_000:
        parsed /= 1000.0
    return parsed if parsed > 0 and math.isfinite(parsed) else None


def _valid_provider_identifier(value):
    """Reject blank, local-only, and sentinel identifiers."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, float) and (not math.isfinite(value) or not value.is_integer()):
        return None
    identifier = str(value).strip()
    if not identifier:
        return None
    lowered = identifier.casefold()
    if lowered in {"0", "none", "null", "unknown", "n/a", "na", "pending"}:
        return None
    if lowered.startswith(("dry-", "dry_", "test-", "test_", "fake-", "fake_", "demo-", "demo_", "mock-", "mock_", "sim-", "sim_", "synthetic-", "placeholder")):  # sentinel rejected as no_data
        return None
    return identifier


def _first_present(mapping, names):
    for name in names:
        if name in mapping:
            return mapping[name]
    return None


def _provider_order_identifier(receipt):
    raw = _first_present(
        receipt,
        ("orderId", "provider_order_id", "dealReference", "id", "txid"),
    )
    if isinstance(raw, (list, tuple)):
        if len(raw) != 1:
            return None
        raw = raw[0]
    return _valid_provider_identifier(raw)


def _provider_trade_identifiers(receipt):
    fills = receipt.get("fills")
    if not isinstance(fills, (list, tuple)) or not fills:
        return []
    identifiers = []
    for fill in fills:
        if not isinstance(fill, dict):
            return []
        trade_id = _valid_provider_identifier(
            _first_present(fill, ("tradeId", "trade_id", "fill_id", "id"))
        )
        if trade_id is None or trade_id in identifiers:
            return []
        identifiers.append(trade_id)
    return identifiers


def _execution_result(
    *,
    venue,
    status,
    reason,
    receipt=None,
    order_id=None,
    trade_ids=None,
    filled_qty=None,
    filled_price=None,
    fee=None,
    fee_currency=None,
    provider_timestamp=None,
    receipt_id=None,
    symbol=None,
    side=None,
):
    success = status == "filled"
    return {
        "success": success,
        "status": status,
        "data_status": "live" if success else status,
        "reason": reason,
        "venue": venue,
        "order_id": order_id,
        "trade_ids": list(trade_ids or []),
        "filled_qty": filled_qty,
        "filled_price": filled_price,
        "fee": fee,
        "fee_currency": fee_currency,
        "provider_timestamp": provider_timestamp,
        "receipt_id": receipt_id,
        "symbol": symbol,
        "side": side,
        "fill_receipt_complete": success,
        "eligible_for_accounting": success,
        "eligible_for_learning": success,
        "receipt": receipt,
    }


def _normalized_venue(value):
    return str(value or "").strip().lower()


def _normalized_symbol(value):
    if not isinstance(value, str):
        return ""
    return "".join(character for character in value.upper() if character.isalnum())


def _same_observed_number(left, right):
    left_number = _finite_provider_number(left)
    right_number = _finite_provider_number(right)
    if left_number is None or right_number is None:
        return False
    return math.isclose(left_number, right_number, rel_tol=1e-12, abs_tol=1e-12)


def _classify_action_evidence(
    position_receipt,
    opportunity_receipt,
    *,
    venue,
    symbol,
    position_id,
    quantity,
    pnl,
    entry_price,
    current_price,
    now=None,
):
    """Require linked, fresh account-position and market-opportunity receipts."""
    venue_name = _normalized_venue(venue)
    symbol_name = _normalized_symbol(symbol)
    expected_position_id = _valid_provider_identifier(position_id)
    current_time = _finite_provider_number(time.time() if now is None else now, positive=True)

    def no_data(reason):
        return {
            "eligible_for_action": False,
            "data_status": "no_data",
            "truth_status": "no_data",
            "generated_values": False,
            "reason": reason,
            "venue": venue_name,
            "symbol": symbol_name or None,
            "position_receipt_id": None,
            "opportunity_receipt_id": None,
        }

    if not venue_name or not symbol_name or expected_position_id is None:
        return no_data("canonical_venue_symbol_and_position_id_required")
    if current_time is None:
        return no_data("current_time_unavailable")
    if not isinstance(position_receipt, dict):
        return no_data("fresh_position_receipt_required")
    if not isinstance(opportunity_receipt, dict):
        return no_data("fresh_opportunity_receipt_required")

    receipt_ids = {}
    timestamps = {}
    for label, receipt, allowed_truth in (
        ("position", position_receipt, {"real_observed"}),
        ("opportunity", opportunity_receipt, {"real_observed", "real_derived"}),
    ):
        if receipt.get("data_status") != "live":
            return no_data(f"{label}_receipt_not_live")
        if str(receipt.get("truth_status") or "").strip().lower() not in allowed_truth:
            return no_data(f"{label}_receipt_truth_unproven")
        if receipt.get("generated_values") is not False:
            return no_data(f"{label}_receipt_generated_values_unproven")
        if receipt.get("eligible_for_action") is not True:
            return no_data(f"{label}_receipt_not_actionable")
        observed_venue = _normalized_venue(
            _first_present(receipt, ("venue", "exchange", "provider"))
        )
        if observed_venue != venue_name:
            return no_data(f"{label}_receipt_venue_mismatch")
        if _normalized_symbol(receipt.get("symbol")) != symbol_name:
            return no_data(f"{label}_receipt_symbol_mismatch")
        source_id = _valid_provider_identifier(receipt.get("source_id"))
        receipt_id = _valid_provider_identifier(receipt.get("receipt_id"))
        if source_id is None or receipt_id is None:
            return no_data(f"{label}_receipt_provenance_ids_required")
        source_timestamp = _parse_provider_timestamp(receipt.get("source_timestamp"))
        received_at = _parse_provider_timestamp(receipt.get("received_at"))
        if source_timestamp is None or received_at is None:
            return no_data(f"{label}_receipt_timestamps_required")
        if (
            source_timestamp < current_time - ACTION_EVIDENCE_MAX_AGE_SECONDS
            or source_timestamp > current_time + ACTION_EVIDENCE_FUTURE_SKEW_SECONDS
            or received_at < current_time - ACTION_EVIDENCE_MAX_AGE_SECONDS
            or received_at > current_time + ACTION_EVIDENCE_FUTURE_SKEW_SECONDS
            or source_timestamp > received_at + ACTION_EVIDENCE_FUTURE_SKEW_SECONDS
        ):
            return no_data(f"fresh_{label}_receipt_required")
        receipt_ids[label] = receipt_id
        timestamps[label] = source_timestamp

    observed_position_id = _valid_provider_identifier(position_receipt.get("position_id"))
    if observed_position_id != expected_position_id:
        return no_data("position_receipt_id_mismatch")
    observed_quantity = _finite_provider_number(position_receipt.get("quantity"), positive=True)
    if observed_quantity is None or not _same_observed_number(observed_quantity, quantity):
        return no_data("position_receipt_quantity_mismatch")

    if opportunity_receipt.get("position_receipt_id") != receipt_ids["position"]:
        return no_data("opportunity_receipt_not_linked_to_position_receipt")
    observed_pnl = _finite_provider_number(opportunity_receipt.get("pnl"), positive=True)
    observed_entry = _finite_provider_number(opportunity_receipt.get("entry_price"), positive=True)
    observed_current = _finite_provider_number(opportunity_receipt.get("current_price"), positive=True)
    if observed_pnl is None or not _same_observed_number(observed_pnl, pnl):
        return no_data("opportunity_receipt_pnl_mismatch")
    if observed_entry is None or not _same_observed_number(observed_entry, entry_price):
        return no_data("opportunity_receipt_entry_price_mismatch")
    if observed_current is None or not _same_observed_number(observed_current, current_price):
        return no_data("opportunity_receipt_current_price_mismatch")

    return {
        "eligible_for_action": True,
        "data_status": "live",
        "truth_status": "real_derived",
        "generated_values": False,
        "reason": "fresh_linked_position_and_opportunity_receipts",
        "venue": venue_name,
        "symbol": symbol_name,
        "position_receipt_id": receipt_ids["position"],
        "opportunity_receipt_id": receipt_ids["opportunity"],
        "source_timestamps": timestamps,
    }


def _classify_terminal_fill_receipt(
    receipt,
    venue,
    *,
    now=None,
    submission_attempted=False,
    expected_symbol=None,
    expected_side=None,
    expected_quantity=None,
):
    """Accept only a fresh, complete, provider-observed terminal fill receipt."""
    venue_name = str(venue or "unknown").strip().lower()
    if not isinstance(receipt, dict):
        status = "pending_reconciliation" if submission_attempted else "no_data"
        return _execution_result(
            venue=venue_name,
            status=status,
            reason="provider_submission_outcome_unproven" if submission_attempted else "provider_receipt_missing",
            receipt=receipt,
        )

    raw_status = str(receipt.get("status") or "").strip().lower()
    data_status = str(receipt.get("data_status") or "").strip().lower()
    order_id = _provider_order_identifier(receipt)

    if (
        receipt.get("dryRun") is True
        or receipt.get("submitted") is False
        or raw_status == "not_submitted"
        or data_status == "not_submitted"
    ):
        return _execution_result(
            venue=venue_name,
            status="not_submitted",
            reason=str(receipt.get("reason") or "provider_order_not_submitted"),
            receipt=receipt,
            order_id=order_id,
        )

    if raw_status in {"rejected", "denied"} and order_id is None:
        return _execution_result(
            venue=venue_name,
            status="not_submitted",
            reason=str(receipt.get("reason") or "provider_submission_rejected"),
            receipt=receipt,
        )

    submission_is_known = bool(
        submission_attempted
        or order_id is not None
        or receipt.get("submission_acknowledged") is True
        or receipt.get("reconciliation_required") is True
    )

    def incomplete(reason):
        return _execution_result(
            venue=venue_name,
            status="pending_reconciliation" if submission_is_known else "no_data",
            reason=reason,
            receipt=receipt,
            order_id=order_id,
        )

    if data_status != "live":
        return incomplete("terminal_live_provider_receipt_required")
    if raw_status != "filled":
        return incomplete("terminal_filled_provider_status_required")
    if receipt.get("fill_receipt_complete") is not True:
        return incomplete("complete_fill_receipt_required")
    if receipt.get("eligible_for_accounting") is not True:
        return incomplete("provider_receipt_not_eligible_for_accounting")
    if receipt.get("eligible_for_learning") is not True:
        return incomplete("provider_receipt_not_eligible_for_learning")
    if receipt.get("generated_values") is not False:
        return incomplete("provider_receipt_contains_unproven_values")
    if str(receipt.get("truth_status") or "").strip().lower() not in {
        "real_observed",
        "real_provider",
    }:
        return incomplete("provider_receipt_truth_unproven")
    if order_id is None:
        return incomplete("non_sentinel_provider_order_id_required")
    receipt_id = _valid_provider_identifier(receipt.get("receipt_id"))
    if receipt_id is None:
        return incomplete("terminal_provider_receipt_id_required")
    provider_receipt_type = _valid_provider_identifier(receipt.get("provider_receipt_type"))
    if provider_receipt_type is None:
        return incomplete("terminal_provider_receipt_type_required")
    if venue_name == "kraken" and receipt.get("provider_receipt_type") not in {"QueryOrders", "ClosedOrders"}:
        return incomplete("kraken_query_or_closed_orders_receipt_required")

    observed_venue = _normalized_venue(
        _first_present(receipt, ("venue", "exchange", "provider"))
    )
    if observed_venue != venue_name:
        return incomplete("terminal_provider_receipt_venue_mismatch")
    observed_symbol = _normalized_symbol(receipt.get("symbol"))
    required_symbol = _normalized_symbol(expected_symbol)
    if not observed_symbol or (required_symbol and observed_symbol != required_symbol):
        return incomplete("terminal_provider_receipt_symbol_mismatch")
    observed_side = str(receipt.get("side") or "").strip().upper()
    required_side = str(expected_side or "").strip().upper()
    if not observed_side or (required_side and observed_side != required_side):
        return incomplete("terminal_provider_receipt_side_mismatch")

    trade_ids = _provider_trade_identifiers(receipt)
    if not trade_ids:
        return incomplete("non_sentinel_provider_trade_ids_required")

    filled_qty = _finite_provider_number(
        _first_present(receipt, ("filled_qty", "executedQty", "filledQty")),
        positive=True,
    )
    filled_price = _finite_provider_number(
        _first_present(receipt, ("filled_avg_price", "avgPrice", "avg_fill_price")),
        positive=True,
    )
    fee = _finite_provider_number(
        _first_present(receipt, ("fee", "fee_amount", "fees")),
        nonnegative=True,
    )
    fee_currency = str(receipt.get("fee_currency") or receipt.get("fee_asset") or "").strip()
    if filled_qty is None:
        return incomplete("observed_provider_filled_quantity_required")
    if expected_quantity is not None and not _same_observed_number(filled_qty, expected_quantity):
        return incomplete("exact_provider_filled_quantity_required")
    if filled_price is None:
        return incomplete("observed_provider_fill_price_required")
    if fee is None or not fee_currency:
        return incomplete("observed_provider_fee_and_currency_required")

    provider_timestamp = _parse_provider_timestamp(receipt.get("provider_timestamp"))
    current_time = _finite_provider_number(time.time() if now is None else now, positive=True)
    if provider_timestamp is None or current_time is None:
        return incomplete("provider_fill_timestamp_required")
    if (
        provider_timestamp < current_time - EXECUTION_RECEIPT_MAX_AGE_SECONDS
        or provider_timestamp > current_time + EXECUTION_RECEIPT_FUTURE_SKEW_SECONDS
    ):
        return incomplete("fresh_provider_fill_timestamp_required")

    return _execution_result(
        venue=venue_name,
        status="filled",
        reason="complete_fresh_terminal_provider_fill_receipt",
        receipt=receipt,
        order_id=order_id,
        trade_ids=trade_ids,
        filled_qty=filled_qty,
        filled_price=filled_price,
        fee=fee,
        fee_currency=fee_currency,
        provider_timestamp=provider_timestamp,
        receipt_id=receipt_id,
        symbol=observed_symbol,
        side=observed_side,
    )

# Import Clients
from aureon.exchanges.capital_client import CapitalClient
from aureon.exchanges.alpaca_client import AlpacaClient
from aureon.exchanges.binance_client import BinanceClient, get_binance_client
from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
from aureon.utils.aureon_sero_client import SeroClient

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
# 🔩 HARMONIC LIQUID ALUMINIUM FIELD - Live Streaming Integration
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════
try:
    from aureon.harmonic.aureon_harmonic_liquid_aluminium import (
        FieldSnapshot,
        HarmonicLiquidAluminiumField,
        harmonic_streaming_runtime,
    )
    HARMONIC_FIELD_AVAILABLE = True
except ImportError:
    HARMONIC_FIELD_AVAILABLE = False
    HarmonicLiquidAluminiumField = None
    harmonic_streaming_runtime = lambda method: method

# Setup fancy logging
def log_queen(msg):
    print(f"\033[95m👑 [QUEEN] {msg}\033[0m")
    time.sleep(0.5)

def log_auris(msg):
    print(f"\033[94m⚕️ [DR. AURIS] {msg}\033[0m")
    time.sleep(0.2)

def log_sniper(msg):
    print(f"\033[92m🎯 [SNIPER] {msg}\033[0m")
    time.sleep(0.3)

def log_system(msg):
    print(f"\033[90m🖥️ [SYSTEM] {msg}\033[0m")

def log_warn(msg):
    print(f"\033[93m⚠️ [WARNING] {msg}\033[0m")

def log_harmonic(msg):
    """🔩 Harmonic field logging - cyan color for liquid aluminium"""
    print(f"\033[96m🔩 [HARMONIC] {msg}\033[0m")

class UnifiedKillChain:
    def __init__(self):
        self.running = True
        self._pending_reconciliations = {}
        log_system("Initializing Exchange Uplinks...")
        
        # ═══════════════════════════════════════════════════════════════════════════════════════════════════════
        # 🔩 Initialize Harmonic Liquid Aluminium Field (Live Stream Layer)
        # ═══════════════════════════════════════════════════════════════════════════════════════════════════════
        self.harmonic_field = None
        if HARMONIC_FIELD_AVAILABLE:
            try:
                self.harmonic_field = HarmonicLiquidAluminiumField(stream_interval_ms=100)
                log_harmonic("Liquid Aluminium Field WIRED - runtime start pending")
            except Exception as e:
                log_warn(f"Harmonic Field init failed: {e}")
                self.harmonic_field = None
        
        # Initialize Clients
        self.capital = CapitalClient()
        self.alpaca = AlpacaClient()
        self.binance = get_binance_client()
        self.kraken = get_kraken_client()
        
        # Kraken warmup delay to avoid "Invalid nonce" errors after heavy init
        log_system("Kraken: Nonce sync warmup (3s)...")
        time.sleep(3)
        
        # Initialize Dr. Auris Throne API (DigitalOcean LLM)
        self.dr_auris = SeroClient()
        
        self._report_connectivity()

    def _report_connectivity(self):
        log_system(f"Capital.com:   {'✅' if self.capital.enabled and self.capital.cst else '❌'}")
        log_system(f"Alpaca:        {'✅' if self.alpaca.api_key else '❌'}")
        log_system(f"Binance:       {'✅' if self.binance.api_key else '❌'}")
        log_system(f"Kraken:        {'✅' if self.kraken.api_key else '❌'}")
        log_system(f"Dr. Auris API: {'✅' if self.dr_auris.enabled else '❌ (AI validation DISABLED)'}")
        if self.harmonic_field:
            log_harmonic("Liquid Aluminium Field: ✅ WIRED")

    def _print_harmonic_summary(self):
        """Print the harmonic liquid aluminium field summary."""
        if not self.harmonic_field:
            return
        
        snapshot = self.harmonic_field.capture_snapshot()
        
        print()
        log_harmonic("═══════════════════════════════════════════════════════════════")
        log_harmonic(f"       🌊 LIQUID ALUMINIUM FIELD - Cycle {snapshot.cycle} 🌊")
        log_harmonic("═══════════════════════════════════════════════════════════════")
        log_harmonic(f"  Total Nodes: {snapshot.total_nodes} | Energy: {snapshot.total_energy:.1f}")
        log_harmonic(f"  Global Hz: {snapshot.global_frequency:.1f} | Amp: {snapshot.global_amplitude:.3f}")
        log_harmonic(f"  Cymatics: {snapshot.cymatics_pattern.value}")
        log_harmonic(f"  Value: ${snapshot.total_value_usd:,.2f} | P&L: ${snapshot.total_pnl_usd:+,.2f}")
        
        # Print layer summaries
        for layer in sorted(self.harmonic_field.layers.values(), key=lambda l: l.layer_id):
            if layer.total_nodes > 0:
                log_harmonic(f"  {layer.icon} {layer.exchange.upper()}: {layer.total_nodes} nodes @ {layer.average_frequency:.0f}Hz")
        
        # Mini waveform visualization
        if snapshot.master_waveform:
            wave_chars = "▁▂▃▄▅▆▇█"
            wave_display = ""
            step = max(1, len(snapshot.master_waveform) // 50)
            for i in range(0, min(50, len(snapshot.master_waveform)), step):
                val = (snapshot.master_waveform[i] + 1) / 2  # Normalize to 0-1
                idx = int(val * (len(wave_chars) - 1))
                wave_display += wave_chars[max(0, min(idx, len(wave_chars)-1))]
            log_harmonic(f"  Wave: [{wave_display}]")
        
        log_harmonic("═══════════════════════════════════════════════════════════════")
        print()

    @harmonic_streaming_runtime
    def run_loop(self):
        log_queen("System fully online. Entering dormant stalking mode.")
        while self.running:
            try:
                print("\n" + "="*60)
                log_system(f"SCAN CYCLE START: {datetime.now().strftime('%H:%M:%S')}")
                
                # 1. CAPITAL.COM SCAN
                if self.capital.enabled and self.capital.cst:
                    self._scan_capital()
                
                # 2. ALPACA SCAN
                if self.alpaca.api_key:
                    self._scan_alpaca()
                
                # 3. KRAKEN SCAN (before Binance - Kraken has fewer positions)
                if self.kraken.api_key:
                    self._scan_kraken()
                
                # 4. BINANCE SCAN (last - has most positions)
                if self.binance.api_key:
                    self._scan_binance()
                
                # ═══════════════════════════════════════════════════════════════
                # 🔩 HARMONIC FIELD SUMMARY: Print the liquid aluminium state
                # ═══════════════════════════════════════════════════════════════
                if self.harmonic_field:
                    self._print_harmonic_summary()
                    
                log_system("Cycle complete. Recharging energy matrix...")
                time.sleep(10) # 10s delay between full cycles
                
            except KeyboardInterrupt:
                log_system("Manual Override detected. Shutting down.")
                self.running = False
            except Exception as e:
                log_warn(f"Critical Loop Error: {e}")
                time.sleep(5)

    def _scan_capital(self):
        log_queen("Scanning Capital.com reality branches...")
        try:
            positions = self.capital.get_positions()
            if not positions:
                log_system("Capital.com: No active threads.")
                return

            for p in positions:
                market = p.get('market', {})
                pos_data = p.get('position', {})
                epic = market.get('epic', 'UNKNOWN')
                upl = float(pos_data.get('upl', 0))
                deal_id = pos_data.get('dealId')
                level = float(market.get('bid', 0)) or float(market.get('offer', 0))
                entry = float(pos_data.get('openLevel', 0))
                size = float(pos_data.get('dealSize', 0))
                
                # ═══════════════════════════════════════════════════════════════
                # 🔩 HARMONIC FIELD: Add node to liquid aluminium field
                # ═══════════════════════════════════════════════════════════════
                if self.harmonic_field and level > 0:
                    asset_class = 'forex' if 'USD' in epic or 'EUR' in epic else 'crypto'
                    node = self.harmonic_field.add_or_update_node(
                        exchange='capital',
                        symbol=epic,
                        current_price=level,
                        entry_price=entry,
                        quantity=size,
                        asset_class=asset_class
                    )
                    log_harmonic(f"[Capital] {epic} → {node.frequency:.1f}Hz | Amp: {node.amplitude:.3f} | {node.state.value}")
                
                self._evaluate_and_kill(
                    exchange="Capital",
                    symbol=epic,
                    pnl=upl,
                    position_id=deal_id,
                    qty=float(pos_data.get('dealSize', 0)),
                    client_ref=self.capital,
                    close_func=self._close_capital
                )
        except Exception as e:
            log_warn(f"Capital Scan Failed: {e}")

    def _scan_alpaca(self):
        log_queen("Scanning Alpaca streams...")
        try:
            positions = self.alpaca.get_positions()
            if not positions:
                log_system("Alpaca: No active threads.")
                return
            
            # ═══════════════════════════════════════════════════════════════
            # 🦙 OPTIMIZED: Batch fetch prices for all positions
            # Uses asset_class from position data OR smart symbol detection
            # ═══════════════════════════════════════════════════════════════
            log_system("Alpaca: Fetching prices (batch)...")
            all_prices = {}
            
            # Known crypto bases (expanded list - Alpaca supported)
            KNOWN_CRYPTO = {
                'BTC', 'ETH', 'SOL', 'DOGE', 'LTC', 'AVAX', 'LINK', 'UNI', 'AAVE', 
                'SHIB', 'PEPE', 'TRUMP', 'XRP', 'ADA', 'DOT', 'MATIC', 'ATOM', 
                'NEAR', 'APT', 'ARB', 'OP', 'FIL', 'GRT', 'MKR', 'SNX', 'CRV', 
                'COMP', 'SUSHI', 'YFI', 'BAT', 'ENJ', 'MANA', 'SAND', 'AXS', 
                'ALGO', 'XLM', 'VET', 'HBAR', 'ICP', 'FTM', 'EGLD', 'THETA',
                'XTZ', 'EOS', 'FLOW', 'KAVA', 'ZEC', 'BCH', 'ETC', 'TRX', 'XMR'
            }
            
            # Separate crypto vs stock symbols using asset_class field
            crypto_symbols = []
            stock_symbols = []
            position_asset_class = {}  # Track asset class for each position
            
            for p in positions:
                sym = p.get('symbol', '')
                asset_class = p.get('asset_class', '').lower()
                position_asset_class[sym] = asset_class
                
                # Method 1: Use asset_class field (most reliable)
                if asset_class == 'crypto':
                    crypto_symbols.append(sym)
                elif asset_class == 'us_equity':
                    stock_symbols.append(sym)
                # Method 2: Fallback to symbol pattern detection
                elif sym.endswith('/USD') or sym.endswith('USD'):
                    base = sym.replace('/USD', '').replace('USD', '')
                    if base in KNOWN_CRYPTO:
                        crypto_symbols.append(sym)
                    else:
                        # Could be stock with USD suffix (rare) or unknown crypto
                        stock_symbols.append(sym)
                else:
                    # No USD suffix = likely stock ticker (AAPL, TSLA, etc.)
                    stock_symbols.append(sym)
            
            log_system(f"Alpaca: Detected {len(crypto_symbols)} crypto, {len(stock_symbols)} stocks")
            
            # Batch fetch crypto prices
            if crypto_symbols:
                try:
                    crypto_quotes = self.alpaca.get_latest_crypto_quotes(crypto_symbols)
                    for sym, q in crypto_quotes.items():
                        bp = float(q.get('bp', 0) or 0)
                        ap = float(q.get('ap', 0) or 0)
                        mid = (bp + ap) / 2 if (bp > 0 and ap > 0) else (bp or ap or 0)
                        all_prices[sym.replace('/', '')] = mid
                        all_prices[sym] = mid
                    log_system(f"Alpaca: Crypto batch loaded {len(crypto_quotes)} quotes")
                except Exception as e:
                    log_warn(f"Alpaca crypto batch quote failed: {e}")
            
            # Batch fetch stock prices (using get_stock_snapshots)
            if stock_symbols:
                try:
                    stock_snaps = self.alpaca.get_stock_snapshots(stock_symbols)
                    stock_loaded = 0
                    for sym, snap in stock_snaps.items():
                        price = 0.0
                        if snap:
                            # Try latestTrade first (most accurate)
                            if 'latestTrade' in snap:
                                price = float(snap['latestTrade'].get('p', 0))
                            elif 'latest_trade' in snap:
                                price = float(snap['latest_trade'].get('p', 0))
                            # Fallback to minuteBar
                            elif 'minuteBar' in snap:
                                price = float(snap['minuteBar'].get('c', 0))
                            elif 'minute_bar' in snap:
                                price = float(snap['minute_bar'].get('c', 0))
                            # Fallback to dailyBar
                            elif 'dailyBar' in snap:
                                price = float(snap['dailyBar'].get('c', 0))
                            elif 'daily_bar' in snap:
                                price = float(snap['daily_bar'].get('c', 0))
                        if price > 0:
                            all_prices[sym] = price
                            stock_loaded += 1
                    log_system(f"Alpaca: Stock batch loaded {stock_loaded} prices")
                except Exception as e:
                    log_warn(f"Alpaca stock batch snapshot failed: {e}")
            
            log_system(f"Alpaca: Loaded {len(all_prices)} prices")
            
            active_count = 0
            dust_count = 0
                
            for p in positions:
                symbol = p.get('symbol')
                
                # Fix formatting for quantity - handle scientific notation
                raw_qty = p.get('qty', 0)
                qty_avail = p.get('qty_available', raw_qty)
                
                try:
                    qty = float(raw_qty)
                    qty_str = f"{qty:f}".rstrip('0').rstrip('.')
                except:
                    qty = 0.0
                    qty_str = "0"

                # ═══════════════════════════════════════════════════════════════
                # 💰 PRICE: Use batch-fetched price, fallback to position data
                # ═══════════════════════════════════════════════════════════════
                current_price = all_prices.get(symbol) or all_prices.get(symbol.replace('/', '')) or float(p.get('current_price', 0))
                
                # ═══════════════════════════════════════════════════════════════
                # 📊 COST BASIS: Use calculate_cost_basis for accurate entry
                # ═══════════════════════════════════════════════════════════════
                avg_entry = 0.0
                try: 
                    avg_entry = float(p.get('avg_entry_price', 0))
                except: 
                    pass

                # Fallback: Use calculate_cost_basis from filled orders
                if avg_entry == 0:
                    try:
                        cost_data = self.alpaca.calculate_cost_basis(symbol)
                        if cost_data and cost_data.get('avg_cost', 0) > 0:
                            avg_entry = cost_data['avg_cost']
                    except:
                        pass

                # Calculate PnL
                upl = float(p.get('unrealized_pl', 0))
                if avg_entry > 0 and current_price > 0:
                    upl = (current_price - avg_entry) * qty
                
                # Get asset class for display
                asset_class = position_asset_class.get(symbol, p.get('asset_class', 'unknown'))
                asset_icon = "📈" if asset_class == 'us_equity' else "🪙" if asset_class == 'crypto' else "❓"
                
                # Filter out dust/tiny positions (different thresholds for stocks vs crypto)
                min_qty_threshold = 0.001 if asset_class == 'us_equity' else 0.00000001
                if qty <= min_qty_threshold:
                    dust_count += 1
                    log_system(f"[Alpaca] 🧹 DUST: {asset_icon} {symbol} | qty={qty_str} (too small to trade)")
                    continue
                
                active_count += 1
                
                # Enhanced logging with asset class
                value = qty * current_price if current_price > 0 else 0
                log_system(f"[Alpaca] {asset_icon} {symbol} ({asset_class}): {qty_str} @ ${current_price:.4f} (${value:.2f})")
                
                # ═══════════════════════════════════════════════════════════════
                # 🔩 HARMONIC FIELD: Add node to liquid aluminium field
                # ═══════════════════════════════════════════════════════════════
                if self.harmonic_field:
                    node = self.harmonic_field.add_or_update_node(
                        exchange='alpaca',
                        symbol=symbol,
                        current_price=current_price,
                        entry_price=avg_entry,
                        quantity=qty,
                        asset_class=asset_class
                    )
                    log_harmonic(f"[Alpaca] {symbol} → {node.frequency:.1f}Hz | Amp: {node.amplitude:.3f} | {node.state.value}")
                     
                self._evaluate_and_kill(
                    exchange="Alpaca",
                    symbol=symbol,
                    pnl=upl,
                    position_id=symbol,
                    qty=qty,
                    client_ref=self.alpaca,
                    close_func=self._close_alpaca,
                    entry_price=avg_entry,
                    current_price=current_price,
                    asset_class=asset_class  # Pass asset class for smarter handling
                )
            
            if active_count == 0 and dust_count > 0:
                log_system(f"Alpaca: {dust_count} dust positions, 0 tradeable.")
            elif active_count == 0:
                log_system("Alpaca: No active threads (Clean).")
            else:
                log_system(f"Alpaca: {active_count} active, {dust_count} dust.")
                
        except Exception as e:
            import traceback
            log_warn(f"Alpaca Scan Failed: {e}")
            traceback.print_exc()

    def _scan_binance(self):
        log_queen("Scanning Binance chain...")
        try:
            # Get account balances
            acct = self.binance.account()
            if not acct or 'balances' not in acct:
                log_system("Binance: No active threads (account/balances missing).")
                return
            
            # Convert to dict format for consistent processing
            balances = {b['asset']: float(b['free']) + float(b['locked']) for b in acct['balances']}
            
            # ═══════════════════════════════════════════════════════════════
            # 🟡 OPTIMIZED: Batch fetch ALL tickers in ONE call
            # ═══════════════════════════════════════════════════════════════
            log_system("Binance: Fetching all tickers (batch)...")
            all_tickers = {}
            try:
                ticker_list = self.binance.get_24h_tickers()
                for t in ticker_list:
                    sym = t.get('symbol', '')
                    if sym:
                        all_tickers[sym] = {
                            'price': float(t.get('lastPrice', 0)),
                            'change': float(t.get('priceChangePercent', 0)),
                            'volume': float(t.get('quoteVolume', 0)),
                            'bid': float(t.get('bidPrice', 0)),
                            'ask': float(t.get('askPrice', 0))
                        }
                log_system(f"Binance: Loaded {len(all_tickers)} ticker prices")
            except Exception as e:
                log_warn(f"Binance batch ticker fetch failed: {e}")
                all_tickers = {}
            
            # Skip stablecoins and special assets
            SKIP_ASSETS = {'USDT', 'USDC', 'BUSD', 'GBP', 'USD', 'EUR', 'DAI', 'FDUSD', 'TUSD', 'USDP'}
            
            active_count = 0
            for asset, qty in balances.items():
                if qty <= 0: 
                    continue
                # Skip stablecoins
                if asset in SKIP_ASSETS:
                    continue
                # Skip Binance Earn (LD prefix)
                if asset.startswith('LD'): 
                    continue 
                
                # ═══════════════════════════════════════════════════════════════
                # 🔍 FIND PRICE: Try different quote currencies
                # ═══════════════════════════════════════════════════════════════
                found_pair = None
                current_price = 0.0
                quote_currencies = ['USDT', 'USDC', 'BTC', 'ETH', 'BNB', 'EUR']
                
                for quote in quote_currencies:
                    if asset == quote:
                        continue
                    pair = f"{asset}{quote}"
                    if pair in all_tickers and all_tickers[pair]['price'] > 0:
                        current_price = all_tickers[pair]['price']
                        found_pair = pair
                        break
                
                # Fallback: Direct API call
                if current_price == 0:
                    for quote in ['USDT', 'USDC']:
                        try:
                            ticker = self.binance.get_ticker(f"{asset}{quote}")
                            price = _finite_provider_number(
                                ticker.get('price') if isinstance(ticker, dict) else None,
                                positive=True,
                            )
                            if price is not None:
                                current_price = price
                                found_pair = f"{asset}{quote}"
                                break
                        except:
                            pass

                if current_price == 0:
                    continue
                
                active_count += 1
                
                # ═══════════════════════════════════════════════════════════════
                # 💰 COST BASIS: Use binance_client's calculate_cost_basis
                # (includes both Spot trades AND Convert history)
                # ═══════════════════════════════════════════════════════════════
                avg_entry = 0.0
                
                # Method 1: Use calculate_cost_basis (covers spot + convert)
                try:
                    cost_data = self.binance.calculate_cost_basis(found_pair)
                    if cost_data and cost_data.get('avg_entry_price', 0) > 0:
                        avg_entry = cost_data['avg_entry_price']
                except:
                    pass
                
                # Method 2: Direct trade history lookup
                if avg_entry == 0:
                    try:
                        my_trades = self.binance.get_my_trades(symbol=found_pair, limit=500, silent=True)
                        if my_trades:
                            t_qty = 0.0
                            t_cost = 0.0
                            for t in my_trades:
                                if t.get('isBuyer'):
                                    t_qty += float(t.get('qty', 0))
                                    t_cost += float(t.get('quoteQty', 0))
                            if t_qty > 0:
                                avg_entry = t_cost / t_qty
                    except:
                        pass
                
                if avg_entry == 0:
                    value = qty * current_price
                    log_system(f"[Binance] 👁️ {asset}: {qty:.6f} @ ${current_price:.4f} (${value:.2f}) | Cost Unknown -> HOLDING SAFE")
                    continue
                
                pnl = (current_price - avg_entry) * qty
                percent = ((current_price - avg_entry) / avg_entry) * 100 if avg_entry > 0 else 0
                
                log_queen(f"[Binance] {found_pair} | Entry: ${avg_entry:.4f} | Curr: ${current_price:.4f} | PnL: ${pnl:.2f} ({percent:+.2f}%)")
                
                # ═══════════════════════════════════════════════════════════════
                # 🔩 HARMONIC FIELD: Add node to liquid aluminium field
                # ═══════════════════════════════════════════════════════════════
                if self.harmonic_field:
                    node = self.harmonic_field.add_or_update_node(
                        exchange='binance',
                        symbol=asset,
                        current_price=current_price,
                        entry_price=avg_entry,
                        quantity=qty,
                        asset_class='crypto'
                    )
                    log_harmonic(f"[Binance] {asset} → {node.frequency:.1f}Hz | Amp: {node.amplitude:.3f} | {node.state.value}")
                
                self._evaluate_and_kill(
                    exchange="Binance",
                    symbol=found_pair,
                    pnl=pnl,
                    position_id=asset,
                    qty=qty,
                    client_ref=self.binance,
                    close_func=self._close_binance,
                    entry_price=avg_entry,
                    current_price=current_price
                )
            
            if active_count == 0:
                log_system("Binance: No active crypto positions.")
            else:
                log_system(f"Binance: Scanned {active_count} positions.")

        except Exception as e:
            log_warn(f"Binance Scan Failed: {e}")
            import traceback
            traceback.print_exc()

    def _scan_kraken(self):
        log_queen("Scanning Kraken depths...")
        try:
            # Pre-sleep to avoid nonce conflicts after other API calls
            time.sleep(2.0)
            balances = self.kraken.get_account_balance()
            if not balances or isinstance(balances, list):
                if isinstance(balances, list):
                    log_warn(f"Kraken Balance Error: {balances}")
                log_system("Kraken: No active balances.")
                return
            
            # ═══════════════════════════════════════════════════════════════
            # 🐙 OPTIMIZED: Use get_24h_tickers() for ALL prices in ONE call
            # This is much more efficient than calling get_ticker() per asset
            # ═══════════════════════════════════════════════════════════════
            log_system("Kraken: Fetching all tickers (batch)...")
            all_tickers = {}
            try:
                ticker_list = self.kraken.get_24h_tickers()
                # Convert list to dict keyed by symbol for fast lookup
                for t in ticker_list:
                    sym = t.get('symbol', '')
                    if sym:
                        all_tickers[sym] = {
                            'price': float(t.get('lastPrice', 0)),
                            'change': float(t.get('priceChangePercent', 0)),
                            'volume': float(t.get('quoteVolume', 0))
                        }
                log_system(f"Kraken: Loaded {len(all_tickers)} ticker prices")
            except Exception as e:
                log_warn(f"Kraken batch ticker fetch failed: {e}")
                all_tickers = {}

            # Skip fiat/stablecoins - these are not tradeable positions
            SKIP_ASSETS = {'ZUSD', 'USD', 'USDC', 'USDT', 'ZEUR', 'EUR', 'ZGBP', 'GBP', 'KFEE', 'FEE'}
            
            active_count = 0
            
            for asset, qty in balances.items():
                try:
                    qty = float(qty)
                except: 
                    continue
                if qty <= 0: 
                    continue
                
                # Skip fiat/stablecoins
                if asset in SKIP_ASSETS or asset.replace('Z', '').replace('X', '') in SKIP_ASSETS:
                    continue
                
                # ═══════════════════════════════════════════════════════════════
                # 🔍 FIND PRICE: Try multiple pair formats (Kraken naming is weird)
                # ═══════════════════════════════════════════════════════════════
                current_price = 0.0
                found_pair = None
                
                # Normalize asset name (XXRP -> XRP, XETH -> ETH)
                clean_asset = asset
                if asset.startswith('XX') and len(asset) > 2:
                    clean_asset = asset[2:]
                elif asset.startswith('X') and len(asset) == 4:
                    clean_asset = asset[1:]
                
                # Try various pair formats to find price
                pair_candidates = [
                    f"{asset}USD", f"{clean_asset}USD",
                    f"{asset}USDT", f"{clean_asset}USDT", 
                    f"{asset}USDC", f"{clean_asset}USDC",
                    f"X{clean_asset}ZUSD", f"XX{clean_asset}ZUSD"
                ]
                
                for pair in pair_candidates:
                    if pair in all_tickers and all_tickers[pair]['price'] > 0:
                        current_price = all_tickers[pair]['price']
                        found_pair = pair
                        break
                
                # Fallback: Search for any ticker containing our asset
                if current_price == 0:
                    for sym, data in all_tickers.items():
                        if clean_asset in sym and 'USD' in sym and data['price'] > 0:
                            current_price = data['price']
                            found_pair = sym
                            break
                
                # Last resort: Direct API call for this specific asset
                if current_price == 0:
                    try:
                        ticker = self.kraken.get_ticker(f"{clean_asset}USD")
                        observed_price = _finite_provider_number(
                            ticker.get('price') if isinstance(ticker, dict) else None,
                            positive=True,
                        )
                        if observed_price is not None:
                            current_price = observed_price
                            found_pair = f"{clean_asset}USD"
                    except:
                        pass
                
                if current_price == 0:
                    log_system(f"[Kraken] ⚠️ {asset}: No price found, skipping")
                    continue

                active_count += 1
                
                # ═══════════════════════════════════════════════════════════════
                # 💰 COST BASIS: Use kraken_client's built-in calculate_cost_basis
                # ═══════════════════════════════════════════════════════════════
                avg_entry = 0.0
                
                # Method 1: Use kraken_client's calculate_cost_basis (fetches trade history)
                try:
                    cost_data = self.kraken.calculate_cost_basis(found_pair or f"{clean_asset}USD")
                    if cost_data and cost_data.get('avg_entry_price', 0) > 0:
                        avg_entry = cost_data['avg_entry_price']
                        log_system(f"[Kraken] {asset}: Cost basis from trades: ${avg_entry:.4f}")
                except Exception as e:
                    pass
                
                # Method 2: Try ledger-based calculation if trades didn't work
                if avg_entry == 0:
                    try:
                        ledgers = self.kraken.get_ledgers(ofs=0)
                        avg_entry = self._calculate_kraken_cost_from_ledger(asset, ledgers)
                        if avg_entry > 0:
                            log_system(f"[Kraken] {asset}: Cost basis from ledger: ${avg_entry:.4f}")
                    except:
                        pass
                
                if avg_entry == 0:
                    value = qty * current_price
                    log_system(f"[Kraken] 👁️ {asset}: {qty:.6f} @ ${current_price:.4f} (${value:.2f}) | Cost Unknown -> HOLDING SAFE")
                    continue
                
                pnl = (current_price - avg_entry) * qty
                percent = ((current_price - avg_entry) / avg_entry) * 100 if avg_entry > 0 else 0
                
                log_queen(f"[Kraken] {found_pair or asset} | Entry: ${avg_entry:.4f} | Curr: ${current_price:.4f} | PnL: ${pnl:.2f} ({percent:+.2f}%)")
                
                # ═══════════════════════════════════════════════════════════════
                # 🔩 HARMONIC FIELD: Add node to liquid aluminium field
                # ═══════════════════════════════════════════════════════════════
                if self.harmonic_field:
                    node = self.harmonic_field.add_or_update_node(
                        exchange='kraken',
                        symbol=clean_asset,
                        current_price=current_price,
                        entry_price=avg_entry,
                        quantity=qty,
                        asset_class='crypto'
                    )
                    log_harmonic(f"[Kraken] {clean_asset} → {node.frequency:.1f}Hz | Amp: {node.amplitude:.3f} | {node.state.value}")
                
                self._evaluate_and_kill(
                    exchange="Kraken",
                    symbol=found_pair or f"{clean_asset}USD",
                    pnl=pnl,
                    position_id=asset,
                    qty=qty,
                    client_ref=self.kraken,
                    close_func=self._close_kraken,
                    entry_price=avg_entry,
                    current_price=current_price
                )

            if active_count == 0:
                log_system("Kraken: No active crypto positions.")
            else:
                log_system(f"Kraken: Scanned {active_count} positions.")

        except Exception as e:
            log_warn(f"Kraken Scan Failed: {e}")
            import traceback
            traceback.print_exc()

    def _calculate_kraken_cost_from_ledger(self, asset, ledgers):
        """Reconstruct Cost Basis from Kraken Ledger Entries (Trades + Conversions)."""
        # Ledger format: {id: {refid, time, type, asset, amount, fee, balance}}
        if not ledgers: return 0.0
        
        # Group by RefID to pair Asset Buy/Receive with USD Spend/Sell
        groups = {}
        for lid, entry in ledgers.items():
            # Include 'trade', 'spend', 'receive' (conversions), 'transfer', 'margin'
            # Note: Kraken Conversions usually show as 'spend'/'receive' or 'trade'.
            if entry['type'] not in ['trade', 'spend', 'receive', 'transfer', 'margin']: continue
            
            refid = entry['refid']
            if refid not in groups: groups[refid] = []
            groups[refid].append(entry)
            
        total_vol = 0.0
        total_cost = 0.0
        
        for refid, entries in groups.items():
            # Look for Positive Asset amount and Negative Currency amount
            asset_change = 0.0
            cost_change = 0.0
            
            for e in entries:
                e_asset = e['asset']
                amt = float(e['amount'])
                
                # Check if asset matches loosely (X/Z prefixes)
                # Asset might be XXRP, ZUSD, or just XRP, USD
                # Need robust normalizing
                is_target_asset = False
                if e_asset == asset: is_target_asset = True
                elif e_asset == f"X{asset}": is_target_asset = True
                elif asset.startswith('X') and e_asset == asset[1:]: is_target_asset = True
                elif e_asset.replace('X','').replace('Z','') == asset.replace('X','').replace('Z',''): is_target_asset = True
                
                if is_target_asset:
                    if amt > 0: asset_change = amt # Received/Bought
                    # We currently ignore Sells/Spends for Entry Price calc (FIFO assumption not implemented, just Avg Buy)
                    
                
                # Check if it's the Quote (USD/EUR/USDT)
                is_quote = False
                if e_asset in ['ZUSD', 'USD', 'USDT', 'ZEUR', 'EUR', 'XXBT', 'XBT', 'ZGBP', 'GBP']:
                    if e_asset not in [asset, f"X{asset}", f"XX{asset}"]: # Ensure accurate quote identification
                         is_quote = True
                
                if is_quote:
                    if amt < 0: cost_change += abs(amt) # Spent Money

            # If we bought/received Asset and spent Money
            if asset_change > 0 and cost_change > 0:
                total_vol += asset_change
                total_cost += cost_change
            
        if total_vol == 0: return 0.0
        return total_cost / total_vol

    def _calculate_kraken_cost_from_trades(self, asset, trades, pair_guess):
        """Reconstruct Cost Basis from Kraken Trade History (Cached)."""
        if not trades: return 0.0
        
        # Normalize asset for matching (e.g. XXRP -> XRP)
        search_asset = asset
        if asset.startswith('X') and len(asset) > 3 and not asset.startswith('XX'):
            search_asset = asset[1:] # XETH -> ETH
        elif asset.startswith('XX'):
            search_asset = asset[2:] # XXRP -> XRP

        total_qty = 0.0
        total_cost = 0.0
        
        # Sort trades by time (oldest first)
        sorted_trades = sorted(trades.items(), key=lambda x: x[1].get('time', 0))
        
        found_any = False
        
        for tid, t in sorted_trades:
            pair = t.get('pair', '')
            t_type = t.get('type', '')
            vol = float(t.get('vol', 0))
            cost = float(t.get('cost', 0))
            price = float(t.get('price', 0))
            
            # loose match
            if search_asset in pair or asset in pair:
                found_any = True
                if t_type == 'buy':
                    total_qty += vol
                    total_cost += cost
                elif t_type == 'sell':
                    total_qty -= vol
                    # Reduce cost basis proportionally
                    if total_qty > 0:
                        avg_price = total_cost / (total_qty + vol)
                        total_cost = total_qty * avg_price
                    else:
                        total_qty = 0
                        total_cost = 0

        if total_qty <= 0: return 0.0
        return total_cost / total_qty


    def _evaluate_and_kill(
        self,
        exchange,
        symbol,
        pnl,
        position_id,
        qty,
        client_ref,
        close_func,
        entry_price=0,
        current_price=0,
        asset_class="",
        *,
        position_receipt=None,
        opportunity_receipt=None,
        now=None,
    ):
        # Format qty to avoid scientific notation if it's a float
        qty_display = f"{qty:.8f}".rstrip('0').rstrip('.') if isinstance(qty, float) else str(qty)
        if qty_display == "": qty_display = "0"
        
        # Asset class icon for better visibility
        asset_icon = "📈" if asset_class == 'us_equity' else "🪙" if asset_class == 'crypto' else ""
        
        log_queen(f"[{exchange}] {asset_icon} Active Thread: {symbol} | PnL: ${pnl:.2f} | Qty: {qty_display}")
        
        if pnl <= 0:
            log_queen(f"Assessment: NEGATIVE ({pnl:.2f}). The hive advises patience.")
            return

        pending_key = (str(exchange).strip().lower(), str(position_id).strip())
        pending_store = getattr(self, "_pending_reconciliations", None)
        if not isinstance(pending_store, dict):
            pending_store = {}
            self._pending_reconciliations = pending_store
        if pending_key in pending_store:
            pending = pending_store[pending_key]
            log_warn(
                f"[{exchange}] {symbol}: provider submission remains pending reconciliation; "
                "duplicate close suppressed"
            )
            return pending

        action_evidence = _classify_action_evidence(
            position_receipt,
            opportunity_receipt,
            venue=exchange,
            symbol=symbol,
            position_id=position_id,
            quantity=qty,
            pnl=pnl,
            entry_price=entry_price,
            current_price=current_price,
            now=now,
        )
        if action_evidence["eligible_for_action"] is not True:
            log_warn(
                f"[{exchange}] {symbol}: autonomous close withheld "
                f"({action_evidence['reason']})"
            )
            return _execution_result(
                venue=_normalized_venue(exchange),
                status="no_data",
                reason=action_evidence["reason"],
                receipt=action_evidence,
                symbol=_normalized_symbol(symbol) or None,
                side="SELL",
            )

        log_queen("Assessment: PROFITABLE. The hive demands harvest.")
        
        # ═══════════════════════════════════════════════════════════════
        # 🗳️ Dr. Auris Throne MANDATORY Validation (2 VOTES REQUIRED)
        # ═══════════════════════════════════════════════════════════════
        log_auris(f"🔮 Consulting Dr. Auris Throne for {symbol} SELL decision...")
        log_auris(f"📊 Context: {exchange} | Entry: ${entry_price:.4f} | Current: ${current_price:.4f}")
        
        # Call Dr. Auris Throne API for validation - NO FALLBACK
        validation_result = self._validate_with_dr_auris(
            exchange=exchange,
            symbol=symbol,
            pnl=pnl,
            entry_price=entry_price,
            current_price=current_price,
            qty=qty,
            side="SELL"
        )
        
        if not validation_result['approved']:
            reason = validation_result.get('reasoning', validation_result.get('reason', 'Unknown'))
            votes = validation_result.get('votes_for', 0)
            log_auris(f"❌ VALIDATION REJECTED: {reason}")
            log_auris(f"   Votes received: {votes}/2 required")
            log_queen(f"Dr. Auris Throne blocked SELL. Queen stands down.")
            return
        
        log_auris(f"✅ DUAL VOTE APPROVED at {validation_result['timestamp']}")
        log_auris(f"Reasoning: {validation_result['reasoning']}")
        log_auris(f"Combined Confidence: {validation_result['confidence']:.2%}")
        log_auris(f"Votes: {validation_result.get('votes_for', 2)}/2 FOR")
        
        # Sniper Exec
        log_sniper(f"Target Acquired: {symbol}. Safety DISENGAGED.")
        log_sniper("TAKING THE SHOT... (No Confirmation Required)")
        
        try:
            provider_receipt = close_func(position_id, qty, symbol)
            execution = _classify_terminal_fill_receipt(
                provider_receipt,
                exchange,
                now=now,
                submission_attempted=True,
                expected_symbol=symbol,
                expected_side="SELL",
                expected_quantity=qty,
            )
        except Exception:
            execution = _execution_result(
                venue=str(exchange).strip().lower(),
                status="pending_reconciliation",
                reason="provider_submission_outcome_unproven",
            )

        if execution["status"] == "pending_reconciliation":
            pending_store[pending_key] = execution
        elif execution["success"]:
            pending_store.pop(pending_key, None)
        
        if execution["success"]:
            log_sniper(f"💥 BOOM. {symbol} Eliminated. Profit Realized.")
            log_queen("Harvest complete.")
            return execution
        if execution["status"] == "pending_reconciliation":
            log_warn(
                f"[{exchange}] {symbol}: close submitted or ambiguous; "
                f"pending provider reconciliation ({execution['reason']})"
            )
        elif execution["status"] == "not_submitted":
            log_warn(f"[{exchange}] {symbol}: close not submitted ({execution['reason']})")
        else:
            log_sniper(f"❌ MISSED SHOT on {symbol}.")
        return execution

    def _validate_with_dr_auris(self, exchange, symbol, pnl, entry_price, current_price, qty, side="SELL"):
        """
        Validate trade with Dr. Auris Throne API (DigitalOcean LLM).
        MANDATORY - NO FALLBACK. Queen MUST get Dr. Auris confirmation.
        Requires 2 VOTES (dual confirmation) for any trade decision.
        Returns dict with approval status, reasoning, timestamp, and confidence.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # CRITICAL: Dr. Auris MUST be configured - NO TRADING WITHOUT HIM
        if not self.dr_auris.enabled:
            log_auris("🚫 Dr. Auris Throne API NOT CONFIGURED - TRADE BLOCKED")
            log_auris("The Queen CANNOT trade without Dr. Auris insight!")
            return {
                'approved': False,
                'reasoning': 'Dr. Auris API not configured - Queen refuses to trade blind',
                'confidence': 0.0,
                'timestamp': timestamp,
                'method': 'blocked_no_api',
                'votes': 0
            }
        
        # Build context for LLM
        context = {
            'exchange': exchange,
            'symbol': symbol,
            'pnl': pnl,
            'entry_price': entry_price,
            'current_price': current_price,
            'qty': qty,
            'side': side,
            'profit_percent': ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
        }
        
        # ═══════════════════════════════════════════════════════════════
        # 🗳️ DUAL VOTE SYSTEM - 2 CONFIRMATIONS REQUIRED
        # ═══════════════════════════════════════════════════════════════
        votes_for = 0
        votes_against = 0
        all_reasoning = []
        all_confidence = []
        max_retries = 5  # More retries for rate limit recovery
        base_delay = 10  # Longer base delay for rate limits
        
        for vote_num in range(1, 3):  # Need 2 votes
            log_auris(f"🗳️ Requesting VOTE {vote_num}/2 from Dr. Auris Throne...")
            
            vote_obtained = False
            retry_delay = base_delay
            
            for attempt in range(1, max_retries + 1):
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    advice = loop.run_until_complete(
                        self.dr_auris.ask_trading_decision(
                            symbol=symbol,
                            side=side,
                            context=context,
                            queen_confidence=0.85
                        )
                    )
                    loop.close()
                    
                    if advice and advice.recommendation:
                        vote_obtained = True
                        if advice.recommendation == "PROCEED":
                            votes_for += 1
                            log_auris(f"   ✅ Vote {vote_num}: PROCEED (Confidence: {advice.confidence:.0%})")
                        else:
                            votes_against += 1
                            log_auris(f"   ❌ Vote {vote_num}: HOLD/REJECT (Confidence: {advice.confidence:.0%})")
                        
                        all_reasoning.append(advice.reasoning)
                        all_confidence.append(advice.confidence)
                        break  # Got valid vote, exit retry loop
                        
                except Exception as e:
                    log_warn(f"   ⚠️ Vote {vote_num} attempt {attempt}/{max_retries} failed: {e}")
                    if attempt < max_retries:
                        log_auris(f"   ⏳ Rate limited - waiting {retry_delay}s before retry (attempt {attempt+1}/{max_retries})...")
                        time.sleep(retry_delay)
                        retry_delay = min(retry_delay * 2, 60)  # Exponential backoff, cap at 60s
            
            if not vote_obtained:
                log_auris(f"   🚫 Vote {vote_num} FAILED after {max_retries} attempts - BLOCKING TRADE")
                log_auris(f"   👑 Queen says: I REFUSE to act without Dr. Auris insight!")
                return {
                    'approved': False,
                    'reasoning': f'Dr. Auris vote {vote_num} failed - Queen refuses partial insight',
                    'confidence': 0.0,
                    'timestamp': timestamp,
                    'method': 'blocked_vote_failed',
                    'votes': vote_num - 1
                }
            
            # Longer delay between votes to avoid rate limiting
            if vote_num < 2:
                log_auris(f"   ⏳ Waiting 15s before requesting vote 2...")
                time.sleep(15)
        
        # ═══════════════════════════════════════════════════════════════
        # 🏛️ VOTE TALLY - Both votes must be PROCEED
        # ═══════════════════════════════════════════════════════════════
        avg_confidence = sum(all_confidence) / len(all_confidence) if all_confidence else 0
        combined_reasoning = " | ".join(all_reasoning)
        
        log_auris(f"🏛️ VOTE RESULT: {votes_for} FOR, {votes_against} AGAINST")
        
        # BOTH votes must approve (unanimous)
        approved = (votes_for == 2)
        
        if approved:
            log_auris(f"✅ UNANIMOUS APPROVAL - Dr. Auris grants permission to {side}")
        else:
            log_auris(f"🚫 NOT UNANIMOUS - Dr. Auris BLOCKS {side} (need 2/2 votes)")
        
        return {
            'approved': approved,
            'reasoning': combined_reasoning,
            'confidence': avg_confidence,
            'timestamp': timestamp,
            'method': 'dr_auris_dual_vote',
            'votes_for': votes_for,
            'votes_against': votes_against,
            'risk_flags': []
        }
    
    # --- Close Functions ---
    def _close_capital(self, deal_id, qty, symbol):
        close_position = getattr(self.capital, "close_position", None)
        if callable(close_position):
            return close_position(deal_id)
        return self.capital._request('DELETE', f'/positions/{deal_id}')

    def _close_alpaca(self, symbol, qty, _unused):
        # Close entire position for symbol
        return self.alpaca._request('DELETE', f'/v2/positions/{symbol}')

    def _close_binance(self, asset, qty, symbol):
        # Sell entire balance of Asset into USDT
        # symbol is like 'BTCUSDT'
        return self.binance.place_market_order(symbol, "SELL", quantity=qty)

    def _close_kraken(self, asset, qty, symbol):
        # Need to construct sell order for pair
        # symbol here is 'XXRPUSD' or similar
        # Kraken quantity must be string often? Client handles it.
        # Use place_market_order directly as execute_trade is async wrapper
        submission = self.kraken.place_market_order(symbol, "sell", qty)
        submitted_state = _classify_terminal_fill_receipt(
            submission,
            "kraken",
            submission_attempted=True,
        )
        order_id = submitted_state.get("order_id")
        if submitted_state["status"] != "pending_reconciliation" or order_id is None:
            return submission

        # One read-back is reconciliation, not an order retry. Never poll or
        # resubmit from this path; an unfilled result is latched by the caller.
        get_order_status = getattr(self.kraken, "get_order_status", None)
        if not callable(get_order_status):
            return submission
        try:
            reconciliation = get_order_status(order_id)
        except Exception:
            return submission
        if not isinstance(reconciliation, dict):
            return submission
        reconciled_state = _classify_terminal_fill_receipt(
            reconciliation,
            "kraken",
            submission_attempted=True,
        )
        if reconciled_state["success"] or reconciled_state.get("order_id") is not None:
            return reconciliation
        return submission

if __name__ == "__main__":
    chain = UnifiedKillChain()
    chain.run_loop()
