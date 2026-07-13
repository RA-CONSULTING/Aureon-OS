#!/usr/bin/env python3
"""
run_integrated_cognitive_system.py -- Entry point for the Aureon ICS

Boots all cognitive subsystems, starts the live terminal dashboard,
launches the Vault UI + Phi Bridge server for phone communication,
and accepts user goals via stdin.

Usage:
    python run_integrated_cognitive_system.py
    python run_integrated_cognitive_system.py --lan
    python run_integrated_cognitive_system.py --remote
    python run_integrated_cognitive_system.py --lan --port 8080
"""

import argparse
import io
import logging
import os
import sys

# Route all voice/LLM calls through the local AureonBrain adapter (no Ollama
# probes) unless the user has explicitly configured an LLM backend.
# This keeps boot time under ~10 s by skipping Ollama model cold-start probes.
os.environ.setdefault("AUREON_VOICE_BACKEND", "brain")
os.environ.setdefault("AUREON_LLM_PROBE_TIMEOUT_S", "3")
os.environ.setdefault("AUREON_LLM_HEALTH_TIMEOUT_S", "2")

# Force UTF-8 on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.WARNING, stream=sys.stderr)

from aureon.core.integrated_cognitive_system import IntegratedCognitiveSystem


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aureon Integrated Cognitive System — all subsystems as one organism",
    )
    parser.add_argument(
        "--lan", action="store_true",
        help="Bind on 0.0.0.0 so phones on the same WiFi can reach the "
             "Phi Bridge at http://<LAN_IP>:<port>/bridge",
    )
    parser.add_argument(
        "--remote", action="store_true",
        help="Start a tunnel (cloudflared/ngrok) so your phone on 4G "
             "can reach the system from anywhere on the internet",
    )
    parser.add_argument(
        "--port", type=int, default=5566,
        help="Port for the Vault UI + Phi Bridge server (default 5566)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable verbose logging",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.INFO)

    ics = IntegratedCognitiveSystem()
    try:
        ics.run(lan=args.lan, remote=args.remote, port=args.port)
    except KeyboardInterrupt:
        pass
    finally:
        ics.shutdown()


if __name__ == "__main__":
    main()
