#!/usr/bin/env python3
"""
🌍 AUREON FULL ORCHESTRATOR 🌍
================================
Hooks up ALL systems:
- Stargate Protocol (12 planetary nodes)
- Quantum Mirror Scanner (timeline detection)
- Timeline Anchor Validator (7-day validation)
- Probability Nexus (3-pass Batten Matrix)
- Queen Hive Mind (execution gate)
- Planet Saver (trade execution & compounding)

ONE SYSTEM TO RULE THEM ALL
"""

import time
import json
import hashlib
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from collections.abc import Mapping
from pathlib import Path
import math

# Sacred constants
PHI = 1.618033988749895
SCHUMANN = 7.83
LOVE_FREQ = 528
LIVE_CONFIRMATION = "AUTHORIZE_RECEIPTED_FULL_ORCHESTRATOR"

@dataclass
class Opportunity:
    """Trading opportunity with full validation"""
    symbol: str
    exchange: str
    price: float
    momentum: float  # 24h change %
    volume: float
    
    # Validation scores
    stargate_resonance: Optional[float] = None
    quantum_coherence: Optional[float] = None
    timeline_anchor_strength: Optional[float] = None
    p1_harmonic: Optional[float] = None
    p2_coherence: Optional[float] = None
    p3_stability: Optional[float] = None
    
    # Final scores
    batten_score: Optional[float] = None
    queen_confidence: Optional[float] = None
    final_score: Optional[float] = None
    
    ready_for_4th: bool = False
    timestamp: str = ""
    source_id: Optional[str] = None
    source_timestamp: Optional[float] = None
    received_at: Optional[float] = None
    receipt_id: Optional[str] = None
    truth_status: str = "no_data"
    generated_values: bool = False
    actionable: bool = False
    accounting_eligible: bool = False
    learning_eligible: bool = False
    market_receipt: Optional[Dict[str, Any]] = None
    gate_receipts: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    validation_receipt: Optional[Dict[str, Any]] = None

@dataclass
class SystemState:
    """Full system state"""
    opportunities_scanned: int = 0
    opportunities_validated: int = 0
    trades_executed: int = 0
    trades_won: int = 0
    total_profit: float = 0.0
    active_position: Optional[Dict] = None
    last_scan: str = ""
    stargate_active: bool = False
    quantum_mirror_active: bool = False
    timeline_validator_active: bool = False
    last_gamma_sync: Optional[str] = None

class AureonFullOrchestrator:
    """
    Master orchestrator connecting all Aureon systems
    """
    
    def __init__(
        self,
        *,
        client: Any = None,
        venue: Optional[str] = None,
        stargate: Any = None,
        quantum_mirror: Any = None,
        timeline_validator: Any = None,
        queen: Any = None,
        state: Optional[SystemState] = None,
        state_path: Optional[Path] = None,
        persist_state: bool = False,
        live_actions_enabled: bool = False,
        gamma_sync_runner: Any = None,
    ):
        self.state = state if state is not None else SystemState()
        self.client = client
        self.venue = str(venue).strip().lower() if venue is not None else None
        self.stargate = stargate
        self.quantum_mirror = quantum_mirror
        self.timeline_validator = timeline_validator
        self.queen = queen
        self.state_path = Path(state_path).resolve() if state_path is not None else None
        self.persist_state = bool(persist_state)
        self.live_actions_enabled = bool(live_actions_enabled)
        self.gamma_sync_runner = gamma_sync_runner
        self.pending_order: Optional[Dict[str, Any]] = None
        self.last_no_data = self._no_data("not_started")
        
    def _load_state(self) -> SystemState:
        if self.state_path is None:
            return SystemState()
        try:
            with self.state_path.open('r', encoding='utf-8') as f:
                data = json.load(f)
                return SystemState(**data)
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            return SystemState()
    
    def _save_state(self):
        if not self.persist_state or self.state_path is None:
            return False
        temp_path = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with temp_path.open('w', encoding='utf-8') as f:
            json.dump(asdict(self.state), f, indent=2)
            f.flush()
        temp_path.replace(self.state_path)
        return True

    @staticmethod
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

    @staticmethod
    def _no_data(reason: str, **context: Any) -> Dict[str, Any]:
        receipt = {
            "status": "no_data",
            "truth_status": "no_data",
            "reason": reason,
            "source_id": None,
            "source_timestamp": None,
            "received_at": time.time(),
            "receipt_id": None,
            "generated_values": False,
            "actionable": False,
            "accounting_eligible": False,
            "learning_eligible": False,
        }
        receipt.update(context)
        return receipt

    @staticmethod
    def _derived_receipt_id(kind: str, payload: Mapping[str, Any]) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        return f"aureon:{kind}:{digest}"

    @classmethod
    def _fresh_ticker_receipt(
        cls,
        receipt: Any,
        *,
        symbol: str,
        venue: str,
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(receipt, Mapping):
            return None
        now = time.time()
        source_timestamp = cls._finite(receipt.get("source_timestamp"), positive=True)
        received_at = cls._finite(receipt.get("received_at"), positive=True)
        price = cls._finite(receipt.get("price"), positive=True)
        change = cls._finite(receipt.get("change_pct"))
        volume_base = cls._finite(receipt.get("volume_24h"), nonnegative=True)
        source_id = str(receipt.get("source_id") or "").strip()
        receipt_id = str(receipt.get("receipt_id") or "").strip()
        receipt_symbol = str(receipt.get("symbol") or "").strip().upper()
        receipt_venue = str(receipt.get("venue") or "").strip().lower()
        expected_symbol = str(symbol).strip().upper()
        expected_venue = str(venue).strip().lower()
        if (
            receipt.get("data_status") != "live"
            or receipt.get("truth_status") != "real_observed"
            or receipt.get("generated_values") is not False
            or not source_id
            or not receipt_id
            or not expected_symbol
            or not expected_venue
            or receipt_symbol != expected_symbol
            or receipt_venue != expected_venue
            or source_timestamp is None
            or received_at is None
            or price is None
            or change is None
            or volume_base is None
            or source_timestamp > received_at + 5.0
            or received_at > now + 5.0
            or now - source_timestamp > 300.0
            or now - received_at > 300.0
        ):
            return None
        return dict(receipt)

    def _actionable_validation_receipt(self, opp: Opportunity) -> Optional[Dict[str, Any]]:
        if (
            opp.actionable is not True
            or opp.accounting_eligible is not False
            or opp.learning_eligible is not False
            or opp.ready_for_4th is not True
            or not self.venue
            or opp.exchange != self.venue
        ):
            return None
        market = self._fresh_ticker_receipt(
            opp.market_receipt,
            symbol=opp.symbol,
            venue=opp.exchange,
        )
        price = self._finite(opp.price, positive=True)
        momentum = self._finite(opp.momentum, positive=True)
        volume = self._finite(opp.volume, positive=True)
        if (
            market is None
            or price is None
            or momentum is None
            or volume is None
            or str(market.get("receipt_id") or "") != str(opp.receipt_id or "")
            or not math.isclose(price, float(market["price"]), rel_tol=1e-12, abs_tol=1e-12)
            or not math.isclose(momentum, float(market["change_pct"]), rel_tol=1e-12, abs_tol=1e-12)
            or not math.isclose(
                volume,
                float(market["volume_24h"]) * price,
                rel_tol=1e-12,
                abs_tol=1e-12,
            )
        ):
            return None

        score_specs = {
            "stargate": ("resonance", opp.stargate_resonance),
            "quantum_mirror": ("coherence", opp.quantum_coherence),
            "timeline_anchor": ("anchor_strength", opp.timeline_anchor_strength),
        }
        score_receipts: Dict[str, Dict[str, Any]] = {}
        for name, (score_key, opportunity_score) in score_specs.items():
            validated = self._score_receipt(
                opp.gate_receipts.get(name),
                score_key=score_key,
                required_input_receipt_ids={str(opp.receipt_id)},
                symbol=opp.symbol,
                venue=opp.exchange,
            )
            score = self._finite(opportunity_score, nonnegative=True)
            if (
                validated is None
                or score is None
                or not math.isclose(
                    score,
                    float(validated[score_key]),
                    rel_tol=1e-12,
                    abs_tol=1e-12,
                )
            ):
                return None
            score_receipts[name] = validated

        p1 = min(momentum / (100 / PHI), 1.0)
        signals = [
            float(opp.stargate_resonance),
            float(opp.quantum_coherence),
            float(opp.timeline_anchor_strength),
        ]
        mean_signal = sum(signals) / len(signals)
        variance = sum((signal - mean_signal) ** 2 for signal in signals) / len(signals)
        p2 = 1.0 - min(variance * 2, 1.0)
        p3 = min(math.log10(volume + 1) / 5, 1.0)
        batten_score = (p1 * p2 * p3) ** (1 / 3)
        batten = opp.gate_receipts.get("batten")
        batten_input_ids = [
            str(opp.receipt_id),
            *[
                str(score_receipts[name]["receipt_id"])
                for name in ("stargate", "quantum_mirror", "timeline_anchor")
            ],
        ]
        batten_payload = {
            "symbol": opp.symbol,
            "venue": opp.exchange,
            "input_receipt_ids": batten_input_ids,
            "p1_harmonic": p1,
            "p2_coherence": p2,
            "p3_stability": p3,
            "batten_score": batten_score,
        }
        batten_values = {
            key: self._finite(
                batten.get(key) if isinstance(batten, Mapping) else None,
                nonnegative=True,
            )
            for key in (
                "p1_harmonic",
                "p2_coherence",
                "p3_stability",
                "batten_score",
            )
        }
        if (
            not isinstance(batten, Mapping)
            or batten.get("status") != "validated"
            or batten.get("truth_status") != "real_derived"
            or batten.get("generated_values") is not False
            or batten.get("eligible_for_action") is not False
            or batten.get("eligible_for_accounting") is not False
            or batten.get("eligible_for_learning") is not False
            or batten.get("input_receipt_ids") != batten_input_ids
            or str(batten.get("receipt_id") or "")
            != self._derived_receipt_id("batten", batten_payload)
            or any(
                batten_values[key] is None
                or not math.isclose(
                    batten_values[key],
                    expected,
                    rel_tol=1e-12,
                    abs_tol=1e-12,
                )
                for key, expected in (
                    ("p1_harmonic", p1),
                    ("p2_coherence", p2),
                    ("p3_stability", p3),
                    ("batten_score", batten_score),
                )
            )
        ):
            return None

        queen_required_ids = {str(opp.receipt_id), *batten_input_ids[1:], str(batten["receipt_id"])}
        queen = self._score_receipt(
            opp.gate_receipts.get("queen"),
            score_key="confidence",
            required_input_receipt_ids=queen_required_ids,
            symbol=opp.symbol,
            venue=opp.exchange,
        )
        queen_confidence = self._finite(opp.queen_confidence, nonnegative=True)
        if (
            queen is None
            or queen_confidence is None
            or not math.isclose(
                queen_confidence,
                float(queen["confidence"]),
                rel_tol=1e-12,
                abs_tol=1e-12,
            )
        ):
            return None

        expected_final = (
            batten_score * 0.4
            + queen_confidence * 0.3
            + signals[0] * 0.1
            + signals[1] * 0.1
            + signals[2] * 0.1
        )
        final_score = self._finite(opp.final_score, nonnegative=True)
        validation = opp.validation_receipt
        validation_inputs = [
            str(opp.receipt_id),
            *batten_input_ids[1:],
            str(batten["receipt_id"]),
            str(queen["receipt_id"]),
        ]
        validation_payload = {
            "symbol": opp.symbol,
            "venue": opp.exchange,
            "input_receipt_ids": validation_inputs,
            "final_score": expected_final,
            "ready_for_4th": True,
        }
        now = time.time()
        source_timestamp = self._finite(
            validation.get("source_timestamp") if isinstance(validation, Mapping) else None,
            positive=True,
        )
        received_at = self._finite(
            validation.get("received_at") if isinstance(validation, Mapping) else None,
            positive=True,
        )
        if (
            final_score is None
            or not math.isclose(final_score, expected_final, rel_tol=1e-12, abs_tol=1e-12)
            or not isinstance(validation, Mapping)
            or validation.get("status") != "validated"
            or validation.get("truth_status") != "real_derived"
            or validation.get("generated_values") is not False
            or validation.get("eligible_for_action") is not True
            or validation.get("eligible_for_accounting") is not False
            or validation.get("eligible_for_learning") is not False
            or validation.get("input_receipt_ids") != validation_inputs
            or str(validation.get("source_id") or "")
            != "aureon:full-orchestrator-validation:v1"
            or str(validation.get("receipt_id") or "")
            != self._derived_receipt_id("full-orchestrator-validation", validation_payload)
            or source_timestamp is None
            or received_at is None
            or source_timestamp > received_at + 5.0
            or received_at > now + 5.0
            or now - source_timestamp > 300.0
            or now - received_at > 300.0
        ):
            return None
        return dict(validation)

    @classmethod
    def _score_receipt(
        cls,
        receipt: Any,
        *,
        score_key: str,
        required_input_receipt_ids: set[str],
        symbol: str,
        venue: str,
    ) -> Optional[Dict[str, Any]]:
        if (
            not isinstance(receipt, Mapping)
            or not required_input_receipt_ids
            or any(not str(item).strip() for item in required_input_receipt_ids)
        ):
            return None
        now = time.time()
        score = cls._finite(receipt.get(score_key), nonnegative=True)
        source_timestamp = cls._finite(receipt.get("source_timestamp"), positive=True)
        received_at = cls._finite(receipt.get("received_at"), positive=True)
        source_id = str(receipt.get("source_id") or "").strip()
        receipt_id = str(receipt.get("receipt_id") or "").strip()
        receipt_symbol = str(receipt.get("symbol") or "").strip().upper()
        receipt_venue = str(receipt.get("venue") or "").strip().lower()
        raw_input_ids = receipt.get("input_receipt_ids")
        if not isinstance(raw_input_ids, (list, tuple, set)):
            return None
        input_ids = {
            str(item).strip()
            for item in raw_input_ids
            if str(item).strip()
        }
        if (
            receipt.get("truth_status") not in {"real_observed", "real_derived"}
            or receipt.get("generated_values") is not False
            or score is None
            or score > 1.0
            or not source_id
            or not receipt_id
            or receipt_symbol != str(symbol).strip().upper()
            or receipt_venue != str(venue).strip().lower()
            or not required_input_receipt_ids.issubset(input_ids)
            or source_timestamp is None
            or received_at is None
            or source_timestamp > received_at + 5.0
            or received_at > now + 5.0
            or now - source_timestamp > 300.0
            or now - received_at > 300.0
        ):
            return None
        validated = dict(receipt)
        validated[score_key] = score
        return validated

    @classmethod
    def _fresh_balance_receipt(
        cls,
        receipt: Any,
        *,
        currency: str,
        venue: str,
    ) -> Optional[float]:
        if not isinstance(receipt, Mapping):
            return None
        now = time.time()
        balances = receipt.get("balances")
        source_timestamp = cls._finite(receipt.get("source_timestamp"), positive=True)
        received_at = cls._finite(receipt.get("received_at"), positive=True)
        source_id = str(receipt.get("source_id") or "").strip()
        receipt_id = str(receipt.get("receipt_id") or "").strip()
        receipt_venue = str(receipt.get("venue") or "").strip().lower()
        amount = cls._finite(
            balances.get(currency) if isinstance(balances, Mapping) else None,
            nonnegative=True,
        )
        if (
            receipt.get("data_status") != "live"
            or receipt.get("truth_status") not in {"real_observed", "real_derived"}
            or receipt.get("generated_values") is not False
            or receipt.get("eligible_for_action") is not True
            or receipt_venue != str(venue).strip().lower()
            or not source_id
            or not receipt_id
            or amount is None
            or source_timestamp is None
            or received_at is None
            or source_timestamp > received_at + 5.0
            or received_at > now + 5.0
            or now - source_timestamp > 300.0
            or now - received_at > 300.0
        ):
            return None
        return amount

    @classmethod
    def _terminal_fill(
        cls,
        receipt: Any,
        *,
        symbol: str,
        side: str,
        venue: str,
        expected_fee_currency: str,
        expected_order_id: Optional[str] = None,
        expected_qty: Optional[float] = None,
        expected_notional: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(receipt, Mapping):
            return None
        now = time.time()
        order_id = str(receipt.get("orderId") or "").strip()
        receipt_id = str(receipt.get("receipt_id") or "").strip()
        source_id = str(receipt.get("source_id") or "").strip()
        receipt_symbol = str(receipt.get("symbol") or "").strip().upper()
        receipt_side = str(receipt.get("side") or "").strip().upper()
        receipt_venue = str(receipt.get("venue") or "").strip().lower()
        quantity = cls._finite(receipt.get("filled_qty"), positive=True)
        price = cls._finite(receipt.get("filled_avg_price"), positive=True)
        notional = cls._finite(receipt.get("filled_notional"), positive=True)
        fee = cls._finite(receipt.get("fee"), nonnegative=True)
        fee_currency = str(receipt.get("fee_currency") or "").strip().upper()
        source_timestamp = cls._finite(receipt.get("source_timestamp"), positive=True)
        received_at = cls._finite(receipt.get("received_at"), positive=True)
        fills = receipt.get("fills")
        trade_ids: List[str] = []
        fill_qty = 0.0
        fill_notional = 0.0
        fill_fee = 0.0
        fills_complete = isinstance(fills, list) and bool(fills)
        if fills_complete:
            for row in fills:
                if not isinstance(row, Mapping):
                    fills_complete = False
                    break
                trade_id = str(row.get("tradeId") or "").strip()
                row_qty = cls._finite(row.get("qty"), positive=True)
                row_price = cls._finite(row.get("price"), positive=True)
                row_fee = cls._finite(row.get("fee"), nonnegative=True)
                row_fee_currency = str(row.get("fee_currency") or "").strip().upper()
                if (
                    not trade_id
                    or row_qty is None
                    or row_price is None
                    or row_fee is None
                    or row_fee_currency != fee_currency
                ):
                    fills_complete = False
                    break
                trade_ids.append(trade_id)
                fill_qty += row_qty
                fill_notional += row_qty * row_price
                fill_fee += row_fee
        computed_average = fill_notional / fill_qty if fill_qty > 0.0 else None
        requested_qty = cls._finite(expected_qty, positive=True) if expected_qty is not None else None
        requested_notional = (
            cls._finite(expected_notional, positive=True)
            if expected_notional is not None
            else None
        )
        if (
            receipt.get("status") != "FILLED"
            or receipt.get("data_status") != "live"
            or receipt.get("truth_status") != "real_observed"
            or receipt.get("generated_values") is not False
            or receipt.get("fill_receipt_complete") is not True
            or receipt.get("eligible_for_action") is not True
            or receipt.get("eligible_for_accounting") is not True
            or receipt.get("eligible_for_learning") is not True
            or receipt.get("reconciliation_required") is not False
            or not order_id
            or not receipt_id
            or not source_id
            or receipt_symbol != str(symbol).strip().upper()
            or receipt_side != str(side).strip().upper()
            or receipt_venue != str(venue).strip().lower()
            or fee_currency != str(expected_fee_currency).strip().upper()
            or (expected_order_id is not None and order_id != str(expected_order_id).strip())
            or quantity is None
            or price is None
            or notional is None
            or fee is None
            or not fee_currency
            or not fills_complete
            or not trade_ids
            or len(set(trade_ids)) != len(trade_ids)
            or computed_average is None
            or not math.isclose(quantity, fill_qty, rel_tol=1e-9, abs_tol=1e-12)
            or not math.isclose(notional, fill_notional, rel_tol=1e-9, abs_tol=1e-12)
            or not math.isclose(price, computed_average, rel_tol=1e-9, abs_tol=1e-12)
            or not math.isclose(fee, fill_fee, rel_tol=1e-9, abs_tol=1e-12)
            or (expected_qty is not None and requested_qty is None)
            or (expected_notional is not None and requested_notional is None)
            or (
                requested_qty is not None
                and not math.isclose(quantity, requested_qty, rel_tol=1e-9, abs_tol=1e-12)
            )
            or (
                requested_notional is not None
                and not math.isclose(notional, requested_notional, rel_tol=1e-9, abs_tol=1e-12)
            )
            or source_timestamp is None
            or received_at is None
            or source_timestamp > received_at + 5.0
            or received_at > now + 5.0
            or now - source_timestamp > 300.0
            or now - received_at > 300.0
        ):
            return None
        return dict(receipt)
    
    def initialize_systems(self):
        """Initialize all subsystems"""
        print("\n" + "="*60)
        print("🌍 AUREON FULL ORCHESTRATOR - INITIALIZING ALL SYSTEMS")
        print("="*60)
        
        # 1. Kraken Client
        print("\n📡 Loading Kraken Client...")
        try:
            from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
            self.client = get_kraken_client()
            self.venue = "kraken"
            print("   ✅ Kraken connected")
        except Exception as e:
            print(f"   ❌ Kraken failed: {e}")
            return False
        
        # 2. Stargate Protocol
        print("\n🌌 Loading Stargate Protocol...")
        try:
            from aureon.wisdom.aureon_stargate_protocol import create_stargate_engine
            self.stargate = create_stargate_engine(with_integrations=False)
            self.state.stargate_active = True
            print(f"   ✅ {len(self.stargate.stargates)} planetary nodes active")
        except Exception as e:
            print(f"   ⚠️ Stargate not available: {e}")
            self.state.stargate_active = False
        
        # 3. Quantum Mirror Scanner
        print("\n🔮 Loading Quantum Mirror Scanner...")
        try:
            from aureon.scanners.aureon_quantum_mirror_scanner import QuantumMirrorScanner
            self.quantum_mirror = QuantumMirrorScanner()
            self.state.quantum_mirror_active = True
            print("   ✅ Quantum mirrors initialized")
        except Exception as e:
            print(f"   ⚠️ Quantum Mirror not available: {e}")
            self.state.quantum_mirror_active = False
        
        # 4. Timeline Anchor Validator
        print("\n⚓ Loading Timeline Anchor Validator...")
        try:
            from aureon.intelligence.aureon_timeline_anchor_validator import TimelineAnchorValidator
            self.timeline_validator = TimelineAnchorValidator()
            self.state.timeline_validator_active = True
            print("   ✅ Timeline validator ready")
        except Exception as e:
            print(f"   ⚠️ Timeline Validator not available: {e}")
            self.state.timeline_validator_active = False
        
        # 5. Queen Hive Mind
        print("\n👑 Loading Queen Hive Mind...")
        try:
            from aureon.utils.aureon_queen_hive_mind import QueenHiveMind
            self.queen = QueenHiveMind()
            print("   ✅ Queen awakened")
        except Exception as e:
            print(f"   ⚠️ Queen not available: {e}")
        
        print("\n" + "="*60)
        print("✅ SYSTEM INITIALIZATION COMPLETE")
        print(f"   Stargate:    {'🟢' if self.state.stargate_active else '🔴'}")
        print(f"   Quantum:     {'🟢' if self.state.quantum_mirror_active else '🔴'}")
        print(f"   Timeline:    {'🟢' if self.state.timeline_validator_active else '🔴'}")
        print("="*60)
        
        return True
    
    def scan_opportunities(self) -> List[Opportunity]:
        """Scan all markets for opportunities"""
        print("\n🔍 SCANNING MARKETS...")

        opportunities: List[Opportunity] = []
        if (
            self.client is None
            or not self.venue
            or not callable(getattr(self.client, "get_ticker_receipt", None))
        ):
            self.last_no_data = self._no_data("receipt_capable_market_client_required")
            return opportunities
        try:
            tickers = self.client.get_24h_tickers()
        except Exception:
            self.last_no_data = self._no_data("market_discovery_failed")
            return opportunities

        seen = set()
        for ticker in tickers if isinstance(tickers, list) else []:
            if not isinstance(ticker, Mapping):
                continue
            symbol = str(ticker.get('symbol') or '').strip().upper()
            if not symbol.endswith('USDC'):
                continue
            if symbol in seen:
                continue
            seen.add(symbol)
            try:
                receipt = self._fresh_ticker_receipt(
                    self.client.get_ticker_receipt(symbol),
                    symbol=symbol,
                    venue=self.venue,
                )
            except Exception:
                receipt = None
            if receipt is None:
                continue
            price = float(receipt["price"])
            change = float(receipt["change_pct"])
            volume = float(receipt["volume_24h"]) * price

            # Filter: positive momentum, decent volume
            if change > 0.5 and volume > 500:
                source_timestamp = float(receipt["source_timestamp"])
                opp = Opportunity(
                    symbol=symbol,
                    exchange=str(receipt["venue"]).strip().lower(),
                    price=price,
                    momentum=change,
                    volume=volume,
                    timestamp=datetime.fromtimestamp(source_timestamp).isoformat(),
                    source_id=str(receipt["source_id"]),
                    source_timestamp=source_timestamp,
                    received_at=float(receipt["received_at"]),
                    receipt_id=str(receipt["receipt_id"]),
                    truth_status="real_derived",
                    generated_values=False,
                    market_receipt=dict(receipt),
                )
                opportunities.append(opp)

        self.state.opportunities_scanned = len(opportunities)
        if not opportunities:
            self.last_no_data = self._no_data("no_complete_fresh_receipted_opportunities")
        print(f"   Found {len(opportunities)} raw opportunities")

        return opportunities
    
    def validate_with_stargate(self, opp: Opportunity) -> Optional[float]:
        """Validate opportunity with Stargate resonance"""
        evaluator = getattr(self.stargate, "evaluate_market_opportunity", None)
        if not self.state.stargate_active or not callable(evaluator):
            return None
        try:
            receipt = evaluator(asdict(opp))
        except Exception:
            return None
        validated = self._score_receipt(
            receipt,
            score_key="resonance",
            required_input_receipt_ids={str(opp.receipt_id or "")},
            symbol=opp.symbol,
            venue=opp.exchange,
        )
        if validated is None:
            return None
        opp.gate_receipts["stargate"] = validated
        return float(validated["resonance"])
    
    def validate_with_quantum_mirror(self, opp: Opportunity) -> Optional[float]:
        """Validate opportunity with Quantum Mirror coherence"""
        evaluator = getattr(self.quantum_mirror, "evaluate_market_opportunity", None)
        if not self.state.quantum_mirror_active or not callable(evaluator):
            return None
        try:
            receipt = evaluator(asdict(opp))
        except Exception:
            return None
        validated = self._score_receipt(
            receipt,
            score_key="coherence",
            required_input_receipt_ids={str(opp.receipt_id or "")},
            symbol=opp.symbol,
            venue=opp.exchange,
        )
        if validated is None:
            return None
        opp.gate_receipts["quantum_mirror"] = validated
        return float(validated["coherence"])
    
    def validate_with_timeline_anchor(self, opp: Opportunity) -> Optional[float]:
        """Check timeline anchor strength"""
        evaluator = getattr(self.timeline_validator, "evaluate_market_opportunity", None)
        if not self.state.timeline_validator_active or not callable(evaluator):
            return None
        try:
            receipt = evaluator(asdict(opp))
        except Exception:
            return None
        validated = self._score_receipt(
            receipt,
            score_key="anchor_strength",
            required_input_receipt_ids={str(opp.receipt_id or "")},
            symbol=opp.symbol,
            venue=opp.exchange,
        )
        if validated is None:
            return None
        opp.gate_receipts["timeline_anchor"] = validated
        return float(validated["anchor_strength"])
    
    def compute_batten_matrix(self, opp: Opportunity) -> Optional[float]:
        """
        Compute 3-pass Batten Matrix validation
        P1: Harmonic validation
        P2: Coherence validation
        P3: Stability validation
        """
        score_specs = {
            "stargate": ("resonance", self._finite(opp.stargate_resonance, nonnegative=True)),
            "quantum_mirror": ("coherence", self._finite(opp.quantum_coherence, nonnegative=True)),
            "timeline_anchor": (
                "anchor_strength",
                self._finite(opp.timeline_anchor_strength, nonnegative=True),
            ),
        }
        scores = tuple(value for _, value in score_specs.values())
        price = self._finite(opp.price, positive=True)
        momentum = self._finite(opp.momentum, positive=True)
        volume = self._finite(opp.volume, positive=True)
        source_timestamp = self._finite(opp.source_timestamp, positive=True)
        received_at = self._finite(opp.received_at, positive=True)
        now = time.time()
        market_receipt = self._fresh_ticker_receipt(
            opp.market_receipt,
            symbol=opp.symbol,
            venue=opp.exchange,
        )
        valid_gate_receipts: Dict[str, Dict[str, Any]] = {}
        for gate_name, (score_key, expected_score) in score_specs.items():
            gate_receipt = self._score_receipt(
                opp.gate_receipts.get(gate_name),
                score_key=score_key,
                required_input_receipt_ids={str(opp.receipt_id or "")},
                symbol=opp.symbol,
                venue=opp.exchange,
            )
            if (
                gate_receipt is None
                or expected_score is None
                or not math.isclose(
                    float(gate_receipt[score_key]),
                    expected_score,
                    rel_tol=1e-12,
                    abs_tol=1e-12,
                )
            ):
                opp.ready_for_4th = False
                return None
            valid_gate_receipts[gate_name] = gate_receipt
        if (
            opp.truth_status != "real_derived"
            or opp.generated_values is not False
            or not opp.symbol
            or not opp.exchange
            or self.venue != opp.exchange
            or not opp.source_id
            or not opp.receipt_id
            or any(score is None or score > 1.0 for score in scores)
            or price is None
            or momentum is None
            or volume is None
            or market_receipt is None
            or str(market_receipt.get("receipt_id") or "") != opp.receipt_id
            or str(market_receipt.get("source_id") or "") != opp.source_id
            or not math.isclose(price, float(market_receipt["price"]), rel_tol=1e-12, abs_tol=1e-12)
            or not math.isclose(momentum, float(market_receipt["change_pct"]), rel_tol=1e-12, abs_tol=1e-12)
            or not math.isclose(
                volume,
                float(market_receipt["volume_24h"]) * price,
                rel_tol=1e-12,
                abs_tol=1e-12,
            )
            or source_timestamp is None
            or received_at is None
            or source_timestamp > received_at + 5.0
            or received_at > now + 5.0
            or now - source_timestamp > 300.0
            or now - received_at > 300.0
        ):
            opp.ready_for_4th = False
            return None
        # P1: Harmonic - based on momentum and golden ratio
        p1 = min(opp.momentum / (100 / PHI), 1.0)
        opp.p1_harmonic = p1
        
        # P2: Coherence - how aligned are all signals
        signals = [opp.stargate_resonance, opp.quantum_coherence, opp.timeline_anchor_strength]
        mean_signal = sum(signals) / len(signals)
        variance = sum((s - mean_signal)**2 for s in signals) / len(signals)
        p2 = 1.0 - min(variance * 2, 1.0)  # Low variance = high coherence
        opp.p2_coherence = p2
        
        # P3: Stability - volume and price stability
        p3 = min(math.log10(opp.volume + 1) / 5, 1.0)
        opp.p3_stability = p3
        
        # Batten Score: geometric mean
        batten = (p1 * p2 * p3) ** (1/3)
        opp.batten_score = batten
        batten_inputs = [
            str(opp.receipt_id),
            *[
                str(valid_gate_receipts[name]["receipt_id"])
                for name in ("stargate", "quantum_mirror", "timeline_anchor")
            ],
        ]
        batten_payload = {
            "symbol": opp.symbol,
            "venue": opp.exchange,
            "input_receipt_ids": batten_inputs,
            "p1_harmonic": p1,
            "p2_coherence": p2,
            "p3_stability": p3,
            "batten_score": batten,
        }
        opp.gate_receipts["batten"] = {
            **batten_payload,
            "status": "validated",
            "data_status": "derived_from_live",
            "truth_status": "real_derived",
            "generated_values": False,
            "eligible_for_action": False,
            "eligible_for_accounting": False,
            "eligible_for_learning": False,
            "source_id": "aureon:batten-matrix:v1",
            "source_timestamp": source_timestamp,
            "received_at": now,
            "receipt_id": self._derived_receipt_id("batten", batten_payload),
        }
        
        # Check if ready for 4th decision
        # All passes must be > 0.5 and coherence must be high
        coherence = 1 - (max(p1, p2, p3) - min(p1, p2, p3))
        opp.ready_for_4th = (p1 > 0.5 and p2 > 0.5 and p3 > 0.5 and coherence > PHI - 1)
        
        return batten
    
    def ask_queen(self, opp: Opportunity) -> Optional[float]:
        """Get Queen's confidence on this opportunity"""
        evaluator = getattr(self.queen, "ask_queen_will_we_win", None)
        if not callable(evaluator):
            return None
        try:
            guidance = evaluator(
                asset=opp.symbol,
                exchange=opp.exchange,
                opportunity_score=opp.batten_score,
                context={
                    'momentum': opp.momentum,
                    'stargate': opp.stargate_resonance,
                    'quantum': opp.quantum_coherence,
                    'timeline': opp.timeline_anchor_strength,
                    'input_receipt_ids': [
                        str(opp.receipt_id),
                        *[
                            str(receipt["receipt_id"])
                            for receipt in opp.gate_receipts.values()
                            if isinstance(receipt, Mapping)
                            and str(receipt.get("receipt_id") or "").strip()
                        ],
                    ],
                }
            )
        except Exception:
            return None
        required_ids = {
            str(opp.receipt_id or ""),
            *{
                str(gate.get("receipt_id") or "")
                for gate in opp.gate_receipts.values()
                if isinstance(gate, Mapping)
            },
        }
        validated = self._score_receipt(
            guidance,
            score_key="confidence",
            required_input_receipt_ids=required_ids,
            symbol=opp.symbol,
            venue=opp.exchange,
        )
        if validated is None:
            return None
        opp.gate_receipts["queen"] = validated
        return float(validated["confidence"])
    
    def validate_opportunities(self, opportunities: List[Opportunity]) -> List[Opportunity]:
        """Run full validation pipeline on all opportunities"""
        print("\n🔬 VALIDATING OPPORTUNITIES...")
        print("   Running: Stargate → Quantum Mirror → Timeline Anchor → Batten Matrix → Queen")
        
        validated = []
        for opp in opportunities:
            opp.stargate_resonance = None
            opp.quantum_coherence = None
            opp.timeline_anchor_strength = None
            opp.p1_harmonic = None
            opp.p2_coherence = None
            opp.p3_stability = None
            opp.batten_score = None
            opp.queen_confidence = None
            opp.final_score = None
            opp.ready_for_4th = False
            opp.actionable = False
            opp.accounting_eligible = False
            opp.learning_eligible = False
            opp.gate_receipts.clear()
            opp.validation_receipt = None
            # Layer 1: Stargate Resonance
            opp.stargate_resonance = self.validate_with_stargate(opp)
            
            # Layer 2: Quantum Mirror Coherence
            opp.quantum_coherence = self.validate_with_quantum_mirror(opp)
            
            # Layer 3: Timeline Anchor Strength
            opp.timeline_anchor_strength = self.validate_with_timeline_anchor(opp)

            if (
                opp.stargate_resonance is None
                or opp.quantum_coherence is None
                or opp.timeline_anchor_strength is None
            ):
                continue
            
            # Layer 4: Batten Matrix (3-pass)
            opp.batten_score = self.compute_batten_matrix(opp)
            if opp.batten_score is None:
                continue
            
            # Layer 5: Queen Confidence
            opp.queen_confidence = self.ask_queen(opp)
            if opp.queen_confidence is None:
                continue
            
            # Final Score
            opp.final_score = (
                opp.batten_score * 0.4 +
                opp.queen_confidence * 0.3 +
                opp.stargate_resonance * 0.1 +
                opp.quantum_coherence * 0.1 +
                opp.timeline_anchor_strength * 0.1
            )
            final_score = self._finite(opp.final_score, nonnegative=True)
            required_gate_names = (
                "stargate",
                "quantum_mirror",
                "timeline_anchor",
                "batten",
                "queen",
            )
            gate_receipt_ids = [
                str(opp.gate_receipts.get(name, {}).get("receipt_id") or "")
                for name in required_gate_names
            ]
            if (
                final_score is None
                or final_score > 1.0
                or any(not receipt_id for receipt_id in gate_receipt_ids)
                or len(set(gate_receipt_ids)) != len(gate_receipt_ids)
            ):
                opp.ready_for_4th = False
                continue
            validation_inputs = [str(opp.receipt_id), *gate_receipt_ids]
            validation_payload = {
                "symbol": opp.symbol,
                "venue": opp.exchange,
                "input_receipt_ids": validation_inputs,
                "final_score": final_score,
                "ready_for_4th": bool(opp.ready_for_4th),
            }
            opp.validation_receipt = {
                **validation_payload,
                "status": "validated",
                "data_status": "derived_from_live",
                "truth_status": "real_derived",
                "generated_values": False,
                "eligible_for_action": bool(opp.ready_for_4th and final_score > 0.5),
                "eligible_for_accounting": False,
                "eligible_for_learning": False,
                "source_id": "aureon:full-orchestrator-validation:v1",
                "source_timestamp": float(opp.source_timestamp),
                "received_at": time.time(),
                "receipt_id": self._derived_receipt_id(
                    "full-orchestrator-validation",
                    validation_payload,
                ),
            }
            opp.actionable = opp.validation_receipt["eligible_for_action"] is True
            opp.accounting_eligible = False
            opp.learning_eligible = False

            if final_score > 0.5:
                validated.append(opp)
        
        # Sort by final score
        validated.sort(key=lambda x: -x.final_score)
        
        self.state.opportunities_validated = len(validated)
        if not validated:
            self.last_no_data = self._no_data("complete_linked_hnc_auris_gate_receipts_required")
        print(f"   ✅ {len(validated)} opportunities passed validation")
        
        return validated
    
    def display_opportunities(self, opportunities: List[Opportunity], top_n: int = 10):
        """Display top opportunities with full validation details"""
        print(f"\n📊 TOP {min(top_n, len(opportunities))} VALIDATED OPPORTUNITIES:")
        print("-" * 80)
        print(f"{'Symbol':<12} {'Mom%':>6} {'P1':>5} {'P2':>5} {'P3':>5} {'Batten':>7} {'Queen':>6} {'Final':>6} {'4th?'}")
        print("-" * 80)
        
        for opp in opportunities[:top_n]:
            fourth = "✅" if opp.ready_for_4th else "⏳"
            print(f"{opp.symbol:<12} {opp.momentum:>6.1f} {opp.p1_harmonic:>5.2f} {opp.p2_coherence:>5.2f} {opp.p3_stability:>5.2f} {opp.batten_score:>7.3f} {opp.queen_confidence:>6.2f} {opp.final_score:>6.3f} {fourth}")
        
        print("-" * 80)
    
    def execute_trade(self, opp: Opportunity, live: bool = False) -> bool:
        """Submit or reconcile one receipted entry without duplicate submissions."""
        if self.state.active_position is not None:
            self.last_no_data = self._no_data("active_position_already_exists")
            return False
        validation_receipt = self._actionable_validation_receipt(opp)
        if validation_receipt is None:
            self.last_no_data = self._no_data(
                "complete_fresh_linked_validation_receipt_required"
            )
            return False
        if not live or not self.live_actions_enabled:
            self.last_no_data = self._no_data(
                "live_actions_not_authorized",
                status="not_submitted",
            )
            return False
        quote_currency = "USDC" if opp.symbol.endswith("USDC") else ""
        if not quote_currency:
            self.last_no_data = self._no_data("explicit_quote_currency_required")
            return False

        terminal: Optional[Dict[str, Any]] = None
        if self.pending_order is not None:
            if (
                self.pending_order.get("symbol") != opp.symbol
                or self.pending_order.get("side") != "BUY"
                or self.pending_order.get("venue") != opp.exchange
                or self.pending_order.get("validation_receipt_id")
                != validation_receipt["receipt_id"]
            ):
                self.last_no_data = self._no_data(
                    "another_order_is_pending_reconciliation"
                )
                return False
            order_id = str(self.pending_order.get("order_id") or "").strip()
            if not order_id:
                self.last_no_data = self._no_data(
                    "entry_submission_unreconcilable_without_order_id",
                    status="pending_reconciliation",
                )
                return False
            status_reader = getattr(self.client, "get_order_status", None)
            if not callable(status_reader):
                self.last_no_data = self._no_data(
                    "entry_order_status_receipt_adapter_required",
                    status="pending_reconciliation",
                )
                return False
            try:
                result = status_reader(order_id)
            except Exception:
                result = None
            terminal = self._terminal_fill(
                result,
                symbol=opp.symbol,
                side="BUY",
                venue=opp.exchange,
                expected_fee_currency=quote_currency,
                expected_order_id=order_id,
                expected_notional=float(self.pending_order["expected_notional"]),
            )
            if terminal is None:
                self.last_no_data = self._no_data(
                    "entry_terminal_receipt_pending_or_incomplete",
                    status="pending_reconciliation",
                )
                return False
        else:
            balance_reader = getattr(
                self.client,
                "get_account_balance_receipt",
                None,
            )
            if not callable(balance_reader):
                self.last_no_data = self._no_data(
                    "fresh_receipted_account_balance_adapter_required"
                )
                return False
            try:
                balance_receipt = balance_reader()
            except Exception:
                self.last_no_data = self._no_data(
                    "account_balance_receipt_request_failed"
                )
                return False
            balance = self._fresh_balance_receipt(
                balance_receipt,
                currency=quote_currency,
                venue=opp.exchange,
            )
            if balance is None:
                self.last_no_data = self._no_data(
                    "fresh_actionable_quote_balance_receipt_required"
                )
                return False
            if balance < 5:
                self.last_no_data = self._no_data(
                    "insufficient_receipted_quote_balance"
                )
                return False
            trade_amount = balance * 0.90
            order_writer = getattr(self.client, "place_market_order", None)
            if not callable(order_writer):
                self.last_no_data = self._no_data(
                    "market_order_submission_adapter_required"
                )
                return False
            try:
                submission = order_writer(
                    opp.symbol,
                    "buy",
                    quote_qty=trade_amount,
                )
            except Exception:
                submission = None
            terminal = self._terminal_fill(
                submission,
                symbol=opp.symbol,
                side="BUY",
                venue=opp.exchange,
                expected_fee_currency=quote_currency,
                expected_notional=trade_amount,
            )
            if terminal is None:
                self.pending_order = {
                    "order_id": (
                        str(submission.get("orderId") or "").strip()
                        if isinstance(submission, Mapping)
                        else ""
                    ),
                    "submission_receipt_id": (
                        str(submission.get("receipt_id") or "").strip()
                        if isinstance(submission, Mapping)
                        else ""
                    ),
                    "symbol": opp.symbol,
                    "side": "BUY",
                    "venue": opp.exchange,
                    "validation_receipt_id": validation_receipt["receipt_id"],
                    "expected_notional": trade_amount,
                }
                self.last_no_data = self._no_data(
                    "entry_submission_pending_terminal_receipt",
                    status="pending_reconciliation",
                )
                return False

        if terminal is None:
            self.last_no_data = self._no_data(
                "entry_terminal_receipt_pending_or_incomplete",
                status="pending_reconciliation",
            )
            return False
        self.pending_order = None
        source_timestamp = float(terminal["source_timestamp"])
        self.state.active_position = {
            "symbol": opp.symbol,
            "venue": opp.exchange,
            "entry_price": float(terminal["filled_avg_price"]),
            "quantity": float(terminal["filled_qty"]),
            "entry_cost": float(terminal["filled_notional"]),
            "entry_fee": float(terminal["fee"]),
            "entry_fee_currency": str(terminal["fee_currency"]),
            "entry_order_id": str(terminal["orderId"]),
            "entry_fill_receipt_id": str(terminal["receipt_id"]),
            "entry_source_id": str(terminal["source_id"]),
            "entry_trade_ids": [
                str(row["tradeId"])
                for row in terminal["fills"]
            ],
            "entry_time": datetime.fromtimestamp(source_timestamp).isoformat(),
            "source_timestamp": source_timestamp,
            "received_at": float(terminal["received_at"]),
            "truth_status": "real_observed",
            "generated_values": False,
            "validation_receipt_id": str(validation_receipt["receipt_id"]),
            "validation_score": opp.final_score,
        }
        self.state.trades_executed += 1
        self._save_state()
        return True
    def check_active_position(
        self,
        target_profit: float = 1.0,
        live: bool = False,
    ) -> Optional[float]:
        """Submit or reconcile one receipted exit without projected accounting."""
        if not self.state.active_position:
            return None
        pos = self.state.active_position
        if not isinstance(pos, Mapping):
            self.last_no_data = self._no_data("active_position_receipt_missing")
            return None

        symbol = str(pos.get("symbol") or "").strip().upper()
        venue = str(pos.get("venue") or "").strip().lower()
        quantity = self._finite(pos.get("quantity"), positive=True)
        entry_price = self._finite(pos.get("entry_price"), positive=True)
        entry_cost = self._finite(pos.get("entry_cost"), positive=True)
        entry_fee = self._finite(pos.get("entry_fee"), nonnegative=True)
        entry_fee_currency = str(pos.get("entry_fee_currency") or "").strip().upper()
        entry_order_id = str(pos.get("entry_order_id") or "").strip()
        entry_fill_receipt_id = str(
            pos.get("entry_fill_receipt_id") or ""
        ).strip()
        entry_source_id = str(pos.get("entry_source_id") or "").strip()
        raw_entry_trade_ids = pos.get("entry_trade_ids")
        if not isinstance(raw_entry_trade_ids, (list, tuple, set)):
            self.last_no_data = self._no_data(
                "complete_terminal_entry_receipt_required"
            )
            return None
        entry_trade_ids = [
            str(item).strip()
            for item in raw_entry_trade_ids
            if str(item).strip()
        ]
        validation_receipt_id = str(
            pos.get("validation_receipt_id") or ""
        ).strip()
        validation_score = self._finite(
            pos.get("validation_score"),
            nonnegative=True,
        )
        entry_source_timestamp = self._finite(
            pos.get("source_timestamp"),
            positive=True,
        )
        entry_received_at = self._finite(
            pos.get("received_at"),
            positive=True,
        )
        quote_currency = "USDC" if symbol.endswith("USDC") else ""
        if (
            pos.get("truth_status") != "real_observed"
            or pos.get("generated_values") is not False
            or not symbol
            or not venue
            or venue != self.venue
            or quantity is None
            or entry_price is None
            or entry_cost is None
            or entry_fee is None
            or entry_fee_currency != quote_currency
            or not entry_order_id
            or not entry_fill_receipt_id
            or not entry_source_id
            or not entry_trade_ids
            or len(set(entry_trade_ids)) != len(entry_trade_ids)
            or not validation_receipt_id
            or validation_score is None
            or validation_score > 1.0
            or entry_source_timestamp is None
            or entry_received_at is None
            or entry_source_timestamp > entry_received_at + 5.0
            or not math.isclose(
                entry_cost,
                quantity * entry_price,
                rel_tol=1e-9,
                abs_tol=1e-12,
            )
        ):
            self.last_no_data = self._no_data(
                "complete_terminal_entry_receipt_required"
            )
            return None

        def commit_exit(terminal_receipt: Mapping[str, Any]) -> float:
            sell_value = float(terminal_receipt["filled_notional"])
            exit_fee = float(terminal_receipt["fee"])
            profit = sell_value - entry_cost - entry_fee - exit_fee
            self.pending_order = None
            if profit > 0.0:
                self.state.trades_won += 1
            self.state.total_profit += profit
            self.state.active_position = None
            self._save_state()
            return profit

        # A previously submitted SELL is reconciled before any new quote read
        # or profit-threshold decision. This keeps one provider read per cycle
        # and prevents market movement from stranding an unresolved order.
        if self.pending_order is not None:
            if (
                self.pending_order.get("symbol") != symbol
                or self.pending_order.get("side") != "SELL"
                or self.pending_order.get("venue") != venue
                or self.pending_order.get("entry_fill_receipt_id")
                != entry_fill_receipt_id
            ):
                self.last_no_data = self._no_data(
                    "another_order_is_pending_reconciliation"
                )
                return None
            order_id = str(self.pending_order.get("order_id") or "").strip()
            if not order_id:
                self.last_no_data = self._no_data(
                    "exit_submission_unreconcilable_without_order_id",
                    status="pending_reconciliation",
                )
                return None
            status_reader = getattr(self.client, "get_order_status", None)
            if not callable(status_reader):
                self.last_no_data = self._no_data(
                    "exit_order_status_receipt_adapter_required",
                    status="pending_reconciliation",
                )
                return None
            try:
                result = status_reader(order_id)
            except Exception:
                result = None
            terminal = self._terminal_fill(
                result,
                symbol=symbol,
                side="SELL",
                venue=venue,
                expected_fee_currency=quote_currency,
                expected_order_id=order_id,
                expected_qty=quantity,
            )
            if terminal is None:
                self.last_no_data = self._no_data(
                    "exit_terminal_receipt_pending_or_incomplete",
                    status="pending_reconciliation",
                )
                return None
            return commit_exit(terminal)

        ticker_reader = getattr(self.client, "get_ticker_receipt", None)
        if not callable(ticker_reader):
            self.last_no_data = self._no_data(
                "fresh_exit_quote_receipt_adapter_required"
            )
            return None
        try:
            ticker = self._fresh_ticker_receipt(
                ticker_reader(symbol),
                symbol=symbol,
                venue=venue,
            )
        except Exception:
            ticker = None
        if ticker is None:
            self.last_no_data = self._no_data(
                "fresh_exit_quote_receipt_required"
            )
            return None
        current_price = self._finite(ticker.get("bid"), positive=True)
        if current_price is None:
            self.last_no_data = self._no_data("fresh_exit_bid_required")
            return None
        current_value = quantity * current_price
        pre_exit_fee_pnl = current_value - entry_cost - entry_fee
        pnl_pct = (pre_exit_fee_pnl / entry_cost) * 100
        if pnl_pct < target_profit:
            return None
        if not live or not self.live_actions_enabled:
            self.last_no_data = self._no_data(
                "live_actions_not_authorized",
                status="not_submitted",
            )
            return None

        order_writer = getattr(self.client, "place_market_order", None)
        if not callable(order_writer):
            self.last_no_data = self._no_data(
                "market_order_submission_adapter_required"
            )
            return None
        try:
            submission = order_writer(
                symbol,
                "sell",
                quantity=quantity,
            )
        except Exception:
            submission = None
        terminal = self._terminal_fill(
            submission,
            symbol=symbol,
            side="SELL",
            venue=venue,
            expected_fee_currency=quote_currency,
            expected_qty=quantity,
        )
        if terminal is None:
            self.pending_order = {
                "order_id": (
                    str(submission.get("orderId") or "").strip()
                    if isinstance(submission, Mapping)
                    else ""
                ),
                "submission_receipt_id": (
                    str(submission.get("receipt_id") or "").strip()
                    if isinstance(submission, Mapping)
                    else ""
                ),
                "symbol": symbol,
                "side": "SELL",
                "venue": venue,
                "entry_fill_receipt_id": entry_fill_receipt_id,
                "expected_qty": quantity,
                "quote_receipt_id": str(ticker["receipt_id"]),
            }
            self.last_no_data = self._no_data(
                "exit_submission_pending_terminal_receipt",
                status="pending_reconciliation",
            )
            return None
        return commit_exit(terminal)
    def _trigger_gamma_sync(self):
        """Triggers the gammaSync.ts script if enough time has passed."""
        now = datetime.now()
        sync_needed = False
        
        if self.state.last_gamma_sync:
            last_sync_time = datetime.fromisoformat(self.state.last_gamma_sync)
            if (now - last_sync_time) > timedelta(minutes=30):
                sync_needed = True
        else:
            # First time running
            sync_needed = True

        if sync_needed:
            print("\n🔄 Triggering Gamma.io Sync...")
            if not callable(self.gamma_sync_runner):
                self.last_no_data = self._no_data("explicit_receipted_gamma_sync_runner_required")
                return False
            try:
                receipt = self.gamma_sync_runner()
            except Exception:
                self.last_no_data = self._no_data("gamma_sync_runner_failed")
                return False
            source_timestamp = self._finite(
                receipt.get("source_timestamp") if isinstance(receipt, Mapping) else None,
                positive=True,
            )
            received_at = self._finite(
                receipt.get("received_at") if isinstance(receipt, Mapping) else None,
                positive=True,
            )
            source_id = str(receipt.get("source_id") or "").strip() if isinstance(receipt, Mapping) else ""
            receipt_id = str(receipt.get("receipt_id") or "").strip() if isinstance(receipt, Mapping) else ""
            receipt_clock = time.time()
            if (
                not isinstance(receipt, Mapping)
                or receipt.get("status") != "completed"
                or receipt.get("truth_status") not in {"real_observed", "real_derived"}
                or receipt.get("generated_values") is not False
                or not source_id
                or not receipt_id
                or source_timestamp is None
                or received_at is None
                or source_timestamp > received_at + 5.0
                or received_at > receipt_clock + 5.0
                or receipt_clock - source_timestamp > 300.0
                or receipt_clock - received_at > 300.0
            ):
                self.last_no_data = self._no_data("complete_gamma_sync_receipt_required")
                return False
            self.state.last_gamma_sync = datetime.fromtimestamp(source_timestamp).isoformat()
            print("   ✅ Gamma sync completed with receipt.")
        return True

    def run_cycle(self, live: bool = False, target_profit: float = 1.0):
        """Run one complete orchestration cycle"""
        print("\n" + "="*70)
        print(f"🌍 AUREON ORCHESTRATOR CYCLE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        # 0. Trigger background syncs
        self._trigger_gamma_sync()

        # 1. Check active position first
        self.check_active_position(target_profit=target_profit, live=live)
        cycle_source_timestamp = None

        # 2. If no position or sold, find new opportunities
        if not self.state.active_position:
            # Scan
            opportunities = self.scan_opportunities()
            # Validate
            validated = self.validate_opportunities(opportunities)
            accepted_timestamps = [
                float(item.source_timestamp)
                for item in validated
                if (
                    item.validation_receipt is not None
                    and self._finite(item.source_timestamp, positive=True) is not None
                )
            ]
            if accepted_timestamps:
                cycle_source_timestamp = max(accepted_timestamps)
            
            # Display
            if validated:
                self.display_opportunities(validated)
                
                # Execute best if ready
                best = validated[0]
                if best.ready_for_4th:
                    self.execute_trade(best, live=live)
            else:
                print("\n⏳ No validated opportunities right now")
        
        # 3. Summary
        print(f"\n📊 SESSION SUMMARY:")
        print(f"   Scanned: {self.state.opportunities_scanned}")
        print(f"   Validated: {self.state.opportunities_validated}")
        print(f"   Trades: {self.state.trades_executed}")
        print(f"   Wins: {self.state.trades_won}")
        print(f"   Profit: ${self.state.total_profit:.2f}")
        
        if cycle_source_timestamp is not None:
            self.state.last_scan = datetime.fromtimestamp(cycle_source_timestamp).isoformat()
        else:
            self.last_no_data = self._no_data("cycle_has_no_fresh_provider_source_receipt")
    
    def run_continuous(self, live: bool = False, interval: int = 60, target: float = 1.0):
        """Run continuous orchestration loop"""
        print(f"\n🔄 CONTINUOUS MODE - Every {interval}s | Target: {target}%")
        print("   Press Ctrl+C to stop\n")
        
        cycle = 0
        while True:
            try:
                cycle += 1
                self.run_cycle(live=live, target_profit=target)
                
                print(f"\n⏳ Next cycle in {interval}s...")
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\n\n🛑 Stopped by user")
                print(f"Final: {self.state.trades_won} wins, ${self.state.total_profit:.2f} profit")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                time.sleep(interval)


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    
    parser = argparse.ArgumentParser(description='Aureon Full Orchestrator')
    parser.add_argument('--run', action='store_true', help='Explicitly initialize provider and subsystem dependencies')
    parser.add_argument('--live', action='store_true', help='Enable live trading')
    parser.add_argument('--confirmation', help='Exact live authorization token')
    parser.add_argument('--continuous', action='store_true', help='Run continuously')
    parser.add_argument('--interval', type=int, default=60, help='Check interval')
    parser.add_argument('--target', type=float, default=1.0, help='Target profit %')
    parser.add_argument('--state-path')
    parser.add_argument('--persist-state', action='store_true')

    args = parser.parse_args(argv)
    if not args.run:
        print("NO_DATA: default invocation is inert; no provider or subsystem was initialized.")
        return 0
    if args.live and args.confirmation != LIVE_CONFIRMATION:
        print("NO_DATA: exact live confirmation token is required.")
        return 2
    if args.persist_state and not args.state_path:
        print("NO_DATA: an explicit state path is required for persistence.")
        return 2

    orchestrator = AureonFullOrchestrator(
        state_path=Path(args.state_path) if args.state_path else None,
        persist_state=args.persist_state,
        live_actions_enabled=args.live,
    )
    
    if not orchestrator.initialize_systems():
        print("❌ Failed to initialize systems")
        return 1
    
    if args.continuous:
        orchestrator.run_continuous(
            live=args.live, 
            interval=args.interval, 
            target=args.target
        )
    else:
        orchestrator.run_cycle(live=args.live, target_profit=args.target)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
