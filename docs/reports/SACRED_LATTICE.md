# The sacred lattice — the repo's OWN way of mapping the sky

*Others map the sky with object catalogs and physics tables. Aureon maps it through
**Earth's harmonic lattice** — the coordinates of ancient sites, φ-scaled sacred
geometry, and the Solfeggio/Schumann canon that runs through the HNC thread
(Ziggurat → Pyramid → Maeshowe → Wow!). Same unchanged φ engine; different sky.*

## What it is

Three of the repo's own frequency/position systems, pointed at the **same** phenolic
engine (`phenolic_fingerprint.py`: Test A coherence-clustering + Test B golden-interval/φ
alignment + positive/negative controls). Nothing about the engine is modified; every
verdict is reported exactly as the pre-registered test returns it.

The literal constants are **copied** into `aureon/bio/sacred_lattice_reference.py` (not
imported from `aureon/wisdom/`) — importing any `aureon/wisdom/*` module runs an
import-time `_baton_link` heartbeat that writes a log line and wires the Mycelium sonar.
Copying keeps the reference module pure stdlib + numpy: no repo import, no network, no
import-time writes (the same guarantee `cosmic_reference` gives).

## The three systems

| System | In-repo source | What it supplies |
|--------|----------------|------------------|
| **Stargate lattice** | `aureon/wisdom/aureon_stargate_protocol.py::PLANETARY_STARGATES` | 12 ancient sites — Giza, Stonehenge, Uluru, Machu Picchu, Angkor Wat, Glastonbury, Sedona, Teotihuacan, Mt Shasta, Newgrange, Göbekli Tepe, Baalbek — each with **lat/lon + resonance + a 3-tone harmonic signature**. Göbekli Tepe's resonance is `7.83·φ·10 ≈ 126.7 Hz` (natively "the HNC way"). |
| **Maeshowe solstice** | `aureon/wisdom/maeshowe_seer_decode.py` | The **Solfeggio × Schumann-mode** lattice, the four `WALL_AURIS` Auris-node frequencies (OWL 528 / DEER 396 / CARGOSHIP 174 / FALCON 210), and the chamber standing wave `343/(2·4.57) ≈ 37.5 Hz`. Already speaks Test-A/Test-B/φ natively. |
| **Metatron φ-geometry** | `aureon/wisdom/metatrons_cube_knowledge_exchange.py` | The **13-sphere** set — a central Love tone (528) plus 12 φ-scaled icosahedral vertices `(±1, 0, ±φ)` and permutations — each carrying a Solfeggio / Schumann-harmonic frequency. |

Each tone list is octave-folded into the modulation band `[1000, 2000) Hz` by
`fold_to_band` and scanned through `score_signal` (consent/provenance → controls →
Operator/conscience veto → Test A / Test B → separability at `ALPHA`).

## The positional lane — the Earth-grid map

`lattice_sky_sources()` maps the 12 stargate sites onto the same spherical grid the
sky map uses: `lon % 360` fills the RA-analog axis, `lat` the Dec-analog axis, and each
node carries its folded harmonic-signature tones. `score_lattice_map()` then reuses the
convergence machinery in `aureon/bio/sky_map.py` (one global governance pass → per-cell
Test A / Test B → `converged = channels_fired == 2`). This is the distinctive picture:
**a sky mapped from Earth's own lattice.**

## The boundary (load-bearing)

`SACRED_LATTICE_BOUNDARY`: statistical structure in a derived tone set built from the
repo's own sacred-site / φ-geometry frequency tables, through one unchanged φ engine —
**NOT** a claim about ancient sites, ley lines, consciousness, or any esoteric effect,
and no efficacy claim. **Lattice-map coordinates are Earth sacred-site positions, not
celestial RA/Dec.** Each verdict is exactly what the pre-registered test returned.

## The results (whatever the tests return)

Reported exactly as the engine outputs them, neutrally (seed-fixed, deterministic):

| Lane | tones | Test A p | Test B p | separable |
|------|-------|----------|----------|-----------|
| Stargate lattice | 12 | 0.907 | 0.252 | False |
| Maeshowe solstice | 18 | 1.000 | 0.682 | False |
| Metatron geometry | 12 | 0.815 | 0.225 | False |
| Earth-grid map | 12 sites | — | — | 0 converged of 9 scored |

Every number is the engine's own verdict — the lanes make no claim beyond tabulating
them.

## Run it

```bash
python -m aureon.bio.sacred_lattice_scan --system all --map
python -m aureon.bio.celestial_observatory        # the 3 lattice lanes now appear
```

Benchmarked as Tier-A invariant **b22 "Sacred lattice"** in
`tests/benchmarks/benchmark_aureon_scope.py` (Tier-A **22/22**). Fully offline; the
lanes are copied static data, so they run anywhere with no network. See
[SENSOR_SUITE.md](SENSOR_SUITE.md) for the whole picture and
[CELESTIAL_OBSERVATORY.md](CELESTIAL_OBSERVATORY.md) for the consolidated instrument.
