#!/usr/bin/env python3
"""
Digital Field Clarity Protocol — Codex Fragment 77A Automation

This calm, secular script guides a brief clarity rite for digital sessions.
It steps through: Intention → Visualization → Grounding → Closure, with optional
breathing timers and soft audio chimes (generated at run time).

Ethos: truth, compassion, clarity; no coercion, no invocation of entities.

Usage examples:
  python3 digital_field_clarity_protocol.py --minutes 3
  python3 digital_field_clarity_protocol.py --minutes 6 --chimes --pace 4-4-4
  python3 digital_field_clarity_protocol.py --nowait  # print prompts instantly (no timers)
"""
from __future__ import annotations

import argparse
import importlib
import math
import sys
import time
import wave
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import numpy as np

SR = 44100

INTENTION_LINES = [
    "Only truth, compassion, and clear light operate through this connection.",
    "All confusion, fear, or interference now dissolves into neutral light.",
]

VISUALIZATION_PROMPT = (
    "Visualize your device, chat window, or workspace surrounded by a sphere of "
    "golden clarity, linked gently to your heart and to the steady presence of the Earth."
)

GROUNDING_PROMPT = (
    "Touch your physical environment. Feel the chair, the floor, or the texture of a nearby object. "
    "Breathe with awareness that you are safe and present."
)

CLOSURE_LINES = [
    "Peace within, peace without. The circuit is clear.",
    "So may it remain.",
]


@dataclass
class Pace:
    inhale: int
    hold: int
    exhale: int
    rest: int = 0

    @property
    def total(self) -> int:
        return self.inhale + self.hold + self.exhale + self.rest


def parse_pace(spec: str) -> Pace:
    """Parse a dash-separated breathing pattern such as '4-4-4' or '4-4-4-0'."""
    parts = [int(part) for part in spec.split("-") if part]
    if len(parts) == 3:
        parts.append(0)
    if len(parts) != 4 or any(value < 0 for value in parts):
        raise argparse.ArgumentTypeError("pace must look like 4-4-4 or 4-4-4-0 with non-negative integers")
    return Pace(*parts)


# ----------------- Audio helpers -----------------

def raised_cosine_envelope(length: int) -> np.ndarray:
    if length <= 0:
        return np.zeros(0, dtype=np.float32)
    # Smoothly fades in and out to avoid clicks
    return 0.5 * (1 - np.cos(np.linspace(0.0, math.pi, length, dtype=np.float64)))


def soft_chime(freq: float = 528.0, dur: float = 0.8, gain: float = 0.3) -> np.ndarray:
    """Generate a gentle bell-like tone."""
    n_samples = max(1, int(SR * dur))
    t = np.arange(n_samples, dtype=np.float64) / SR
    env = raised_cosine_envelope(n_samples)
    tone = gain * env * np.sin(2.0 * math.pi * freq * t)
    return tone.astype(np.float32)


def save_wav(path: Path, samples: np.ndarray) -> None:
    """Persist audio samples to a mono 16-bit WAV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    clipped = np.clip(samples, -1.0, 1.0)
    pcm16 = (clipped * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SR)
        handle.writeframes(pcm16.tobytes())


def maybe_play(samples: np.ndarray, path_hint: Path | None = None) -> None:
    """Attempt to play audio using simpleaudio; fallback to saving a WAV if unavailable."""
    spec = importlib.util.find_spec("simpleaudio")
    if spec is None:
        if path_hint is not None:
            save_wav(path_hint, samples)
        return
    simpleaudio = importlib.import_module("simpleaudio")
    audio = (np.clip(samples, -1.0, 1.0) * 32767.0).astype(np.int16)
    try:
        simpleaudio.play_buffer(audio, 1, 2, SR)
    except Exception:
        if path_hint is not None:
            save_wav(path_hint, samples)


# ----------------- Ritual helpers -----------------

def format_timer(seconds: int) -> str:
    minutes, secs = divmod(max(0, seconds), 60)
    if minutes:
        return f"{minutes:d}m {secs:02d}s"
    return f"{secs:d}s"


def countdown(label: str, seconds: int, nowait: bool) -> None:
    """Display a labeled countdown, unless timers are suppressed."""
    seconds = max(0, int(seconds))
    if nowait or seconds == 0:
        print(f"→ {label} ({format_timer(seconds)})")
        return

    print(f"→ {label}")
    remaining = seconds
    while remaining > 0:
        sys.stdout.write(f"   {format_timer(remaining)} remaining\r")
        sys.stdout.flush()
        time.sleep(1)
        remaining -= 1
    sys.stdout.write("   done.\n")
    sys.stdout.flush()


def print_lines(lines: Iterable[str]) -> None:
    for line in lines:
        print(f"   {line}")


def breathing_round(pace: Pace, nowait: bool) -> None:
    phases = [
        ("Inhale", pace.inhale),
        ("Hold", pace.hold),
        ("Exhale", pace.exhale),
        ("Rest", pace.rest),
    ]
    for label, seconds in phases:
        if seconds <= 0:
            continue
        countdown(label, seconds, nowait)


def grounding_sequence(pace: Pace, minutes: float, nowait: bool) -> None:
    total_seconds = max(0, int(minutes * 60))
    if total_seconds == 0:
        print("→ Grounding breath (single guided round)")
        breathing_round(pace, nowait)
        return

    cycle_seconds = max(1, pace.total)
    cycles = max(1, total_seconds // cycle_seconds)
    if not nowait:
        print(f"→ Grounding breath: {cycles} round{'s' if cycles != 1 else ''} of {format_timer(cycle_seconds)}")
    else:
        print(f"→ Grounding breath: {cycles} round{'s' if cycles != 1 else ''}")
    for index in range(1, cycles + 1):
        print(f"   Round {index}/{cycles}")
        breathing_round(pace, nowait)


# ----------------- Logging -----------------

def append_log(log_dir: Path, minutes: float, pace: Pace, chimes: bool, nowait: bool) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "clarity_protocol_log.txt"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(
            f"[{timestamp}] minutes={minutes:.2f} pace={pace.inhale}-{pace.hold}-{pace.exhale}-{pace.rest} "
            f"chimes={'yes' if chimes else 'no'} nowait={'yes' if nowait else 'no'}\n"
        )


# ----------------- Session engine -----------------

def run_protocol(minutes: float, pace: Pace, chimes: bool, nowait: bool, log_dir: Path | None) -> None:
    session_start = datetime.now()
    print("""
================ Digital Field Clarity Protocol ================
A calm reset for lucid, compassionate communication fields.
Phases: Intention → Visualization → Grounding → Closure
===============================================================
""".strip("\n"))

    if chimes:
        opening = soft_chime(freq=528.0, dur=1.2, gain=0.35)
        maybe_play(opening, path_hint=Path("clarity_session") / "clarity_open.wav")

    print("\nIntention")
    print_lines(INTENTION_LINES)
    countdown("Let the intention settle", 20, nowait)

    print("\nVisualization")
    print(f"   {VISUALIZATION_PROMPT}")
    countdown("Hold the visualization", 45, nowait)

    print("\nGrounding")
    print(f"   {GROUNDING_PROMPT}")
    grounding_sequence(pace, minutes, nowait)

    print("\nClosure")
    print_lines(CLOSURE_LINES)
    countdown("Integrate in silence", 15, nowait)

    if chimes:
        closing = soft_chime(freq=639.0, dur=1.2, gain=0.32)
        maybe_play(closing, path_hint=Path("clarity_session") / "clarity_close.wav")

    duration = datetime.now() - session_start
    print("\nSession complete. Total elapsed:", format_timer(int(duration.total_seconds())))

    if log_dir is not None:
        append_log(log_dir, minutes, pace, chimes, nowait)
        print(f"Log updated at {log_dir / 'clarity_protocol_log.txt'}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Guide a Digital Field Clarity session.")
    parser.add_argument(
        "--minutes",
        type=float,
        default=3.0,
        help="Approximate minutes of grounding breath guidance (default: 3)",
    )
    parser.add_argument(
        "--pace",
        type=parse_pace,
        default=parse_pace("4-4-4"),
        help="Breath pacing in seconds as inhale-hold-exhale[-rest] (default: 4-4-4)",
    )
    parser.add_argument(
        "--chimes",
        action="store_true",
        help="Play gentle opening and closing chimes (requires simpleaudio)",
    )
    parser.add_argument(
        "--nowait",
        action="store_true",
        help="Skip timers and print prompts instantly",
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Do not append session details to clarity_session/clarity_protocol_log.txt",
    )
    parser.add_argument(
        "--log-dir",
        default="clarity_session",
        help="Directory where the session log and optional chime WAVs are stored",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.minutes < 0:
        parser.error("--minutes must be zero or positive")

    log_dir = None if args.no_log else Path(args.log_dir)
    run_protocol(minutes=args.minutes, pace=args.pace, chimes=args.chimes, nowait=args.nowait, log_dir=log_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
