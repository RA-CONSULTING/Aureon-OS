#!/usr/bin/env python3
"""
🎯 AUREON UNIFIED DASHBOARD API - REST Endpoints for Unified Dashboard
=======================================================================

Provides REST API endpoints that the React unified dashboard connects to.
Integrates with System Coordinator, Decision Engine, and Feed Hub.

Endpoints:
  GET  /api/orca-status - Orca kill cycle real-time status
  POST /api/orca-command - Send commands to Orca (start/stop/adjust)
  GET  /api/system-coordination - Multi-system coordination state
  GET  /api/unified-state - Complete unified state snapshot
  GET  /api/feed-status - All consolidated feed streams status
  GET  /api/decisions - Latest trading decisions by symbol
  GET  /api/health - Health check endpoint

Author: Aureon Trading System
Date: March 2026
"""

import asyncio
import json
from aiohttp import web
from datetime import datetime
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Lazy imports (avoid circular dependencies)
def get_coordinator():
    try:
        from aureon.core.aureon_system_coordinator import SystemCoordinator
        if not hasattr(get_coordinator, '_instance'):
            get_coordinator._instance = SystemCoordinator()
        return get_coordinator._instance
    except Exception as e:
        logger.warning(f"Could not get coordinator: {e}")
        return None


def get_decision_engine():
    try:
        from aureon.intelligence.aureon_unified_decision_engine import UnifiedDecisionEngine
        if not hasattr(get_decision_engine, '_instance'):
            get_decision_engine._instance = UnifiedDecisionEngine()
        return get_decision_engine._instance
    except Exception as e:
        logger.warning(f"Could not get decision engine: {e}")
        return None


def get_feed_hub():
    try:
        from aureon.data_feeds.aureon_real_data_feed_hub import get_feed_hub as _get_feed_hub
        return _get_feed_hub()
    except Exception as e:
        logger.warning(f"Could not get feed hub: {e}")
        return None


class UnifiedDashboardAPI:
    """REST API for unified dashboard."""

    def __init__(self):
        """Initialize the API handler."""
        self.app = web.Application()
        self._setup_routes()
        self.startup_time = datetime.now()

    def _setup_routes(self):
        """Setup all API routes."""
        routes = [
            # Orca endpoints
            web.get('/api/orca-status', self.get_orca_status),
            web.post('/api/orca-command', self.post_orca_command),

            # System coordination
            web.get('/api/system-coordination', self.get_system_coordination),
            web.get('/api/system-health', self.get_system_health),

            # Unified state
            web.get('/api/unified-state', self.get_unified_state),

            # Feeds
            web.get('/api/feed-status', self.get_feed_status),

            # Decisions
            web.get('/api/decisions', self.get_decisions),
            web.get('/api/decisions/{symbol}', self.get_decision_by_symbol),

            # Health
            web.get('/api/health', self.get_health),

            # Root
            web.get('/api', self.get_api_root),
        ]
        self.app.add_routes(routes)

    async def get_orca_status(self, request: web.Request) -> web.Response:
        """GET /api/orca-status - Get Orca kill cycle status."""
        try:
            coordinator = get_coordinator()
            if not coordinator:
                return web.json_response({"error": "Coordinator unavailable"}, status=503)

            orca_state = coordinator.get_system_state("orca_complete_kill_cycle")

            if not orca_state:
                return web.json_response({
                    "status": "unknown",
                    "message": "Orca system not found in registry"
                })

            # Enhance with execution readiness
            can_execute, blockers = coordinator.can_execute_orca()

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
            logger.error(f"Error getting orca status: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def post_orca_command(self, request: web.Request) -> web.Response:
        """POST /api/orca-command - Send command to Orca."""
        try:
            data = await request.json()
            command = data.get("command")  # "start", "stop", "pause", "resume"
            parameters = data.get("parameters", {})

            coordinator = get_coordinator()
            if not coordinator:
                return web.json_response({"error": "Coordinator unavailable"}, status=503)

            # Check if execution is allowed
            can_execute, blockers = coordinator.can_execute_orca()

            if command in ["start", "resume"] and not can_execute:
                return web.json_response({
                    "success": False,
                    "message": "Cannot execute Orca - dependencies not ready",
                    "blockers": blockers
                }, status=400)

            # Would send to actual Orca system (ThoughtBus topic)
            try:
                from aureon.core.aureon_thought_bus import ThoughtBus
                tb = ThoughtBus()
                tb.publish("orca.command", {
                    "command": command,
                    "parameters": parameters,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                logger.warning(f"Could not publish to ThoughtBus: {e}")

            return web.json_response({
                "success": True,
                "command": command,
                "message": f"Command '{command}' sent to Orca",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error posting orca command: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def get_system_coordination(self, request: web.Request) -> web.Response:
        """GET /api/system-coordination - Get current system coordination state."""
        try:
            coordinator = get_coordinator()
            if not coordinator:
                return web.json_response({"error": "Coordinator unavailable"}, status=503)

            state = coordinator.get_coordination_state()
            return web.json_response(state)
        except Exception as e:
            logger.error(f"Error getting coordination state: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def get_system_health(self, request: web.Request) -> web.Response:
        """GET /api/system-health - Get health of all systems."""
        try:
            coordinator = get_coordinator()
            if not coordinator:
                return web.json_response({"error": "Coordinator unavailable"}, status=503)

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
            logger.error(f"Error checking system health: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def get_unified_state(self, request: web.Request) -> web.Response:
        """GET /api/unified-state - Get complete unified state snapshot."""
        try:
            coordinator = get_coordinator()
            decision_engine = get_decision_engine()
            feed_hub = get_feed_hub()

            # Gather all state
            coordination_state = coordinator.get_coordination_state() if coordinator else {}
            decisions = decision_engine.get_all_decisions() if decision_engine else {}
            feed_status = feed_hub.get_consolidated_feeds_status() if feed_hub else {}

            # Convert decisions to JSON-serializable format
            decisions_json = {
                symbol: {
                    "type": dec.decision_type.value,
                    "timestamp": dec.timestamp.isoformat(),
                    "confidence": dec.confidence,
                    "reason": dec.reason.value,
                    "coordination_ok": dec.system_coordination_ok,
                    "risk_ok": dec.risk_check_passed
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
            logger.error(f"Error getting unified state: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def get_feed_status(self, request: web.Request) -> web.Response:
        """GET /api/feed-status - Get consolidated feed streams status."""
        try:
            feed_hub = get_feed_hub()
            if not feed_hub:
                return web.json_response({"error": "Feed hub unavailable"}, status=503)

            status = feed_hub.get_consolidated_feeds_status()
            return web.json_response(status)
        except Exception as e:
            logger.error(f"Error getting feed status: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def get_decisions(self, request: web.Request) -> web.Response:
        """GET /api/decisions - Get latest trading decisions."""
        try:
            decision_engine = get_decision_engine()
            if not decision_engine:
                return web.json_response({"error": "Decision engine unavailable"}, status=503)

            decisions = decision_engine.get_all_decisions()

            # Convert to JSON-serializable format
            decisions_json = {
                symbol: {
                    "id": dec.decision_id,
                    "type": dec.decision_type.value,
                    "symbol": dec.symbol,
                    "timestamp": dec.timestamp.isoformat(),
                    "confidence": dec.confidence,
                    "reason": dec.reason.value,
                    "signals_used": dec.signals_used,
                    "coordination_ok": dec.system_coordination_ok,
                    "risk_ok": dec.risk_check_passed,
                    "cancel_reason": dec.cancel_reason,
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
            logger.error(f"Error getting decisions: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def get_decision_by_symbol(self, request: web.Request) -> web.Response:
        """GET /api/decisions/{symbol} - Get decision for a specific symbol."""
        try:
            symbol = request.match_info['symbol']
            decision_engine = get_decision_engine()
            if not decision_engine:
                return web.json_response({"error": "Decision engine unavailable"}, status=503)

            decision = decision_engine.get_latest_decision(symbol)

            if not decision:
                return web.json_response(
                    {"message": f"No decision found for {symbol}"},
                    status=404
                )

            return web.json_response({
                "id": decision.decision_id,
                "type": decision.decision_type.value,
                "symbol": decision.symbol,
                "timestamp": decision.timestamp.isoformat(),
                "confidence": decision.confidence,
                "reason": decision.reason.value,
                "signals_used": decision.signals_used,
                "coordination_ok": decision.system_coordination_ok,
                "risk_ok": decision.risk_check_passed,
                "cancel_reason": decision.cancel_reason,
                "metadata": decision.metadata
            })
        except Exception as e:
            logger.error(f"Error getting decision: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def get_health(self, request: web.Request) -> web.Response:
        """GET /api/health - Health check endpoint."""
        try:
            coordinator = get_coordinator()
            is_healthy = coordinator is not None

            return web.json_response({
                "status": "healthy" if is_healthy else "degraded",
                "timestamp": datetime.now().isoformat(),
                "uptime": (datetime.now() - self.startup_time).total_seconds(),
                "components": {
                    "coordinator": "ok" if coordinator else "missing",
                    "decision_engine": "ok" if get_decision_engine() else "missing",
                    "feed_hub": "ok" if get_feed_hub() else "missing"
                }
            })
        except Exception as e:
            logger.error(f"Error in health check: {e}")
            return web.json_response({
                "status": "error",
                "error": str(e)
            }, status=500)

    async def get_api_root(self, request: web.Request) -> web.Response:
        """GET /api - API root endpoint with documentation."""
        return web.json_response({
            "name": "Aureon Unified Dashboard API",
            "version": "1.0",
            "endpoints": {
                "orca": {
                    "GET /api/orca-status": "Orca kill cycle real-time status",
                    "POST /api/orca-command": "Send command to Orca"
                },
                "coordination": {
                    "GET /api/system-coordination": "Multi-system coordination state",
                    "GET /api/system-health": "Health of all systems"
                },
                "state": {
                    "GET /api/unified-state": "Complete unified state snapshot",
                    "GET /api/feed-status": "Consolidated feed streams status"
                },
                "decisions": {
                    "GET /api/decisions": "Latest trading decisions",
                    "GET /api/decisions/{symbol}": "Decision for specific symbol"
                },
                "health": {
                    "GET /api/health": "Health check endpoint"
                }
            }
        })


async def start_api_server(port: int = 13334, host: str = "0.0.0.0"):
    """
    Start the unified dashboard API server.

    Args:
        port: Port to run on (default 13334)
        host: Host to bind to (default 0.0.0.0)
    """
    api = UnifiedDashboardAPI()
    runner = web.AppRunner(api.app)

    try:
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        logger.info(f"🎯 Unified Dashboard API running on http://{host}:{port}")

        # Keep running
        await asyncio.Event().wait()
    except Exception as e:
        logger.error(f"Error starting API server: {e}")
        await runner.cleanup()
        raise


async def main():
    """Start the API server."""
    await start_api_server(port=13334)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())
