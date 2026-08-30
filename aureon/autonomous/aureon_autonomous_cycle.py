import argparse
import math
import time
import sys
from collections.abc import Mapping
from typing import Any, Optional

# ==========================================
# 🔄 AUREON AUTONOMOUS CYCLE (Infinite Loop)
# ==========================================
# Phase 1: Energy Scan (Balance Check)
# Phase 2: Quantum Selection (Target Acquisition)
# Phase 3: Deployment (Buy Execution)
# Phase 4: Harvest Watch (PnL Monitoring)
# Phase 5: Kinetic Strike (Sell Execution)
# ==========================================

# Strategy configuration. These are policy parameters, never provider data.
TARGET_ASSET = "COPPER"
TRADE_SIZE = 0.01
PROFIT_TARGET_GBP = 0.02
MIN_BALANCE_THRESHOLD = 20.0  # GBP
LOOP_DELAY = 10  # Seconds
MAX_RECEIPT_AGE_SECONDS = 300.0
LIVE_CONFIRMATION = "AUTHORIZE_RECEIPTED_CAPITAL_CYCLE"


def _finite(value: Any, *, positive: bool = False, nonnegative: bool = False) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    if positive and number <= 0.0:
        return None
    if nonnegative and number < 0.0:
        return None
    return number


def _receipt_timestamp(value: Any) -> Optional[float]:
    return _finite(value, positive=True)


def _fresh(source_timestamp: Any, received_at: Any, *, now: Optional[float] = None) -> bool:
    source = _receipt_timestamp(source_timestamp)
    received = _receipt_timestamp(received_at)
    reference = time.time() if now is None else now
    return bool(
        source is not None
        and received is not None
        and math.isfinite(reference)
        and source <= received + 5.0
        and received <= reference + 5.0
        and reference - source <= MAX_RECEIPT_AGE_SECONDS
        and reference - received <= MAX_RECEIPT_AGE_SECONDS
    )


def _no_data(reason: str, *, status: str = "no_data", **context: Any) -> dict[str, Any]:
    receipt = {
        "status": status,
        "data_status": "no_data",
        "truth_status": "no_data",
        "reason": reason,
        "source_id": None,
        "source_timestamp": None,
        "received_at": time.time(),
        "receipt_id": None,
        "generated_values": False,
        "actionable": False,
        "eligible_for_state": False,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
    }
    receipt.update(context)
    return receipt

# Logging Personas
def log_queen(msg):
    print(f"👑 [QUEEN] {msg}")
    sys.stdout.flush()

def log_auris(msg):
    print(f"⚕️ [DR. AURIS] {msg}")
    sys.stdout.flush()

def log_sniper(msg):
    print(f"🎯 [SNIPER] {msg}")
    sys.stdout.flush()

def log_system(msg):
    print(f"🖥️ [SYSTEM] {msg}")
    sys.stdout.flush()

def log_profit(msg):
    print(f"💰 [PROFIT GATE] {msg}")
    sys.stdout.flush()

class AutonomousAgent:
    def __init__(
        self,
        client: Any,
        *,
        target_asset: str = TARGET_ASSET,
        trade_size: float = TRADE_SIZE,
        profit_target_gbp: float = PROFIT_TARGET_GBP,
        min_balance_threshold: float = MIN_BALANCE_THRESHOLD,
        live_actions_enabled: bool = False,
    ):
        if client is None:
            raise ValueError("an explicitly configured Capital client is required")
        normalized_asset = str(target_asset or "").strip().upper()
        normalized_trade_size = _finite(trade_size, positive=True)
        normalized_profit_target = _finite(profit_target_gbp, positive=True)
        normalized_min_balance = _finite(min_balance_threshold, nonnegative=True)
        if (
            not normalized_asset
            or normalized_trade_size is None
            or normalized_profit_target is None
            or normalized_min_balance is None
        ):
            raise ValueError("finite strategy policy parameters are required")
        self.client = client
        self.target_asset = normalized_asset
        self.trade_size = normalized_trade_size
        self.profit_target_gbp = normalized_profit_target
        self.min_balance_threshold = normalized_min_balance
        self.live_actions_enabled = bool(live_actions_enabled)
        self.active_deal_id = None
        self.pending_deal_reference = None
        self.pending_action = None
        self.start_balance = None
        self.last_quote_receipt = None
        self.last_no_data = _no_data("not_started")

    @staticmethod
    def _field(value: Any, name: str, default: Any = None) -> Any:
        if isinstance(value, Mapping) and name in value:
            return value.get(name)
        return getattr(value, name, default)

    def _set_no_data(self, reason: str, **context: Any) -> None:
        self.last_no_data = _no_data(reason, **context)

    @classmethod
    def _terminal_fill(cls, receipt: Any, *, expected_side: Optional[str] = None) -> Optional[dict[str, Any]]:
        if not isinstance(receipt, Mapping):
            return None
        side = str(receipt.get("side") or "").strip().upper()
        provider_order_id = str(receipt.get("provider_order_id") or "").strip()
        provider_deal_id = str(receipt.get("provider_deal_id") or "").strip()
        source_id = str(receipt.get("source_id") or "").strip()
        quantity = _finite(receipt.get("filled_qty"), positive=True)
        price = _finite(receipt.get("filled_avg_price"), positive=True)
        fee_amount = _finite(receipt.get("fee_amount"), nonnegative=True)
        fee_currency = str(receipt.get("fee_currency") or "").strip().upper()
        if (
            receipt.get("status") != "filled"
            or receipt.get("truth_status") != "real_observed"
            or receipt.get("generated_values") is not False
            or receipt.get("terminal_fill") is not True
            or receipt.get("terminal_fill_receipt_complete") is not True
            or receipt.get("eligible_for_state") is not True
            or receipt.get("eligible_for_pnl") is not True
            or receipt.get("eligible_for_learning") is not True
            or not provider_order_id
            or not provider_deal_id
            or not source_id
            or quantity is None
            or price is None
            or fee_amount is None
            or not fee_currency
            or not _fresh(receipt.get("source_timestamp"), receipt.get("received_at"))
            or (expected_side is not None and side != expected_side)
        ):
            return None
        return dict(receipt)

    def _reconcile_pending(self, *, expected_side: str) -> Optional[dict[str, Any]]:
        reference = str(self.pending_deal_reference or "").strip()
        if not reference or self.pending_action != expected_side:
            return None
        confirmation = self.client.confirm_order(reference)
        terminal = self._terminal_fill(confirmation, expected_side=expected_side)
        if terminal is None:
            self._set_no_data(
                "terminal_fee_complete_confirmation_pending",
                status="pending_reconciliation",
                pending_deal_reference=reference,
            )
            return None
        self.pending_deal_reference = None
        self.pending_action = None
        return terminal
        
    def connect(self):
        if not (getattr(self.client, "enabled", False) and getattr(self.client, "cst", None)):
            self._set_no_data("capital_client_not_authenticated")
            log_system("CRITICAL: Uplink Failed.")
            return False
        log_system("✅ Uplink Enforced. Shared Session Active.")
        return True

    def get_energy(self):
        """Phase 1: Energy Scan"""
        try:
            balances = self.client.get_account_balance()
            gbp_energy = _finite(self._field(balances, "GBP"), nonnegative=True)
            source_ids = list(self._field(balances, "source_ids") or [])
            if (
                self._field(balances, "truth_status") != "real_derived"
                or self._field(balances, "generated_values") is not False
                or not source_ids
                or not _fresh(
                    self._field(balances, "source_timestamp"),
                    self._field(balances, "received_at"),
                )
                or gbp_energy is None
            ):
                self._set_no_data("fresh_complete_gbp_balance_receipt_required")
                return None
            return gbp_energy
        except Exception as e:
            log_system(f"Energy Scan Error: {e}")
            self._set_no_data("balance_request_failed")
            return None

    def scan_reality(self):
        """Phase 2: Quantum Selection"""
        log_queen("Scanning reality branches for opportunity...")
        
        # In a full version, this would check multiple assets.
        # For this cycle, we focus on the proven timeline: COPPER.
        
        ticker = self.client.get_ticker(self.target_asset)
        price = _finite(self._field(ticker, "price"), positive=True)
        bid = _finite(self._field(ticker, "bid"), positive=True)
        ask = _finite(self._field(ticker, "ask"), positive=True)
        source_id = str(self._field(ticker, "source_id") or "").strip()
        
        if (
            self._field(ticker, "truth_status") == "real_derived"
            and self._field(ticker, "generated_values") is False
            and self._field(ticker, "action_eligible") is True
            and source_id
            and _fresh(
                self._field(ticker, "source_timestamp"),
                self._field(ticker, "received_at"),
            )
            and price is not None
            and bid is not None
            and ask is not None
            and ask >= bid
        ):
            self.last_quote_receipt = dict(ticker)
            log_auris(f"Harmonics detected on {self.target_asset} @ {price}")
            return True, price
        else:
            self.last_quote_receipt = None
            self._set_no_data("fresh_complete_tradeable_quote_receipt_required")
            log_auris(f"Void detected. {self.target_asset} has no actionable receipt.")
            return False, None

    def deploy_capital(self, price):
        """Phase 3: Deployment (Buy)"""
        log_queen(f"Authorizing deployment of capital into {self.target_asset}...")
        quote_price = _finite(self._field(self.last_quote_receipt, "price"), positive=True)
        requested_price = _finite(price, positive=True)
        if (
            self.last_quote_receipt is None
            or quote_price is None
            or requested_price is None
            or not math.isclose(quote_price, requested_price, rel_tol=1e-12, abs_tol=0.0)
            or not _fresh(
                self._field(self.last_quote_receipt, "source_timestamp"),
                self._field(self.last_quote_receipt, "received_at"),
            )
        ):
            self._set_no_data("fresh_quote_receipt_must_be_revalidated_before_submission")
            return False
        if not self.live_actions_enabled:
            self._set_no_data("live_actions_not_authorized", status="not_submitted")
            return False
        if self.pending_deal_reference:
            terminal = self._reconcile_pending(expected_side="BUY")
            if terminal is None:
                return False
            self.active_deal_id = terminal["provider_deal_id"]
            return True

        positions = self.client.get_positions()
        if positions:
            self._set_no_data("provider_visible_position_requires_terminal_fee_receipt_reconciliation")
            return False

        submission = self.client.place_market_order(
            self.target_asset,
            "BUY",
            self.trade_size,
        )
        terminal = self._terminal_fill(submission, expected_side="BUY")
        if terminal is not None:
            self.active_deal_id = terminal["provider_deal_id"]
            return True
        reference = str(self._field(submission, "dealReference") or "").strip()
        if reference:
            self.pending_deal_reference = reference
            self.pending_action = "BUY"
            self._set_no_data(
                "open_submission_pending_terminal_fee_complete_confirmation",
                status="pending_reconciliation",
                pending_deal_reference=reference,
            )
        else:
            self._set_no_data("open_submission_not_confirmed", status="not_submitted")
        return False

    def monitor_harvest(self):
        """Phase 4: Harvest Watch"""
        if not self.active_deal_id:
            return "NO_TARGET"

        get_positions = getattr(self.client, "get_positions_with_fees", None)
        positions = get_positions() if callable(get_positions) else self.client.get_positions()
        target_pos = None
        for row in positions or []:
            if not isinstance(row, Mapping):
                continue
            position = row.get("position")
            if isinstance(position, Mapping) and str(position.get("dealId") or "") == self.active_deal_id:
                target_pos = row
                break
        if target_pos is None:
            self._set_no_data("position_readback_missing_does_not_prove_close")
            return "NO_DATA"

        pnl_receipt = target_pos.get("current_pnl_receipt")
        if not isinstance(pnl_receipt, Mapping):
            self._set_no_data("fresh_actionable_provider_pnl_receipt_required")
            return "NO_DATA"
        upl = _finite(pnl_receipt.get("upl"))
        epic = str(pnl_receipt.get("epic") or "").strip().upper()
        currency = str(pnl_receipt.get("currency") or "").strip().upper()
        source_id = str(pnl_receipt.get("source_id") or "").strip()
        if (
            pnl_receipt.get("truth_status") not in {"real_observed", "real_derived"}
            or pnl_receipt.get("generated_values") is not False
            or pnl_receipt.get("action_eligible") is not True
            or not source_id
            or not epic
            or currency != "GBP"
            or upl is None
            or not _fresh(pnl_receipt.get("source_timestamp"), pnl_receipt.get("received_at"))
        ):
            self._set_no_data("fresh_actionable_provider_pnl_receipt_required")
            return "NO_DATA"

        log_profit(f"Monitoring {epic} | UnPnL: £{upl:.2f} | Target: >£{self.profit_target_gbp}")

        if upl >= self.profit_target_gbp:
            return "RIPE"
        elif upl < -2.0: # Safety valve (Stop Loss)
            return "ROTTEN"
        else:
            return "GROWING"

    def execute_kill(self):
        """Phase 5: Kinetic Strike (Sell)"""
        if not self.live_actions_enabled:
            self._set_no_data("live_actions_not_authorized", status="not_submitted")
            return False
        if not self.active_deal_id:
            self._set_no_data("terminal_entry_fill_required_before_close", status="not_submitted")
            return False
        log_queen("Profit target acquired. EXECUTE.")
        log_sniper(f"Locking target {self.active_deal_id}...")

        if self.pending_deal_reference:
            terminal = self._reconcile_pending(expected_side="SELL")
            if terminal is None:
                return False
            if terminal.get("provider_deal_id") != self.active_deal_id:
                self._set_no_data("close_confirmation_deal_id_mismatch")
                return False
            self.active_deal_id = None
            return True

        submission = self.client.close_position(self.active_deal_id)
        terminal = self._terminal_fill(submission, expected_side="SELL")
        if terminal is not None:
            if terminal.get("provider_deal_id") != self.active_deal_id:
                self._set_no_data("close_confirmation_deal_id_mismatch")
                return False
            self.active_deal_id = None
            return True
        reference = str(self._field(submission, "dealReference") or "").strip()
        if reference:
            self.pending_deal_reference = reference
            self.pending_action = "SELL"
            self._set_no_data(
                "close_submission_pending_terminal_fee_complete_confirmation",
                status="pending_reconciliation",
                pending_deal_reference=reference,
            )
        else:
            self._set_no_data("close_submission_not_confirmed", status="not_submitted")
        return False

    def run(self):
        if not self.live_actions_enabled:
            self._set_no_data("live_actions_not_authorized", status="not_submitted")
            return self.last_no_data
        if not self.connect():
            return self.last_no_data

        print("\n🔄 ENABLED: INFINITE PROFIT CYCLE")
        print("Press Ctrl+C to stop the machine.\n")

        self.start_balance = self.get_energy()
        if self.start_balance is None:
            return self.last_no_data
        log_system(f"Initial Energy: £{self.start_balance:.2f}")

        try:
            while True:
                if self.pending_deal_reference:
                    action = str(self.pending_action or "")
                    terminal = self._reconcile_pending(expected_side=action)
                    if terminal is not None:
                        if action == "BUY":
                            self.active_deal_id = terminal["provider_deal_id"]
                        elif action == "SELL" and terminal.get("provider_deal_id") == self.active_deal_id:
                            self.active_deal_id = None
                    time.sleep(LOOP_DELAY)
                    continue

                energy = self.get_energy()
                if energy is None:
                    time.sleep(LOOP_DELAY)
                    continue

                # === STATE: HOLDING ===
                if self.active_deal_id:
                    log_system("Current State: HOLDING (terminal fill proven)")
                    status = self.monitor_harvest()

                    if status == "RIPE":
                        log_auris("Harmonic peak reached. Collapsing wave function.")
                        closed = self.execute_kill()
                        if closed:
                            new_energy = self.get_energy()
                            if new_energy is not None and self.start_balance is not None:
                                diff = new_energy - self.start_balance
                                log_profit(f"Cycle Complete. Net System Change: £{diff:+.2f}")
                    elif status == "ROTTEN":
                        log_queen("Rot detected. Purging timeline.")
                        self.execute_kill()
                    else:
                        log_queen("No fresh actionable PnL receipt; holding state unchanged.")
                        time.sleep(LOOP_DELAY)

                # === STATE: HUNTING ===
                else:
                    log_system("Current State: HUNTING")

                    if energy < self.min_balance_threshold:
                        log_system(f"⚠️ Low Energy (£{energy}). Buying capability compromised.")
                        time.sleep(30)
                        continue

                    valid, price = self.scan_reality()
                    if valid:
                        success = self.deploy_capital(price)
                        if success:
                            log_queen("Timeline anchored. Resetting cycle.")
                        else:
                            log_system("Deployment failed. Retrying shortly.")
                            time.sleep(5)
                    else:
                        time.sleep(10)
                
                time.sleep(2)

        except KeyboardInterrupt:
            log_system("🛑 Manual Override. Safety Systems Engaged.")
        return self.last_no_data


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Receipt-gated Capital autonomous cycle")
    parser.add_argument("--live-actions", action="store_true")
    parser.add_argument("--confirmation")
    parser.add_argument("--target")
    parser.add_argument("--trade-size", type=float)
    parser.add_argument("--profit-target-gbp", type=float)
    parser.add_argument("--min-balance-gbp", type=float)
    args = parser.parse_args(argv)
    if not args.live_actions:
        print("NO_DATA: default invocation is inert; no provider client was constructed.")
        return 0
    if args.confirmation != LIVE_CONFIRMATION:
        print("NO_DATA: exact live confirmation token is required.")
        return 2
    if (
        not args.target
        or args.trade_size is None
        or args.profit_target_gbp is None
        or args.min_balance_gbp is None
    ):
        print("NO_DATA: explicit target, size, profit target, and minimum balance are required.")
        return 2

    from aureon.exchanges.capital_client import CapitalClient

    agent = AutonomousAgent(
        CapitalClient(),
        target_asset=args.target,
        trade_size=args.trade_size,
        profit_target_gbp=args.profit_target_gbp,
        min_balance_threshold=args.min_balance_gbp,
        live_actions_enabled=True,
    )
    agent.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
