"""The Auris panel — nine nodes, wired into a decision.

``aureon/vault/auris_metacognition.py`` holds a complete nine-node deliberative
voter: Tiger, Falcon, Hummingbird, Dolphin, Deer, Owl, Panda, CargoShip,
Clownfish, each a deterministic reading of a different slice of the organism,
tallied into a consensus with a Lighthouse clearance at 0.945. No LLM, no
network — pure logic.

``vote()`` already has callers (``vault.self_feedback_loop``,
``harmonic.auris_voice_filter``, ``queen.hnc_human_loop``), but none of them
reach the action gate, which reads only TWO scalars from the planetary throne
(cosmic_score, gate_open). What was missing was a path from the nine nodes into
a decision, not the voter itself.

The unlock is that ``vote()`` is duck-typed: every node reads its slice through
``getattr(vault, ...)``. This module builds that view from the live organism —
the HNC field, the blended subfields, the throne — so the panel can speak into
a decision.

**Absence is the hard part, and it is not free.** Four nodes use the idiom
``float(getattr(vault, name, DEFAULT) or DEFAULT)``, which cannot tell an
unmeasured slice from a measured zero: leave ``dominant_frequency_hz`` at 0.0
and Hummingbird reads 528.0 Hz and votes BUY at 0.85 — *"on the love tone"* —
on nothing at all. Clownfish does the same with ``""`` → ``"love"``. An entirely
blind vault still returns consensus NEUTRAL at confidence 0.7, seven of nine
agreeing.

Those nodes cannot be changed from here — they have live callers elsewhere — so
this module reports the fabrication instead of hiding it. ``build_vault``
records which slices came from a real measurement, and :class:`PanelReading`
publishes both the ratio (:attr:`~PanelReading.evidence_ratio`) and the names of
the nodes that voted on a constant (:attr:`~PanelReading.ungrounded_nodes`). A
consensus reached on defaults is visible as such rather than passing as
agreement.

Two nodes are permanently ungrounded, and saying so is the point: Tiger wants a
Casimir drift force and Panda wants a vault capacity, and the organism measures
neither. They are absent from :data:`PANEL_SLICES` rather than fed a stand-in.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any

LOG = logging.getLogger("aureon.gates.panel")

# The vault slices this module can actually fill from a real reading. This is
# the denominator of ``evidence_ratio``, and it is deliberately the count of
# what is *attempted*, not the count of the vault's attributes: a denominator
# larger than the number of things that can ever be grounded would cap the ratio
# below 1.0 forever and silently discount every downstream confidence.
PANEL_SLICES: tuple[str, ...] = (
    "last_lambda_t",          # Falcon      <- field.lambda_t
    "love_amplitude",         # Dolphin     <- field.coherence_gamma
    "gratitude_score",        # Deer        <- field.symbolic_life_score
    "cortex_snapshot",        # CargoShip   <- blended subfields
    "cortex_bands",           # Owl         <- subfields keyed by an EEG band
    "dominant_frequency_hz",  # Hummingbird <- throne.schumann_hz
    "dominant_chakra",        # Clownfish   <- throne.consciousness_level
)
PANEL_INPUTS = len(PANEL_SLICES)

# Which slice each node needs before its vote means anything. Tiger and Panda
# name slices that are in no roster because nothing in the organism measures
# them; they are listed so their permanent abstention is explicit.
NODE_SLICE: dict[str, str] = {
    "Tiger": "last_casimir_force",
    "Falcon": "last_lambda_t",
    "Hummingbird": "dominant_frequency_hz",
    "Dolphin": "love_amplitude",
    "Deer": "gratitude_score",
    "Owl": "cortex_bands",
    "Panda": "vault_capacity",
    "CargoShip": "cortex_snapshot",
    "Clownfish": "dominant_chakra",
}

# Divisor applied to Λ(t) before tanh. Chosen so a Λ of ~2 (the bounded regime
# the damped echo settles into, (S+O)/(1-β) with β=0.85) maps to roughly 0.76 —
# comfortably past Falcon's ±0.5 "strong" threshold without pinning tanh at
# ±1.0, which would re-create the saturation in a new place.
LAMBDA_SCALE = 2.0

# The band names ``AurisMetacognition._owl`` actually branches on. A cortex
# snapshot keyed by anything else (subfield source names, say) leaves Owl unable
# to recognise a band, so it is not counted as grounding Owl.
OWL_BANDS = frozenset({"gamma", "alpha", "delta"})


@dataclass
class FieldVault:
    """The eight-attribute view ``AurisMetacognition.vote()`` duck-types against.

    Field names are dictated by the nine node methods; do not rename them.
    """

    last_casimir_force: float = 0.0      # Tiger — volatility (never grounded)
    last_lambda_t: float = 0.0           # Falcon — momentum / Λ(t)
    dominant_frequency_hz: float = 0.0   # Hummingbird — stability
    love_amplitude: float = 0.0          # Dolphin + the Lighthouse product
    gratitude_score: float = 0.0         # Deer — sensing
    cortex_snapshot: dict[str, float] | None = None  # Owl + CargoShip
    dominant_chakra: str = ""            # Clownfish — symbiosis
    max_size: int = 1                    # Panda — capacity (with __len__)
    _size: int = 0
    # Which of PANEL_SLICES this vault actually filled from a measurement.
    # Not read by any node — it is bookkeeping for PanelReading.
    grounded_slices: frozenset[str] = field(default_factory=frozenset)

    def __len__(self) -> int:  # Panda reads len(vault) against max_size
        return self._size


@dataclass
class PanelReading:
    """What the nine nodes concluded, and how much of it was grounded.

    ``lighthouse_cleared`` is reported, never acted on, and is close to
    unreachable by construction: ``AurisMetacognition`` clears it when
    ``confidence × love_amplitude > 0.945``, and confidence is quantised to
    0.3 / 0.7 / 0.95. Clearance therefore needs eight of nine nodes agreeing
    *and* ``love_amplitude`` — here the field's Γ — above 0.99474. Γ is a mean
    coherence, so in practice that does not happen. It is surfaced as a reading,
    not used as a gate; see ``switchboard.GateReading.lighthouse``.
    """

    available: bool
    consensus: str | None = None
    confidence: float | None = None
    agreeing: int = 0
    total: int = 9
    lighthouse_cleared: bool = False
    grounded_inputs: int = 0
    total_inputs: int = PANEL_INPUTS
    ungrounded_nodes: tuple[str, ...] = ()
    blocker: str | None = None

    @property
    def evidence_ratio(self) -> float:
        """Share of the panel's inputs that came from a real measurement."""
        return self.grounded_inputs / self.total_inputs if self.total_inputs else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "consensus": self.consensus,
            "confidence": round(self.confidence, 4) if self.confidence is not None else None,
            "agreeing": self.agreeing,
            "total": self.total,
            "lighthouse_cleared": self.lighthouse_cleared,
            "grounded_inputs": self.grounded_inputs,
            "total_inputs": self.total_inputs,
            "evidence_ratio": round(self.evidence_ratio, 4),
            "ungrounded_nodes": list(self.ungrounded_nodes),
            "blocker": self.blocker,
        }


def build_vault(bus: Any = None) -> tuple[FieldVault, int]:
    """Assemble the vault view from the live organism.

    Returns the vault and the count of :data:`PANEL_SLICES` that came from a
    real reading, so callers can tell a grounded consensus from one reached on
    defaults. ``vault.grounded_slices`` names them.

    Two mappings that used to be here are deliberately gone:

    ``last_casimir_force = divergence × 10``
        Tiger branches at 3.0 (BUY, "act") and 6.0 (RALLY). Divergence is the
        max-min spread of the subfield life scores, so it lives in [0, 1] and
        the ×10 put the switchboard's own caution threshold — 0.35, the point
        at which ``evaluate`` forces a REDO because the body disagrees with
        itself — squarely inside Tiger's "act" band, and 0.6 into "rally". The
        organism's disagreement was being read as a reason to act harder,
        through an uncalibrated constant, while the same number was correctly
        being read as a reason to stop three lines away. Divergence keeps its
        real consumer in ``switchboard.evaluate``; it is not laundered into a
        Casimir force nothing measures.

    ``max_size = len(cortex_snapshot)``
        With ``_size`` set to the same length, Panda's fill ratio was exactly
        100% whenever any subfield existed and 0% otherwise — a constant
        wearing the costume of a measurement, and one that reported
        "vault 100% full" and voted STABILISE. There is no capacity reading in
        the organism, so Panda gets none.
    """
    field_level: str | None = None
    vault = FieldVault(cortex_snapshot={})
    grounded: set[str] = set()

    try:
        from aureon.core.hnc_field import blend_field, read_canonical_field

        canonical = read_canonical_field(bus)
        # getattr, not attribute access: every stand-in for the field in this
        # repo is duck-typed, and a fake without this attribute raised
        # AttributeError inside this guarded block — silently aborting the
        # whole field read and emptying cortex_snapshot with it. The second
        # time one line of mine broke a slice it never touched.
        if canonical.available and getattr(canonical, "consciousness_level", None):
            # Held for the throne block below, which runs in its own try and
            # cannot see `canonical`. Referencing it there raised NameError,
            # and because that block is guarded the failure was SILENT: it took
            # dominant_frequency_hz down with it and dropped the panel from 6/7
            # grounded slices to 5/7 while reporting no error at all.
            field_level = str(getattr(canonical, "consciousness_level", "") or "")
        if canonical.available:
            if canonical.lambda_t is not None:
                # Squashed, not raw. Falcon branches at ±0.5 and ±0.1, which
                # only carries information while Λ lives near that scale. It
                # does not: the echo recursion integrates, and a live run took
                # Λ from 4.9 to 1960 over two days, so Falcon returned BUY at
                # 0.8 from the first minute onward and never moved again. A
                # node pinned to one answer is worse than an absent one — it
                # is counted as grounded and it is reading a real number, so
                # nothing marks it as uninformative.
                #
                # tanh maps the whole real line onto (-1, 1) while preserving
                # sign and staying monotonic, so the node's own thresholds
                # regain their meaning without touching the vote logic (which
                # has other callers). The scale divisor keeps ordinary Λ
                # excursions inside the band rather than saturating tanh in
                # turn — this transforms the reading, it does not clip it.
                vault.last_lambda_t = math.tanh(float(canonical.lambda_t) / LAMBDA_SCALE)
                grounded.add("last_lambda_t")
            if canonical.coherence_gamma is not None:
                # Dolphin reads love as amplitude; Γ is the organism's coherence.
                vault.love_amplitude = float(canonical.coherence_gamma)
                grounded.add("love_amplitude")
            if canonical.symbolic_life_score is not None:
                vault.gratitude_score = float(canonical.symbolic_life_score)
                grounded.add("gratitude_score")

        blended = blend_field(bus)
        if blended.available:
            # CargoShip reads the mean of the cortex map; each subfield is a
            # real organ, so the mean is a real macro-Γ.
            snapshot = {}
            for source, sub in (_read_subfields(bus) or {}).items():
                score = sub.get("symbolic_life_score") if isinstance(sub, dict) else None
                if score is not None:
                    snapshot[str(source)] = float(score)
            if snapshot:
                vault.cortex_snapshot = snapshot
                grounded.add("cortex_snapshot")
                # Owl branches on band identity — gamma / alpha / delta — and a
                # snapshot keyed by subfield source names ("grants", "market")
                # can never match one, so Owl abstains at NEUTRAL whatever the
                # amplitudes are. Only count it grounded when a band is present.
                if any(k.lower() in OWL_BANDS for k in snapshot):
                    grounded.add("cortex_bands")
    except Exception:  # noqa: BLE001 — a missing field is a value, never a crash
        LOG.debug("field read for panel skipped", exc_info=True)

    try:
        from aureon.intelligence.dr_auris_throne import get_dr_auris_throne

        state = get_dr_auris_throne().get_state()
        hz = getattr(state, "schumann_hz", None)
        if hz:
            vault.dominant_frequency_hz = float(hz)
            grounded.add("dominant_frequency_hz")
        # Consciousness level: the FIELD is authoritative, not the throne.
        #
        # DrAurisThrone is autostarted by organism_daemon, so when only the HNC
        # daemon is running its singleton returns a default CosmicState whose
        # consciousness_level is "DORMANT". Clownfish was voting on that word
        # while the live trace said FLOWING — a stale constant beating a real
        # measurement, which is the precise failure this panel exists to avoid.
        # The canonical field carries the level the Master Formula actually
        # computed, so prefer it and fall back to the throne.
        level = field_level or getattr(state, "consciousness_level", None)
        if level:
            vault.dominant_chakra = str(level)
            grounded.add("dominant_chakra")
    except Exception:  # noqa: BLE001
        LOG.debug("throne read for panel skipped", exc_info=True)

    vault.grounded_slices = frozenset(grounded)
    return vault, len(vault.grounded_slices)


def ungrounded_nodes(grounded_slices: frozenset[str]) -> tuple[str, ...]:
    """Nodes whose slice was never measured, so their vote is a constant.

    Tiger and Panda are always here: nothing in the organism measures a Casimir
    drift force or a vault capacity.
    """
    return tuple(node for node, slice_name in NODE_SLICE.items()
                 if slice_name not in grounded_slices)


def _read_subfields(bus: Any) -> dict[str, Any] | None:
    try:
        from aureon.core.hnc_field import read_subfields

        return read_subfields(bus)
    except Exception:  # noqa: BLE001
        return None


def auris_panel(bus: Any = None) -> PanelReading:
    """Convene the nine nodes over the live organism. Never raises."""
    try:
        from aureon.vault.auris_metacognition import AurisMetacognition
    except Exception as exc:  # noqa: BLE001
        return PanelReading(available=False, blocker=f"panel unavailable: {type(exc).__name__}")

    vault, grounded = build_vault(bus)
    try:
        result = AurisMetacognition().vote(vault)
    except Exception as exc:  # noqa: BLE001
        return PanelReading(available=False, blocker=f"vote failed: {type(exc).__name__}")

    return PanelReading(
        available=True,
        consensus=getattr(result, "consensus", None),
        confidence=float(getattr(result, "confidence", 0.0) or 0.0),
        agreeing=int(getattr(result, "agreeing", 0) or 0),
        total=int(getattr(result, "total", 9) or 9),
        lighthouse_cleared=bool(getattr(result, "lighthouse_cleared", False)),
        grounded_inputs=grounded,
        ungrounded_nodes=ungrounded_nodes(vault.grounded_slices),
    )


__all__ = ["NODE_SLICE", "OWL_BANDS", "PANEL_INPUTS", "PANEL_SLICES",
           "FieldVault", "PanelReading", "auris_panel", "build_vault",
           "ungrounded_nodes"]
