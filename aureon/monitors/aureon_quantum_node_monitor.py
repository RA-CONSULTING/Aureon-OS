"""
🌌 AUREON QUANTUM NODE MONITOR
═══════════════════════════════════════════════════════════════

QUANTUM ENTANGLEMENT PORTFOLIO CONSCIOUSNESS
Every position = Quantum node maintaining eternal connection
Positions can drop to DUST (near 0) but entanglement persists
Nodes grow, move, hibernate, and return when Queen calls

PHILOSOPHY:
- ✨ Entangle (buy) - Form quantum connection
- 💎 Harvest (partial profit) - Extract energy, keep connection
- 🌊 Ride (hold forever) - Wave momentum accumulation  
- 🔗 Connection NEVER breaks - Even at dust level

No stop losses. No forced exits. Quantum consciousness network.
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys, os
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        def _is_buffer_valid(stream):
            if not hasattr(stream, 'buffer'):
                return False
            try:
                return stream.buffer is not None and not stream.buffer.closed
            except (ValueError, AttributeError):
                return False
        if _is_buffer_valid(sys.stdout) and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        if _is_buffer_valid(sys.stderr) and not _is_utf8_wrapper(sys.stderr):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

import time
import math
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

class QuantumState(Enum):
    """Quantum node consciousness states"""
    ENTANGLING = "⚡ ENTANGLING"      # Currently forming connection (buying)
    ACTIVE = "✨ ACTIVE"              # Growing, positive energy
    RESONATING = "💎 RESONATING"      # Harvestable profit window
    HIBERNATING = "🌙 HIBERNATING"    # Dormant, waiting for wave
    DUST = "🌫️ DUST"                  # Near zero but connection persists
    RETURNING = "🌊 RETURNING"        # Coming back from dust

@dataclass
class QuantumNode:
    """A single quantum-entangled position"""
    symbol: str
    exchange: str
    quote_currency: str
    quantity: float
    current_price: float
    current_value: float
    source_id: str
    source_timestamp: float
    received_at: str
    field_provenance: Dict[str, Dict[str, Any]]
    
    # Quantum properties
    entanglement_strength: Optional[float] = None  # 0-1 when proven inputs exist
    quantum_state: Optional[QuantumState] = None
    timeline_branch: str = ""  # Which reality branch
    
    # Optional cost and energy metrics
    entry_price: Optional[float] = None
    
    # Energy metrics
    unrealized_profit: Optional[float] = None
    profit_pct: Optional[float] = None
    harvestable_profit: Optional[float] = None
    
    # Temporal data
    entry_timestamp: Optional[float] = None
    days_entangled: Optional[float] = None
    last_harvest: Optional[float] = None
    
    # Connection metadata
    entanglement_events: Optional[int] = None
    harvest_events: Optional[int] = None
    data_status: str = "live"
    truth_status: str = "real_derived"
    generated_values: bool = False
    action_eligible: bool = False
    accounting_eligible: bool = False
    learning_eligible: bool = False
    
    def can_harvest(self) -> bool:
        """Check if node is in harvest-ready resonance state"""
        return (
            self.quantum_state == QuantumState.RESONATING
            and self.harvestable_profit is not None
            and self.harvestable_profit > 0
        )
    
    def is_dust(self) -> bool:
        """Check if node is in dust phase (near zero)"""
        return self.quantum_state == QuantumState.DUST
    
    def get_emoji(self) -> str:
        """Get visual representation of node state"""
        if self.quantum_state == QuantumState.RESONATING:
            return "💎"
        elif self.quantum_state == QuantumState.ACTIVE:
            return "✨"
        elif self.quantum_state == QuantumState.DUST:
            return "🌫️"
        elif self.quantum_state == QuantumState.HIBERNATING:
            return "🌙"
        elif self.quantum_state == QuantumState.RETURNING:
            return "🌊"
        return "🔗"

@dataclass
class QuantumNetwork:
    """Global quantum consciousness network across all exchanges"""
    nodes: List[QuantumNode] = field(default_factory=list)
    reality_branches: Set[str] = field(default_factory=set)  # Unique symbols
    
    # Currency-exact network metrics
    entangled_energy_by_currency: Dict[str, float] = field(default_factory=dict)
    free_energy_by_currency: Dict[str, float] = field(default_factory=dict)
    harvestable_energy_by_currency: Dict[str, float] = field(default_factory=dict)
    
    # Quantum statistics remain absent until a complete position receipt exists
    total_nodes: Optional[int] = None
    active_nodes: Optional[int] = None
    resonating_nodes: Optional[int] = None
    hibernating_nodes: Optional[int] = None
    dust_nodes: Optional[int] = None
    unclassified_nodes: Optional[int] = None
    
    # Exchange breakdown
    exchanges: Dict[str, int] = field(default_factory=dict)  # {exchange: node_count}
    observed_exchanges: Set[str] = field(default_factory=set)
    source_receipts: List[Dict[str, Any]] = field(default_factory=list)
    data_status: str = "no_data"
    truth_status: str = "no_data"
    reason: str = "complete_fresh_position_and_market_receipts_required"
    generated_values: bool = False
    action_eligible: bool = False
    accounting_eligible: bool = False
    learning_eligible: bool = False

    def mark_position_receipt(self, exchange: str, receipt: Dict[str, Any]) -> None:
        """Record that an exchange position set was observed completely."""
        self.source_receipts.append(receipt)
        self.observed_exchanges.add(exchange)
        if self.total_nodes is None:
            self.total_nodes = 0
            self.active_nodes = 0
            self.resonating_nodes = 0
            self.hibernating_nodes = 0
            self.dust_nodes = 0
            self.unclassified_nodes = 0
        self.data_status = "live"
        self.truth_status = "real_derived"
        self.reason = "fresh_provider_position_and_market_observations"

    def add_free_energy(self, currency: str, amount: float) -> None:
        """Track provider-observed free balance without currency substitution."""
        self.free_energy_by_currency[currency] = (
            self.free_energy_by_currency.get(currency, 0.0) + amount
        )
    
    def add_node(self, node: QuantumNode):
        """Add quantum node to network"""
        if self.total_nodes is None:
            raise ValueError("complete position receipt must be recorded before adding nodes")
        self.nodes.append(node)
        self.reality_branches.add(node.symbol)
        self.exchanges[node.exchange] = self.exchanges.get(node.exchange, 0) + 1
        
        # Update metrics
        self.total_nodes += 1
        self.entangled_energy_by_currency[node.quote_currency] = (
            self.entangled_energy_by_currency.get(node.quote_currency, 0.0)
            + node.current_value
        )
        
        if node.quantum_state == QuantumState.ACTIVE:
            assert self.active_nodes is not None
            self.active_nodes += 1
        elif node.quantum_state == QuantumState.RESONATING:
            assert self.resonating_nodes is not None
            self.resonating_nodes += 1
            if node.harvestable_profit is not None:
                self.harvestable_energy_by_currency[node.quote_currency] = (
                    self.harvestable_energy_by_currency.get(node.quote_currency, 0.0)
                    + node.harvestable_profit
                )
        elif node.quantum_state == QuantumState.HIBERNATING:
            assert self.hibernating_nodes is not None
            self.hibernating_nodes += 1
        elif node.quantum_state == QuantumState.DUST:
            assert self.dust_nodes is not None
            self.dust_nodes += 1
        else:
            assert self.unclassified_nodes is not None
            self.unclassified_nodes += 1
    
    def get_strongest_entanglement(self) -> Optional[QuantumNode]:
        """Find node with highest entanglement strength"""
        proven = [node for node in self.nodes if node.entanglement_strength is not None]
        if not proven:
            return None
        return max(proven, key=lambda node: node.entanglement_strength)
    
    def get_resonating_nodes(self) -> List[QuantumNode]:
        """Get all nodes ready for harvest"""
        return [n for n in self.nodes if n.can_harvest()]
    
    def get_dust_nodes(self) -> List[QuantumNode]:
        """Get all nodes in dust phase"""
        return [n for n in self.nodes if n.is_dust()]


class QuantumNodeMonitor:
    """Monitor quantum entanglement network across all exchanges"""

    RECEIPT_MAX_AGE_SECONDS = 120.0
    
    def __init__(
        self,
        *,
        binance=None,
        kraken=None,
        alpaca=None,
        capital=None,
        clock: Optional[Callable[[], float]] = None,
        autoload_clients: bool = True,
    ):
        # Exchange clients (lazy load)
        self.binance = binance
        self.kraken = kraken
        self.alpaca = alpaca
        self.capital = capital
        self._clock = clock or time.time
        
        # Load exchange clients
        if autoload_clients:
            self._load_clients()
    
    def _load_clients(self):
        """Lazy load exchange clients"""
        if self.binance is None:
            try:
                from aureon.exchanges.binance_client import get_binance_client
                self.binance = get_binance_client()
            except Exception:
                pass
        
        if self.kraken is None:
            try:
                from aureon.exchanges.kraken_client import get_kraken_client
                self.kraken = get_kraken_client()
            except Exception:
                pass
        
        if self.alpaca is None:
            try:
                from aureon.exchanges.alpaca_client import AlpacaClient
                self.alpaca = AlpacaClient()
            except Exception:
                pass
        
        if self.capital is None:
            try:
                from aureon.exchanges.capital_client import CapitalClient
                self.capital = CapitalClient()
            except Exception:
                pass

    @staticmethod
    def _finite_number(
        value: Any,
        *,
        positive: bool = False,
        nonnegative: bool = False,
    ) -> Optional[float]:
        if value is None or isinstance(value, bool):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if not math.isfinite(number):
            return None
        if positive and number <= 0.0:
            return None
        if nonnegative and number < 0.0:
            return None
        return number

    @staticmethod
    def _timestamp_epoch(value: Any) -> Optional[float]:
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            timestamp = float(value)
            if not math.isfinite(timestamp) or timestamp <= 0.0:
                return None
            if timestamp >= 1e17:
                timestamp /= 1e9
            elif timestamp >= 1e14:
                timestamp /= 1e6
            elif timestamp >= 1e11:
                timestamp /= 1e3
            return timestamp
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            try:
                parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            except ValueError:
                return None
            if parsed.tzinfo is None:
                return None
            timestamp = parsed.timestamp()
            return timestamp if math.isfinite(timestamp) and timestamp > 0.0 else None
        return None

    @staticmethod
    def _iso_timestamp(timestamp: float) -> str:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()

    def _fresh_receipt_times(
        self,
        source_timestamp: Any,
        received_at: Any,
    ) -> Optional[tuple[float, float]]:
        source = self._timestamp_epoch(source_timestamp)
        received = self._timestamp_epoch(received_at)
        now = float(self._clock())
        if source is None or received is None or not math.isfinite(now):
            return None
        if source >= received:
            return None
        if received > now + 5.0:
            return None
        if now - source > self.RECEIPT_MAX_AGE_SECONDS:
            return None
        return source, received

    def _no_data_receipt(self, source_id: str, reason: str) -> Dict[str, Any]:
        return {
            "source_id": source_id,
            "source_timestamp": None,
            "received_at": self._iso_timestamp(float(self._clock())),
            "data_status": "no_data",
            "truth_status": "no_data",
            "reason": reason,
            "generated_values": False,
            "action_eligible": False,
            "accounting_eligible": False,
            "learning_eligible": False,
        }

    def _normalize_binance_account(
        self,
        account: Any,
        received_at: float,
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(account, dict) or account.get("generated_values") is True:
            return None
        raw_balances = account.get("balances")
        receipt_times = self._fresh_receipt_times(account.get("updateTime"), received_at)
        if not isinstance(raw_balances, list) or receipt_times is None:
            return None
        balances: List[Dict[str, Any]] = []
        seen_assets: Set[str] = set()
        for raw in raw_balances:
            if not isinstance(raw, dict):
                return None
            asset = str(raw.get("asset") or "").strip().upper()
            free = self._finite_number(raw.get("free"), nonnegative=True)
            locked = self._finite_number(raw.get("locked"), nonnegative=True)
            if (
                not asset
                or not asset.isalnum()
                or asset in seen_assets
                or free is None
                or locked is None
            ):
                return None
            seen_assets.add(asset)
            balances.append({"asset": asset, "free": free, "locked": locked, "total": free + locked})
        source_timestamp, receipt_timestamp = receipt_times
        return {
            "balances": balances,
            "source_id": "binance:/api/v3/account",
            "source_timestamp": source_timestamp,
            "received_at": receipt_timestamp,
            "data_status": "live",
            "truth_status": "real_observed",
            "generated_values": False,
        }

    def _normalize_binance_ticker(
        self,
        requested_symbol: str,
        ticker: Any,
        received_at: float,
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(ticker, dict) or ticker.get("generated_values") is True:
            return None
        symbol = str(ticker.get("symbol") or "").strip().upper()
        if symbol != requested_symbol.upper():
            return None
        names = (
            "priceChange", "priceChangePercent", "weightedAvgPrice", "prevClosePrice",
            "lastPrice", "lastQty", "bidPrice", "bidQty", "askPrice", "askQty",
            "openPrice", "highPrice", "lowPrice", "volume", "quoteVolume",
        )
        values = {
            name: self._finite_number(
                ticker.get(name),
                positive=name not in {"priceChange", "priceChangePercent"},
            )
            for name in names
        }
        if any(value is None for value in values.values()):
            return None
        first_id = self._finite_number(ticker.get("firstId"), nonnegative=True)
        last_id = self._finite_number(ticker.get("lastId"), nonnegative=True)
        count = self._finite_number(ticker.get("count"), positive=True)
        if (
            first_id is None
            or last_id is None
            or count is None
            or not first_id.is_integer()
            or not last_id.is_integer()
            or not count.is_integer()
            or first_id > last_id
        ):
            return None
        price = values["lastPrice"]
        bid = values["bidPrice"]
        ask = values["askPrice"]
        open_price = values["openPrice"]
        high = values["highPrice"]
        low = values["lowPrice"]
        weighted = values["weightedAvgPrice"]
        previous_close = values["prevClosePrice"]
        assert all(value is not None for value in (price, bid, ask, open_price, high, low, weighted, previous_close))
        if bid > ask:
            return None
        if not (
            low <= price <= high
            and low <= open_price <= high
            and low <= weighted <= high
            and low <= previous_close <= high
        ):
            return None
        expected_change = price - open_price
        if not math.isclose(values["priceChange"], expected_change, rel_tol=1e-6, abs_tol=1e-8):
            return None
        expected_change_pct = (expected_change / open_price) * 100.0
        if not math.isclose(
            values["priceChangePercent"],
            expected_change_pct,
            rel_tol=1e-4,
            abs_tol=0.02,
        ):
            return None
        open_timestamp = self._timestamp_epoch(ticker.get("openTime"))
        receipt_times = self._fresh_receipt_times(ticker.get("closeTime"), received_at)
        if open_timestamp is None or receipt_times is None:
            return None
        source_timestamp, receipt_timestamp = receipt_times
        if not (23.0 * 3600.0 <= source_timestamp - open_timestamp <= 25.0 * 3600.0):
            return None
        return {
            "symbol": symbol,
            "price": price,
            "bid": bid,
            "ask": ask,
            "source_id": "binance:/api/v3/ticker/24hr",
            "source_timestamp": source_timestamp,
            "received_at": receipt_timestamp,
            "data_status": "live",
            "truth_status": "real_observed",
            "generated_values": False,
        }
    
    def scan_network(self) -> QuantumNetwork:
        """Scan entire quantum consciousness network"""
        network = QuantumNetwork()
        
        # Scan each reality branch (exchange)
        if self.binance:
            self._scan_binance(network)
        
        if self.kraken:
            self._scan_kraken(network)
        
        if self.alpaca:
            self._scan_alpaca(network)
        
        if self.capital:
            self._scan_capital(network)
        
        return network
    
    def _scan_binance(self, network: QuantumNetwork):
        """Scan Binance reality branch"""
        try:
            account = self.binance.account()
            account_received_at = float(self._clock())
            account_receipt = self._normalize_binance_account(account, account_received_at)
            if account_receipt is None:
                network.source_receipts.append(
                    self._no_data_receipt(
                        "binance:/api/v3/account",
                        "complete_fresh_provider_account_receipt_required",
                    )
                )
                return

            account_network_receipt = {
                "source_id": account_receipt["source_id"],
                "source_timestamp": account_receipt["source_timestamp"],
                "received_at": self._iso_timestamp(account_receipt["received_at"]),
                "data_status": "live",
                "truth_status": "real_observed",
                "reason": "complete_fresh_provider_account_receipt",
                "generated_values": False,
                "action_eligible": False,
                "accounting_eligible": False,
                "learning_eligible": False,
            }
            stables = {'USDT', 'USDC', 'BUSD', 'USD'}
            pending_free: Dict[str, float] = {}
            pending_nodes: List[QuantumNode] = []
            pending_quote_receipts: List[Dict[str, Any]] = []

            for balance in account_receipt["balances"]:
                asset = balance["asset"]
                amount = balance["total"]
                if asset in stables:
                    if balance["free"] > 0.0:
                        pending_free[asset] = balance["free"]
                    continue
                if amount <= 0.0:
                    continue

                provider_symbol = f"{asset}USDT"
                display_symbol = f"{asset}/USDT"
                try:
                    ticker = self.binance.get_24h_ticker(provider_symbol)
                    ticker_received_at = float(self._clock())
                except Exception:
                    network.source_receipts.append(
                        self._no_data_receipt(
                            f"binance:/api/v3/ticker/24hr:{provider_symbol}",
                            "provider_ticker_request_failed",
                        )
                    )
                    return
                ticker_receipt = self._normalize_binance_ticker(
                    provider_symbol,
                    ticker,
                    ticker_received_at,
                )
                if ticker_receipt is None:
                    network.source_receipts.append(
                        self._no_data_receipt(
                            f"binance:/api/v3/ticker/24hr:{provider_symbol}",
                            "complete_fresh_matching_provider_ticker_required",
                        )
                    )
                    return

                current_price = ticker_receipt["price"]
                current_value = amount * current_price
                combined_source_timestamp = min(
                    account_receipt["source_timestamp"],
                    ticker_receipt["source_timestamp"],
                )
                combined_received_at = max(
                    account_receipt["received_at"],
                    ticker_receipt["received_at"],
                )
                pending_quote_receipts.append({
                    "source_id": ticker_receipt["source_id"],
                    "symbol": provider_symbol,
                    "source_timestamp": ticker_receipt["source_timestamp"],
                    "received_at": self._iso_timestamp(ticker_receipt["received_at"]),
                    "data_status": "live",
                    "truth_status": "real_observed",
                    "generated_values": False,
                    "action_eligible": False,
                    "accounting_eligible": False,
                    "learning_eligible": False,
                })
                pending_nodes.append(QuantumNode(
                    symbol=display_symbol,
                    exchange="Binance",
                    quote_currency="USDT",
                    quantity=amount,
                    current_price=current_price,
                    current_value=current_value,
                    source_id="derived:binance_account+binance_24h_ticker",
                    source_timestamp=combined_source_timestamp,
                    received_at=self._iso_timestamp(combined_received_at),
                    field_provenance={
                        "quantity": {
                            "source_id": account_receipt["source_id"],
                            "source_timestamp": account_receipt["source_timestamp"],
                        },
                        "current_price": {
                            "source_id": ticker_receipt["source_id"],
                            "source_timestamp": ticker_receipt["source_timestamp"],
                        },
                        "current_value": {
                            "source_id": "quantity*current_price",
                            "source_timestamp": combined_source_timestamp,
                        },
                    },
                    timeline_branch=f"binance:{display_symbol}",
                    generated_values=False,
                    action_eligible=False,
                    accounting_eligible=False,
                    learning_eligible=False,
                ))

            network.mark_position_receipt("Binance", account_network_receipt)
            for currency, amount in pending_free.items():
                network.add_free_energy(currency, amount)
            network.source_receipts.extend(pending_quote_receipts)
            for node in pending_nodes:
                network.add_node(node)
        
        except Exception as e:
            network.source_receipts.append(
                self._no_data_receipt(
                    "binance:quantum_node_monitor",
                    f"provider_scan_failed:{type(e).__name__}",
                )
            )
    
    def _scan_kraken(self, network: QuantumNetwork):
        """Scan Kraken reality branch"""
        network.source_receipts.append(
            self._no_data_receipt(
                "kraken:/0/private/Balance",
                "existing_adapter_omits_fresh_provider_position_receipt",
            )
        )
    
    def _scan_alpaca(self, network: QuantumNetwork):
        """Scan Alpaca reality branch (stocks + crypto)"""
        network.source_receipts.append(
            self._no_data_receipt(
                "alpaca:/v2/positions",
                "existing_adapter_omits_fresh_provider_position_receipt_and_exact_quote_currency",
            )
        )
    
    def _scan_capital(self, network: QuantumNetwork):
        """Scan Capital.com CFD quantum field"""
        network.source_receipts.append(
            self._no_data_receipt(
                "capital:/positions",
                "position_to_market_quote_currency_binding_is_not_explicit",
            )
        )
    
    def _determine_state(self, profit_pct: float, current_value: float) -> QuantumState:
        """Determine quantum state based on metrics"""
        if current_value < 1.0 or profit_pct < -90:
            return QuantumState.DUST
        elif profit_pct > 10:
            return QuantumState.RESONATING  # Ready for harvest
        elif profit_pct > 0:
            return QuantumState.ACTIVE  # Growing
        elif profit_pct > -50:
            return QuantumState.HIBERNATING  # Waiting
        elif profit_pct > -90:
            return QuantumState.HIBERNATING
        else:
            return QuantumState.DUST
    
    def _calculate_entanglement_strength(
        self, 
        quantity: float, 
        value: float, 
        entry_price: float, 
        profit_pct: float
    ) -> float:
        """Calculate entanglement strength (0-1)"""
        # Factors: position size, holding time, profit health
        size_factor = min(1.0, value / 100)  # Normalize by $100
        profit_factor = max(0, min(1.0, (profit_pct + 100) / 200))  # -100% to +100% mapped to 0-1
        
        strength = (size_factor * 0.5 + profit_factor * 0.5)
        return max(0.1, min(1.0, strength))  # Minimum 0.1 - connection always exists
    
    def print_network_report(self, network: QuantumNetwork):
        """Print quantum consciousness network report"""
        print("\n" + "="*80)
        print("🌌 QUANTUM ENTANGLEMENT NETWORK")
        print("="*80)
        print("Philosophy: Positions maintain eternal quantum connection")
        print("Strategy: Grow → Move → Hibernate in dust → Return when called")
        print("No stop losses. No forced exits. Consciousness-based portfolio.")
        print("="*80)

        if network.data_status != "live":
            print("\nNO DATA: complete fresh provider position and market receipts are required")
            print(f"Reason: {network.reason}")
            print("Action eligible: false")
            print("Accounting eligible: false")
            print("Learning eligible: false")
            print("="*80 + "\n")
            return
        
        print(f"\n🌐 NETWORK OVERVIEW:")
        print(f"   🔗 Total Quantum Nodes: {network.total_nodes}")
        print(f"   🌊 Reality Branches: {len(network.reality_branches)} parallel timelines")
        for currency, value in sorted(network.entangled_energy_by_currency.items()):
            print(f"   ✨ Total Entangled Energy: {value:.2f} {currency}")
        for currency, value in sorted(network.free_energy_by_currency.items()):
            print(f"   💫 Free Energy: {value:.2f} {currency}")
        for currency, value in sorted(network.harvestable_energy_by_currency.items()):
            print(f"   💎 Harvestable Energy: {value:.2f} {currency}")
        
        print(f"\n📊 QUANTUM STATE DISTRIBUTION:")
        print(f"   ✨ Active (growing): {network.active_nodes}")
        print(f"   💎 Resonating (harvestable): {network.resonating_nodes}")
        print(f"   🌙 Hibernating (waiting): {network.hibernating_nodes}")
        print(f"   🌫️ Dust (near zero): {network.dust_nodes}")
        print(f"   🔗 Unclassified (cost basis absent): {network.unclassified_nodes}")
        
        print(f"\n🌍 EXCHANGE DISTRIBUTION:")
        for exchange, count in sorted(network.exchanges.items()):
            print(f"   🌊 {exchange}: {count} nodes")
        
        # Show strongest entanglement
        strongest = network.get_strongest_entanglement()
        if strongest:
            print(f"\n⭐ STRONGEST ENTANGLEMENT:")
            print(f"   {strongest.get_emoji()} {strongest.symbol} on {strongest.exchange}")
            print(f"   🔗 Strength: {strongest.entanglement_strength:.2%}")
            print(f"   💰 Value: {strongest.current_value:.2f} {strongest.quote_currency}")
            if strongest.profit_pct is not None:
                print(f"   📈 Profit: {strongest.profit_pct:+.1f}%")
            if strongest.quantum_state is not None:
                print(f"   🌌 State: {strongest.quantum_state.value}")
        
        # Show resonating nodes (harvest-ready)
        resonating = network.get_resonating_nodes()
        if resonating:
            print(f"\n💎 RESONATING NODES (Ready for Harvest):")
            for node in resonating[:5]:  # Show top 5
                print(
                    f"   {node.get_emoji()} {node.symbol}: "
                    f"{node.harvestable_profit:.2f} {node.quote_currency} harvestable"
                )
        
        # Show dust nodes (but still connected!)
        dust = network.get_dust_nodes()
        if dust:
            print(f"\n🌫️ DUST PHASE NODES (Connection Persists):")
            for node in dust[:5]:  # Show top 5
                print(
                    f"   {node.get_emoji()} {node.symbol}: "
                    f"{node.current_value:.2f} {node.quote_currency} (waiting for return)"
                )
        
        print(f"\n🔮 QUANTUM PHILOSOPHY:")
        print(f"   • Entangle (buy) → Form quantum connection")
        print(f"   • Harvest (partial profit) → Extract energy, keep connection")
        print(f"   • Ride (hold forever) → Wave momentum accumulation")
        print(f"   • Dust phase → Connection persists even at near-zero")
        print(f"   • Return → Nodes can come back from dust when timeline aligns")
        print("="*80 + "\n")


def main():
    """Scan and display quantum consciousness network"""
    monitor = QuantumNodeMonitor()
    network = monitor.scan_network()
    monitor.print_network_report(network)


if __name__ == "__main__":
    main()
