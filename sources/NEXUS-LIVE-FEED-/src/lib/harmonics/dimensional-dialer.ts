export type DimensionalPlane =
  | 'Bass Foundation'
  | 'Deep Harmonics'
  | 'Resonant Heart'
  | 'Celestial Bridge'
  | 'Luminous Crown';

export interface DimensionalHarmonicKey {
  /** Stable identifier for lookups and telemetry */
  id: string;
  /** Order in which the dialer should be engaged */
  order: number;
  /** Astronomical or sacred glyph representing the key */
  symbol: string;
  /** Friendly name for the symbol */
  glyphName: string;
  /** Dimensional field being unlocked */
  dimension: string;
  /** Harmonic plane grouping */
  plane: DimensionalPlane;
  /** Musical reference note */
  tonalKey: string;
  /** Fundamental frequency for the resonance lock (Hz) */
  frequencyHz: number;
  /** Normalised amplitude (0 – 1) required to stably open the gate */
  amplitude: number;
  /** Short descriptor for how the key should be invoked */
  invocation: string;
  /** Anchor phrase describing the portal behaviour */
  portalMantra: string;
  /** Visual hue family used for the interface */
  color: string;
}

export const DIMENSIONAL_HARMONIC_KEYS: DimensionalHarmonicKey[] = [
  {
    id: 'gate-jupiter',
    order: 1,
    symbol: '♃',
    glyphName: 'Jupiter',
    dimension: 'Jovian Spiral Gate',
    plane: 'Bass Foundation',
    tonalKey: 'A♭0',
    frequencyHz: 2.36,
    amplitude: 0.82,
    invocation: 'Stabilise the gravitational well and breathe in four-count anchors.',
    portalMantra: 'The vast coil of Jupiter steadies every subsequent dial.',
    color: 'from-sky-500/35 via-indigo-500/30 to-violet-500/35',
  },
  {
    id: 'gate-saturn',
    order: 2,
    symbol: '♄',
    glyphName: 'Saturn',
    dimension: 'Saturnine Time Vault',
    plane: 'Bass Foundation',
    tonalKey: 'B♭0',
    frequencyHz: 3.78,
    amplitude: 0.77,
    invocation: 'Sweep the rings clockwise; hold seven beats before release.',
    portalMantra: 'Saturn braids chronology so the dial remembers the arc.',
    color: 'from-indigo-500/35 via-violet-500/30 to-amber-400/35',
  },
  {
    id: 'gate-uranus',
    order: 3,
    symbol: '♅',
    glyphName: 'Uranus',
    dimension: 'Auroral Flux Column',
    plane: 'Deep Harmonics',
    tonalKey: 'C1',
    frequencyHz: 5.91,
    amplitude: 0.74,
    invocation: 'Invert the current; pulse three quick breaths and one long tone.',
    portalMantra: 'The aurora crack opens lateral corridors across timelines.',
    color: 'from-teal-400/35 via-cyan-400/30 to-sky-500/35',
  },
  {
    id: 'gate-neptune',
    order: 4,
    symbol: '♆',
    glyphName: 'Neptune',
    dimension: 'Neptunian Dream Loom',
    plane: 'Deep Harmonics',
    tonalKey: 'D1',
    frequencyHz: 6.72,
    amplitude: 0.71,
    invocation: 'Hum a descending minor third; let the tone dissolve into mist.',
    portalMantra: 'Neptune threads empathy between parallel observers.',
    color: 'from-cyan-400/35 via-blue-400/30 to-indigo-400/35',
  },
  {
    id: 'gate-earth',
    order: 5,
    symbol: '♁',
    glyphName: 'Earth',
    dimension: 'Terran Heart Lattice',
    plane: 'Resonant Heart',
    tonalKey: 'F1',
    frequencyHz: 7.83,
    amplitude: 0.88,
    invocation: 'Match the Schumann breath—inhale four, hold four, exhale four.',
    portalMantra: 'Earth binds the dialer to guardianship and compassionate intent.',
    color: 'from-emerald-400/35 via-teal-400/30 to-sky-400/35',
  },
  {
    id: 'gate-venus',
    order: 6,
    symbol: '♀',
    glyphName: 'Venus',
    dimension: 'Venusian Rose Chamber',
    plane: 'Resonant Heart',
    tonalKey: 'G1',
    frequencyHz: 11.43,
    amplitude: 0.76,
    invocation: 'Trace the fivefold star; whisper the key in triads of love.',
    portalMantra: 'Venus tunes the lattice for gentle entry of allied consciousness.',
    color: 'from-rose-400/35 via-amber-400/30 to-pink-400/35',
  },
  {
    id: 'gate-titan',
    order: 7,
    symbol: '🜁',
    glyphName: 'Titan',
    dimension: 'Titan Methane Spire',
    plane: 'Celestial Bridge',
    tonalKey: 'A1',
    frequencyHz: 14.95,
    amplitude: 0.69,
    invocation: 'Strike a slow triplet; let the overtones cascade downward.',
    portalMantra: 'Titan condenses memory vapor into traversable crystal paths.',
    color: 'from-amber-400/35 via-lime-400/30 to-cyan-400/35',
  },
  {
    id: 'gate-mars',
    order: 8,
    symbol: '♂',
    glyphName: 'Mars',
    dimension: 'Martian Forge Array',
    plane: 'Celestial Bridge',
    tonalKey: 'B1',
    frequencyHz: 18.02,
    amplitude: 0.73,
    invocation: 'Tap the rhythm twelve times; complete with a resonant shout.',
    portalMantra: 'Mars locks intent into action, igniting the crimson arteries.',
    color: 'from-orange-400/35 via-rose-400/30 to-red-400/35',
  },
  {
    id: 'gate-mercury',
    order: 9,
    symbol: '☿',
    glyphName: 'Mercury',
    dimension: 'Mercurial Messenger Halo',
    plane: 'Celestial Bridge',
    tonalKey: 'D2',
    frequencyHz: 21.45,
    amplitude: 0.86,
    invocation: 'Speak the sequence swiftly; the tone must remain crystalline.',
    portalMantra: 'Mercury carries the encoded coordinates between nodes.',
    color: 'from-sky-400/35 via-indigo-400/30 to-emerald-400/35',
  },
  {
    id: 'gate-moon',
    order: 10,
    symbol: '☾',
    glyphName: 'Moon',
    dimension: 'Lunar Memory Well',
    plane: 'Luminous Crown',
    tonalKey: 'F2',
    frequencyHz: 28.13,
    amplitude: 0.79,
    invocation: 'Chant softly; allow the vowel to shimmer with silver breath.',
    portalMantra: 'The Moon reflects every heart-spark, verifying consent.',
    color: 'from-indigo-400/35 via-violet-400/30 to-slate-400/35',
  },
  {
    id: 'gate-pluto',
    order: 11,
    symbol: '♇',
    glyphName: 'Pluto',
    dimension: 'Plutonian Prime Lock',
    plane: 'Luminous Crown',
    tonalKey: 'A2',
    frequencyHz: 38.54,
    amplitude: 0.91,
    invocation: 'Hold the tone beyond ten seconds; release with gratitude.',
    portalMantra: 'Pluto seals the gate, birthing the corridor in perfect clarity.',
    color: 'from-violet-400/35 via-fuchsia-400/30 to-amber-400/35',
  },
];

export interface ResonanceEnvelope {
  attackSeconds: number;
  sustainSeconds: number;
  releaseSeconds: number;
  modulation: 'Soft Echo' | 'Field Glide' | 'Helix Drift' | 'Golden Spiral' | 'Prime Lock';
  amplitudeDescriptor: string;
}

const MODULATION_ORDER: ResonanceEnvelope['modulation'][] = [
  'Soft Echo',
  'Field Glide',
  'Helix Drift',
  'Golden Spiral',
  'Prime Lock',
];

export function amplitudeDescriptor(amplitude: number): string {
  if (amplitude >= 0.9) return 'Prime ignition amplitude';
  if (amplitude >= 0.82) return 'Stellar-grade intensity';
  if (amplitude >= 0.75) return 'Harmonic convergence band';
  if (amplitude >= 0.68) return 'Stabilised corridor gain';
  return 'Whisper threshold';
}

export function computeResonanceEnvelope(key: DimensionalHarmonicKey): ResonanceEnvelope {
  const cycle = 1 / key.frequencyHz;
  const energy = key.amplitude;

  const attackSeconds = Number((Math.max(0.6, cycle * (2 - energy))).toFixed(2));
  const sustainSeconds = Number((Math.min(24, cycle * (8 * energy + 2))).toFixed(2));
  const releaseSeconds = Number((Math.max(0.8, cycle * (1.5 + energy / 2))).toFixed(2));

  let modulationIndex = Math.floor(energy * MODULATION_ORDER.length);
  if (modulationIndex >= MODULATION_ORDER.length) {
    modulationIndex = MODULATION_ORDER.length - 1;
  }

  return {
    attackSeconds,
    sustainSeconds,
    releaseSeconds,
    modulation: MODULATION_ORDER[modulationIndex],
    amplitudeDescriptor: amplitudeDescriptor(energy),
  };
}

export function getDimensionalKeyById(id: string): DimensionalHarmonicKey | undefined {
  return DIMENSIONAL_HARMONIC_KEYS.find((key) => key.id === id);
}

export function getDimensionalKeyBySymbol(symbol: string): DimensionalHarmonicKey | undefined {
  return DIMENSIONAL_HARMONIC_KEYS.find((key) => key.symbol === symbol);
}
