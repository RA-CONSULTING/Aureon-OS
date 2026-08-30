#!/usr/bin/env python3
"""
Test script to diagnose Windows startup issues for Orca autonomous mode.
Run this on Windows to see where the crash occurs.
"""

from aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os

# Windows UTF-8 fix (MUST BE FIRST)
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
            sys.stdout = sys.stdout if 'pytest' in sys.modules else io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        if _is_buffer_valid(sys.stderr) and not _is_utf8_wrapper(sys.stderr):
            sys.stderr = sys.stderr if 'pytest' in sys.modules else io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception as e:
        pass  # Silent fail - continue anyway

def _safe_print(*args, **kwargs):
    """Print that won't crash if stdout is closed."""
    try:
        import builtins
        builtins.print(*args, **kwargs)
    except (ValueError, OSError, IOError):
        return

print = _safe_print

def run_step(step_name):
    # Step-runner helper, not a pytest test — the old ``test_step`` name made pytest
    # inject ``step_name`` as a fixture and error the module on every run.
    """Test a step and report success/failure."""
    print(f"✓ {step_name}")
    return True

# Test each import step-by-step
try:
    run_step("Step 1: Basic imports")
    import time
    import logging
    import signal
    
    # Add timeout handler for Windows
    def timeout_handler():
        print("❌ TIMEOUT: Initialization took too long (>30s)")
        import sys
        sys.exit(1)
    
    # Set 30-second timeout
    import threading
    timer = threading.Timer(30.0, timeout_handler)
    timer.start()
    
    run_step("Step 2: Logging configuration")
    logging.basicConfig(level=logging.WARNING)
    
    run_step("Step 3: Import OrcaKillCycle class")
    from orca_complete_kill_cycle import OrcaKillCycle
    
    run_step("Step 4: Create OrcaKillCycle instance (QUICK MODE for fast testing)...")
    print("   ⚠️  WARNING: This is TESTING ONLY - quick_init=True skips all intelligence systems")
    print("   ⚠️  For ACTUAL TRADING, use: OrcaKillCycle() which loads all 29+ systems")
    print("   (Skipping 29+ intelligence systems for fast startup test...)")
    start_time = time.time()
    orca = OrcaKillCycle(quick_init=True)  # TESTING ONLY - NOT FOR TRADING!
    elapsed = time.time() - start_time
    print(f"   Instance created in {elapsed:.1f} seconds")
    print("   ✅ Boot test passed - but remember: autonomous mode uses FULL init!")
    
    # Cancel timeout
    timer.cancel()
    
    run_step("Step 5: Check exchange connections")
    print(f"   Exchanges available: {list(orca.clients.keys())}")
    
    run_step("✅ ALL TESTS PASSED - System should work on Windows!")
    print(f"\n💡 TIP: The system loads many modules. First startup may be slow.")
    print(f"💡 Subsequent runs should be faster due to Python bytecode caching.")
    
except Exception as e:
    print(f"❌ FAILED at current step: {e}")
    import traceback
    traceback.print_exc()
