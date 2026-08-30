import logging
import math
import time
from dataclasses import dataclass, field
from collections.abc import Mapping
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Define preferred stablecoins in order of preference
PREFERRED_STABLES = ["USDC", "USDT", "ZUSD", "USD"]

@dataclass
class HarvestResult:
    """Result of a single harvest operation."""
    success: bool
    amount_harvested_usd: Optional[float]
    stablecoin_received: Optional[float]
    stablecoin_asset: Optional[str]
    exchange: str
    message: str
    trade_id: Optional[str] = None
    status: str = "no_data"
    data_status: str = "no_data"
    truth_status: str = "no_data"
    source_id: Optional[str] = None
    source_timestamp: Optional[float] = None
    received_at: Optional[float] = None
    receipt_id: Optional[str] = None
    generated_values: bool = False
    eligible_for_action: bool = False
    eligible_for_external_action: bool = False
    eligible_for_accounting: bool = False
    eligible_for_learning: bool = False

@dataclass
class SmartHarvestManager:
    """
    Manages the 10-9-1 profit harvesting and reinvestment loop.

    This system intercepts realized profits, splits them according to the 10-9-1 model,
    converts the harvested portion to stablecoins, and manages a treasury for future
    reinvestment.
    """
    barter_navigator: 'BarterNavigator'
    exchange_client: 'UnifiedExchangeClient' # A unified interface for all exchanges
    
    harvest_rate: float = 0.10  # Default 10% harvest rate
    reinvestment_threshold_usd: float = 10.0  # Minimum treasury amount to trigger reinvestment
    
    # Internal state
    _last_harvest_time: float = field(default=0.0, repr=False)
    _active_harvests: Dict[str, HarvestResult] = field(default_factory=dict, repr=False)

    def __post_init__(self):
        logger.info(
            f"SmartHarvestManager initialized. Harvest Rate: {self.harvest_rate*100}%, "
            f"Reinvestment Threshold: ${self.reinvestment_threshold_usd}"
        )

    @staticmethod
    def _no_data(reason: str, *, exchange: str = "") -> HarvestResult:
        """Return a numeric-free result that cannot be mistaken for a conversion."""
        return HarvestResult(
            success=False,
            amount_harvested_usd=None,
            stablecoin_received=None,
            stablecoin_asset=None,
            exchange=str(exchange or ""),
            message=reason,
        )

    @staticmethod
    def _field(receipt: Any, name: str, default: Any = None) -> Any:
        if isinstance(receipt, Mapping):
            return receipt.get(name, default)
        return getattr(receipt, name, default)

    @classmethod
    def _verified_profit(cls, outcome: Any) -> Optional[Tuple[float, str, str]]:
        """Accept only a fresh terminal execution/accounting receipt."""
        try:
            net_profit = float(cls._field(outcome, "net_profit_usd"))
            source_timestamp = float(cls._field(outcome, "source_timestamp"))
            received_at = float(cls._field(outcome, "received_at"))
        except (TypeError, ValueError):
            return None
        now = time.time()
        order_id = str(
            cls._field(outcome, "provider_order_id")
            or cls._field(outcome, "order_id")
            or ""
        ).strip()
        source_id = str(cls._field(outcome, "source_id") or "").strip()
        receipt_id = str(cls._field(outcome, "receipt_id") or "").strip()
        from_asset = str(cls._field(outcome, "to_asset") or "").strip().upper()
        exchange = str(cls._field(outcome, "exchange") or "").strip().lower()
        if (
            cls._field(outcome, "is_win") is not True
            or cls._field(outcome, "data_status") != "live"
            or cls._field(outcome, "truth_status") not in {"real_observed", "real_derived"}
            or cls._field(outcome, "generated_values") is not False
            or cls._field(outcome, "fill_receipt_complete") is not True
            or cls._field(outcome, "eligible_for_accounting") is not True
            or not all(math.isfinite(value) for value in (net_profit, source_timestamp, received_at, now))
            or net_profit <= 0.01
            or not source_id
            or not receipt_id
            or not order_id
            or not from_asset
            or not exchange
            or source_timestamp > received_at + 5.0
            or received_at > now + 5.0
            or now - source_timestamp > 300.0
            or now - received_at > 300.0
        ):
            return None
        return net_profit, from_asset, exchange

    def process_profit(self, outcome: 'WinOutcome', portfolio: 'RealPortfolioSnapshot') -> Optional[HarvestResult]:
        """
        Processes a winning trade, harvests profit, and updates the portfolio.
        This is the primary entry point for the harvesting process.
        """
        if not self._field(outcome, "is_win", False):
            return None

        verified_profit = self._verified_profit(outcome)
        if verified_profit is None:
            return self._no_data(
                "fresh_terminal_profit_receipt_required",
                exchange=str(self._field(outcome, "exchange") or ""),
            )
        net_profit_usd, from_asset, exchange = verified_profit

        profit_to_harvest = net_profit_usd * self.harvest_rate
        profit_to_compound = net_profit_usd - profit_to_harvest

        logger.info(
            f"Processing receipted profit of ${net_profit_usd:.4f}. "
            f"Harvesting ${profit_to_harvest:.4f} (10%), Compounding ${profit_to_compound:.4f} (90%)."
        )

        # The allocation equation is advisory until a conversion adapter provides
        # a complete provider receipt. This module never submits an order itself.
        harvest_result = self._convert_to_stablecoin(
            profit_to_harvest, 
            from_asset=from_asset,
            exchange=exchange,
        )

        logger.info("Harvest not submitted: %s", harvest_result.message)

        return harvest_result

    def _convert_to_stablecoin(self, amount_usd: float, from_asset: str, exchange: str) -> HarvestResult:
        """
        Finds the best path to a preferred stablecoin and executes the conversion.
        """
        return self._no_data(
            "conversion_adapter_with_terminal_provider_receipt_required",
            exchange=exchange,
        )

    def check_reinvestment_opportunities(self, portfolio: 'RealPortfolioSnapshot'):
        """
        Checks if the treasury has enough funds and if there are opportunities to deploy capital.
        """
        return self._no_data(
            "reinvestment_requires_fresh_treasury_and_terminal_execution_receipts"
        )
