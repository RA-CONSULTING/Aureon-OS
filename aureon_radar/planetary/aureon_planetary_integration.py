#!/usr/bin/env python3
"""
🌌 AUREON PLANETARY INTEGRATION 🌌
═══════════════════════════════════════════════════════════════════════════

Master orchestrator connecting:
1. Bot Hunter Dashboard → Live bot detection
2. Quantum Telescope → Sacred geometry analysis
3. Planetary Tracker → Country/clan identification
4. Global Map → Visual dashboard

Complete data flow:
Exchange → Bot Hunter → Quantum Analysis → Planetary Tracking → Global Visualization
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
from aureon.utils.console_utf8 import ensure_utf8_stdout  # noqa: E402

ensure_utf8_stdout()

import asyncio
import aiohttp
from aiohttp import web
import json
import logging
from typing import Dict, Set

class PlanetaryIntegration:
    """
    Integrates all systems into unified planetary consciousness.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Connections
        self.bot_hunter_ws = None
        self.quantum_ws = None
        self.map_clients: Set = set()
        
        # State
        self.bots: Dict = {}
        self.quantum_analysis: Dict = {}
        self.planetary_state: Dict = {}
        
        # Setup web server
        self.app = web.Application()
        self.app.router.add_get('/ws', self.handle_websocket)
        
    async def connect_to_bot_hunter(self, url="ws://localhost:9999"):
        """Connect to Bot Hunter Dashboard."""
        self.logger.info(f"🤖 Connecting to Bot Hunter: {url}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(url) as ws:
                    self.bot_hunter_ws = ws
                    self.logger.info("✅ Connected to Bot Hunter")
                    
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            await self.process_bot_data(data)
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            self.logger.error(f"Bot Hunter error: {ws.exception()}")
                            
        except Exception as e:
            self.logger.error(f"Failed to connect to Bot Hunter: {e}")
            await asyncio.sleep(5)
            # Retry connection
            await self.connect_to_bot_hunter(url)
    
    async def connect_to_quantum(self, url="ws://localhost:11006"):
        """Connect to Quantum Bridge."""
        self.logger.info(f"🌌 Connecting to Quantum Bridge: {url}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(url) as ws:
                    self.quantum_ws = ws
                    self.logger.info("✅ Connected to Quantum Bridge")
                    
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            await self.process_quantum_data(data)
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            self.logger.error(f"Quantum error: {ws.exception()}")
                            
        except Exception as e:
            self.logger.error(f"Failed to connect to Quantum: {e}")
            await asyncio.sleep(5)
            await self.connect_to_quantum(url)
    
    async def process_bot_data(self, data: Dict):
        """Process bot detection data."""
        if data.get("type") == "bot_detection":
            bot = data.get("bot", {})
            bot_id = bot.get("bot_id")
            
            if bot_id:
                self.bots[bot_id] = bot
                self.logger.info(f"🤖 Bot detected: {bot_id} ({bot.get('pattern', 'unknown')})")
                
                # Enrich with planetary context
                await self.enrich_planetary_context(bot)
    
    async def process_quantum_data(self, data: Dict):
        """Process quantum analysis data."""
        if data.get("type") == "quantum_analysis":
            analysis = data.get("analysis", {})
            bot_id = analysis.get("bot_id")
            
            if bot_id:
                self.quantum_analysis[bot_id] = analysis
                self.logger.info(f"🌌 Quantum analysis: {bot_id} → {analysis.get('sacred_shape', 'unknown')}")
                
                # Merge with bot data
                if bot_id in self.bots:
                    self.bots[bot_id].update({
                        "sacred_shape": analysis.get("sacred_shape"),
                        "quantum_coherence": analysis.get("quantum_coherence", 0.5),
                        "manipulation_risk": analysis.get("manipulation_risk", 0.5),
                    })
    
    async def enrich_planetary_context(self, bot: Dict):
        """Add planetary context (country, clan, etc.)."""
        exchange = bot.get("exchange", "unknown").lower()
        
        # Map exchange to country
        exchange_countries = {
            "binance": "Malta/Global",
            "kraken": "USA",
            "coinbase": "USA",
            "alpaca": "USA",
            "bitfinex": "Hong Kong",
            "huobi": "Seychelles",
        }
        
        country = exchange_countries.get(exchange, "Global")
        bot["country"] = country
        
        # Estimate coordinates (simplified)
        country_coords = {
            "USA": (37.0902, -95.7129),
            "Malta/Global": (35.9375, 14.3754),
            "Hong Kong": (22.3193, 114.1694),
            "Seychelles": (-4.6796, 55.4920),
            "Global": (0, 0),
        }
        
        lat, lon = country_coords.get(country, (0, 0))
        bot["lat"] = lat
        bot["lon"] = lon
        
        # Detect clan affiliation (simplified - based on pattern + country)
        pattern = bot.get("pattern", "unknown")
        clan_id = f"{country}_{pattern}"
        bot["clan_id"] = clan_id
        
        # Broadcast to map clients
        await self.broadcast_to_map(bot)
    
    async def broadcast_to_map(self, bot: Dict):
        """Broadcast bot data to global map clients."""
        # Aggregate all bots by country
        country_stats = {}
        clan_stats = {}
        
        for b in self.bots.values():
            country = b.get("country", "Global")
            if country not in country_stats:
                country_stats[country] = {
                    "country": country,
                    "bot_count": 0,
                    "volume": 0.0,
                    "dominant_pattern": {},
                    "aggression": 0.0,
                    "clan_count": 0,
                }
            
            country_stats[country]["bot_count"] += 1
            country_stats[country]["volume"] += b.get("volume", 0.0)
            
            pattern = b.get("pattern", "unknown")
            if pattern not in country_stats[country]["dominant_pattern"]:
                country_stats[country]["dominant_pattern"][pattern] = 0
            country_stats[country]["dominant_pattern"][pattern] += 1
            
            # Clan tracking
            clan_id = b.get("clan_id")
            if clan_id:
                if clan_id not in clan_stats:
                    clan_stats[clan_id] = {
                        "clan_id": clan_id,
                        "name": f"{country} {pattern} Pack",
                        "country": country,
                        "members": 0,
                        "volume": 0.0,
                        "strategy": pattern,
                        "color": self._generate_color(clan_id),
                    }
                clan_stats[clan_id]["members"] += 1
                clan_stats[clan_id]["volume"] += b.get("volume", 0.0)
        
        # Find dominant pattern for each country
        for stats in country_stats.values():
            if stats["dominant_pattern"]:
                stats["dominant_pattern"] = max(
                    stats["dominant_pattern"].items(),
                    key=lambda x: x[1]
                )[0]
            else:
                stats["dominant_pattern"] = "unknown"
        
        # Prepare overview
        overview = {
            "type": "planetary_overview",
            "data": {
                "stats": {
                    "total_bots_tracked": len(self.bots),
                    "total_clans_identified": len(clan_stats),
                    "most_active_country": max(
                        country_stats.values(),
                        key=lambda x: x["bot_count"]
                    )["country"] if country_stats else "Unknown",
                    "tidal_wave_strength": 0.5,  # Simplified
                },
                "countries": sorted(
                    country_stats.values(),
                    key=lambda x: x["bot_count"],
                    reverse=True
                ),
                "clans": sorted(
                    clan_stats.values(),
                    key=lambda x: x["members"],
                    reverse=True
                ),
                "active_battles": [],  # Will be populated by battle detection
            }
        }
        
        # Broadcast to all map clients
        if self.map_clients:
            msg = json.dumps(overview)
            for client in list(self.map_clients):
                try:
                    await client.send_str(msg)
                except Exception as e:
                    self.logger.warning(f"Failed to send to map client: {e}")
                    self.map_clients.discard(client)
    
    def _generate_color(self, clan_id: str) -> str:
        """Generate unique color for clan."""
        import hashlib
        hash_val = int(hashlib.md5(clan_id.encode()).hexdigest()[:6], 16)
        r = (hash_val >> 16) & 0xFF
        g = (hash_val >> 8) & 0xFF
        b = hash_val & 0xFF
        return f"#{r:02x}{g:02x}{b:02x}"
    
    async def handle_websocket(self, request):
        """Handle WebSocket connections from map dashboard."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.map_clients.add(ws)
        self.logger.info(f"🗺️  Map client connected (total: {len(self.map_clients)})")
        
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.ERROR:
                    self.logger.error(f"Map client error: {ws.exception()}")
        finally:
            self.map_clients.discard(ws)
            self.logger.info(f"🗺️  Map client disconnected (total: {len(self.map_clients)})")
        
        return ws
    
    async def start_server(self, port=12000):
        """Start WebSocket server for map clients."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        
        self.logger.info(f"🌍 Planetary Integration server started on port {port}")
    
    async def run(self):
        """Run the complete integration."""
        # Start WebSocket server
        await self.start_server(port=12000)
        
        # Connect to subsystems in parallel
        await asyncio.gather(
            self.connect_to_bot_hunter("ws://localhost:9999"),
            self.connect_to_quantum("ws://localhost:11006"),
        )

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    print("🌌 AUREON PLANETARY INTEGRATION 🌌")
    print("=" * 80)
    print("Connecting all systems:")
    print("  Bot Hunter (port 9999) → Live bot detection")
    print("  Quantum Bridge (port 11006) → Sacred geometry analysis")
    print("  Planetary Integration (port 12000) → Country/clan tracking")
    print("  Global Map (port 12000) → Visual dashboard")
    print("=" * 80)
    print()
    
    integration = PlanetaryIntegration()
    
    try:
        await integration.run()
    except KeyboardInterrupt:
        print("\n\n🌍 Planetary Integration stopped")

if __name__ == "__main__":
    asyncio.run(main())
