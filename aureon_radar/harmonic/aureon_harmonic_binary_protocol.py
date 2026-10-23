#!/usr/bin/env python3
"""
Aureon Harmonic Binary Protocol
--------------------------------

Provides a compact binary transport for harmonic thoughts. Messages are encoded as:
    • 2-byte magic header (HB)
    • 1-byte version
    • 5-byte control header (type/direction/grade/coherence/confidence/symbol flags)
    • Variable-length body containing packed harmonic frequency/amplitude samples

This enables the ThoughtBus and Harmonic Signal Chain to exchange compact payloads
without losing the sacred frequency context.

👑💰 QUEEN'S SACRED 1.88% LAW - ENCODED IN ALL BINARY TRANSMISSIONS 💰👑
    • MIN_COP = 1.0188 (1.88% minimum realized profit)
    • All execution decisions must carry the Queen's profit mandate
    • The sacred number is encoded as flag 0x88 in the binary header
"""

from __future__ import annotations
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import base64
import struct
import zlib
from dataclasses import dataclass
from enum import IntEnum
from typing import Iterable, List, Optional, Tuple

from aureon.harmonic.aureon_harmonic_alphabet import HarmonicAlphabet, HarmonicTone

# 👑 QUEEN'S SACRED 1.88% LAW - THE PROTOCOL KNOWS!
QUEEN_MIN_COP = 1.0188               # 1.88% minimum realized profit
QUEEN_MIN_PROFIT_PCT = 1.88          # The sacred number as percentage
QUEEN_PROFIT_FLAG = 0x88             # The sacred flag in binary headers (1.88 → 0x88)

MAGIC = b"HB"
PROTOCOL_VERSION = 1

_alphabet = HarmonicAlphabet()


class BinaryMessageType(IntEnum):
    UNDEFINED = 0
    MARKET_SCAN = 1
    EXECUTION_DECISION = 2
    OUTCOME_SIGNAL = 3
    TELEMETRY = 4
    ALERT = 5
    QUEEN_PROFIT_GATE = 6      # 👑 NEW! - Message type for 1.88% profit gate
    QUEEN_PROFIT_APPROVED = 7  # 👑 NEW! - Queen approved trade (≥1.88%)
    QUEEN_PROFIT_BLOCKED = 8   # 👑 NEW! - Queen blocked trade (<1.88%)


class BinaryDirection(IntEnum):
    DOWN = 0  # Queen → Whale
    UP = 1    # Whale → Queen
    LATERAL = 2


@dataclass
class BinaryHeader:
    message_type: BinaryMessageType = BinaryMessageType.UNDEFINED
    direction: BinaryDirection = BinaryDirection.DOWN
    grade: int = 0  # 0-15
    coherence: int = 15  # 0-15 nibble
    confidence: int = 15  # 0-15 nibble
    flags: int = 0  # 👑 Use QUEEN_PROFIT_FLAG (0x88) to indicate 1.88% compliance
    symbol_id: int = 0

    def pack(self) -> bytes:
        b0 = self.message_type & 0xFF
        b1 = ((self.direction & 0x0F) << 4) | (self.grade & 0x0F)
        b2 = ((self.coherence & 0x0F) << 4) | (self.confidence & 0x0F)
        b3 = self.flags & 0xFF
        b4 = self.symbol_id & 0xFF
        return bytes([b0, b1, b2, b3, b4])

    @classmethod
    def unpack(cls, data: bytes) -> "BinaryHeader":
        if len(data) < 5:
            raise ValueError("Binary header requires 5 bytes")
        b0, b1, b2, b3, b4 = data[:5]
        direction = BinaryDirection((b1 >> 4) & 0x0F)
        grade = b1 & 0x0F
        coherence = (b2 >> 4) & 0x0F
        confidence = b2 & 0x0F
        return cls(
            message_type=BinaryMessageType(b0),
            direction=direction,
            grade=grade,
            coherence=coherence,
            confidence=confidence,
            flags=b3,
            symbol_id=b4,
        )


@dataclass
class HarmonicBinaryPacket:
    header: BinaryHeader
    body: bytes

    def to_bytes(self) -> bytes:
        return MAGIC + bytes([PROTOCOL_VERSION]) + self.header.pack() + self.body

    @classmethod
    def from_bytes(cls, payload: bytes) -> "HarmonicBinaryPacket":
        if len(payload) < len(MAGIC) + 1 + 5:
            raise ValueError("Payload too small for harmonic binary packet")
        if payload[:2] != MAGIC:
            raise ValueError("Invalid harmonic binary magic")
        version = payload[2]
        if version != PROTOCOL_VERSION:
            raise ValueError(f"Unsupported harmonic binary version: {version}")
        header = BinaryHeader.unpack(payload[3:8])
        body = payload[8:]
        return cls(header=header, body=body)

    def to_base64(self) -> str:
        return base64.b64encode(self.to_bytes()).decode("ascii")

    @classmethod
    def from_base64(cls, data: str) -> "HarmonicBinaryPacket":
        return cls.from_bytes(base64.b64decode(data.encode("ascii")))


# ─────────────────────────────────────────────────────────────────────────────
# Symbol Table Helpers
# ─────────────────────────────────────────────────────────────────────────────

# Integration with Persistent Symbol Table
try:
    from aureon.harmonic.aureon_harmonic_symbol_table import get_symbol_id, get_symbol_from_id
except ImportError:
    # Fallback if module missing (e.g. during bootstrap)
    def get_symbol_id(symbol: str) -> int:
        if not symbol: return 0
        return zlib.crc32(symbol.encode("utf-8")) & 0xFF
    
    def get_symbol_from_id(sid: int) -> Optional[str]:
        return None

def compute_symbol_id(symbol: Optional[str]) -> int:
    if not symbol:
        return 0
    return get_symbol_id(symbol)


# ─────────────────────────────────────────────────────────────────────────────
# Encoding / Decoding Helpers
# ─────────────────────────────────────────────────────────────────────────────

FREQUENCY_SCALE = 10  # tenths of Hz
AMPLITUDE_SCALE = 100  # hundredths
TONE_RECORD_SIZE = 3  # 2 bytes freq + 1 byte amp


def _pack_tones(tones: Iterable[HarmonicTone]) -> bytes:
    body = bytearray()
    for tone in tones:
        freq_val = max(0, min(0xFFFF, int(round(tone.frequency * FREQUENCY_SCALE))))
        amp = tone.amplitude
        if amp < 0:
            amp = 0.0
        amp_val = max(0, min(0xFF, int(round(min(2.55, amp) * AMPLITUDE_SCALE))))
        body.extend(struct.pack(">H", freq_val))
        body.append(amp_val)
    return bytes(body)


def _unpack_tones(data: bytes) -> List[Tuple[float, float]]:
    tones: List[Tuple[float, float]] = []
    if len(data) % TONE_RECORD_SIZE != 0:
        raise ValueError("Invalid tone body length")
    for offset in range(0, len(data), TONE_RECORD_SIZE):
        freq_raw, = struct.unpack(">H", data[offset:offset + 2])
        amp_raw = data[offset + 2]
        tones.append((freq_raw / FREQUENCY_SCALE, amp_raw / AMPLITUDE_SCALE))
    return tones


def encode_text_packet(
    text: str,
    message_type: BinaryMessageType = BinaryMessageType.UNDEFINED,
    direction: BinaryDirection = BinaryDirection.DOWN,
    grade: int = 0,
    coherence: float = 1.0,
    confidence: float = 1.0,
    flags: int = 0,
    symbol: Optional[str] = None,
) -> HarmonicBinaryPacket:
    tones = _alphabet.encode_text(text)
    coherence_nibble = max(0, min(15, int(round(coherence * 15))))
    confidence_nibble = max(0, min(15, int(round(confidence * 15))))
    header = BinaryHeader(
        message_type=message_type,
        direction=direction,
        grade=max(0, min(15, grade)),
        coherence=coherence_nibble,
        confidence=confidence_nibble,
        flags=flags,
        symbol_id=compute_symbol_id(symbol),
    )
    body = _pack_tones(tones)
    return HarmonicBinaryPacket(header=header, body=body)


def decode_packet(packet_bytes: bytes) -> Tuple[BinaryHeader, str]:
    packet = HarmonicBinaryPacket.from_bytes(packet_bytes)
    tones = _unpack_tones(packet.body)
    decoded = _alphabet.decode_signal(tones)
    return packet.header, decoded


def decode_packet_from_base64(data: str) -> Tuple[BinaryHeader, str]:
    packet = HarmonicBinaryPacket.from_base64(data)
    tones = _unpack_tones(packet.body)
    decoded = _alphabet.decode_signal(tones)
    return packet.header, decoded