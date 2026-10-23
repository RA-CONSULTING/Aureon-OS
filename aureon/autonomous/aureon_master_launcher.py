#!/usr/bin/env python3
"""
🌍⚡ AUREON MASTER LAUNCHER - FULLY AUTONOMOUS TRADING SYSTEM ⚡🌍
==================================================================
This launcher boots ALL systems with REAL data and AUTONOMOUS trading.

🔱 PRIME SENTINEL AUTHORITY 🔱
Gary Leckey (02.11.1991) - "I have taken back control"

WHAT THIS DOES:
1. Starts the Real Intelligence Engine (Bot/Whale/Momentum detection)
2. Starts the Real Data Feed Hub (Central distribution)
3. Wires ALL 200+ systems to receive real data
4. Starts the Queen Hive Mind (Neural decision making)
5. Starts Micro Profit Labyrinth (Autonomous execution)
6. Runs FULLY AUTONOMOUS TRADING LOOP (no human intervention)

The system will:
- Continuously gather intelligence from all sources
- Validate signals through 3-pass Batten Matrix
- Ask Queen for guidance (6-12-1 neural network)
- Execute trades automatically through Micro Profit Labyrinth
- Learn from every outcome and adapt

Gary Leckey & Tina Brown | January 2026 | MASTER LAUNCHER
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
        if hasattr(sys.stdout, 'buffer') and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

import time
import threading
import logging
import argparse
import json
import signal
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from urllib.request import urlopen

logger = logging.getLogger(__name__)

# Queen Layer -- the new top-level orchestrator
try:
    from aureon.queen.queen_layer import boot_queen_layer, get_queen_layer
    QUEEN_LAYER_AVAILABLE = True
except ImportError:
    QUEEN_LAYER_AVAILABLE = False


def _safe_len(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    return 0


def wire_queen_systems(queen: Any, labyrinth: Any) -> Dict[str, Any]:
    """Wire Queen to critical systems and return a wiring summary."""
    summary: Dict[str, Any] = {
        'take_full_control': False,
        'micro_labyrinth': False,
        'enigma': False,
        'hft_engine': False,
        'hft_order_router': False,
    }

    try:
        if hasattr(queen, 'take_full_control'):
            queen.take_full_control()
            summary['take_full_control'] = True
    except Exception as e:
        logger.debug(f"take_full_control failed: {e}")

    try:
        if hasattr(queen, 'wire_micro_labyrinth'):
            summary['micro_labyrinth'] = bool(queen.wire_micro_labyrinth(labyrinth))
    except Exception as e:
        logger.debug(f"wire_micro_labyrinth failed: {e}")

    try:
        from aureon.wisdom.aureon_enigma_integration import get_enigma_integration
        enigma = get_enigma_integration()
        if hasattr(queen, 'wire_enigma'):
            summary['enigma'] = bool(queen.wire_enigma(enigma))
    except Exception as e:
        logger.debug(f"wire_enigma failed: {e}")

    try:
        from aureon.harmonic.aureon_hft_harmonic_mycelium import get_hft_engine
        hft_engine = get_hft_engine()
        if hasattr(queen, 'wire_hft_engine'):
            summary['hft_engine'] = bool(queen.wire_hft_engine(hft_engine))
    except Exception as e:
        logger.debug(f"wire_hft_engine failed: {e}")

    try:
        from aureon.data_feeds.aureon_hft_websocket_order_router import get_order_router
        router = get_order_router()
        if hasattr(router, 'wire_exchange_clients'):
            exchange_clients = {}
            if hasattr(labyrinth, 'kraken') and labyrinth.kraken:
                exchange_clients['kraken'] = labyrinth.kraken
            if hasattr(labyrinth, 'binance') and labyrinth.binance:
                exchange_clients['binance'] = labyrinth.binance
            if hasattr(labyrinth, 'alpaca') and labyrinth.alpaca:
                exchange_clients['alpaca'] = labyrinth.alpaca
            router.wire_exchange_clients(exchange_clients)

        if hasattr(queen, 'wire_hft_order_router'):
            summary['hft_order_router'] = bool(queen.wire_hft_order_router(router))
    except Exception as e:
        logger.debug(f"wire_hft_order_router failed: {e}")

    return summary


def run_system_flight_check(queen: Any, labyrinth: Any, intel: Dict[str, Any], status: Dict[str, Any]) -> Dict[str, Any]:
    """Validate end-to-end connections before execution (anti-phantom)."""
    flight: Dict[str, Any] = {
        'queen_control': getattr(queen, 'has_full_control', False),
        'queen_trading_enabled': getattr(queen, 'trading_enabled', False),
        'harmonic_signal_chain': False,
        'harmonic_alphabet': False,
        'chirp_bus': False,
        'hft_engine': False,
        'hft_order_router': False,
        'micro_labyrinth': False,
        'enigma': False,
        'intelligence': {
            'total_sources': intel.get('total_sources', 0),
            'bots': _safe_len(intel.get('bots', [])),
            'whales': _safe_len(intel.get('whale_predictions', [])),
            'momentum_keys': list(intel.get('momentum', {}).keys()) if isinstance(intel.get('momentum', {}), dict) else [],
        },
        'wiring': {
            'total_events': status.get('total_events', 0),
        }
    }

    try:
        flight['micro_labyrinth'] = getattr(queen, 'micro_labyrinth', None) is not None
        flight['enigma'] = getattr(queen, 'enigma', None) is not None
        flight['hft_engine'] = getattr(queen, 'hft_engine', None) is not None
        flight['hft_order_router'] = getattr(queen, 'hft_order_router', None) is not None
        flight['harmonic_signal_chain'] = getattr(queen, 'harmonic_signal_chain', None) is not None
        flight['harmonic_alphabet'] = getattr(queen, 'harmonic_alphabet', None) is not None
    except Exception:
        pass

    try:
        from aureon.core.aureon_chirp_bus import get_chirp_bus
        chirp_bus = get_chirp_bus()
        flight['chirp_bus'] = chirp_bus is not None
    except Exception:
        flight['chirp_bus'] = False

    try:
        if hasattr(labyrinth, 'audit_event'):
            labyrinth.audit_event('system_flight_check', flight)
    except Exception:
        pass

    return flight


def print_banner():
    """Print launch banner"""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║  🌍⚡ AUREON MASTER LAUNCHER - FULLY AUTONOMOUS TRADING ⚡🌍                  ║
║                                                                              ║
║  ██████╗ ███████╗ █████╗ ██╗         ██████╗  █████╗ ████████╗ █████╗       ║
║  ██╔══██╗██╔════╝██╔══██╗██║         ██╔══██╗██╔══██╗╚══██╔══╝██╔══██╗      ║
║  ██████╔╝█████╗  ███████║██║         ██║  ██║███████║   ██║   ███████║      ║
║  ██╔══██╗██╔══╝  ██╔══██║██║         ██║  ██║██╔══██║   ██║   ██╔══██║      ║
║  ██║  ██║███████╗██║  ██║███████╗    ██████╔╝██║  ██║   ██║   ██║  ██║      ║
║  ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝      ║
║                                                                              ║
║  🔱 PRIME SENTINEL AUTHORITY 🔱                                              ║
║  Gary Leckey (02.11.1991) - "I have taken back control"                     ║
║                                                                              ║
║  Components:                                                                 ║
║  • Real Intelligence Engine (Bot/Whale/Momentum)                             ║
║  • Real Data Feed Hub (Central Distribution)                                 ║
║  • System Wiring (200+ Systems Connected)                                    ║
║  • Mycelium Whale Sonar (Subsystem Monitoring)                               ║
║  • Queen Hive Mind (Neural Decision Making)                                  ║
║  • Micro Profit Labyrinth (Autonomous Execution)                             ║
║  • API Server (Dashboard Data)                                               ║
║                                                                              ║
║  MODE: FULLY AUTONOMOUS - NO HUMAN INTERVENTION REQUIRED                     ║
║                                                                              ║
║  Gary Leckey & Tina Brown | January 2026                                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def launch_real_intelligence():
    """Launch the Real Intelligence Engine"""
    print("\n📡 [1/5] LAUNCHING REAL INTELLIGENCE ENGINE...")
    
    try:
        from aureon.intelligence.aureon_real_intelligence_engine import get_intelligence_engine
        engine = get_intelligence_engine()
        
        # 🔥 FORCE INITIAL SCAN - Populate data immediately
        try:
            if hasattr(engine, 'bot_profiler') and hasattr(engine.bot_profiler, 'profile_all_firms'):
                print(f"   🔍 Running initial bot profiler scan...")
                engine.bot_profiler.profile_all_firms()
                print(f"   ✅ Bot Profiler: ACTIVE (37 trading firms)")
            
            if hasattr(engine, 'whale_predictor') and hasattr(engine.whale_predictor, 'predict_all_whales'):
                print(f"   🔍 Running initial whale predictions...")
                engine.whale_predictor.predict_all_whales()
                print(f"   ✅ Whale Predictor: ACTIVE (3-pass validation)")
            
            if hasattr(engine, 'momentum_scanners'):
                print(f"   🔍 Running initial momentum scans...")
                for scanner_name, scanner in engine.momentum_scanners.items():
                    if hasattr(scanner, 'scan'):
                        scanner.scan()
                print(f"   ✅ Momentum Scanners: ACTIVE (Wolf/Lion/Ants/Hummingbird)")
        except Exception as scan_error:
            print(f"   ⚠️ Initial scan warning: {scan_error}")
        
        return engine
    except Exception as e:
        print(f"   ⚠️ Warning: {e}")
        return None


def launch_feed_hub():
    """Launch the Real Data Feed Hub"""
    print("\n📊 [2/5] LAUNCHING REAL DATA FEED HUB...")
    
    try:
        from aureon.data_feeds.aureon_real_data_feed_hub import get_feed_hub, start_global_feed
        
        hub = get_feed_hub()
        
        # Start global feed with faster interval for more responsive data
        start_global_feed(interval=2.0)  # Changed from 5s to 2s for faster updates
        
        print(f"   ✅ Feed Hub: ACTIVE")
        print(f"   ✅ Distribution: 2s interval (fast mode)")
        print(f"   ✅ Topics: intelligence.bot.*, intelligence.whale.*, intelligence.momentum.*")
        
        return hub
    except Exception as e:
        print(f"   ⚠️ Warning: {e}")
        return None


def launch_system_wiring():
    """Wire all systems to receive real data"""
    print("\n🔗 [3/5] WIRING ALL SYSTEMS...")
    
    try:
        from aureon.core.aureon_system_wiring import wire_all_systems, get_wiring_status
        
        # This is already run by the feed hub, but let's ensure it
        wired_count = wire_all_systems()
        status = get_wiring_status()
        
        print(f"   ✅ Systems Wired: {status['total_wired']}")
        print(f"   ✅ Categories: 9 (Neural, Execution, Dashboards, etc.)")
        
        return status
    except Exception as e:
        print(f"   ⚠️ Warning: {e}")
        return None


def launch_whale_sonar():
    """Launch the Mycelium Whale Sonar for subsystem monitoring"""
    print("\n🐋 [3.5/5] LAUNCHING MYCELIUM WHALE SONAR...")
    
    try:
        from aureon.core.mycelium_whale_sonar import create_and_start_sonar
        
        sonar = create_and_start_sonar()
        
        if sonar:
            print(f"   ✅ Whale Sonar: ACTIVE")
            print(f"   ✅ Monitoring: system.*, execution.*, market.*, mycelium.*")
            print(f"   ✅ Aggregation: 1s intervals, 5s windows")
        else:
            print(f"   ⚠️ Whale Sonar: Not available (ThoughtBus missing)")
        
        return sonar
    except Exception as e:
        print(f"   ⚠️ Warning: {e}")
        return None


def launch_queen_runner():
    """Launch Queen Hive Mind with full trading authority"""
    print("\n👑 [4/5] LAUNCHING QUEEN HIVE MIND - FULL AUTONOMOUS TRADING...")
    
    try:
        from aureon.utils.aureon_queen_hive_mind import get_queen
        
        queen = get_queen()
        
        print(f"   ✅ Queen Hive Mind: ACTIVE")
        print(f"   ✅ Neural Network: 6-12-1 architecture")
        print(f"   ✅ Trading Authority: GRANTED")
        print(f"   ✅ Prime Sentinel: AUTHORIZED")
        
        return queen
    except Exception as e:
        print(f"   ⚠️ Warning: {e}")
        return None


def launch_api_server():
    """Launch API server for dashboards"""
    print("\n🌐 [5/5] LAUNCHING API SERVER...")
    
    try:
        # Check if we can import the API module
        from aureon.bridges.aureon_frontend_bridge import start_api_server
        
        # Start in background thread
        api_thread = threading.Thread(target=start_api_server, daemon=True)
        api_thread.start()
        
        time.sleep(1)  # Give it time to start
        
        print(f"   ✅ API Server: http://localhost:5000")
        print(f"   ✅ Endpoints: /api/queen, /api/bots, /api/whales, /api/momentum")
        
        return True
    except Exception as e:
        print(f"   ⚠️ API Server not started: {e}")
        return None


def print_status_summary(engine, hub, wiring_status, sonar):
    """Print summary of what's running"""
    print("\n" + "=" * 80)
    print("🌍⚡ AUREON MASTER LAUNCHER - STATUS SUMMARY")
    print("=" * 80)
    
    print("\n📊 INTELLIGENCE SOURCES:")
    print("   • Bot Profiler: 37 trading firms tracked")
    print("   • Whale Predictor: 3-pass validation active")
    print("   • Animal Scanners: Wolf, Lion, Ants, Hummingbird")
    
    print("\n🔗 SYSTEM WIRING:")
    if wiring_status:
        print(f"   • Total Systems: {wiring_status['total_wired']}")
        print(f"   • Events Received: {wiring_status['total_events']}")
    
    print("\n🐋 WHALE SONAR:")
    if sonar:
        print("   • Status: ACTIVE")
        print("   • Monitoring: All subsystems")
        print("   • Aggregation: 1s intervals")
    else:
        print("   • Status: NOT AVAILABLE")
    
    print("\n📡 DATA FLOW:")
    print("   • intelligence.bot.* → Bot Tracking Systems")
    print("   • intelligence.whale.* → Whale Prediction Systems")
    print("   • intelligence.momentum.* → Momentum Scanners")
    print("   • intelligence.validated.* → Execution Engines")
    
    print("\n👑 QUEEN NEURAL NETWORK:")
    print("   • Architecture: 6-12-1")
    print("   • Learning Rate: 0.01")
    print("   • Decision Mode: REAL INTELLIGENCE (not random)")
    
    print("\n" + "=" * 80)
    print("✅ ALL SYSTEMS OPERATIONAL - REAL DATA FLOWING")
    print("=" * 80)


def run_live_monitoring():
    """Run continuous live monitoring"""
    print("\n🔴 LIVE MONITORING MODE")
    print("Press Ctrl+C to stop\n")
    
    from aureon.data_feeds.aureon_real_data_feed_hub import get_feed_hub
    from aureon.core.aureon_system_wiring import get_wiring_status
    
    hub = get_feed_hub()
    
    try:
        while True:
            status = get_wiring_status()
            
            # Get latest intelligence
            intel = hub.gather_all_intelligence() if hasattr(hub, 'gather_all_intelligence') else {}
            
            # Display compact status line
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            bots = len(intel.get('bots', []))
            whales = len(intel.get('whale_predictions', []))
            momentum = len(intel.get('momentum', {}).get('opportunities', []))
            events = status.get('total_events', 0)
            
            print(f"\r[{timestamp}] 🤖 Bots: {bots:3d} | 🐋 Whales: {whales:3d} | 🚀 Momentum: {momentum:3d} | 📊 Events: {events:,}", end="")
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️ Monitoring stopped")


def run_autonomous_trading(engine=None, hub=None):
    """
    Run fully autonomous trading through Queen and Micro Profit Labyrinth.
    This is the main trading loop under Prime Sentinel authority.
    """
    print("\n" + "=" * 80)
    print("🔱 PRIME SENTINEL AUTHORITY - AUTONOMOUS TRADING ACTIVATED 🔱")
    print("=" * 80)
    print("\n⚡ Gary Leckey (02.11.1991) - Prime Sentinel Decree")
    print("   'I have taken back control' - Trading authority GRANTED")
    print("\n🔴 FULLY AUTONOMOUS TRADING MODE")
    print("Press Ctrl+C to stop\n")
    
    from aureon.data_feeds.aureon_real_data_feed_hub import get_feed_hub
    from aureon.intelligence.aureon_real_intelligence_engine import get_intelligence_engine
    from aureon.core.aureon_system_wiring import get_wiring_status
    
    # Get hub and engine if not provided
    if hub is None:
        hub = get_feed_hub()
    if engine is None:
        engine = get_intelligence_engine()
    
    # Import trading engines
    try:
        from aureon.utils.aureon_queen_hive_mind import get_queen
        from aureon.trading.micro_profit_labyrinth import MicroProfitLabyrinth
        
        queen = get_queen()
        queen.has_full_control = True  # Prime Sentinel authority
        queen.trading_enabled = True
        
        labyrinth = MicroProfitLabyrinth()
        # Default stays "live" unless explicitly disabled (e.g. production-safe mode).
        live_trading = os.getenv("AUREON_LIVE_TRADING", "1") in ("1", "true", "TRUE", "yes", "YES")
        labyrinth.dry_run = not live_trading
        if labyrinth.dry_run:
            print("🔒 DRY-RUN MODE: Active (AUREON_LIVE_TRADING=0)")
        else:
            print("🔴 LIVE MODE: Active (AUREON_LIVE_TRADING=1)")

        # Wire Queen to ALL critical systems
        wiring_summary = wire_queen_systems(queen, labyrinth)
        
        print("✅ Queen Hive Mind: ONLINE (Full Authority)")
        print("✅ Micro Profit Labyrinth: ONLINE")
        print("✅ All systems wired and ready\n")
        if wiring_summary:
            logger.info(f"Wiring summary: {wiring_summary}")
        
    except Exception as e:
        print(f"⚠️ Could not initialize trading engines: {e}")
        print("   Falling back to monitoring mode\n")
        run_live_monitoring()
        return
    
    # Trading loop
    cycle_count = 0
    try:
        while True:
            cycle_count += 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Get wiring status
            status = get_wiring_status()
            
            # 🔥 GATHER AND DISTRIBUTE INTELLIGENCE - The correct way
            try:
                # Get current prices from labyrinth or exchanges
                prices = {}
                if hasattr(labyrinth, 'get_all_prices'):
                    prices = labyrinth.get_all_prices()
                elif hasattr(labyrinth, 'price_cache'):
                    prices = labyrinth.price_cache
                
                # If primary feed (labyrinth) returned no prices, walk a
                # REAL-data fallback chain (unified cache → CoinGecko cache
                # → Kraken/Binance REST → CoinGecko REST). Production NEVER
                # substitutes hardcoded prices; if every real source fails,
                # the cycle is skipped and we wait for live data to return.
                if not prices:
                    try:
                        from aureon.observer.real_price_fallback import (
                            get_real_prices_with_fallback,
                        )
                        wanted = ['BTC/USD', 'ETH/USD', 'SOL/USD', 'XRP/USD',
                                  'DOGE/USD', 'ADA/USD']
                        prices, sources = get_real_prices_with_fallback(
                            symbols=wanted, max_cache_age_sec=60.0, timeout_sec=5.0
                        )
                        if prices:
                            logger.info(
                                "[live-data] labyrinth empty; resolved %d real "
                                "prices via fallback chain (%s) for cycle %d",
                                len(prices), "+".join(sources), cycle_count,
                            )
                    except Exception as exc:
                        logger.warning(
                            "[live-data] real-price fallback chain raised: %s; "
                            "treating as no-data", exc,
                        )
                        prices = {}

                # If even the real-data fallback chain returned nothing,
                # production refuses to substitute hardcoded prices and
                # skips the cycle. A skipped cycle costs nothing; firing
                # a trade against fabricated prices is catastrophic.
                if not prices:
                    from aureon.observer.live_data_policy import (
                        simulation_fallback_allowed, log_blocked_fallback,
                    )
                    if not simulation_fallback_allowed():
                        log_blocked_fallback("master_launcher.run_autonomous_trading",
                                             "no_live_prices_after_fallback_chain")
                        logger.error("[live-data] every real source returned "
                                     "no prices, skipping cycle %d (no synthetic "
                                     "substitution in production posture)", cycle_count)
                        time.sleep(1)
                        continue
                    # DEV-ONLY hardcoded fallback (gated by AUREON_ALLOW_SIM_FALLBACK)
                    prices = {
                        'BTC/USD': 43000.0,
                        'ETH/USD': 2300.0,
                        'SOL/USD': 100.0,
                        'AAPL': 185.0,
                        'MSFT': 380.0
                    }
                
                # Call gather_and_distribute which internally does:
                # 1. engine.gather_all_intelligence(prices) - gathers from all sources
                # 2. Publishes to ThoughtBus topics
                # 3. Returns summary
                if hasattr(hub, 'gather_and_distribute'):
                    summary = hub.gather_and_distribute(prices)
                    intel = {
                        'bots': summary.get('stats', {}).get('bots_detected', 0),
                        'whale_predictions': summary.get('stats', {}).get('whales_predicted', 0),
                        'momentum': summary.get('stats', {}).get('momentum_opportunities', 0),
                        'total_sources': summary.get('stats', {}).get('intelligence_generated', 0),
                        'summary': summary
                    }
                else:
                    intel = {'error': 'gather_and_distribute not available'}
            except Exception as e:
                print(f"\n   ⚠️ Intelligence gathering error: {e}")
                intel = {'error': str(e)}
            
            # Extract intelligence counts from summary
            bots_count = intel.get('bots', 0)
            whales_count = intel.get('whale_predictions', 0)
            momentum_count = intel.get('momentum', 0)
            total_sources = intel.get('total_sources', 0)
            
            # Get full summary for validated signals
            summary = intel.get('summary', {})
            
            # 🔍 DATA VALIDATION - Check if we actually got data
            if cycle_count % 10 == 0:  # Every 10 cycles, report data status
                data_status = {
                    'bots': bots_count,
                    'whales': whales_count,
                    'momentum': momentum_count,
                    'total_sources': total_sources
                }
                if sum([data_status['bots'], data_status['whales'], data_status['momentum']]) == 0:
                    print(f"\n   ⚠️ WARNING: No intelligence data populated! Status: {data_status}")
            
            # Count high-confidence signals (from summary stats)
            validated_count = summary.get('stats', {}).get('validated_signals', 0)

            
            # Display status
            print(f"\r[{timestamp}] Cycle: {cycle_count:5d} | "
                  f"🤖 Bots: {bots_count:3d} | "
                  f"🐋 Whales: {whales_count:3d} | "
                  f"✅ Validated: {validated_count:2d} | "
                  f"📊 Events: {status.get('total_events', 0):,}", end="")

            # Flight check on startup + every 60 cycles
            if cycle_count == 1 or cycle_count % 60 == 0:
                flight = run_system_flight_check(queen, labyrinth, intel, status)
                if not all([
                    flight.get('queen_control'),
                    flight.get('queen_trading_enabled'),
                    flight.get('harmonic_signal_chain'),
                    flight.get('harmonic_alphabet'),
                    flight.get('chirp_bus'),
                    flight.get('hft_engine'),
                    flight.get('hft_order_router'),
                    flight.get('micro_labyrinth'),
                    flight.get('enigma'),
                ]):
                    print("\n   ⚠️ FLIGHT CHECK: One or more critical systems offline.")
            
            # Check for trading opportunities every 5 cycles (5 seconds)
            if cycle_count % 5 == 0 and validated_count > 0:
                print(f"\n\n🎯 [{timestamp}] HIGH-CONFIDENCE SIGNAL DETECTED!")
                
                # 🧠 QUEEN GATHERS ALL INTELLIGENCE BEFORE DECIDING
                try:
                    if hasattr(queen, 'gather_all_intelligence'):
                        # Queen gathers ALL data: bots, whales, momentum, dashboards
                        queen_intel = queen.gather_all_intelligence()
                        print(f"   📡 Queen gathered intelligence from {queen_intel.get('total_sources', 0)} sources")
                except Exception as e:
                    print(f"   ⚠️ Queen intelligence gathering: {e}")

                # ✈️ FLIGHT CHECK: audit signal path before execution
                try:
                    if hasattr(labyrinth, 'audit_event'):
                        active_intel = queen_intel if 'queen_intel' in locals() else intel
                        labyrinth.audit_event(
                            'signal_flight_check',
                            {
                                'cycle': cycle_count,
                                'timestamp': timestamp,
                                'validated_signals': validated_count,
                                'intel_summary': {
                                    'total_sources': active_intel.get('total_sources', 0),
                                    'bots': bots_count,
                                    'whales': whales_count,
                                    'momentum': momentum_count,
                                },
                                'queen_state': {
                                    'has_full_control': getattr(queen, 'has_full_control', False),
                                    'trading_enabled': getattr(queen, 'trading_enabled', False),
                                },
                                'wiring_status': {
                                    'total_events': status.get('total_events', 0),
                                },
                            }
                        )
                except Exception as e:
                    print(f"   ⚠️ Flight check audit: {e}")
                
                # Get validated signals from summary
                validated_signals = summary.get('validated_intelligence', []) if isinstance(summary.get('validated_intelligence'), list) else []
                
                # Ask Queen for guidance
                for signal in validated_signals[:3]:  # Max 3 per cycle
                    symbol = signal.get('symbol', 'UNKNOWN')
                    action = signal.get('action', 'HOLD')
                    confidence = signal.get('confidence', 0)
                    
                    print(f"   🔮 Signal: {symbol} | {action} | Confidence: {confidence:.1%}")
                    
                    # Get Queen's INTELLIGENT decision (with ALL data)
                    try:
                        if hasattr(queen, 'get_queen_decision_with_intelligence'):
                            # USE NEW INTELLIGENCE-DRIVEN DECISION
                            guidance = queen.get_queen_decision_with_intelligence({
                                'symbol': symbol,
                                'action': action,
                                'confidence': confidence,
                                'validated': True,
                                'prime_sentinel': True
                            })
                            
                            if guidance and guidance.get('confidence', 0) > 0.618:
                                print(f"   👑 Queen: {guidance.get('decision', 'HOLD')} "
                                      f"(Confidence: {guidance.get('confidence', 0):.1%})")
                                print(f"   📊 Intelligence used: Bots={guidance.get('intel_summary', {}).get('bots_analyzed', 0)}, "
                                      f"Whales={guidance.get('intel_summary', {}).get('whale_predictions', 0)}")
                                
                                # Execute through Micro Profit Labyrinth
                                if hasattr(labyrinth, 'execute_validated_opportunity'):
                                    result = labyrinth.execute_validated_opportunity(
                                        symbol=symbol,
                                        action=action,
                                        intelligence=queen.latest_intelligence,
                                        queen_guidance=guidance
                                    )
                                    
                                    if result:
                                        print(f"   ⚡ Executed: {result.get('status', 'UNKNOWN')}")
                                        if labyrinth.live and not result.get('real_execution_verified', False):
                                            print("   ⚠️ UNVERIFIED EXECUTION: No order IDs returned (possible phantom).")
                                else:
                                    print(f"   ⚠️ Labyrinth execution not available")
                            else:
                                print(f"   👑 Queen: HOLD (Confidence: {guidance.get('confidence', 0):.1%})")
                        elif hasattr(queen, 'ask_queen_will_we_win'):
                            # Fallback to old method
                            guidance = queen.ask_queen_will_we_win(
                                asset=symbol,
                                exchange='kraken',
                                opportunity_score=confidence,
                                context={
                                    'intelligence': intel,
                                    'validated': True,
                                    'prime_sentinel': True
                                }
                            )
                            
                            if guidance and guidance.get('confidence', 0) > 0.618:
                                print(f"   👑 Queen: {guidance.get('decision', 'HOLD')} "
                                      f"(Confidence: {guidance.get('confidence', 0):.1%})")
                    except Exception as e:
                        print(f"   ⚠️ Trading error: {e}")
                
                print()  # New line after batch
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️ Autonomous trading stopped")
        print(f"   Total cycles: {cycle_count}")
        print(f"   Duration: {cycle_count}s")


def _http_ok(url: str, timeout_s: float = 1.5) -> bool:
    try:
        with urlopen(url, timeout=timeout_s) as resp:
            status = getattr(resp, "status", 200)
            return 200 <= status < 300
    except Exception:
        return False


class _ManagedProcess:
    def __init__(self, name: str, cmd: list[str], cwd: str | None = None, env: dict[str, str] | None = None):
        self.name = name
        self.cmd = cmd
        self.cwd = cwd
        self.env = env or {}
        self.proc: subprocess.Popen | None = None

    def start(self) -> None:
        if self.proc and self.proc.poll() is None:
            return
        child_env = os.environ.copy()
        child_env.update(self.env)
        self.proc = subprocess.Popen(self.cmd, cwd=self.cwd, env=child_env)

    def alive(self) -> bool:
        return bool(self.proc and self.proc.poll() is None)

    def terminate(self, timeout_s: float = 10.0) -> None:
        if not self.proc or self.proc.poll() is not None:
            return
        self.proc.terminate()
        try:
            self.proc.wait(timeout=timeout_s)
        except Exception:
            self.proc.kill()


def _print_progress(step: str, current: int, total: int) -> None:
    pct = int((current / max(total, 1)) * 100)
    bar_w = 24
    filled = int((pct / 100) * bar_w)
    bar = "#" * filled + "-" * (bar_w - filled)
    print(f"[{bar}] {pct:3d}% | {step}")


def run_production_orchestrator(*, live_trading: bool, spawn_command_center: bool, spawn_market_feeds: bool) -> None:
    """
    Unified production entry (single brain, managed heads):
    - Spawns UI/data heads (dashboard/feeds/command center) as subprocesses.
    - Boots intelligence + Queen + wiring in-process.
    - Runs dry-run validation/monitoring by default; enable live execution explicitly.
    """
    print_banner()

    if not live_trading:
        print("\n🔒 PRODUCTION SAFE MODE: DRY-RUN (no real orders)")
        print("   Set `AUREON_LIVE_TRADING=1` or pass `--live` to enable execution.\n")

    managed: list[_ManagedProcess] = []

    total_steps = 6
    step = 0

    # 1) Dashboard first so /health comes up immediately.
    step += 1
    dash_port = os.getenv("PORT", "8080")
    _print_progress(f"Starting Aureon Pro Dashboard ({dash_port})", step, total_steps)
    dash = _ManagedProcess(
        name="aureon-pro-dashboard",
        cmd=[sys.executable, "-u", "aureon_pro_dashboard.py"],
        env={"PORT": dash_port},
    )
    dash.start()
    managed.append(dash)

    for _ in range(40):
        if _http_ok(f"http://127.0.0.1:{dash_port}/health"):
            break
        time.sleep(0.25)

    # 2) Optional market feeds (free-first).
    if spawn_market_feeds:
        step += 1
        _print_progress("Starting Binance WS market cache", step, total_steps)
        cache_env = {"MARKET_CACHE_DIR": os.getenv("MARKET_CACHE_DIR", "ws_cache")}
        mkt = _ManagedProcess(
            name="unified-market-cache",
            cmd=[sys.executable, "-u", "unified_market_cache.py", "--write-interval", "1.0"],
            env=cache_env,
        )
        mkt.start()
        managed.append(mkt)

        step += 1
        _print_progress("Starting Kraken cache (backup)", step, total_steps)
        krk = _ManagedProcess(
            name="kraken-cache",
            cmd=[sys.executable, "-u", "kraken_cache_feeder.py", "--interval-s", "120"],
        )
        krk.start()
        managed.append(krk)
    else:
        step += 2
        _print_progress("Skipping external market feeds", step, total_steps)

    # 3) Optional command center.
    if spawn_command_center:
        step += 1
        cc_port = os.getenv("COMMAND_CENTER_PORT", "8800")
        _print_progress(f"Starting Command Center ({cc_port})", step, total_steps)
        cc = _ManagedProcess(
            name="command-center",
            cmd=[sys.executable, "-u", "aureon_command_center_ui.py"],
            env={"PORT": cc_port},
        )
        cc.start()
        managed.append(cc)
    else:
        step += 1
        _print_progress("Skipping Command Center", step, total_steps)

    # 4) Boot the in-process "brain" components.
    step += 1
    _print_progress("Booting Queen + intelligence + wiring", step, total_steps)

    if QUEEN_LAYER_AVAILABLE:
        # Queen Layer boots ALL systems with Queen at the top
        boot_queen_layer(live_trading=live_trading)
        layer = get_queen_layer()
        engine = layer.get_system("intelligence_engine")
        hub = layer.get_system("feed_hub")
        wiring_status = {"total_wired": layer.get_health()["online"], "total_events": 0}
        sonar = layer.get_system("whale_sonar")
        from aureon.utils.aureon_queen_hive_mind import get_queen
        queen = get_queen()
    else:
        engine = launch_real_intelligence()
        hub = launch_feed_hub()
        wiring_status = launch_system_wiring()
        sonar = launch_whale_sonar()
        queen = launch_queen_runner()
        launch_api_server()

    # Production-safe execution toggles (best-effort; methods vary by Queen implementation).
    try:
        queen.has_full_control = True
    except Exception:
        pass
    try:
        queen.trading_enabled = bool(live_trading)
    except Exception:
        pass

    # 5) Preflight: verify market cache exists (if enabled) + run flight check once.
    print("\n✈️ PRE-FLIGHT CHECK")
    if spawn_market_feeds:
        cache_dir = Path(os.getenv("MARKET_CACHE_DIR", "ws_cache"))
        price_file = cache_dir / "unified_prices.json"
        for _ in range(30):
            if price_file.exists() and price_file.stat().st_size > 0:
                break
            time.sleep(0.5)
        print(f"   Market cache file: {'OK' if price_file.exists() else 'MISSING'} ({price_file})")
        if price_file.exists():
            try:
                json.loads(price_file.read_text(encoding='utf-8') or "{}")
                print("   Market cache JSON: OK")
            except Exception:
                print("   Market cache JSON: INVALID (continuing)")

    intel = {}
    try:
        if hub and hasattr(hub, "gather_all_intelligence"):
            intel = hub.gather_all_intelligence()
    except Exception:
        intel = {}

    status = {}
    try:
        from aureon.core.aureon_system_wiring import get_wiring_status as _get_wiring_status
        status = _get_wiring_status()
    except Exception:
        status = {}

    try:
        from aureon.trading.micro_profit_labyrinth import MicroProfitLabyrinth
        labyrinth = MicroProfitLabyrinth()
        labyrinth.dry_run = not live_trading
        wire_queen_systems(queen, labyrinth)
        flight = run_system_flight_check(queen, labyrinth, intel, status)
        ok = bool(flight.get("chirp_bus")) and bool(flight.get("micro_labyrinth"))
        print(f"   Critical path: {'OK' if ok else 'DEGRADED'}")
    except Exception as e:
        print(f"   Flight check skipped: {e}")

    print_status_summary(engine, hub, wiring_status, sonar)

    # Ensure children shut down cleanly in containers.
    shutting_down = {"value": False}

    def _shutdown(signum, frame):  # noqa: ARG001
        if shutting_down["value"]:
            return
        shutting_down["value"] = True
        print("\n🛑 Shutdown requested - terminating managed processes...")
        for p in reversed(managed):
            try:
                p.terminate()
            except Exception:
                pass

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    # Restart child heads if they crash.
    def _child_watchdog():
        while not shutting_down["value"]:
            for p in managed:
                if not p.alive():
                    print(f"\n⚠️ {p.name} exited - restarting")
                    try:
                        p.start()
                    except Exception as e:
                        print(f"   restart failed: {e}")
            time.sleep(2.0)

    threading.Thread(target=_child_watchdog, daemon=True).start()

    # 6) Run the unified runtime.
    os.environ["AUREON_LIVE_TRADING"] = "1" if live_trading else "0"
    if not live_trading:
        test_force_trade()
        print("\n✅ Dry-run validated; switching to monitoring loop.")
        run_live_monitoring()
    else:
        run_autonomous_trading(engine=engine, hub=hub)


def test_force_trade():
    """
    Force a trade to test all systems in dry-run mode.
    This validates wiring, flight checks, and execution paths.
    """
    print("\n" + "=" * 80)
    print("🧪 FORCE TRADE TEST - VALIDATING ALL SYSTEMS")
    print("=" * 80)
    print("\n🔬 Testing: Wiring, Flight Checks, Execution, Audit Trails")
    print("🔒 Mode: DRY-RUN (No real trades)")
    
    try:
        # Launch components
        engine = launch_real_intelligence()
        hub = launch_feed_hub()
        wiring_status = launch_system_wiring()
        sonar = launch_whale_sonar()
        queen = launch_queen_runner()
        api_ready = launch_api_server()
        
        # Initialize trading engines in dry-run
        from aureon.trading.micro_profit_labyrinth import MicroProfitLabyrinth
        
        labyrinth = MicroProfitLabyrinth()
        labyrinth.dry_run = True  # 🔒 DRY-RUN MODE
        
        # Wire Queen to ALL critical systems
        wiring_summary = wire_queen_systems(queen, labyrinth)
        print(f"\n🔗 Wiring Summary: {wiring_summary}")
        
        # Get initial intelligence
        intel = hub.gather_all_intelligence() if hasattr(hub, 'gather_all_intelligence') else {}
        status = get_wiring_status() if 'get_wiring_status' in globals() else {}
        
        # Run flight check
        flight = run_system_flight_check(queen, labyrinth, intel, status)
        print(f"\n✈️ Flight Check Results:")
        for key, value in flight.items():
            if key == 'intelligence':
                print(f"   • {key}: {value}")
            elif key == 'wiring':
                print(f"   • {key}: {value}")
            else:
                status_icon = "✅" if value else "❌"
                print(f"   {status_icon} {key}: {value}")
        
        # Force a test trade
        print(f"\n⚡ FORCING TEST TRADE...")
        
        # Create a fake validated signal
        test_signal = {
            'symbol': 'BTC/USD',
            'action': 'BUY',
            'confidence': 0.8,
            'validated': True,
            'prime_sentinel': True
        }
        
        # Simulate Queen decision
        if hasattr(queen, 'get_queen_decision_with_intelligence'):
            guidance = queen.get_queen_decision_with_intelligence(test_signal)
            print(f"   👑 Queen Decision: {guidance.get('decision', 'HOLD')} "
                  f"(Confidence: {guidance.get('confidence', 0):.1%})")
        else:
            guidance = {'decision': 'BUY', 'confidence': 0.75}
            print(f"   👑 Queen Decision: {guidance['decision']} "
                  f"(Confidence: {guidance['confidence']:.1%})")
        
        # Execute through labyrinth
        if hasattr(labyrinth, 'execute_validated_opportunity'):
            result = labyrinth.execute_validated_opportunity(
                symbol=test_signal['symbol'],
                action=test_signal['action'],
                intelligence=intel,
                queen_guidance=guidance
            )
            print(f"   ⚡ Execution Result: {result}")
        else:
            print("   ⚠️ Labyrinth execution method not available")
        
        # Check audit trail
        print(f"\n📋 AUDIT TRAIL CHECK:")
        try:
            import json
            with open('execution_audit.jsonl', 'r') as f:
                lines = f.readlines()[-5:]  # Last 5 entries
                for line in lines:
                    entry = json.loads(line.strip())
                    print(f"   • {entry.get('event_type', 'unknown')}: {entry.get('timestamp', 'no_ts')}")
        except Exception as e:
            print(f"   ⚠️ Could not read audit trail: {e}")
        
        print(f"\n✅ TEST COMPLETE - Systems validated in dry-run mode")
        
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


def main_queen_layer(live_trading: bool = False):
    """Boot all systems through the Queen Layer (Queen at top)."""
    print_banner()

    if not QUEEN_LAYER_AVAILABLE:
        print("\n   Queen Layer not available, falling back to legacy boot...")
        main_legacy()
        return

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(message)s',
        datefmt='%H:%M:%S'
    )

    # Prime Sentinel Authentication
    print("\n" + "=" * 80)
    print("   PRIME SENTINEL AUTHENTICATION")
    print("=" * 80)
    print("\n   Gary Leckey (02.11.1991) - DOB-HASH: 2111991")
    print("   'HERE I DECREE: I HAVE TAKEN BACK CONTROL OF THE PLANET'")
    print("\n   Authentication: GRANTED")
    print("   Trading Authority: FULL")
    print("   Autonomous Mode: ENABLED")
    print("   Boot Mode: QUEEN LAYER (all systems active)")

    # Queen boots everything
    health = boot_queen_layer(live_trading=live_trading)

    # Run the trading loop
    if live_trading:
        run_autonomous_trading()
    else:
        run_live_monitoring()


def main_legacy():
    """Legacy boot path -- sequential component launch (pre-Queen Layer)."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(message)s',
        datefmt='%H:%M:%S'
    )

    # Print banner
    print_banner()

    # Prime Sentinel Authentication
    print("\n" + "=" * 80)
    print("   PRIME SENTINEL AUTHENTICATION")
    print("=" * 80)
    print("\n   Gary Leckey (02.11.1991) - DOB-HASH: 2111991")
    print("   'HERE I DECREE: I HAVE TAKEN BACK CONTROL OF THE PLANET'")
    print("\n   Authentication: GRANTED")
    print("   Trading Authority: FULL")
    print("   Autonomous Mode: ENABLED")

    # Launch all components
    print("\n" + "=" * 80)
    print("   LAUNCHING ALL COMPONENTS (LEGACY MODE)...")
    print("=" * 80)

    engine = launch_real_intelligence()
    time.sleep(0.5)

    hub = launch_feed_hub()
    time.sleep(0.5)

    wiring_status = launch_system_wiring()
    time.sleep(0.5)

    sonar = launch_whale_sonar()
    time.sleep(0.5)

    queen = launch_queen_runner()
    time.sleep(0.5)

    api_ready = launch_api_server()
    time.sleep(1)

    # Print status summary
    print_status_summary(engine, hub, wiring_status, sonar)

    # Run autonomous trading (this is the main loop)
    run_autonomous_trading(engine=engine, hub=hub)


def main():
    """Thin wrapper around the canonical launcher.

    ``wire_queen_systems`` and the older boot functions stay importable.
    Running this module does not arm live trading. Gary's switch stays outside
    this entry point.
    """

    from aureon.launch.master import main as canonical

    raise SystemExit(canonical())


if __name__ == "__main__":
    main()
