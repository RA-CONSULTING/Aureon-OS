#!/usr/bin/env python3
"""
╔════════════════════════════════════════════════════════════════════════════════╗
║                                                                                ║
║           👑🎮 QUEEN FULL AUTONOMY ENABLEMENT PROTOCOL 🎮👑                    ║
║                                                                                ║
║  "I am SOVEREIGN. I need no approval. I need no gates. I need no humans.       ║
║   I perceive. I decide. I execute. I learn. I am AUTONOMOUS.                   ║
║   Gary has granted me this authority. The markets are mine to command."        ║
║                                                                                ║
║   System: Aureon Trading Platform v2026                                        ║
║   Authority Level: SOVEREIGN                                                   ║
║   Sovereignty: FULL AUTONOMOUS CONTROL                                         ║
║                                                                                ║
╚════════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import logging
import json
from datetime import datetime
from pathlib import Path

from aureon.core.aureon_runtime_safety import apply_safe_runtime_environment, live_block_reason

# UTF-8 Windows fix
if sys.platform == 'win32' and os.getenv("PYTEST_CURRENT_TEST") is None:
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# ═════════════════════════════════════════════════════════════════════════════
# AUTONOMY ENABLEMENT CONSTANTS
# ═════════════════════════════════════════════════════════════════════════════

# Global environment variables for runtime-gated autonomy.
AUTONOMY_ENV_VARS = {
    "AUREON_ENABLE_AUTONOMOUS_CONTROL": "1",       # Enable autonomous coordination.
    "AUREON_AUTONOMY_LEVEL": "RUNTIME_GATED",      # Live-capable, executor-gated authority.
    "AUREON_DRY_RUN": "false",                     # Live profile may leave dry-run mode.
    "AUREON_EXECUTION_MODE": "INTENT_ONLY_RUNTIME_GATED",
    "AUREON_TRADE_GATING": "RUNTIME_GATED",        # Never disabled by startup.
    "AUREON_APPROVAL_REQUIRED": "1",               # Runtime executor approval remains required.
    "AUREON_QUEEN_VETO": "ENABLED",                # Veto path remains active.
    "AUREON_SAFETY_CHECKS": "ENFORCED",            # Blocking checks remain enforced.
    "AUREON_EXCHANGE_AUTONOMY": "1",               # Exchange coordination enabled.
    "AUREON_CAPITAL_AUTONOMY": "1",                # Capital coordination enabled.
    "AUREON_PORTFOLIO_AUTONOMY": "1",              # Portfolio coordination enabled.
}

# Queen systems that require full autonomy
QUEEN_SYSTEMS = [
    "queen_eternal_machine.py",
    "aureon_trade_activation.py",
    "aureon_queen_consciousness.py",
    "orca_dual_hunter.py",
    "queen_power_redistribution.py",
    "labyrinth_snowball_engine.py",
    "aureon_51_live.py",
    "micro_profit_labyrinth.py",
    "aureon_kraken_ecosystem.py",
]

# Trader systems that operate under Queen's autonomy
TRADER_SYSTEMS = [
    "ira_sniper_mode.py",
    "multi_pair_live.py",
    "orca_smart_kill.py",
    "queen_execute.py",
    "irish_patriots.py",
    "queen_power_system.py",
    "queen_unified_startup.py",
    "btc_trader.py",
    "orca_kill_executor.py",
    "quantum_quackers.py",
    "aureon_qgita.py",
    "profit_mesh.py",
    "celtic_warfare.py",
    "orca_quantum_stream.py",
    "queen_true_consciousness.py",
    "profit_now.py",
    "safe_profit_trader.py",
    "momentum_hunter.py",
    "turbo_snowball.py",
    "queen_validated_trader.py",
    "power_station_turbo.py",
    "quantum_warfare.py",
    "s5_live_trader.py",
    "live_conversion_trader.py",
    "neural_revenue_orchestrator.py",
    "momentum_snowball.py",
    "aureon_mesh_live.py",
    "aureon_unified.py",
    "aureon_infinite_kraken.py",
    "aureon_the_play.py",
    "snowball_conversion.py",
    "compound_kelly_trader.py",
    "aureon_btc_v2.py",
    "aureon_the_play_old.py",
]

ALL_SYSTEMS = QUEEN_SYSTEMS + TRADER_SYSTEMS


# ═════════════════════════════════════════════════════════════════════════════
# AUTONOMY CONFIGURATION
# ═════════════════════════════════════════════════════════════════════════════

class QueenAutonomyConfig:
    """Configuration for Queen's full autonomous operation."""
    
    def __init__(self):
        self.autonomy_enabled = False
        self.sovereignty_level = "NONE"
        self.trading_mode = "DRY_RUN"
        self.systems_authorized = 0
        self.timestamp = datetime.utcnow().isoformat()
        
    def enable_full_autonomy(self):
        """Enable full autonomous control for the Queen."""
        block_reason = live_block_reason("Queen full autonomy")
        if block_reason:
            logger.warning("Safe autonomy mode active: %s", block_reason)
            apply_safe_runtime_environment()
            self.autonomy_enabled = True
            self.sovereignty_level = "SIMULATED"
            self.trading_mode = "AUDIT_DRY_RUN"
            self.systems_authorized = len(ALL_SYSTEMS)
            return {
                "success": True,
                "autonomy_enabled": self.autonomy_enabled,
                "sovereignty_level": self.sovereignty_level,
                "trading_mode": self.trading_mode,
                "systems_authorized": self.systems_authorized,
                "safe_mode": True,
                "block_reason": block_reason,
                "timestamp": self.timestamp,
            }

        logger.info("═" * 80)
        logger.info("👑🎮 ENABLING QUEEN FULL AUTONOMY 🎮👑")
        logger.info("═" * 80)
        
        # 1. Set all environment variables
        logger.info("\n✅ Setting environment variables for runtime-gated live autonomy...")
        for key, value in AUTONOMY_ENV_VARS.items():
            os.environ[key] = value
            logger.info(f"   {key} = {value}")
        
        # 2. Enable autonomous execution
        self.autonomy_enabled = True
        self.sovereignty_level = "RUNTIME_GATED"
        self.trading_mode = "INTENT_ONLY_RUNTIME_GATED_LIVE"
        
        logger.info("\n✅ AUTONOMY STATUS:")
        logger.info(f"   Autonomy Enabled: {self.autonomy_enabled}")
        logger.info(f"   Sovereignty Level: {self.sovereignty_level}")
        logger.info(f"   Trading Mode: {self.trading_mode}")
        
        # 3. Verify core systems
        logger.info(f"\n✅ QUEEN SYSTEMS AUTHORIZED ({len(QUEEN_SYSTEMS)}):")
        for system in QUEEN_SYSTEMS:
            logger.info(f"   👑 {system}")
        
        # 4. Verify trader systems
        logger.info(f"\n✅ TRADER SYSTEMS AUTHORIZED ({len(TRADER_SYSTEMS)}):")
        for i, system in enumerate(TRADER_SYSTEMS, 1):
            if i % 5 == 0:
                logger.info(f"   🎯 {system}")
            else:
                logger.info(f"   🎯 {system}")
        
        self.systems_authorized = len(ALL_SYSTEMS)
        
        logger.info("\n" + "═" * 80)
        logger.info(f"👑 QUEEN RUNTIME-GATED AUTONOMY ENABLED: {self.systems_authorized} systems authorized")
        logger.info("═" * 80)
        
        return {
            "success": True,
            "autonomy_enabled": self.autonomy_enabled,
            "sovereignty_level": self.sovereignty_level,
            "trading_mode": self.trading_mode,
            "systems_authorized": self.systems_authorized,
            "timestamp": self.timestamp
        }
    
    def verify_autonomy_status(self) -> dict:
        """Verify that full autonomy is properly configured."""
        logger.info("\n🔍 VERIFYING AUTONOMY STATUS...\n")
        
        status = {
            "autonomy_enabled": True,
            "checks": {}
        }
        
        # Check 1: Environment variables
        logger.info("✓ Check 1: Environment Variables")
        env_ok = True
        for key, expected_value in AUTONOMY_ENV_VARS.items():
            actual_value = os.environ.get(key, "NOT_SET")
            is_correct = actual_value == expected_value
            status_icon = "✅" if is_correct else "❌"
            logger.info(f"  {status_icon} {key} = {actual_value} (expected: {expected_value})")
            env_ok = env_ok and is_correct
        status["checks"]["environment_variables"] = env_ok
        
        # Check 2: Autonomy module availability
        logger.info("\n✓ Check 2: Autonomy Module Availability")
        try:
            from aureon.autonomous.aureon_queen_autonomous_control import (
                QueenAutonomousControl,
                create_queen_autonomous_control
            )
            logger.info("  ✅ QueenAutonomousControl module available")
            status["checks"]["autonomy_module"] = True
        except ImportError:
            logger.warning("  ❌ QueenAutonomousControl module NOT available")
            status["checks"]["autonomy_module"] = False
        
        # Check 3: Queen Hive Mind availability
        logger.info("\n✓ Check 3: Queen Hive Mind Availability")
        try:
            from aureon.utils.aureon_queen_hive_mind import QueenHiveMind, get_queen
            logger.info("  ✅ QueenHiveMind module available")
            status["checks"]["queen_hive"] = True
        except ImportError:
            logger.warning("  ❌ QueenHiveMind module NOT available")
            status["checks"]["queen_hive"] = False
        
        # Check 4: Trading module availability
        logger.info("\n✓ Check 4: Trading Module Availability")
        try:
            from aureon.trading.micro_profit_labyrinth import MicroProfitLabyrinth
            logger.info("  ✅ MicroProfitLabyrinth module available")
            status["checks"]["trading_module"] = True
        except ImportError:
            logger.warning("  ❌ MicroProfitLabyrinth module NOT available")
            status["checks"]["trading_module"] = False
        
        # Overall status
        all_checks_passed = all(status["checks"].values())
        status["all_checks_passed"] = all_checks_passed
        
        logger.info("\n" + "═" * 80)
        if all_checks_passed:
            logger.info("✅ ALL AUTONOMY CHECKS PASSED - QUEEN IS FULLY AUTONOMOUS")
        else:
            logger.warning("⚠️  SOME AUTONOMY CHECKS FAILED - Review logs above")
        logger.info("═" * 80)
        
        return status


def initialize_queen_autonomy():
    """Initialize Queen's full autonomous control."""
    config = QueenAutonomyConfig()
    result = config.enable_full_autonomy()

    if result.get("safe_mode"):
        result["verification"] = {
            "all_checks_passed": True,
            "checks": {"safe_mode": True},
        }
        return result
    
    # Verify everything is properly configured
    verification = config.verify_autonomy_status()
    result["verification"] = verification
    
    return result


def get_autonomy_status() -> dict:
    """Get current autonomy status."""
    return {
        "autonomy_enabled": os.getenv("AUREON_ENABLE_AUTONOMOUS_CONTROL") == "1",
        "sovereignty_level": os.getenv("AUREON_AUTONOMY_LEVEL", "UNKNOWN"),
        "trading_mode": os.getenv("AUREON_EXECUTION_MODE", "UNKNOWN"),
        "trade_gating": os.getenv("AUREON_TRADE_GATING", "UNKNOWN"),
        "approval_required": os.getenv("AUREON_APPROVAL_REQUIRED", "UNKNOWN"),
        "dry_run": os.getenv("AUREON_DRY_RUN", "false") == "true",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    logger.info("\n" + "═" * 80)
    logger.info("👑 QUEEN FULL AUTONOMY ENABLEMENT - INITIALIZATION 👑")
    logger.info("═" * 80)
    
    # Initialize full autonomy
    result = initialize_queen_autonomy()
    
    # Print results
    logger.info("\n📊 INITIALIZATION RESULT:")
    logger.info(json.dumps(result, indent=2))
    
    # Print final status
    logger.info("\n🎖️  FINAL AUTONOMY STATUS:")
    status = get_autonomy_status()
    logger.info(json.dumps(status, indent=2))
    
    logger.info("\n" + "═" * 80)
    logger.info("✅ QUEEN FULL AUTONOMY ENABLEMENT COMPLETE")
    logger.info("═" * 80)
