#!/usr/bin/env python3
"""
🎯 UNIFIED DASHBOARD SERVER - Combined HTML + REST API
=======================================================

Serves both the HTML dashboard and REST API endpoints on a single port.

Usage:
    python unified_dashboard_server.py
    # Open http://localhost:13334 in browser
"""

import asyncio
from aiohttp import web
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class UnifiedDashboardServer:
    """Server that combines dashboard HTML + REST API."""

    def __init__(self):
        """Initialize server."""
        self.app = web.Application()
        self.root_dir = Path(__file__).parent
        self._setup_routes()
        self.startup_time = datetime.now()

    def _setup_routes(self):
        """Setup all routes."""
        # Serve dashboard HTML
        self.app.router.add_get('/', self.serve_dashboard)
        self.app.router.add_get('/dashboard', self.serve_dashboard)
        self.app.router.add_get('/unified', self.serve_dashboard)

        # API endpoints
        self.app.router.add_get('/api', self.get_api_root)
        self.app.router.add_get('/api/orca-status', self.get_orca_status)
        self.app.router.add_post('/api/orca-command', self.post_orca_command)
        self.app.router.add_get('/api/system-coordination', self.get_system_coordination)
        self.app.router.add_get('/api/system-health', self.get_system_health)
        self.app.router.add_get('/api/unified-state', self.get_unified_state)
        self.app.router.add_get('/api/feed-status', self.get_feed_status)
        self.app.router.add_get('/api/decisions', self.get_decisions)
        self.app.router.add_get('/api/decisions/{symbol}', self.get_decision_by_symbol)
        self.app.router.add_get('/api/health', self.get_health)

    async def serve_dashboard(self, request: web.Request) -> web.Response:
        """Serve the dashboard HTML."""
        try:
            dashboard_file = self.root_dir / "dashboard.html"
            if dashboard_file.exists():
                content = dashboard_file.read_text()
                return web.Response(text=content, content_type='text/html')
            else:
                return web.Response(text="Dashboard HTML not found", status=404)
        except Exception as e:
            logger.error(f"Error serving dashboard: {e}")
            return web.Response(text=str(e), status=500)

    async def get_api_root(self, request: web.Request) -> web.Response:
        """GET /api - API documentation."""
        return web.json_response({
            "name": "Aureon Unified Dashboard API",
            "version": "1.0",
            "base_url": str(request.url).split('/api')[0],
            "endpoints": {
                "dashboard": {
                    "GET /": "Main dashboard interface",
                    "GET /dashboard": "Dashboard alias",
                    "GET /unified": "Unified dashboard alias"
                },
                "orca": {
                    "GET /api/orca-status": "Get Orca execution status",
                    "POST /api/orca-command": "Send command to Orca (start/stop/pause)"
                },
                "coordination": {
                    "GET /api/system-coordination": "System coordination state",
                    "GET /api/system-health": "System health metrics"
                },
                "state": {
                    "GET /api/unified-state": "Complete unified state",
                    "GET /api/feed-status": "Feed stream status"
                },
                "decisions": {
                    "GET /api/decisions": "All trading decisions",
                    "GET /api/decisions/{symbol}": "Decision for symbol"
                },
                "health": {
                    "GET /api/health": "API health check"
                }
            }
        })

    async def get_orca_status(self, request: web.Request) -> web.Response:
        """GET /api/orca-status - Orca execution status."""
        try:
            from aureon.core.aureon_system_coordinator import SystemCoordinator

            coordinator = SystemCoordinator()
            orca_state = coordinator.get_system_state("orca_complete_kill_cycle")
            can_execute, blockers = coordinator.can_execute_orca()

            if not orca_state:
                return web.json_response({
                    "status": "unknown",
                    "message": "Orca system not found"
                })

            return web.json_response({
                "status": orca_state.get("state"),
                "ready_for_execution": can_execute,
                "blockers": blockers,
                "last_heartbeat": orca_state.get("last_heartbeat"),
                "error": orca_state.get("error"),
                "metadata": orca_state.get("metadata", {}),
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def post_orca_command(self, request: web.Request) -> web.Response:
        """POST /api/orca-command - Send command to Orca."""
        try:
            data = await request.json()
            command = data.get("command")

            # Publish command (would integrate with actual Orca)
            logger.info(f"Orca command received: {command}")

            return web.json_response({
                "success": True,
                "command": command,
                "message": f"Command '{command}' sent to Orca",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def get_system_coordination(self, request: web.Request) -> web.Response:
        """GET /api/system-coordination - System coordination state."""
        try:
            from aureon.core.aureon_system_coordinator import SystemCoordinator

            coordinator = SystemCoordinator()
            state = coordinator.get_coordination_state()
            return web.json_response(state)
        except Exception as e:
            logger.error(f"Error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def get_system_health(self, request: web.Request) -> web.Response:
        """GET /api/system-health - System health."""
        try:
            from aureon.core.aureon_system_coordinator import SystemCoordinator

            coordinator = SystemCoordinator()
            health = coordinator.check_system_health()
            healthy_count = sum(1 for h in health.values() if h)
            total_count = len(health)

            return web.json_response({
                "healthy": healthy_count,
                "total": total_count,
                "health_percentage": (healthy_count / total_count * 100) if total_count > 0 else 0,
                "systems": health,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def get_unified_state(self, request: web.Request) -> web.Response:
        """GET /api/unified-state - Complete unified state."""
        try:
            from aureon.core.aureon_system_coordinator import SystemCoordinator
            from aureon.intelligence.aureon_unified_decision_engine import UnifiedDecisionEngine
            from aureon.data_feeds.aureon_real_data_feed_hub import get_feed_hub

            coordinator = SystemCoordinator()
            decision_engine = UnifiedDecisionEngine()
            feed_hub = get_feed_hub()

            coordination_state = coordinator.get_coordination_state()
            decisions = decision_engine.get_all_decisions()
            feed_status = feed_hub.get_consolidated_feeds_status()

            decisions_json = {
                symbol: {
                    "type": dec.decision_type.value,
                    "timestamp": dec.timestamp.isoformat(),
                    "confidence": dec.confidence,
                    "reason": dec.reason.value
                }
                for symbol, dec in decisions.items()
            }

            return web.json_response({
                "timestamp": datetime.now().isoformat(),
                "coordination": coordination_state,
                "decisions": decisions_json,
                "feeds": feed_status,
                "uptime": (datetime.now() - self.startup_time).total_seconds()
            })
        except Exception as e:
            logger.error(f"Error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def get_feed_status(self, request: web.Request) -> web.Response:
        """GET /api/feed-status - Feed stream status."""
        try:
            from aureon.data_feeds.aureon_real_data_feed_hub import get_feed_hub

            feed_hub = get_feed_hub()
            status = feed_hub.get_consolidated_feeds_status()
            return web.json_response(status)
        except Exception as e:
            logger.error(f"Error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def get_decisions(self, request: web.Request) -> web.Response:
        """GET /api/decisions - All trading decisions."""
        try:
            from aureon.intelligence.aureon_unified_decision_engine import UnifiedDecisionEngine

            engine = UnifiedDecisionEngine()
            decisions = engine.get_all_decisions()

            decisions_json = {
                symbol: {
                    "id": dec.decision_id,
                    "type": dec.decision_type.value,
                    "symbol": dec.symbol,
                    "timestamp": dec.timestamp.isoformat(),
                    "confidence": dec.confidence,
                    "reason": dec.reason.value,
                    "signals_used": dec.signals_used,
                    "metadata": dec.metadata
                }
                for symbol, dec in decisions.items()
            }

            return web.json_response({
                "total": len(decisions),
                "decisions": decisions_json,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def get_decision_by_symbol(self, request: web.Request) -> web.Response:
        """GET /api/decisions/{symbol} - Decision for symbol."""
        try:
            symbol = request.match_info['symbol']
            from aureon.intelligence.aureon_unified_decision_engine import UnifiedDecisionEngine

            engine = UnifiedDecisionEngine()
            decision = engine.get_latest_decision(symbol)

            if not decision:
                return web.json_response(
                    {"message": f"No decision for {symbol}"},
                    status=404
                )

            return web.json_response({
                "id": decision.decision_id,
                "type": decision.decision_type.value,
                "symbol": decision.symbol,
                "timestamp": decision.timestamp.isoformat(),
                "confidence": decision.confidence,
                "reason": decision.reason.value,
                "metadata": decision.metadata
            })
        except Exception as e:
            logger.error(f"Error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def get_health(self, request: web.Request) -> web.Response:
        """GET /api/health - Health check."""
        try:
            return web.json_response({
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "uptime": (datetime.now() - self.startup_time).total_seconds(),
                "api": "online",
                "dashboard": "online"
            })
        except Exception as e:
            logger.error(f"Error: {e}")
            return web.json_response({
                "status": "error",
                "error": str(e)
            }, status=500)


async def main():
    """Start the server."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s'
    )

    server = UnifiedDashboardServer()
    runner = web.AppRunner(server.app)

    try:
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 13334)
        await site.start()

        logger.info("=" * 80)
        logger.info("🎯 AUREON UNIFIED DASHBOARD SERVER")
        logger.info("=" * 80)
        logger.info(f"🌐 Dashboard: http://localhost:13334")
        logger.info(f"📡 API: http://localhost:13334/api")
        logger.info(f"🏥 Health: http://localhost:13334/api/health")
        logger.info("=" * 80)
        logger.info("Press Ctrl+C to stop\n")

        # Keep running
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
