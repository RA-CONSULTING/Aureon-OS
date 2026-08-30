#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║     📊 TRADE LOGGER & PROBABILITY MATRIX DATA VALIDATOR 📊                           ║
║     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                ║
║                                                                                      ║
║     Comprehensive logging for:                                                      ║
║       • Every trade executed (entry/exit timestamps)                                 ║
║       • Probability matrix predictions vs actual outcomes                            ║
║       • HNC frequency harmonics during each trade                                    ║
║       • Full market sweep verification                                               ║
║       • Cross-reference trader data with market conditions                           ║
║                                                                                      ║
║     Output: JSONL files for analysis & ML training                                   ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import json
import time
import logging
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from pathlib import Path
import threading
from collections import defaultdict

# Configure logging with safe UTF-8/ASCII handling
class SafeUTF8Formatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        # On Windows, if stdout is not UTF-8, we might still crash when printing
        # even if we return a string here. The crash happens in stream.write().
        # So we should try to ensure the stream handles it, or strip chars if needed.
        return msg

# Custom StreamHandler that forces UTF-8 encoding on Windows
class SafeStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            if getattr(stream, 'closed', False):
                return
            # If on Windows and stream has a buffer, write bytes directly to bypass cp1252
            if os.name == 'nt' and hasattr(stream, 'buffer'):
                try:
                    if getattr(stream.buffer, 'closed', False):
                        return
                except (ValueError, AttributeError):
                    return
                stream.buffer.write((msg + self.terminator).encode('utf-8'))
                stream.flush()
            else:
                stream.write(msg + self.terminator)
                self.flush()
        except (ValueError, OSError, IOError):
            return
        except Exception:
            self.handleError(record)

# Use sys.stdout explicitly which should be wrapped by now if running from main
import sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_TRUE_VALUES = {"1", "true", "yes", "on"}


def _operational_writes_suppressed() -> bool:
    """Return True for audit/import probes that must not create runtime files."""
    return any(
        os.getenv(name, "").strip().lower() in _TRUE_VALUES
        for name in ("AUREON_AUDIT_MODE", "AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS")
    )

# Configure handlers if not already set
if not logger.handlers:
    # Console Handler (Safe for Windows)
    stream_handler = SafeStreamHandler(sys.stdout)
    stream_handler.setFormatter(SafeUTF8Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logger.addHandler(stream_handler)

# Prevent propagation to root to avoid double logging or using unsafe root handlers
logger.propagate = False


@dataclass
class TradeEntry:
    """Complete record of a single trade"""
    timestamp: str
    symbol: str
    side: str  # BUY/SELL
    exchange: str
    entry_price: float
    entry_time: float
    quantity: float
    entry_value: float
    coherence: float
    dominant_node: str
    hnc_frequency: float
    hnc_is_harmonic: bool
    probability_score: float
    imperial_probability: float
    cosmic_phase: str
    earth_coherence: float
    gates_passed: int
    # Exchange order tracking
    order_id: str = ""  # Exchange order ID (txid for Kraken, id for Alpaca, orderId for Binance)
    order_status: str = ""  # filled, partial, pending, rejected
    
@dataclass
class TradeExit:
    """Exit record for a trade"""
    trade_id: str
    timestamp: str
    symbol: str
    exit_price: float
    exit_time: float
    exit_value: float
    gross_pnl: float
    net_pnl: float
    pnl_pct: float
    fees: float
    reason: str  # TP/SL/REBALANCE/etc
    hold_time_seconds: float
    hold_time_minutes: float
    # Exchange order tracking
    order_id: str = ""  # Exchange order ID for exit
    order_status: str = ""
    
@dataclass
class ProbabilityValidation:
    """Cross-reference actual outcomes with predictions"""
    symbol: str
    entry_timestamp: str
    exit_timestamp: str
    predicted_probability: float
    predicted_action: str  # BUY/SELL/HOLD
    actual_outcome: str  # WIN/LOSS
    outcome_pct: float
    validation_1m: Optional[bool] = None  # Did 1m prediction match?
    validation_5m: Optional[bool] = None  # Did 5m prediction match?
    frequency_band: str = ""  # 174/256/396/432/440/etc
    coherence_level: str = ""  # LOW/MEDIUM/HIGH
    
@dataclass
class MarketSweepRecord:
    """Full market conditions during trading period"""
    timestamp: str
    total_opportunities_found: int
    opportunities_entered: int
    opportunities_rejected: int
    rejection_reasons: Dict[str, int] = field(default_factory=dict)  # {reason: count}
    hissing_frequencies: List[float] = field(default_factory=list)  # 440Hz distortion
    harmonic_frequencies: List[float] = field(default_factory=list)  # 256/528Hz
    average_coherence: float = 0.0
    system_flux: str = ""  # BULLISH/BEARISH/NEUTRAL
    dominant_node_distribution: Dict[str, int] = field(default_factory=dict)

class TradeLogger:
    """Comprehensive trade logging system"""
    
    def __init__(
        self,
        output_dir: Optional[str] = None,
        log_path: Optional[str] = None,
    ):
        if output_dir is None:
            output_dir = os.getenv("AUREON_TRADE_LOG_DIR") or os.path.join(
                tempfile.gettempdir(), "aureon_trade_logs"
            )
        self.output_dir = Path(output_dir)
        configured_log_path = log_path or os.getenv("AUREON_TRADE_LOG_PATH")
        self.log_path = Path(configured_log_path) if configured_log_path else self.output_dir / "trade_logger.log"
        self._persistence_suppressed = _operational_writes_suppressed()
        self._persistence_active = False
        
        # Initialize output files
        self.trades_file = self.output_dir / f"trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        self.exits_file = self.output_dir / f"exits_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        self.validations_file = self.output_dir / f"validations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        self.market_sweep_file = self.output_dir / f"market_sweep_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        # CRITICAL: Execution log for exchange order IDs
        self.executions_file = self.output_dir / f"executions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        
        # In-memory tracking
        self.active_trades: Dict[str, Dict] = {}  # {trade_id: trade_data}
        self.trade_counter = 0
        self.lock = threading.Lock()
        
        logger.info(f"📊 Trade Logger initialized")
        logger.info(f"   Output directory: {self.output_dir}")
        logger.info(f"   Trades file: {self.trades_file.name}")

    def _activate_persistence(self) -> bool:
        """Create runtime paths and the file handler only on the first real write."""
        if self._persistence_suppressed:
            return False
        if self._persistence_active:
            return True

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        resolved = str(self.log_path.resolve())
        if not any(
            isinstance(handler, logging.FileHandler)
            and getattr(handler, "_aureon_trade_log_path", None) == resolved
            for handler in logger.handlers
        ):
            file_handler = logging.FileHandler(self.log_path, encoding="utf-8")
            file_handler._aureon_trade_log_path = resolved
            file_handler.setFormatter(
                SafeUTF8Formatter("%(asctime)s [%(levelname)s] %(message)s")
            )
            logger.addHandler(file_handler)
        self._persistence_active = True
        return True

    def _append_jsonl(self, path: Path, payload: Dict[str, Any]) -> bool:
        if not self._activate_persistence():
            return False
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")
        return True
        
    def log_trade_entry(self, trade_data: Dict[str, Any]) -> str:
        """Log a trade entry and return trade_id"""
        with self.lock:
            self.trade_counter += 1
            trade_id = f"TRADE_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.trade_counter:06d}"
        
        entry = TradeEntry(
            timestamp=datetime.now().isoformat(),
            symbol=trade_data.get('symbol', 'UNKNOWN'),
            side=trade_data.get('side', 'BUY'),
            exchange=trade_data.get('exchange', 'kraken'),
            entry_price=trade_data.get('entry_price', 0.0),
            entry_time=trade_data.get('entry_time', time.time()),
            quantity=trade_data.get('quantity', 0.0),
            entry_value=trade_data.get('entry_value', 0.0),
            coherence=trade_data.get('coherence', 0.5),
            dominant_node=trade_data.get('dominant_node', 'Unknown'),
            hnc_frequency=trade_data.get('hnc_frequency', 256.0),
            hnc_is_harmonic=trade_data.get('hnc_is_harmonic', False),
            probability_score=trade_data.get('probability_score', 0.5),
            imperial_probability=trade_data.get('imperial_probability', 0.5),
            cosmic_phase=trade_data.get('cosmic_phase', 'UNKNOWN'),
            earth_coherence=trade_data.get('earth_coherence', 0.5),
            gates_passed=trade_data.get('gates_passed', 0),
        )
        
        # Store for later exit matching
        with self.lock:
            self.active_trades[trade_id] = asdict(entry)
        
        self._append_jsonl(self.trades_file, {
            'trade_id': trade_id,
            **asdict(entry),
        })
        
        logger.info(f"📝 Trade Entry: {trade_id} | {entry.symbol} @ {entry.entry_price:.6f} | Γ={entry.coherence:.2f}")
        
        return trade_id
    
    def log_trade_exit(self, trade_id: str, exit_data: Dict[str, Any]) -> None:
        """Log trade exit and calculate P&L"""
        exit_record = TradeExit(
            trade_id=trade_id,
            timestamp=datetime.now().isoformat(),
            symbol=exit_data.get('symbol', 'UNKNOWN'),
            exit_price=exit_data.get('exit_price', 0.0),
            exit_time=exit_data.get('exit_time', time.time()),
            exit_value=exit_data.get('exit_value', 0.0),
            gross_pnl=exit_data.get('gross_pnl', 0.0),
            net_pnl=exit_data.get('net_pnl', 0.0),
            pnl_pct=exit_data.get('pnl_pct', 0.0),
            fees=exit_data.get('fees', 0.0),
            reason=exit_data.get('reason', 'UNKNOWN'),
            hold_time_seconds=exit_data.get('hold_time_seconds', 0.0),
            hold_time_minutes=exit_data.get('hold_time_seconds', 0.0) / 60.0,
        )
        
        self._append_jsonl(self.exits_file, asdict(exit_record))
        
        # Remove from active trades
        with self.lock:
            if trade_id in self.active_trades:
                del self.active_trades[trade_id]
        
        result = "✅ WIN" if exit_record.net_pnl > 0 else "❌ LOSS"
        logger.info(f"📊 Trade Exit: {trade_id} | {result} | P&L: ${exit_record.net_pnl:+.2f} ({exit_record.pnl_pct:+.2f}%) | Reason: {exit_record.reason}")

        # Feed outcome into Autonomy Hub feedback loop (closes the learning circle)
        try:
            from aureon.autonomous.aureon_autonomy_hub import get_autonomy_hub
            hub = get_autonomy_hub()
            hub.record_trade_outcome({
                'symbol': exit_record.symbol,
                'net_pnl': exit_record.net_pnl,
                'pnl_pct': exit_record.pnl_pct,
                'total_fees': exit_record.fees,
                'exchange': self.active_trades.get(trade_id, {}).get('exchange', 'unknown'),
            })
        except Exception:
            pass  # Hub not available yet

        # Feed outcome into War Planner (adversarial chess learning)
        try:
            from aureon.command_centers.aureon_strategic_war_planner import get_war_planner
            planner = get_war_planner()
            planner.record_outcome(exit_record.symbol, exit_record.net_pnl)
        except Exception:
            pass  # War Planner not available yet
    
    def log_execution(self, execution_type: str, exchange: str, symbol: str, 
                      side: str, order_id: str, quantity: float = 0.0,
                      price: float = 0.0, value_usd: float = 0.0,
                      status: str = "executed", raw_response: Dict = None,
                      error: str = None) -> None:
        """
        📝 Log every exchange execution with order ID for verification.
        
        Args:
            execution_type: 'BUY', 'SELL', 'CONVERT', 'CANCEL'
            exchange: 'kraken', 'binance', 'alpaca', 'capital'
            symbol: Trading pair (e.g., 'BTC/USD', 'ETHUSD')
            side: 'buy' or 'sell'
            order_id: Exchange order ID (txid for Kraken, id for Alpaca, orderId for Binance)
            quantity: Amount of base asset
            price: Execution price
            value_usd: Total value in USD
            status: 'executed', 'pending', 'rejected', 'cancelled', 'partial'
            raw_response: Raw exchange response (optional, for debugging)
            error: Error message if failed
        """
        execution_record = {
            "type": "execution",
            "timestamp": datetime.now().isoformat(),
            "unix_time": time.time(),
            "execution_type": execution_type.upper(),
            "exchange": exchange.lower(),
            "symbol": symbol,
            "side": side.lower(),
            "order_id": order_id or "UNKNOWN",
            "quantity": quantity,
            "price": price,
            "value_usd": value_usd,
            "status": status,
            "error": error,
        }
        
        # Include raw response for debugging (sanitized)
        if raw_response:
            # Don't include sensitive data
            safe_response = {k: v for k, v in raw_response.items() 
                           if k not in ['api_key', 'signature', 'secret']}
            execution_record["raw_response"] = safe_response
        
        self._append_jsonl(self.executions_file, execution_record)
        self._append_jsonl(self.trades_file, execution_record)
        
        # Log to console with clear visibility
        status_icon = "✅" if status in ["executed", "filled"] else "⚠️" if status == "partial" else "❌"
        order_short = (order_id[:12] + "...") if order_id and len(order_id) > 12 else order_id
        
        log_msg = (
            f"{status_icon} EXECUTION | {execution_type.upper()} | {exchange.upper()} | "
            f"{symbol} | {side.upper()} | Qty: {quantity:.6f} | Price: ${price:.4f} | "
            f"Value: ${value_usd:.2f} | OrderID: {order_short} | Status: {status}"
        )
        
        if error:
            logger.error(f"{log_msg} | ERROR: {error}")
        else:
            logger.info(log_msg)
    
    def log_conversion(self, exchange: str, from_asset: str, to_asset: str,
                       from_amount: float, to_amount: float, order_id: str,
                       status: str = "executed", fee: float = 0.0) -> None:
        """Log a conversion (swap) between assets."""
        self.log_execution(
            execution_type="CONVERT",
            exchange=exchange,
            symbol=f"{from_asset}/{to_asset}",
            side="convert",
            order_id=order_id,
            quantity=from_amount,
            price=to_amount / from_amount if from_amount > 0 else 0,
            value_usd=0,  # Would need price lookup
            status=status,
            raw_response={
                "from_asset": from_asset,
                "to_asset": to_asset,
                "from_amount": from_amount,
                "to_amount": to_amount,
                "fee": fee
            }
        )
    
    def log_probability_validation(self, validation_data: Dict[str, Any]) -> None:
        """Log prediction vs actual outcome for ML training"""
        validation = ProbabilityValidation(
            symbol=validation_data.get('symbol', 'UNKNOWN'),
            entry_timestamp=validation_data.get('entry_timestamp', datetime.now().isoformat()),
            exit_timestamp=validation_data.get('exit_timestamp', datetime.now().isoformat()),
            predicted_probability=validation_data.get('predicted_probability', 0.5),
            predicted_action=validation_data.get('predicted_action', 'HOLD'),
            actual_outcome=validation_data.get('actual_outcome', 'UNKNOWN'),
            outcome_pct=validation_data.get('outcome_pct', 0.0),
            validation_1m=validation_data.get('validation_1m'),
            validation_5m=validation_data.get('validation_5m'),
            frequency_band=validation_data.get('frequency_band', ''),
            coherence_level=validation_data.get('coherence_level', ''),
        )
        
        self._append_jsonl(self.validations_file, asdict(validation))
        
        accuracy = "✅" if (validation.predicted_action == 'BUY' and validation.actual_outcome == 'WIN') else "❌"
        logger.info(f"📈 Validation: {accuracy} {validation.symbol} | Pred: {validation.predicted_action} | Actual: {validation.actual_outcome} ({validation.outcome_pct:+.2f}%)")
    
    def log_market_sweep(self, sweep_data: Dict[str, Any]) -> None:
        """Log full market analysis snapshot"""
        sweep = MarketSweepRecord(
            timestamp=datetime.now().isoformat(),
            total_opportunities_found=sweep_data.get('total_opportunities_found', 0),
            opportunities_entered=sweep_data.get('opportunities_entered', 0),
            opportunities_rejected=sweep_data.get('opportunities_rejected', 0),
            rejection_reasons=sweep_data.get('rejection_reasons', {}),
            hissing_frequencies=sweep_data.get('hissing_frequencies', []),
            harmonic_frequencies=sweep_data.get('harmonic_frequencies', []),
            average_coherence=sweep_data.get('average_coherence', 0.0),
            system_flux=sweep_data.get('system_flux', 'NEUTRAL'),
            dominant_node_distribution=sweep_data.get('dominant_node_distribution', {}),
        )
        
        self._append_jsonl(self.market_sweep_file, asdict(sweep))
        
        logger.info(f"🌍 Market Sweep: Found {sweep.total_opportunities_found} opp | Entered {sweep.opportunities_entered} | Γ_avg={sweep.average_coherence:.2f} | Flux: {sweep.system_flux}")
    
    def get_trade_summary(self) -> Dict[str, Any]:
        """Get summary statistics of logged trades"""
        # Count files
        trade_count = sum(1 for line in open(self.trades_file, encoding='utf-8')) if self.trades_file.exists() else 0
        exit_count = sum(1 for line in open(self.exits_file, encoding='utf-8')) if self.exits_file.exists() else 0
        validation_count = sum(1 for line in open(self.validations_file, encoding='utf-8')) if self.validations_file.exists() else 0
        
        return {
            'total_trades_entered': trade_count,
            'total_trades_exited': exit_count,
            'active_trades': len(self.active_trades),
            'validations_recorded': validation_count,
            'trades_file': str(self.trades_file),
            'exits_file': str(self.exits_file),
            'validations_file': str(self.validations_file),
            'market_sweep_file': str(self.market_sweep_file),
        }
    
    def export_training_data(self, output_file: str = None) -> str:
        """Export all data in ML-friendly format"""
        if output_file is None:
            output_file = self.output_dir / f"training_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        
        # Merge trades + exits + validations
        training_records = []
        
        try:
            with open(self.trades_file, encoding='utf-8') as f:
                trades = [json.loads(line) for line in f]
            
            with open(self.exits_file, encoding='utf-8') as f:
                exits = {line['trade_id']: json.loads(line) for line in f if 'trade_id' in line}
        except:
            trades = []
            exits = {}
        
        # Combine
        for trade in trades:
            trade_id = trade.get('trade_id')
            exit_data = exits.get(trade_id)
            
            if exit_data:
                record = {
                    **trade,
                    **exit_data,
                    'completed': True
                }
            else:
                record = {
                    **trade,
                    'completed': False
                }
            
            training_records.append(record)
        
        if self._activate_persistence():
            with open(output_file, 'w', encoding='utf-8') as f:
                for record in training_records:
                    f.write(json.dumps(record) + '\n')
        
        logger.info(f"💾 Exported {len(training_records)} training records to {output_file}")
        return str(output_file)

# Global logger instance
_trade_logger = None

def get_trade_logger() -> TradeLogger:
    """Get or create global trade logger"""
    global _trade_logger
    if _trade_logger is None:
        _trade_logger = TradeLogger()
    return _trade_logger

if __name__ == '__main__':
    logger = get_trade_logger()
    
    # Test logging
    logger.log_trade_entry({
        'symbol': 'BTCUSD',
        'side': 'BUY',
        'exchange': 'kraken',
        'entry_price': 95000.0,
        'quantity': 0.01,
        'entry_value': 950.0,
        'coherence': 0.65,
        'dominant_node': 'Tiger',
        'hnc_frequency': 256.0,
        'hnc_is_harmonic': True,
        'probability_score': 0.72,
        'imperial_probability': 0.68,
        'cosmic_phase': 'ALIGNMENT',
        'earth_coherence': 0.78,
        'gates_passed': 4,
    })
    
    logger.log_market_sweep({
        'total_opportunities_found': 45,
        'opportunities_entered': 3,
        'opportunities_rejected': 42,
        'average_coherence': 0.58,
        'system_flux': 'BULLISH',
        'harmonic_frequencies': [256.0, 528.0, 396.0],
    })
    
    print("\n✅ Trade Logger initialized and ready for integration")
