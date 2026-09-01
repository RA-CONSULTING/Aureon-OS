"""
CasimirQuantifier — Self-Consistency Meter via Casimir Plates
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"Self-quantifies itself using Casimir."

Treats the vault's present state and its τ-delayed past state as two
Casimir plates. The force between the plates is a measure of "drift" —
a metric for how much the vault has changed in the intervening interval.

Low drift  → stable system (narrow plate gap, force bounded)
High drift → system undergoing transformation (wide gap, force spikes)

The quantifier wraps `aureon.utils.aureon_miner.CasimirEffectEngine`
when available, and falls back to a pure-Python surrogate otherwise.
"""

from __future__ import annotations

import hashlib
import logging
import math
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger("aureon.vault.casimir")

CASIMIR_RELEASE_HOLD = (
    "casimir_quantifier_hold:production_magic_star_release_unavailable"
)


# ─────────────────────────────────────────────────────────────────────────────
# Reading dataclass
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class CasimirReading:
    force: float
    vacuum_energy: float
    photon_density: float
    plate_separation: float
    present_fingerprint: str
    past_fingerprint: str
    drift_bits: int
    timestamp: float


# ─────────────────────────────────────────────────────────────────────────────
# CasimirQuantifier
# ─────────────────────────────────────────────────────────────────────────────


class CasimirQuantifier:
    """
    Wraps the existing CasimirEffectEngine (if importable) with two
    plates: vault_present and vault_past. Per tick:

      1. compute the vault's present fingerprint
      2. compute the vault's past (τ-seconds-ago) fingerprint
      3. compute hamming distance (drift_bits) between them
      4. emit virtual photons scaled to drift
      5. update_vacuum → read total_casimir_force

    The force is returned in the reading so the calling loop can use it
    to modulate rally mode, Auris voting, etc.
    """

    def __init__(self, tau_s: float = 30.0, *, use_native_engine: bool = False):
        if use_native_engine:
            raise RuntimeError(CASIMIR_RELEASE_HOLD)
        self.tau_s = float(tau_s)
        self._engine: Any = None
        self._engine_kind: str = "stub"
        self._last_reading: Optional[CasimirReading] = None
        if use_native_engine:
            self._load_engine()

    def _load_engine(self) -> None:
        raise RuntimeError(CASIMIR_RELEASE_HOLD)
        try:
            from aureon.utils.aureon_miner import CasimirEffectEngine
            self._engine = CasimirEffectEngine()
            # Register two plates to act as our past vs present reference
            try:
                self._engine.add_plate("vault_present", "VAULT_PRESENT", coupling=1.0)
            except Exception:
                pass
            try:
                self._engine.add_plate("vault_past", "VAULT_PAST", coupling=1.0)
            except Exception:
                pass
            self._engine_kind = "native"
            logger.info("CasimirQuantifier: wrapping native CasimirEffectEngine")
        except Exception as e:
            logger.debug("Falling back to stub Casimir engine: %s", e)
            self._engine = None
            self._engine_kind = "stub"

    # ─────────────────────────────────────────────────────────────────────
    # Measurement
    # ─────────────────────────────────────────────────────────────────────

    def measure(self, vault: Any) -> CasimirReading:
        """
        Compute the Casimir force between the vault's present and past.
        """
        raise RuntimeError(CASIMIR_RELEASE_HOLD)
        present_fp = self._vault_fingerprint(vault)
        past_fp = self._vault_fingerprint_at_tau(vault, self.tau_s)

        drift_bits = self._hamming_hex(present_fp, past_fp)

        if self._engine is not None and self._engine_kind == "native":
            reading = self._measure_native(vault, present_fp, past_fp, drift_bits)
        else:
            reading = self._measure_stub(vault, present_fp, past_fp, drift_bits)

        # Write the force back into the vault so downstream modules can read it
        try:
            vault.last_casimir_force = reading.force
        except Exception:
            pass

        self._last_reading = reading
        return reading

    # ─────────────────────────────────────────────────────────────────────
    # Native path — emit virtual photons into the real engine
    # ─────────────────────────────────────────────────────────────────────

    def _measure_native(
        self,
        vault: Any,
        present_fp: str,
        past_fp: str,
        drift_bits: int,
    ) -> CasimirReading:
        raise RuntimeError(CASIMIR_RELEASE_HOLD)
        # Emit a photon from each plate whose energy tracks the drift
        energy = float(max(1.0, min(255.0, drift_bits * 4.0)))
        nonce_present = int(present_fp[:8], 16)
        nonce_past = int(past_fp[:8], 16)
        try:
            self._engine.emit_virtual_photon("vault_present", energy, nonce_present)
            self._engine.emit_virtual_photon("vault_past", energy * 0.9, nonce_past)
            self._engine.update_vacuum()
        except Exception as e:
            logger.debug("native update_vacuum failed: %s", e)

        force = float(getattr(self._engine, "total_casimir_force", 0.0) or 0.0)
        photon_density = float(getattr(self._engine, "photon_density", 0.0) or 0.0)
        vacuum_energy = float(getattr(self._engine, "zero_point_energy", 0.0) or 0.0)

        # Normalise the raw force to a bounded [0, 10] range so downstream
        # code doesn't have to worry about extreme values
        force_norm = min(10.0, math.log1p(abs(force)) * 2.0)

        # Separation tracks drift_bits — more drift, wider gap
        separation = 1.0 + drift_bits * 0.1

        return CasimirReading(
            force=force_norm,
            vacuum_energy=vacuum_energy,
            photon_density=photon_density,
            plate_separation=separation,
            present_fingerprint=present_fp,
            past_fingerprint=past_fp,
            drift_bits=drift_bits,
            timestamp=time.time(),
        )

    # ─────────────────────────────────────────────────────────────────────
    # Stub path — pure-Python Casimir approximation
    # ─────────────────────────────────────────────────────────────────────

    def _measure_stub(
        self,
        vault: Any,
        present_fp: str,
        past_fp: str,
        drift_bits: int,
    ) -> CasimirReading:
        # F ∝ 1 / a^4  where a is the plate separation
        # Use drift_bits as a proxy for separation: low drift → narrow gap → high force
        separation = 1.0 + drift_bits * 0.1
        # Bounded force in [0, 10]
        raw = 2.5 / (separation ** 4 + 0.01)
        force = min(10.0, raw)
        vacuum_energy = force * 0.5
        photon_density = min(1.0, drift_bits / 64.0)

        return CasimirReading(
            force=force,
            vacuum_energy=vacuum_energy,
            photon_density=photon_density,
            plate_separation=separation,
            present_fingerprint=present_fp,
            past_fingerprint=past_fp,
            drift_bits=drift_bits,
            timestamp=time.time(),
        )

    # ─────────────────────────────────────────────────────────────────────
    # Fingerprints
    # ─────────────────────────────────────────────────────────────────────

    def _vault_fingerprint(self, vault: Any) -> str:
        """
        Use the vault's own fingerprint() method if present, otherwise
        compute a quick hash from its current state fields.
        """
        try:
            fp = vault.fingerprint()
            if isinstance(fp, str) and len(fp) >= 8:
                return fp[:16]
        except Exception:
            pass
        parts = [
            f"size={len(vault) if hasattr(vault, '__len__') else 0}",
            f"love={getattr(vault, 'love_amplitude', 0.0):.4f}",
            f"grat={getattr(vault, 'gratitude_score', 0.0):.4f}",
            f"lambda={getattr(vault, 'last_lambda_t', 0.0):.4f}",
            f"rally={bool(getattr(vault, 'rally_active', False))}",
        ]
        raw = "|".join(parts).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:16]

    def _vault_fingerprint_at_tau(self, vault: Any, tau_s: float) -> str:
        """
        Fingerprint of the vault's state as of tau_s ago. We approximate
        this by taking a different slice of the vault's contents (those
        with timestamp ≤ now - tau) and hashing just the size + last
        known love amplitude prior to tau ago.
        """
        try:
            past_cards = vault.snapshot_at_tau(tau_s)
            past_size = len(past_cards)
        except Exception:
            past_size = 0

        parts = [
            f"past_size={past_size}",
            f"tau={tau_s:.2f}",
            f"love={getattr(vault, 'love_amplitude', 0.0):.4f}",
            f"id={getattr(vault, 'vault_id', '')}",
        ]
        raw = "|".join(parts).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:16]

    @staticmethod
    def _hamming_hex(a: str, b: str) -> int:
        """Return hamming distance between two equal-length hex strings (in bits)."""
        if len(a) != len(b):
            return max(len(a), len(b)) * 4
        try:
            ai = int(a, 16)
            bi = int(b, 16)
            return bin(ai ^ bi).count("1")
        except ValueError:
            return sum(1 for x, y in zip(a, b) if x != y)

    # ─────────────────────────────────────────────────────────────────────
    # Status
    # ─────────────────────────────────────────────────────────────────────

    @property
    def last_reading(self) -> Optional[CasimirReading]:
        return self._last_reading

    def get_status(self) -> Dict[str, Any]:
        r = self._last_reading
        return {
            "engine_kind": self._engine_kind,
            "tau_s": self.tau_s,
            "last_force": round(r.force, 6) if r else None,
            "last_vacuum_energy": round(r.vacuum_energy, 6) if r else None,
            "last_photon_density": round(r.photon_density, 6) if r else None,
            "last_drift_bits": r.drift_bits if r else None,
        }
