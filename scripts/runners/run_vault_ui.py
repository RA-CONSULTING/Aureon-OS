#!/usr/bin/env python3
"""
run_vault_ui.py — Launch the Aureon Vault UI for communicating with the vault
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Starts a Flask server on the configured port, serves the chat UI at /,
and optionally starts the self-feedback loop daemon so the vault is
alive while you talk to it.

Usage:
    python scripts/runners/run_vault_ui.py
    python scripts/runners/run_vault_ui.py --port 5566 --start-loop
    python scripts/runners/run_vault_ui.py --host 0.0.0.0 --port 8080 --interval 0.5
"""

from __future__ import annotations

import argparse
import logging
import os
import sys


def _setup_path() -> None:
    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if repo not in sys.path:
        sys.path.insert(0, repo)


def _detect_lan_ip() -> str:
    """Best-effort LAN IPv4 lookup. Returns "" if no usable address."""
    import socket

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # No packet is actually sent — connect() on UDP only sets the
        # default route, which lets us read the outbound interface IP.
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return ""
    finally:
        try:
            s.close()
        except Exception:
            pass


def main() -> None:
    _setup_path()

    from aureon.core.aureon_env import bootstrap_credentials

    bootstrap_credentials()

    parser = argparse.ArgumentParser(
        description="Launch the Aureon Vault UI for communicating with the vault",
    )
    parser.add_argument("--host", default="127.0.0.1", help="bind host (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5566, help="bind port (default 5566)")
    parser.add_argument(
        "--lan", action="store_true",
        help="bind on 0.0.0.0 so phones / other devices on the same WiFi can hit "
             "the vault and the phi-bridge mobile UI at /bridge",
    )
    parser.add_argument(
        "--start-loop", action="store_true",
        help="also start the self-feedback loop daemon in the background",
    )
    parser.add_argument(
        "--interval", type=float, default=1.0,
        help="base interval seconds for the love+gratitude clock (default 1.0)",
    )
    parser.add_argument(
        "--no-signals", action="store_true",
        help="do not start QueenCortex/MyceliumMind/LoveStream signal daemons (metrics may be flat)",
    )
    parser.add_argument(
        "--love-stream-rate", type=float, default=1.0,
        help="LoveStream publish rate in Hz when signals are enabled (default 1.0)",
    )
    parser.add_argument(
        "--no-voice", action="store_true",
        help="disable the voice layer (chat endpoints will 400)",
    )
    parser.add_argument(
        "--no-integrations", action="store_true",
        help="do not wire the Ollama/Obsidian integration layer",
    )
    parser.add_argument(
        "--no-ollama", action="store_true",
        help="skip Ollama voice wiring even when integrations are enabled",
    )
    parser.add_argument(
        "--no-obsidian", action="store_true",
        help="skip Obsidian bridge+sink wiring even when integrations are enabled",
    )
    parser.add_argument(
        "--ollama-model", default=None,
        help="override the Ollama model name used for integrated voices",
    )
    parser.add_argument(
        "--obsidian-vault-path", default=None,
        help="filesystem vault path for Obsidian fallback mode",
    )
    parser.add_argument(
        "--pathway-map", action="store_true",
        help="also build the full neural pathway graph at startup (slower)",
    )
    parser.add_argument(
        "--run-integration-audit", action="store_true",
        help="also run the full integration audit trail at startup (slower)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="verbose logging",
    )
    args = parser.parse_args()

    level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    if args.lan and args.host == "127.0.0.1":
        args.host = "0.0.0.0"

    from aureon.vault import AureonSelfFeedbackLoop
    from aureon.vault.ui import run_server
    from aureon.integrations import wire_integrations

    loop = AureonSelfFeedbackLoop(
        base_interval_s=args.interval,
        enable_voice=not args.no_voice,
    )

    wiring_result = None
    if not args.no_integrations:
        if args.obsidian_vault_path:
            os.environ["AUREON_OBSIDIAN_VAULT_PATH"] = args.obsidian_vault_path
        wiring_result = wire_integrations(
            vault=loop.vault,
            loop=loop,
            enable_ollama=not args.no_ollama,
            enable_obsidian=not args.no_obsidian,
            enable_pathway_mapping=args.pathway_map,
            run_audit=args.run_integration_audit,
            ollama_model=args.ollama_model,
        )

    # Optional signal daemons. These publish into the shared ThoughtBus so the
    # vault state is non-flat even when the UI is run standalone.
    cortex = None
    mind = None
    love_stream = None
    if not args.no_signals:
        try:
            from aureon.queen.queen_cortex import get_cortex
            cortex = get_cortex()
            cortex.start()
        except Exception:
            cortex = None
        try:
            from aureon.queen.queen_mycelium_mind import get_mycelium_mind
            mind = get_mycelium_mind()
            mind.start()
        except Exception:
            mind = None
        try:
            from aureon.swarm_motion.love_stream import StandingWaveLoveStream
            love_stream = StandingWaveLoveStream(sample_rate_hz=float(args.love_stream_rate))
            love_stream.start()
        except Exception:
            love_stream = None

    print("=" * 72)
    print("  AUREON VAULT UI — Queen's Voice")
    print("=" * 72)
    print(f"  Loop ID:     {loop.loop_id}")
    print(f"  Voice layer: {'ENABLED' if loop.voice_engine else 'DISABLED'}")
    print(f"  Signals:     {'ENABLED' if not args.no_signals else 'disabled'}")
    print(
        f"  Integrations:{' ENABLED' if not args.no_integrations else ' disabled'}"
    )
    print(f"  Bind:        http://{args.host}:{args.port}/")
    print(f"  Interval:    {args.interval}s")
    print(f"  Background:  {'YES' if args.start_loop else 'no (use /api/loop/start to wake it)'}")
    if args.lan:
        lan_ip = _detect_lan_ip()
        print(f"  Phi-Bridge:  ENABLED  (LAN bind 0.0.0.0)")
        if lan_ip:
            print(f"  Phone URL:   http://{lan_ip}:{args.port}/bridge")
            print(f"  Desktop UI:  http://{lan_ip}:{args.port}/")
    print("=" * 72)
    print()
    if wiring_result is not None:
        for note in wiring_result.notes:
            print(f"  integration: {note}")
        print()
    print("  Open the URL in a browser to chat with the vault.")
    print("  Send a message, press Converse, or click Run one tick.")
    if args.lan:
        print()
        print("  Phone setup:")
        print("    1) Phone must be on the same WiFi as this PC.")
        print("    2) Open the Phone URL above in the phone's browser.")
        print("    3) Use 'Add to Home Screen' to install the bridge as an app.")
        print("    4) If the phone can't reach it, allow the port through the")
        print(f"       Windows firewall:")
        print(f"       New-NetFirewallRule -DisplayName 'Aureon Vault' \\")
        print(f"         -Direction Inbound -Action Allow -Protocol TCP \\")
        print(f"         -LocalPort {args.port} -Profile Private")
    print("  Press Ctrl-C to stop.")
    print()

    try:
        run_server(
            host=args.host,
            port=args.port,
            loop=loop,
            start_loop=args.start_loop,
        )
    except KeyboardInterrupt:
        print("\nShutting down vault UI...")
        try:
            loop.stop()
        except Exception:
            pass
        for daemon in (love_stream, mind, cortex):
            try:
                if daemon is not None and hasattr(daemon, "stop"):
                    daemon.stop()
            except Exception:
                pass


if __name__ == "__main__":
    main()
