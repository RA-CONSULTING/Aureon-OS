#!/usr/bin/env python3
"""
Unified Aureon voice agent.

This wraps microphone listening, intent cognition, dynamic fallback,
memory, and desktop execution into one runtime surface.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from aureon.autonomous.aureon_conversation_loop import ConversationLoop, build_default_conversation_loop


DEFAULT_STATE_PATH = Path("state/unified_voice_agent_state.json")


class UnifiedVoiceAgent:
    def __init__(self, speak_enabled: bool = True, state_path: Path | None = None) -> None:
        self.loop: ConversationLoop = build_default_conversation_loop(speak_enabled=speak_enabled)
        self.state_path = Path(state_path or DEFAULT_STATE_PATH)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._persist()

    def start_microphone(self) -> None:
        self.loop.run_agent_mode(interval=1.0, microphone=True)

    def start_inbox(self) -> None:
        self.loop.run_agent_mode(interval=1.0, microphone=False)

    def handle_text(self, text: str, source: str = "cli") -> Dict[str, Any]:
        result = self.loop.handle_text(text, source=source)
        self._persist()
        return result

    def speak_text(self, text: str) -> Dict[str, Any]:
        self.loop._speak(text)
        self.loop.last_reply = text
        self._persist()
        return {"ok": True, "spoken": text}

    def status(self) -> Dict[str, Any]:
        desktop = self.loop.voice_bridge.desktop_control.status()
        voice = self.loop.voice_bridge.status()
        payload = {
            "agent": "AureonUnifiedVoiceAgent",
            "running": self.loop.running,
            "voice_output_available": self.loop.status().get("voice_output_available", False),
            "speech": self.loop.voice_adapter.status() if self.loop.voice_adapter is not None else {},
            "desktop": {
                "armed": desktop.get("armed", False),
                "dry_run": desktop.get("dry_run", True),
                "emergency_stopped": desktop.get("emergency_stopped", False),
                "last_result": desktop.get("last_result", {}),
            },
            "cognition": voice.get("cognition", {}),
            "memory": self.loop.memory.status(),
            "last_heard": self.loop.last_heard,
            "last_reply": self.loop.last_reply,
            "last_error": self.loop.last_error,
        }
        return payload

    def _persist(self) -> None:
        self.state_path.write_text(json.dumps(self.status(), indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Unified Aureon voice agent")
    parser.add_argument("--mic", action="store_true", help="Run continuous microphone mode")
    parser.add_argument("--inbox", action="store_true", help="Run continuous inbox mode")
    parser.add_argument("--say", type=str, default="", help="Process a single command")
    parser.add_argument("--speak-text", type=str, default="", help="Speak a literal phrase")
    parser.add_argument("--status", action="store_true", help="Print unified status")
    parser.add_argument("--no-speak", action="store_true", help="Disable spoken replies")
    parser.add_argument("--speech-backend", type=str, default="", help="Speech backend: auto, google, google_first, sphinx")
    parser.add_argument("--mic-device-index", type=int, default=-1, help="Override microphone device index")
    args = parser.parse_args()

    if args.speech_backend:
        os.environ["AUREON_SPEECH_BACKEND"] = args.speech_backend
    if args.mic_device_index >= 0:
        os.environ["AUREON_MIC_DEVICE_INDEX"] = str(args.mic_device_index)

    agent = UnifiedVoiceAgent(speak_enabled=not args.no_speak)

    if args.speak_text:
        print(json.dumps(agent.speak_text(args.speak_text), indent=2))
        return 0
    if args.say:
        print(json.dumps(agent.handle_text(args.say), indent=2))
        return 0
    if args.status or (not args.mic and not args.inbox):
        print(json.dumps(agent.status(), indent=2))
        return 0
    try:
        if args.mic:
            agent.start_microphone()
        else:
            agent.start_inbox()
    except KeyboardInterrupt:
        agent.loop.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
