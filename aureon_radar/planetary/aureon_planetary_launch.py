#!/usr/bin/env python3
"""
🚀 AUREON PLANETARY LAUNCH 🚀
═══════════════════════════════════════════════════════════════════════════

ONE COMMAND TO START EVERYTHING:
- Connects to existing Bot Hunter (port 9999)
- Connects to existing Quantum Bridge (port 11006)  
- Starts Global Map Dashboard (port 12100)
- Shows planetary overview with countries, clans, tidal waves
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
        if hasattr(sys.stdout, 'buffer') and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        # Skip stderr wrapping (causes Windows exit errors)
    except Exception:
        pass

import asyncio
import aiohttp
from aiohttp import web
import json
import logging
from typing import Dict, Set
from collections import defaultdict

# Import dashboard HTML
from aureon.bots_intelligence.aureon_global_bot_map import DASHBOARD_HTML

class SimplePlanetaryDashboard:
    """Simplified planetary dashboard that works with existing systems."""
    
    def __init__(self, port=12100):
        self.port = port
        self.logger = logging.getLogger(__name__)
        
        # State
        self.bots = {}
        self.map_clients: Set = set()
        
        # Setup web server
        self.app = web.Application()
        self.app.router.add_get('/', self.handle_index)
        self.app.router.add_get('/ws', self.handle_websocket)
    
    async def handle_index(self, request):
        """Serve dashboard."""
        # Replace WebSocket URL to match this server
        html = DASHBOARD_HTML.replace('ws://localhost:12000', f'ws://localhost:{self.port}/ws')
        return web.Response(text=html, content_type='text/html')
    
    async def handle_websocket(self, request):
        """Handle WebSocket connections from dashboard."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.map_clients.add(ws)
        self.logger.info(f"🗺️  Map client connected (total: {len(self.map_clients)})")
        
        # Send initial overview
        await ws.send_str(json.dumps(self.get_overview()))
        
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.ERROR:
                    self.logger.error(f"Map client error: {ws.exception()}")
        finally:
            self.map_clients.discard(ws)
        
        return ws
    
    async def listen_to_bot_hunter(self):
        """Listen to Bot Hunter on port 9999."""
        self.logger.info("🤖 Listening to Bot Hunter on port 9999...")
        
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    # Connect to Bot Hunter WebSocket
                    async with session.ws_connect('http://localhost:9999') as ws:
                        self.logger.info("✅ Connected to Bot Hunter")
                        
                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                data = json.loads(msg.data)
                                await self.process_bot_data(data)
                                
            except Exception as e:
                self.logger.warning(f"Bot Hunter connection error: {e}")
                await asyncio.sleep(5)
    
    async def process_bot_data(self, data: Dict):
        """Process bot data and update state."""
        if data.get("type") in ["bot_detection", "bot_update"]:
            bot = data.get("bot", {})
            bot_id = bot.get("bot_id")
            
            if bot_id:
                # Add planetary context
                exchange = bot.get("exchange", "unknown").lower()
                country_map = {
                    "binance": "Malta/Global",
                    "kraken": "USA",
                    "alpaca": "USA",
                }
                bot["country"] = country_map.get(exchange, "Global")
                bot["clan_id"] = f"{bot['country']}_{bot.get('pattern', 'unknown')}"
                
                self.bots[bot_id] = bot
                
                # Broadcast update
                await self.broadcast_overview()
    
    def get_overview(self) -> Dict:
        """Generate planetary overview."""
        # Aggregate by country
        countries = defaultdict(lambda: {
            "bot_count": 0,
            "volume": 0.0,
            "patterns": defaultdict(int),
            "aggression": 0.0,
        })
        
        clans = defaultdict(lambda: {
            "members": 0,
            "volume": 0.0,
        })
        
        for bot in self.bots.values():
            country = bot.get("country", "Global")
            countries[country]["bot_count"] += 1
            countries[country]["volume"] += bot.get("volume", 0.0)
            countries[country]["patterns"][bot.get("pattern", "unknown")] += 1
            
            clan_id = bot.get("clan_id")
            if clan_id:
                clans[clan_id]["members"] += 1
                clans[clan_id]["volume"] += bot.get("volume", 0.0)
        
        # Format countries
        country_list = []
        for country, stats in sorted(countries.items(), key=lambda x: x[1]["bot_count"], reverse=True):
            dominant_pattern = max(stats["patterns"].items(), key=lambda x: x[1])[0] if stats["patterns"] else "unknown"
            country_list.append({
                "country": country,
                "bot_count": stats["bot_count"],
                "volume": stats["volume"],
                "dominant_pattern": dominant_pattern,
                "aggression": stats["aggression"],
                "clan_count": len([c for c in clans if country in c]),
            })
        
        # Format clans
        clan_list = []
        for clan_id, stats in sorted(clans.items(), key=lambda x: x[1]["members"], reverse=True)[:10]:
            parts = clan_id.split("_")
            clan_list.append({
                "clan_id": clan_id,
                "name": f"{parts[0]} {parts[1] if len(parts) > 1 else 'Pack'}",
                "country": parts[0],
                "members": stats["members"],
                "volume": stats["volume"],
                "strategy": parts[1] if len(parts) > 1 else "unknown",
                "color": f"#{''.join(f'{ord(c):02x}' for c in clan_id[:3])}",
            })
        
        return {
            "type": "planetary_overview",
            "data": {
                "stats": {
                    "total_bots_tracked": len(self.bots),
                    "total_clans_identified": len(clans),
                    "most_active_country": country_list[0]["country"] if country_list else "Unknown",
                    "tidal_wave_strength": 0.5,
                },
                "countries": country_list,
                "clans": clan_list,
                "active_battles": [],
            }
        }
    
    async def broadcast_overview(self):
        """Broadcast overview to all clients."""
        if self.map_clients:
            msg = json.dumps(self.get_overview())
            for client in list(self.map_clients):
                try:
                    await client.send_str(msg)
                except:
                    self.map_clients.discard(client)
    
    async def start(self):
        """Start everything."""
        # Start web server
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        
        print(f"\n{'='*80}")
        print(f"🌍 AUREON PLANETARY DASHBOARD ACTIVE")
        print(f"{'='*80}")
        print(f"🗺️  Global Map: http://localhost:{self.port}")
        print(f"🤖 Bot Hunter: http://localhost:9999")
        print(f"🌌 Quantum Bridge: http://localhost:11007")
        print(f"\nTracking:")
        print(f"  • Countries & regions")
        print(f"  • Bot clans & packs")
        print(f"  • Global tidal movements")
        print(f"  • Coordinated battles")
        print(f"{'='*80}\n")
        
        # Start listening to bot hunter
        await self.listen_to_bot_hunter()

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    dashboard = SimplePlanetaryDashboard(port=12100)
    await dashboard.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🌍 Planetary Dashboard stopped")
