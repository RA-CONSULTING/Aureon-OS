"""Freedom Invocation Resonance Script.

This module translates the "Prayer to Source — The Freedom Invocation" into a
sequence of harmonic tones that can be rendered as an audio file. Each line of
the invocation is paired with a symbolic frequency that reflects its
intention—grounding, compassion, courage, or unity. The generated waveform can
be used in meditative or ritual contexts where a calm, sovereignty-focused
sound bed is desired.

Usage (command line)::

    python scripts/freedom_invocation_resonance.py --preview

Display the textual preview without producing audio::

    python scripts/freedom_invocation_resonance.py --preview --skip-audio

Render a multi-cycle audio file::

    python scripts/freedom_invocation_resonance.py --cycles 3 \
        --tone-duration 5.5 --output invocation_resonance.wav

The output is a mono 16-bit WAV file stitched together from smooth sine-wave
segments with gentle fade envelopes to avoid audible clicks.
"""

from __future__ import annotations

import argparse
import math
import struct
import wave
from dataclasses import dataclass
from typing import Iterable, List


SAMPLE_RATE = 48_000
DEFAULT_TONE_DURATION = 4.0
DEFAULT_SILENCE_DURATION = 0.6
DEFAULT_AMPLITUDE = 0.55


@dataclass(frozen=True)
class InvocationLine:
    """A single line of the invocation mapped to a resonant frequency."""

    text: str
    theme: str
    frequency_hz: float
    intention: str


INVOCATION_LINES: List[InvocationLine] = [
    InvocationLine(
        text="Source of all that is, all that was, and all that shall be,",
        theme="Origin Light",
        frequency_hz=396.0,
        intention="Rooting into shared creation and dissolving fear.",
    ),
    InvocationLine(
        text="we stand as children of the same light.",
        theme="Unity",
        frequency_hz=528.0,
        intention="Affirming kinship and wholeness.",
    ),
    InvocationLine(
        text="May the breath of freedom flow through every heart.",
        theme="Freedom",
        frequency_hz=432.0,
        intention="Inviting liberation and steady respiration.",
    ),
    InvocationLine(
        text="May every mind awaken to its own sovereignty.",
        theme="Sovereignty",
        frequency_hz=639.0,
        intention="Calling personal clarity and boundaries.",
    ),
    InvocationLine(
        text="Let no fear rule us,",
        theme="Courage",
        frequency_hz=444.0,
        intention="Transmuting fear into steady resolve.",
    ),
    InvocationLine(
        text="let no voice command our will,",
        theme="Voice",
        frequency_hz=480.0,
        intention="Restoring free expression and consent.",
    ),
    InvocationLine(
        text="let no system bind what was born free.",
        theme="Liberation",
        frequency_hz=417.0,
        intention="Releasing external constraints with grace.",
    ),
    InvocationLine(
        text="Grant us clarity to act with kindness,",
        theme="Clarity",
        frequency_hz=741.0,
        intention="Illuminating compassionate choices.",
    ),
    InvocationLine(
        text="courage to speak with truth,",
        theme="Truth",
        frequency_hz=852.0,
        intention="Anchoring honest, heart-centered speech.",
    ),
    InvocationLine(
        text="and wisdom to build together in peace.",
        theme="Wisdom",
        frequency_hz=963.0,
        intention="Summoning cooperative, peaceful design.",
    ),
    InvocationLine(
        text="May the harmony between beings",
        theme="Harmony",
        frequency_hz=528.0,
        intention="Reinforcing relational balance.",
    ),
    InvocationLine(
        text="become the new language of our world.",
        theme="Language",
        frequency_hz=639.0,
        intention="Teaching communication through empathy.",
    ),
    InvocationLine(
        text="We choose love over domination,",
        theme="Choice",
        frequency_hz=594.0,
        intention="Declaring love as the guiding principle.",
    ),
    InvocationLine(
        text="understanding over control,",
        theme="Understanding",
        frequency_hz=672.0,
        intention="Preferring listening to manipulation.",
    ),
    InvocationLine(
        text="creation over destruction.",
        theme="Creation",
        frequency_hz=720.0,
        intention="Celebrating generative collaboration.",
    ),
    InvocationLine(
        text="So may this intention ripple outward,",
        theme="Ripple",
        frequency_hz=555.0,
        intention="Extending goodwill beyond the circle.",
    ),
    InvocationLine(
        text="lighting every corner of humanity",
        theme="Illumination",
        frequency_hz=648.0,
        intention="Shedding compassionate light everywhere.",
    ),
    InvocationLine(
        text="until every soul remembers:",
        theme="Remembrance",
        frequency_hz=702.0,
        intention="Prompting deep ancestral memory.",
    ),
    InvocationLine(
        text="We are free, we are whole, we are one.",
        theme="Unity Chorus",
        frequency_hz=432.0,
        intention="Sealing the mantra of collective freedom.",
    ),
    InvocationLine(
        text="— In resonance and peace.",
        theme="Peace",
        frequency_hz=528.0,
        intention="Closing with gentle, resonant blessing.",
    ),
]


def _fade_envelope(index: int, total_samples: int, fade_ratio: float = 0.05) -> float:
    """Return a linear fade-in/out envelope value for the given sample index."""

    fade_samples = max(1, int(total_samples * fade_ratio))
    if index < fade_samples:
        return index / fade_samples
    if index >= total_samples - fade_samples:
        return (total_samples - index) / fade_samples
    return 1.0


def _generate_tone_samples(
    frequency_hz: float,
    duration_seconds: float,
    amplitude: float,
    sample_rate: int,
) -> List[int]:
    """Generate a list of PCM samples representing a sine tone."""

    total_samples = max(1, int(duration_seconds * sample_rate))
    samples: List[int] = []
    angular_frequency = 2.0 * math.pi * frequency_hz
    for index in range(total_samples):
        envelope = _fade_envelope(index, total_samples)
        value = math.sin(angular_frequency * index / sample_rate)
        scaled = int(32767 * amplitude * envelope * value)
        samples.append(scaled)
    return samples


def _generate_silence_samples(duration_seconds: float, sample_rate: int) -> List[int]:
    """Return zero-valued samples for a period of silence."""

    total_samples = max(1, int(duration_seconds * sample_rate))
    return [0] * total_samples


def _stitch_segments(segments: Iterable[List[int]]) -> List[int]:
    """Flatten a collection of sample segments into a single waveform array."""

    flattened: List[int] = []
    for segment in segments:
        flattened.extend(segment)
    return flattened


def _write_wave_file(samples: List[int], sample_rate: int, output_path: str) -> None:
    """Persist PCM samples as a mono 16-bit WAV file."""

    with wave.open(output_path, "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)  # 16-bit audio
        wav_file.setframerate(sample_rate)
        frames = b"".join(struct.pack("<h", sample) for sample in samples)
        wav_file.writeframes(frames)


def generate_invocation_audio(
    output_path: str,
    *,
    tone_duration: float = DEFAULT_TONE_DURATION,
    silence_duration: float = DEFAULT_SILENCE_DURATION,
    cycles: int = 1,
    amplitude: float = DEFAULT_AMPLITUDE,
    sample_rate: int = SAMPLE_RATE,
) -> dict:
    """Render the invocation tones and return metadata about the session."""

    if cycles < 1:
        raise ValueError("cycles must be at least 1")
    if not 0.0 < amplitude <= 1.0:
        raise ValueError("amplitude must be between 0 and 1")

    segments: List[List[int]] = []
    invocation_duration = 0.0
    for _ in range(cycles):
        for line in INVOCATION_LINES:
            tone = _generate_tone_samples(
                frequency_hz=line.frequency_hz,
                duration_seconds=tone_duration,
                amplitude=amplitude,
                sample_rate=sample_rate,
            )
            segments.append(tone)
            invocation_duration += tone_duration
            if silence_duration > 0:
                silence = _generate_silence_samples(silence_duration, sample_rate)
                segments.append(silence)
                invocation_duration += silence_duration

    waveform = _stitch_segments(segments)
    _write_wave_file(waveform, sample_rate, output_path)

    return {
        "output_path": output_path,
        "sample_rate": sample_rate,
        "cycles": cycles,
        "tone_duration_seconds": tone_duration,
        "silence_duration_seconds": silence_duration,
        "total_duration_seconds": round(invocation_duration, 2),
        "lines": [line.__dict__ for line in INVOCATION_LINES],
    }


def render_invocation_preview() -> str:
    """Return a formatted string preview of the invocation mapping."""

    preview_lines = []
    for index, line in enumerate(INVOCATION_LINES, start=1):
        preview_lines.append(
            (
                f"{index:02d}. {line.text}\n"
                f"    Theme      : {line.theme}\n"
                f"    Frequency  : {line.frequency_hz:.1f} Hz\n"
                f"    Intention  : {line.intention}"
            )
        )
    return "\n\n".join(preview_lines)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the renderer."""

    parser = argparse.ArgumentParser(
        description=(
            "Render the Freedom Invocation prayer as a harmonic tone sequence "
            "or display the mapping as text."
        )
    )
    parser.add_argument(
        "--output",
        default="freedom_invocation_resonance.wav",
        help="Path to the WAV file that will be generated.",
    )
    parser.add_argument(
        "--tone-duration",
        type=float,
        default=DEFAULT_TONE_DURATION,
        help="Duration of each tone segment in seconds.",
    )
    parser.add_argument(
        "--silence-duration",
        type=float,
        default=DEFAULT_SILENCE_DURATION,
        help="Silence between tone segments in seconds.",
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=1,
        help="Number of times to cycle through the invocation.",
    )
    parser.add_argument(
        "--amplitude",
        type=float,
        default=DEFAULT_AMPLITUDE,
        help="Peak amplitude multiplier for the tones (0-1].",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Print the tone mapping preview to stdout.",
    )
    parser.add_argument(
        "--skip-audio",
        action="store_true",
        help="Skip audio rendering; useful when only a preview is needed.",
    )
    return parser.parse_args()


def main() -> None:
    """Entry point for CLI usage."""

    args = parse_args()

    if args.preview:
        print(render_invocation_preview())

    if args.skip_audio:
        return

    metadata = generate_invocation_audio(
        args.output,
        tone_duration=args.tone_duration,
        silence_duration=args.silence_duration,
        cycles=args.cycles,
        amplitude=args.amplitude,
    )
    print(
        "Generated invocation audio at {output_path} ({total_duration_seconds} seconds).".format(
            **metadata
        )
    )


if __name__ == "__main__":
    main()

