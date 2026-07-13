#!/usr/bin/env python3
"""
AUREON UNIFIED LIVE DASHBOARD - Real-Time Trading Command Center
═══════════════════════════════════════════════════════════════════════════════

ONE dashboard to rule them all. Clean, focused, streaming real metrics.

CORE PRINCIPLES:
    - Simplify: 3 tabs (Trading, Intelligence, Systems) instead of 6+
    - Stream: WebSocket broadcasts real metrics every 1-5 seconds
    - Integrate: ThoughtBus bridge for all system events
    - Consistency: Uses same logic as Batten Matrix/Queen systems
    - Performance: Lazy system loading, efficient broadcasting

ARCHITECTURE:
    Backend: aiohttp + WebSocket (/live)
    Bridge: ThoughtBus → WebSocket event stream
    Frontend: Clean HTML + vanilla JS (no framework bloat)
    Metrics: Portfolio, P&L, Positions, Trades, Bots, Systems

TABS:
    1. TRADING - Portfolio totals, positions, recent trades, P&L
    2. INTELLIGENCE - Bot detection, whale sonar, firm tracking
    3. SYSTEMS - Exchange health, validation pipeline, ThoughtBus

Gary Leckey & GitHub Copilot | 2026
═══════════════════════════════════════════════════════════════════════════════
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os

# Windows UTF-8 fix
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

import asyncio
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Set, Any, Optional
from pathlib import Path
from aiohttp import web

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Sacred constants
import math
PHI = (1 + math.sqrt(5)) / 2  # 1.618... Golden ratio


# ═══════════════════════════════════════════════════════════════════════════════
# THOUGHTBUS BRIDGE - Stream Real Events to WebSocket
# ═══════════════════════════════════════════════════════════════════════════════

class ThoughtBusBridge:
    """
    Bridge between ThoughtBus (internal pub/sub) and WebSocket (external clients).
    
    Subscribes to critical topics and broadcasts to all connected WebSocket clients.
    """
    
    def __init__(self, dashboard):
        self.dashboard = dashboard
        self.thought_bus = None
        self.subscriptions = []
        
    def initialize(self):
        """Initialize ThoughtBus connection and subscriptions."""
        try:
            from aureon.core.aureon_thought_bus import get_thought_bus
            self.thought_bus = get_thought_bus()
            
            # Subscribe to critical topics
            topics = [
                "market.*",           # Market data updates
                "execution.*",        # Trade executions
                "system.*",           # System health
                "whale.sonar.*",      # Whale/subsystem signals
                "harvest.*",          # Avalanche harvester events
                "validation.*",       # Queen validation pipeline
                "bot.*",              # Bot detection
                "position.*",         # Position updates
            ]
            
            for topic in topics:
                sub_id = self.thought_bus.subscribe(topic, self._on_thought)
                self.subscriptions.append(sub_id)
            
            logger.info(f"✓ ThoughtBus bridge initialized ({len(topics)} topics)")
            return True
            
        except Exception as e:
            logger.warning(f"ThoughtBus not available: {e}")
            return False
    
    async def _on_thought(self, thought):
        """Handle incoming thought from ThoughtBus."""
        try:
            # Convert thought to WebSocket message
            msg = self._thought_to_message(thought)
            if msg:
                await self.dashboard.broadcast(msg)
        except Exception as e:
            logger.debug(f"Failed to process thought: {e}")
    
    def _thought_to_message(self, thought) -> Optional[Dict]:
        """Convert ThoughtBus thought to WebSocket message."""
        try:
            topic = thought.topic
            payload = thought.payload
            
            # Market updates
            if topic.startswith("market."):
                return {
                    "type": "market_update",
                    "data": payload,
                    "timestamp": thought.ts
                }
            
            # Trade executions
            elif topic.startswith("execution."):
                return {
                    "type": "trade_executed",
                    "data": payload,
                    "timestamp": thought.ts
                }
            
            # Harvest events
            elif topic.startswith("harvest."):
                return {
                    "type": "harvest_event",
                    "data": payload,
                    "timestamp": thought.ts
                }
            
            # Bot detection
            elif topic.startswith("bot."):
                return {
                    "type": "bot_detected",
                    "data": payload,
                    "timestamp": thought.ts
                }
            
            # Whale sonar
            elif topic.startswith("whale.sonar."):
                return {
                    "type": "whale_signal",
                    "data": payload,
                    "timestamp": thought.ts
                }
            
            # System health
            elif topic.startswith("system."):
                return {
                    "type": "system_health",
                    "data": payload,
                    "timestamp": thought.ts
                }
            
            # Validation pipeline
            elif topic.startswith("validation."):
                return {
                    "type": "validation_update",
                    "data": payload,
                    "timestamp": thought.ts
                }
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to convert thought: {e}")
            return None


# ═══════════════════════════════════════════════════════════════════════════════
# UNIFIED DASHBOARD SERVER
# ═══════════════════════════════════════════════════════════════════════════════

class AureonUnifiedDashboard:
    """
    Unified live dashboard with real-time metric streaming.
    
    Consolidates portfolio, intelligence, and system monitoring into ONE interface.
    """
    
    def __init__(self, port: int = 8080, host: str = '0.0.0.0'):
        self.port = port
        self.host = host
        self.app = web.Application()
        self.clients: Set[web.WebSocketResponse] = set()
        
        # ThoughtBus bridge
        self.thought_bridge = ThoughtBusBridge(self)
        
        # Lazy-loaded systems (avoid blocking imports at startup)
        self._queen = None
        self._cost_basis = None
        self._harvester = None
        self._kraken = None
        self._alpaca = None
        self._binance = None
        self._capital = None
        
        # Metrics cache
        self.last_metrics = {}
        self.last_update = 0
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup HTTP and WebSocket routes."""
        self.app.router.add_get('/', self.handle_index)
        self.app.router.add_get('/live', self.handle_websocket)
        self.app.router.add_get('/api/portfolio', self.handle_portfolio_api)
        self.app.router.add_get('/api/systems', self.handle_systems_api)
        self.app.router.add_get('/api/intelligence', self.handle_intelligence_api)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LAZY SYSTEM LOADING
    # ═══════════════════════════════════════════════════════════════════════════
    
    @property
    def queen(self):
        """Lazy load Queen Hive Mind."""
        if self._queen is None:
            try:
                from aureon.utils.aureon_queen_hive_mind import QueenHiveMind
                self._queen = QueenHiveMind()
                logger.info("✓ Queen Hive Mind loaded")
            except Exception as e:
                logger.debug(f"Queen not available: {e}")
        return self._queen
    
    @property
    def cost_basis(self):
        """Lazy load Cost Basis Tracker."""
        if self._cost_basis is None:
            try:
                from aureon.portfolio.cost_basis_tracker import CostBasisTracker
                self._cost_basis = CostBasisTracker()
                logger.info("✓ Cost Basis Tracker loaded")
            except Exception as e:
                logger.debug(f"Cost Basis Tracker not available: {e}")
        return self._cost_basis
    
    @property
    def harvester(self):
        """Lazy load Avalanche Harvester."""
        if self._harvester is None:
            try:
                from aureon.trading.aureon_avalanche_harvester import AvalancheHarvester
                self._harvester = AvalancheHarvester()
                logger.info("✓ Avalanche Harvester loaded")
            except Exception as e:
                logger.debug(f"Avalanche Harvester not available: {e}")
        return self._harvester
    
    @property
    def kraken(self):
        """Lazy load Kraken client."""
        if self._kraken is None:
            try:
                from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
                self._kraken = get_kraken_client()
                logger.info("✓ Kraken client loaded")
            except Exception as e:
                logger.debug(f"Kraken not available: {e}")
        return self._kraken
    
    @property
    def alpaca(self):
        """Lazy load Alpaca client."""
        if self._alpaca is None:
            try:
                from aureon.exchanges.alpaca_client import AlpacaClient
                self._alpaca = AlpacaClient()
                logger.info("✓ Alpaca client loaded")
            except Exception as e:
                logger.debug(f"Alpaca not available: {e}")
        return self._alpaca
    
    @property
    def binance(self):
        """Lazy load Binance client."""
        if self._binance is None:
            try:
                from aureon.exchanges.binance_client import BinanceClient, get_binance_client
                self._binance = get_binance_client()
                logger.info("✓ Binance client loaded")
            except Exception as e:
                logger.debug(f"Binance not available: {e}")
        return self._binance
    
    @property
    def capital(self):
        """Lazy load Capital.com client."""
        if self._capital is None:
            try:
                from aureon.exchanges.capital_client import CapitalClient
                self._capital = CapitalClient()
                logger.info("✓ Capital.com client loaded")
            except Exception as e:
                logger.debug(f"Capital not available: {e}")
        return self._capital
    
    # ═══════════════════════════════════════════════════════════════════════════
    # METRICS COLLECTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def collect_portfolio_metrics(self) -> Dict[str, Any]:
        """Collect portfolio metrics (total value, P&L, positions)."""
        metrics = {
            "timestamp": time.time(),
            "total_value_usd": 0.0,
            "cash_available": 0.0,
            "assets_value": 0.0,
            "pnl_today": 0.0,
            "pnl_total": 0.0,
            "positions_count": 0,
            "positions": [],
            "exchanges": {}
        }
        
        try:
            # Collect from each exchange
            exchanges_data = []
            
            if self.kraken:
                kraken_data = self._collect_kraken_portfolio()
                exchanges_data.append(kraken_data)
                metrics["exchanges"]["kraken"] = kraken_data
            
            if self.alpaca:
                alpaca_data = self._collect_alpaca_portfolio()
                exchanges_data.append(alpaca_data)
                metrics["exchanges"]["alpaca"] = alpaca_data
            
            if self.binance:
                binance_data = self._collect_binance_portfolio()
                exchanges_data.append(binance_data)
                metrics["exchanges"]["binance"] = binance_data
            
            if self.capital:
                capital_data = self._collect_capital_portfolio()
                exchanges_data.append(capital_data)
                metrics["exchanges"]["capital"] = capital_data
            
            # Aggregate totals
            for exchange in exchanges_data:
                metrics["total_value_usd"] += exchange.get("total_value", 0)
                metrics["cash_available"] += exchange.get("cash", 0)
                metrics["assets_value"] += exchange.get("assets_value", 0)
                metrics["pnl_today"] += exchange.get("pnl_today", 0)
                metrics["pnl_total"] += exchange.get("pnl_total", 0)
                metrics["positions_count"] += exchange.get("positions_count", 0)
                metrics["positions"].extend(exchange.get("positions", []))
            
            # NORMALIZE position field names for frontend (pnl_pct → pnlPercent)
            for position in metrics["positions"]:
                if "pnl_pct" in position and "pnlPercent" not in position:
                    position["pnlPercent"] = position.pop("pnl_pct")
        
        except Exception as e:
            logger.error(f"Failed to collect portfolio metrics: {e}")
        
        return metrics
    
    def _collect_kraken_portfolio(self) -> Dict[str, Any]:
        """Collect Kraken portfolio data."""
        data = {
            "exchange": "kraken",
            "status": "offline",
            "total_value": 0.0,
            "cash": 0.0,
            "assets_value": 0.0,
            "pnl_today": 0.0,
            "pnl_total": 0.0,
            "positions_count": 0,
            "positions": []
        }
        
        try:
            balance = self.kraken.get_balance()
            
            # Calculate values
            for asset, qty in balance.items():
                if asset in ['USD', 'ZUSD', 'USDT', 'USDC']:
                    data["cash"] += qty
                else:
                    # Get current price
                    try:
                        pair = f"{asset}/USD"
                        ticker = self.kraken.get_ticker(pair)
                        if ticker and 'last' in ticker:
                            price = float(ticker['last'])
                            value = qty * price
                            data["assets_value"] += value
                            
                            # Get entry price from cost basis
                            entry_price = None
                            if self.cost_basis:
                                entry_price = self.cost_basis.get_entry_price(asset, exchange='kraken')
                            
                            if entry_price:
                                entry_value = qty * entry_price
                                pnl = value - entry_value
                                pnl_pct = (pnl / entry_value * 100) if entry_value > 0 else 0
                            else:
                                pnl = 0
                                pnl_pct = 0
                            
                            data["positions"].append({
                                "symbol": asset,
                                "quantity": qty,
                                "price": price,
                                "value": value,
                                "entry_price": entry_price,
                                "pnl": pnl,
                                "pnl_pct": pnl_pct
                            })
                            data["positions_count"] += 1
                            data["pnl_total"] += pnl
                    except:
                        continue
            
            data["total_value"] = data["cash"] + data["assets_value"]
            data["status"] = "online"
            
        except Exception as e:
            logger.debug(f"Failed to collect Kraken portfolio: {e}")
        
        return data
    
    def _collect_alpaca_portfolio(self) -> Dict[str, Any]:
        """Collect Alpaca portfolio data."""
        data = {
            "exchange": "alpaca",
            "status": "offline",
            "total_value": 0.0,
            "cash": 0.0,
            "assets_value": 0.0,
            "pnl_today": 0.0,
            "pnl_total": 0.0,
            "positions_count": 0,
            "positions": []
        }
        
        try:
            # Get account info
            account = self.alpaca.get_account()
            data["cash"] = float(account.get('cash', 0))
            data["total_value"] = float(account.get('portfolio_value', 0))
            data["assets_value"] = data["total_value"] - data["cash"]
            
            # Get positions
            positions = self.alpaca.get_positions()
            for pos in positions:
                symbol = pos.get('symbol', '')
                qty = float(pos.get('qty', 0))
                current_price = float(pos.get('current_price', 0))
                avg_entry = float(pos.get('avg_entry_price', 0))
                market_value = float(pos.get('market_value', 0))
                unrealized_pl = float(pos.get('unrealized_pl', 0))
                unrealized_plpc = float(pos.get('unrealized_plpc', 0)) * 100
                
                data["positions"].append({
                    "symbol": symbol,
                    "quantity": qty,
                    "price": current_price,
                    "value": market_value,
                    "entry_price": avg_entry,
                    "pnl": unrealized_pl,
                    "pnl_pct": unrealized_plpc
                })
                data["positions_count"] += 1
                data["pnl_total"] += unrealized_pl
            
            data["status"] = "online"
            
        except Exception as e:
            logger.debug(f"Failed to collect Alpaca portfolio: {e}")
        
        return data
    
    def _collect_binance_portfolio(self) -> Dict[str, Any]:
        """Collect Binance portfolio data."""
        data = {
            "exchange": "binance",
            "status": "offline",
            "total_value": 0.0,
            "cash": 0.0,
            "assets_value": 0.0,
            "pnl_today": 0.0,
            "pnl_total": 0.0,
            "positions_count": 0,
            "positions": []
        }
        
        try:
            balance = self.binance.get_balance()
            
            for asset, qty in balance.items():
                if asset in ['USD', 'USDT', 'USDC', 'BUSD']:
                    data["cash"] += qty
                else:
                    # Get current price
                    try:
                        pair = f"{asset}USDT"
                        ticker = self.binance.get_ticker(pair)
                        if ticker and 'price' in ticker:
                            price = float(ticker['price'])
                            value = qty * price
                            data["assets_value"] += value
                            
                            # Get entry price
                            entry_price = None
                            if self.cost_basis:
                                entry_price = self.cost_basis.get_entry_price(asset, exchange='binance')
                            
                            if entry_price:
                                entry_value = qty * entry_price
                                pnl = value - entry_value
                                pnl_pct = (pnl / entry_value * 100) if entry_value > 0 else 0
                            else:
                                pnl = 0
                                pnl_pct = 0
                            
                            data["positions"].append({
                                "symbol": asset,
                                "quantity": qty,
                                "price": price,
                                "value": value,
                                "entry_price": entry_price,
                                "pnl": pnl,
                                "pnl_pct": pnl_pct
                            })
                            data["positions_count"] += 1
                            data["pnl_total"] += pnl
                    except:
                        continue
            
            data["total_value"] = data["cash"] + data["assets_value"]
            data["status"] = "online"
            
        except Exception as e:
            logger.debug(f"Failed to collect Binance portfolio: {e}")
        
        return data
    
    def _collect_capital_portfolio(self) -> Dict[str, Any]:
        """Collect Capital.com portfolio data (CFD positions)."""
        data = {
            "exchange": "capital",
            "status": "offline",
            "total_value": 0.0,
            "cash": 0.0,
            "assets_value": 0.0,
            "pnl_today": 0.0,
            "pnl_total": 0.0,
            "positions_count": 0,
            "positions": []
        }
        
        try:
            if not self.capital or not getattr(self.capital, 'enabled', False):
                return data
            
            positions = self.capital.get_positions()
            
            for pos in positions:
                epic = pos.get('market', {}).get('epic', '')
                direction = pos.get('position', {}).get('direction', '')
                size = float(pos.get('position', {}).get('size', 0))
                opening_level = float(pos.get('position', {}).get('level', 0))
                current_level = float(pos.get('market', {}).get('bid' if direction == 'BUY' else 'offer', 0))
                
                # Calculate P&L
                if direction == 'BUY':
                    pnl = (current_level - opening_level) * size
                else:
                    pnl = (opening_level - current_level) * size
                
                market_value = size * current_level
                pnl_pct = (pnl / (size * opening_level) * 100) if opening_level > 0 else 0
                
                data["positions"].append({
                    "symbol": epic,
                    "quantity": size,
                    "price": current_level,
                    "value": market_value,
                    "entry_price": opening_level,
                    "pnl": pnl,
                    "pnl_pct": pnl_pct,
                    "direction": direction
                })
                data["positions_count"] += 1
                data["pnl_total"] += pnl
                data["assets_value"] += abs(market_value)
            
            data["total_value"] = data["assets_value"]
            data["status"] = "online"
            
        except Exception as e:
            logger.debug(f"Failed to collect Capital.com portfolio: {e}")
        
        return data
    
    def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system health metrics."""
        metrics = {
            "timestamp": time.time(),
            "exchanges": {},
            "thought_bus": {"status": "unknown"},
            "queen": {"status": "unknown"},
            "harvester": {"status": "unknown"}
        }
        
        try:
            # Exchange health
            metrics["exchanges"]["kraken"] = {"status": "online" if self.kraken else "offline"}
            metrics["exchanges"]["alpaca"] = {"status": "online" if self.alpaca else "offline"}
            metrics["exchanges"]["binance"] = {"status": "online" if self.binance else "offline"}
            metrics["exchanges"]["capital"] = {"status": "online" if self.capital and getattr(self.capital, 'enabled', False) else "offline"}
            
            # ThoughtBus
            if self.thought_bridge.thought_bus:
                metrics["thought_bus"] = {"status": "online"}
            
            # Queen
            if self.queen:
                metrics["queen"] = {"status": "online"}
            
            # Harvester
            if self.harvester:
                metrics["harvester"] = {
                    "status": "online",
                    "treasury_usd": getattr(self.harvester.treasury, 'total_usd', 0)
                }
        
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
        
        return metrics
    
    def collect_intelligence_metrics(self) -> Dict[str, Any]:
        """Collect intelligence metrics (bots, whales, etc.)."""
        metrics = {
            "timestamp": time.time(),
            "bots_detected": 0,
            "whale_signals": [],
            "validation_pipeline": {},
            "top_firms": [],
            "bot_percentage": 0.0,
            "active_symbols": []
        }
        
        try:
            # Check for whale sonar data
            sonar_file = Path('whale_sonar_state.json')
            if sonar_file.exists():
                with open(sonar_file, 'r') as f:
                    sonar_data = json.load(f)
                    metrics["whale_signals"] = sonar_data.get("whales", [])[:10]  # Top 10
            
            # Check for bot detection data
            bot_file = Path('bot_detection_state.json')
            if bot_file.exists():
                with open(bot_file, 'r') as f:
                    bot_data = json.load(f)
                    metrics["bots_detected"] = bot_data.get("total_bots", 0)
                    metrics["bot_percentage"] = bot_data.get("bot_percentage", 0.0)
                    metrics["active_symbols"] = bot_data.get("active_symbols", [])[:20]
            
            # Check for firm intelligence
            firm_file = Path('all_firms_complete.json')
            if firm_file.exists():
                with open(firm_file, 'r') as f:
                    firm_data = json.load(f)
                    # Get top 10 firms by capital
                    firms = firm_data.get("firms", [])
                    sorted_firms = sorted(firms, key=lambda x: x.get("estimated_capital_usd", 0), reverse=True)
                    metrics["top_firms"] = sorted_firms[:10]
            
            # Check validation pipeline
            validation_file = Path('7day_pending_validations.json')
            if validation_file.exists():
                with open(validation_file, 'r') as f:
                    validation_data = json.load(f)
                    metrics["validation_pipeline"] = {
                        "pending_count": len(validation_data) if isinstance(validation_data, list) else 0,
                        "pending_symbols": [v.get("symbol") for v in (validation_data if isinstance(validation_data, list) else [])][:10]
                    }
        
        except Exception as e:
            logger.debug(f"Failed to collect intelligence metrics: {e}")
        
        return metrics
    
    # ═══════════════════════════════════════════════════════════════════════════
    # WEBSOCKET HANDLERS
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def handle_websocket(self, request):
        """Handle WebSocket connections."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.clients.add(ws)
        logger.info(f"WebSocket client connected ({len(self.clients)} total)")
        
        try:
            # Send initial state
            await ws.send_json({
                "type": "connected",
                "data": {"message": "Connected to Aureon Unified Dashboard"}
            })
            
            # Keep connection alive and handle incoming messages
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    # Handle client commands if needed
                    pass
                elif msg.type == web.WSMsgType.ERROR:
                    logger.error(f'WebSocket error: {ws.exception()}')
        
        finally:
            self.clients.discard(ws)
            logger.info(f"WebSocket client disconnected ({len(self.clients)} remaining)")
        
        return ws
    
    async def broadcast(self, data: Dict):
        """Broadcast data to all connected WebSocket clients."""
        if not self.clients:
            return
        
        dead_clients = set()
        
        for ws in self.clients:
            try:
                await ws.send_json(data)
            except Exception as e:
                logger.debug(f"Failed to send to client: {e}")
                dead_clients.add(ws)
        
        # Remove dead clients
        self.clients -= dead_clients
    
    async def metrics_stream_loop(self):
        """Stream metrics to all clients every 2 seconds."""
        while True:
            try:
                await asyncio.sleep(2)
                
                if not self.clients:
                    continue
                
                # Collect and broadcast portfolio metrics
                portfolio = self.collect_portfolio_metrics()
                await self.broadcast({
                    "type": "portfolio_update",
                    "data": portfolio
                })
                
                # Collect and broadcast system metrics (every 5 seconds)
                if time.time() - self.last_update > 5:
                    systems = self.collect_system_metrics()
                    await self.broadcast({
                        "type": "system_update",
                        "data": systems
                    })
                    
                    # Also broadcast intelligence metrics
                    intelligence = self.collect_intelligence_metrics()
                    await self.broadcast({
                        "type": "intelligence_update",
                        "data": intelligence
                    })
                    
                    self.last_update = time.time()
            
            except Exception as e:
                logger.error(f"Metrics stream error: {e}")
                await asyncio.sleep(5)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HTTP HANDLERS
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def handle_index(self, request):
        """Serve main dashboard HTML."""
        html = self._get_dashboard_html()
        return web.Response(text=html, content_type='text/html')
    
    async def handle_portfolio_api(self, request):
        """REST API endpoint for portfolio data."""
        data = self.collect_portfolio_metrics()
        return web.json_response(data)
    
    async def handle_systems_api(self, request):
        """REST API endpoint for system health."""
        data = self.collect_system_metrics()
        return web.json_response(data)
    
    async def handle_intelligence_api(self, request):
        """REST API endpoint for intelligence data."""
        data = self.collect_intelligence_metrics()
        return web.json_response(data)
    
    def _get_dashboard_html(self) -> str:
        """Generate dashboard HTML."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aureon Unified Live Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0a0e1a 0%, #1a1f3a 100%);
            color: #e0e0e0;
            min-height: 100vh;
        }
        
        .header {
            background: rgba(20, 25, 45, 0.95);
            backdrop-filter: blur(10px);
            padding: 1rem 2rem;
            border-bottom: 2px solid #2d3548;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }
        
        .header h1 {
            color: #61dafb;
            font-size: 1.8rem;
            font-weight: 300;
            letter-spacing: 2px;
        }
        
        .header .subtitle {
            color: #888;
            font-size: 0.9rem;
            margin-top: 0.3rem;
        }
        
        .tabs {
            display: flex;
            gap: 1rem;
            padding: 1rem 2rem;
            background: rgba(20, 25, 45, 0.8);
            border-bottom: 1px solid #2d3548;
        }
        
        .tab {
            padding: 0.7rem 1.5rem;
            background: transparent;
            border: 1px solid #2d3548;
            border-radius: 8px;
            color: #888;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 0.95rem;
        }
        
        .tab:hover {
            background: rgba(97, 218, 251, 0.1);
            border-color: #61dafb;
            color: #61dafb;
        }
        
        .tab.active {
            background: rgba(97, 218, 251, 0.2);
            border-color: #61dafb;
            color: #61dafb;
        }
        
        .content {
            padding: 2rem;
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
            animation: fadeIn 0.3s;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .metric-card {
            background: rgba(30, 35, 55, 0.8);
            backdrop-filter: blur(10px);
            border: 1px solid #2d3548;
            border-radius: 12px;
            padding: 1.5rem;
            transition: all 0.3s;
        }
        
        .metric-card:hover {
            border-color: #61dafb;
            transform: translateY(-2px);
            box-shadow: 0 8px 16px rgba(97, 218, 251, 0.2);
        }
        
        .metric-card .label {
            color: #888;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 0.5rem;
        }
        
        .metric-card .value {
            color: #61dafb;
            font-size: 2rem;
            font-weight: 300;
            margin-bottom: 0.3rem;
        }
        
        .metric-card .change {
            font-size: 0.9rem;
        }
        
        .metric-card .change.positive { color: #4caf50; }
        .metric-card .change.negative { color: #f44336; }
        
        .positions-table {
            background: rgba(30, 35, 55, 0.8);
            border: 1px solid #2d3548;
            border-radius: 12px;
            overflow: hidden;
        }
        
        .positions-table table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .positions-table th {
            background: rgba(20, 25, 45, 0.9);
            padding: 1rem;
            text-align: left;
            color: #61dafb;
            font-weight: 500;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .positions-table td {
            padding: 1rem;
            border-top: 1px solid #2d3548;
        }
        
        .positions-table tr:hover {
            background: rgba(97, 218, 251, 0.05);
        }
        
        .status-badge {
            display: inline-block;
            padding: 0.3rem 0.8rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
        }
        
        .status-badge.online {
            background: rgba(76, 175, 80, 0.2);
            color: #4caf50;
            border: 1px solid #4caf50;
        }
        
        .status-badge.offline {
            background: rgba(244, 67, 54, 0.2);
            color: #f44336;
            border: 1px solid #f44336;
        }
        
        .connection-status {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 0.5rem 1rem;
            border-radius: 8px;
            font-size: 0.85rem;
            z-index: 1000;
        }
        
        .connection-status.connected {
            background: rgba(76, 175, 80, 0.2);
            border: 1px solid #4caf50;
            color: #4caf50;
        }
        
        .connection-status.disconnected {
            background: rgba(244, 67, 54, 0.2);
            border: 1px solid #f44336;
            color: #f44336;
        }
        
        .pulse {
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }
    </style>
</head>
<body>
    <div class="connection-status disconnected" id="connectionStatus">
        ⚪ Connecting...
    </div>
    
    <div class="header">
        <h1>🌊 AUREON UNIFIED LIVE DASHBOARD</h1>
        <div class="subtitle">Real-Time Trading Command Center • Multi-Exchange Intelligence</div>
    </div>
    
    <div class="tabs">
        <div class="tab active" onclick="switchTab('trading')">📊 Trading</div>
        <div class="tab" onclick="switchTab('intelligence')">🧠 Intelligence</div>
        <div class="tab" onclick="switchTab('systems')">⚙️ Systems</div>
    </div>
    
    <div class="content">
        <!-- TRADING TAB -->
        <div id="trading-tab" class="tab-content active">
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="label">Total Portfolio Value</div>
                    <div class="value" id="total-value">$0.00</div>
                    <div class="change positive" id="value-change">--</div>
                </div>
                <div class="metric-card">
                    <div class="label">Cash Available</div>
                    <div class="value" id="cash-available">$0.00</div>
                </div>
                <div class="metric-card">
                    <div class="label">P&L Today</div>
                    <div class="value" id="pnl-today">$0.00</div>
                    <div class="change" id="pnl-today-pct">--</div>
                </div>
                <div class="metric-card">
                    <div class="label">P&L Total</div>
                    <div class="value" id="pnl-total">$0.00</div>
                    <div class="change" id="pnl-total-pct">--</div>
                </div>
            </div>
            
            <div class="positions-table">
                <h3 style="padding: 1rem; color: #61dafb;">Active Positions</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Exchange</th>
                            <th>Symbol</th>
                            <th>Quantity</th>
                            <th>Price</th>
                            <th>Value</th>
                            <th>Entry</th>
                            <th>P&L</th>
                            <th>P&L %</th>
                        </tr>
                    </thead>
                    <tbody id="positions-body">
                        <tr>
                            <td colspan="8" style="text-align: center; color: #888;">
                                Waiting for data...
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- INTELLIGENCE TAB -->
        <div id="intelligence-tab" class="tab-content">
            <h2 style="color: #61dafb; margin-bottom: 1rem;">🧠 Market Intelligence</h2>
            
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="label">Bots Detected</div>
                    <div class="value" id="bots-detected">0</div>
                </div>
                <div class="metric-card">
                    <div class="label">Bot Trade %</div>
                    <div class="value" id="bot-percentage">0%</div>
                </div>
                <div class="metric-card">
                    <div class="label">Whale Signals</div>
                    <div class="value" id="whale-count">0</div>
                </div>
                <div class="metric-card">
                    <div class="label">Validation Queue</div>
                    <div class="value" id="validation-pending">0</div>
                </div>
            </div>
            
            <div class="positions-table" style="margin-top: 2rem;">
                <h3 style="padding: 1rem; color: #61dafb;">🐋 Active Whale Signals</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Whale</th>
                            <th>Signal Strength</th>
                            <th>Event Rate</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody id="whale-signals-body">
                        <tr>
                            <td colspan="4" style="text-align: center; color: #888;">
                                No whale signals detected
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            <div class="positions-table" style="margin-top: 2rem;">
                <h3 style="padding: 1rem; color: #61dafb;">🏢 Top Trading Firms</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Firm</th>
                            <th>Capital (Est.)</th>
                            <th>HQ Location</th>
                            <th>Activity</th>
                        </tr>
                    </thead>
                    <tbody id="firms-body">
                        <tr>
                            <td colspan="4" style="text-align: center; color: #888;">
                                No firm data available
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- SYSTEMS TAB -->
        <div id="systems-tab" class="tab-content">
            <h2 style="color: #61dafb; margin-bottom: 1rem;">⚙️ System Health</h2>
            
            <div class="metrics-grid" id="systems-grid">
                <div class="metric-card">
                    <div class="label">Kraken</div>
                    <span class="status-badge offline" id="kraken-status">Offline</span>
                </div>
                <div class="metric-card">
                    <div class="label">Alpaca</div>
                    <span class="status-badge offline" id="alpaca-status">Offline</span>
                </div>
                <div class="metric-card">
                    <div class="label">Binance</div>
                    <span class="status-badge offline" id="binance-status">Offline</span>
                </div>
                <div class="metric-card">
                    <div class="label">Capital.com</div>
                    <span class="status-badge offline" id="capital-status">Offline</span>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let ws = null;
        let reconnectTimer = null;
        
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/live`;
            
            ws = new WebSocket(wsUrl);
            
            ws.onopen = () => {
                console.log('✓ WebSocket connected');
                updateConnectionStatus(true);
            };
            
            ws.onmessage = (event) => {
                const msg = JSON.parse(event.data);
                handleMessage(msg);
            };
            
            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
            
            ws.onclose = () => {
                console.log('WebSocket disconnected');
                updateConnectionStatus(false);
                // Reconnect after 3 seconds
                reconnectTimer = setTimeout(connectWebSocket, 3000);
            };
        }
        
        function updateConnectionStatus(connected) {
            const status = document.getElementById('connectionStatus');
            if (connected) {
                status.className = 'connection-status connected';
                status.innerHTML = '🟢 Live';
            } else {
                status.className = 'connection-status disconnected';
                status.innerHTML = '🔴 Disconnected';
            }
        }
        
        function handleMessage(msg) {
            switch(msg.type) {
                case 'portfolio_update':
                    updatePortfolioDisplay(msg.data);
                    break;
                case 'system_update':
                    updateSystemsDisplay(msg.data);
                    break;
                case 'intelligence_update':
                    updateIntelligenceDisplay(msg.data);
                    break;
                case 'trade_executed':
                    showTradeNotification(msg.data);
                    break;
                case 'harvest_event':
                    showHarvestNotification(msg.data);
                    break;
                case 'bot_detected':
                    showBotNotification(msg.data);
                    break;
                case 'whale_signal':
                    showWhaleNotification(msg.data);
                    break;
            }
        }
        
        function updatePortfolioDisplay(data) {
            // Update totals
            document.getElementById('total-value').textContent = 
                '$' + data.total_value_usd.toFixed(2);
            document.getElementById('cash-available').textContent = 
                '$' + data.cash_available.toFixed(2);
            document.getElementById('pnl-today').textContent = 
                (data.pnl_today >= 0 ? '+' : '') + '$' + data.pnl_today.toFixed(2);
            document.getElementById('pnl-total').textContent = 
                (data.pnl_total >= 0 ? '+' : '') + '$' + data.pnl_total.toFixed(2);
            
            // Update positions table
            const tbody = document.getElementById('positions-body');
            if (data.positions && data.positions.length > 0) {
                tbody.innerHTML = data.positions.map(pos => `
                    <tr>
                        <td>${getExchangeName(pos)}</td>
                        <td><strong>${pos.symbol}</strong></td>
                        <td>${pos.quantity.toFixed(4)}</td>
                        <td>$${pos.price.toFixed(2)}</td>
                        <td>$${pos.value.toFixed(2)}</td>
                        <td>${pos.entry_price ? '$' + pos.entry_price.toFixed(2) : '--'}</td>
                        <td class="${pos.pnl >= 0 ? 'positive' : 'negative'}">
                            ${pos.pnl >= 0 ? '+' : ''}$${pos.pnl.toFixed(2)}
                        </td>
                        <td class="${pos.pnl_pct >= 0 ? 'positive' : 'negative'}">
                            ${pos.pnl_pct >= 0 ? '+' : ''}${pos.pnl_pct.toFixed(2)}%
                        </td>
                    </tr>
                `).join('');
            } else {
                tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: #888;">No positions</td></tr>';
            }
        }
        
        function getExchangeName(pos) {
            // Try to determine exchange from position data
            return 'Unknown';
        }
        
        function updateSystemsDisplay(data) {
            if (data.exchanges) {
                updateExchangeStatus('kraken', data.exchanges.kraken?.status);
                updateExchangeStatus('alpaca', data.exchanges.alpaca?.status);
                updateExchangeStatus('binance', data.exchanges.binance?.status);
                updateExchangeStatus('capital', data.exchanges.capital?.status);
            }
        }
        
        function updateExchangeStatus(exchange, status) {
            const badge = document.getElementById(`${exchange}-status`);
            if (badge) {
                badge.className = `status-badge ${status}`;
                badge.textContent = status === 'online' ? 'Online' : 'Offline';
            }
        }
        
        function updateIntelligenceDisplay(data) {
            // Update intelligence metrics
            document.getElementById('bots-detected').textContent = data.bots_detected || 0;
            document.getElementById('bot-percentage').textContent = 
                (data.bot_percentage || 0).toFixed(1) + '%';
            document.getElementById('whale-count').textContent = 
                (data.whale_signals?.length || 0);
            document.getElementById('validation-pending').textContent = 
                (data.validation_pipeline?.pending_count || 0);
            
            // Update whale signals table
            const whaleBody = document.getElementById('whale-signals-body');
            if (data.whale_signals && data.whale_signals.length > 0) {
                whaleBody.innerHTML = data.whale_signals.map(whale => `
                    <tr>
                        <td><strong>${whale.name || whale.whale || 'Unknown'}</strong></td>
                        <td>${(whale.signal_strength || whale.score || 0).toFixed(2)}</td>
                        <td>${(whale.event_rate || 0).toFixed(1)}/s</td>
                        <td>
                            <span class="status-badge ${whale.critical ? 'offline' : 'online'}">
                                ${whale.critical ? 'CRITICAL' : 'Active'}
                            </span>
                        </td>
                    </tr>
                `).join('');
            } else {
                whaleBody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #888;">No whale signals detected</td></tr>';
            }
            
            // Update firms table
            const firmsBody = document.getElementById('firms-body');
            if (data.top_firms && data.top_firms.length > 0) {
                firmsBody.innerHTML = data.top_firms.map(firm => `
                    <tr>
                        <td><strong>${firm.name || 'Unknown'}</strong></td>
                        <td>${formatCurrency(firm.estimated_capital_usd || 0)}</td>
                        <td>${firm.hq_location || firm.country || '--'}</td>
                        <td>
                            <span class="status-badge online">
                                ${firm.active_symbols?.length || 0} symbols
                            </span>
                        </td>
                    </tr>
                `).join('');
            } else {
                firmsBody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #888;">No firm data available</td></tr>';
            }
        }
        
        function formatCurrency(value) {
            if (value >= 1e12) return '$' + (value / 1e12).toFixed(1) + 'T';
            if (value >= 1e9) return '$' + (value / 1e9).toFixed(1) + 'B';
            if (value >= 1e6) return '$' + (value / 1e6).toFixed(1) + 'M';
            return '$' + value.toFixed(0);
        }
        
        function showTradeNotification(data) {
            console.log('Trade executed:', data);
            // TODO: Show toast notification
        }
        
        function showHarvestNotification(data) {
            console.log('Harvest event:', data);
            // TODO: Show toast notification
        }
        
        function showBotNotification(data) {
            console.log('Bot detected:', data);
            // Flash bot count
            const botEl = document.getElementById('bots-detected');
            if (botEl) {
                botEl.style.color = '#f44336';
                setTimeout(() => { botEl.style.color = '#61dafb'; }, 1000);
            }
        }
        
        function showWhaleNotification(data) {
            console.log('Whale signal:', data);
            // Flash whale count
            const whaleEl = document.getElementById('whale-count');
            if (whaleEl) {
                whaleEl.style.color = '#4caf50';
                setTimeout(() => { whaleEl.style.color = '#61dafb'; }, 1000);
            }
        }
        
        function switchTab(tabName) {
            // Update tab buttons
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            event.target.classList.add('active');
            
            // Update tab content
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(`${tabName}-tab`).classList.add('active');
        }
        
        // Connect on load
        connectWebSocket();
    </script>
</body>
</html>"""
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SERVER LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def start(self):
        """Start the dashboard server."""
        logger.info("=" * 80)
        logger.info("AUREON UNIFIED LIVE DASHBOARD")
        logger.info("=" * 80)
        logger.info(f"Starting server on http://{self.host}:{self.port}")
        
        # Initialize ThoughtBus bridge
        self.thought_bridge.initialize()
        
        # Start metrics streaming loop
        asyncio.create_task(self.metrics_stream_loop())
        
        # Start web server
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        logger.info(f"✓ Dashboard live at http://{self.host}:{self.port}")
        logger.info("=" * 80)
        
        # Keep running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("\nShutting down...")
            await runner.cleanup()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Aureon Unified Live Dashboard')
    parser.add_argument('--port', type=int, default=8080, help='Server port (default: 8080)')
    parser.add_argument('--host', default='0.0.0.0', help='Server host (default: 0.0.0.0)')
    args = parser.parse_args()
    
    dashboard = AureonUnifiedDashboard(port=args.port, host=args.host)
    
    try:
        asyncio.run(dashboard.start())
    except KeyboardInterrupt:
        logger.info("\n✓ Dashboard stopped")


if __name__ == '__main__':
    main()
