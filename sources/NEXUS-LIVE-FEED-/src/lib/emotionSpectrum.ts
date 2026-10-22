export interface EmotionZone {
  id: string
  label: string
  element: string
  color: string
  frequencies: number[]
  anchor: number
  range: [number, number]
  frequencyLabel: string
  rangeLabel: string
}

const clamp = (value: number, min: number, max: number) =>
  Math.min(max, Math.max(min, value))

export const EMOTION_SPECTRUM_MIN = 100
export const EMOTION_SPECTRUM_MAX = 1150

const EMOTION_ZONE_DEFINITIONS: Array<{
  id: string
  label: string
  element: string
  color: string
  frequencies: number[]
}> = [
  {
    id: "anger",
    label: "Anger",
    element: "Fire / Plasma",
    color: "#ff3b30",
    frequencies: [147],
  },
  {
    id: "sadness",
    label: "Sadness",
    element: "Water",
    color: "#2563eb",
    frequencies: [174],
  },
  {
    id: "hope",
    label: "Hope",
    element: "Air / Fluid Crystal",
    color: "#facc15",
    frequencies: [396, 437],
  },
  {
    id: "forgiveness",
    label: "Forgiveness",
    element: "Fluid Crystal",
    color: "#f97316",
    frequencies: [417],
  },
  {
    id: "peace",
    label: "Peace",
    element: "Harmonic Air",
    color: "#22c55e",
    frequencies: [432],
  },
  {
    id: "joy",
    label: "Joy",
    element: "Light Particles",
    color: "#06b6d4",
    frequencies: [741],
  },
  {
    id: "compassion",
    label: "Compassion",
    element: "Quantum Entanglement",
    color: "#8b5cf6",
    frequencies: [852],
  },
  {
    id: "wonder",
    label: "Wonder",
    element: "Coherence Field",
    color: "#4f46e5",
    frequencies: [963],
  },
  {
    id: "awe",
    label: "Awe",
    element: "Vacuum Potential",
    color: "#f8fafc",
    frequencies: [1111],
  },
]

const computeZoneRange = (anchors: number[], index: number) => {
  const anchor = anchors[index]
  const previous = anchors[index - 1]
  const next = anchors[index + 1]

  const lower = index === 0 ? EMOTION_SPECTRUM_MIN : (anchor + previous) / 2
  const upper =
    index === anchors.length - 1 ? EMOTION_SPECTRUM_MAX : (anchor + next) / 2

  return [lower, upper] as [number, number]
}

const roundLabel = (value: number) =>
  value % 1 === 0 ? value.toFixed(0) : value.toFixed(1)

export const EMOTION_ZONES: EmotionZone[] = (() => {
  const anchors = EMOTION_ZONE_DEFINITIONS.map((definition) =>
    definition.frequencies.reduce((sum, freq) => sum + freq, 0) /
    definition.frequencies.length
  )

  return EMOTION_ZONE_DEFINITIONS.map((definition, index) => {
    const anchor = anchors[index]
    const range = computeZoneRange(anchors, index)
    const frequencyLabel = definition.frequencies
      .map((frequency) => `${roundLabel(frequency)} Hz`)
      .join(" • ")
    const rangeLabel = `${roundLabel(range[0])}–${roundLabel(range[1])} Hz`

    return {
      ...definition,
      anchor,
      range,
      frequencyLabel,
      rangeLabel,
    }
  })
})()

const incrementalTicks = Array.from(
  { length: Math.floor((EMOTION_SPECTRUM_MAX - EMOTION_SPECTRUM_MIN) / 100) + 1 },
  (_, index) => EMOTION_SPECTRUM_MIN + index * 100
)

export const EMOTION_FREQUENCY_TICKS = Array.from(
  new Set<number>([
    ...incrementalTicks,
    ...EMOTION_ZONE_DEFINITIONS.flatMap((definition) => definition.frequencies),
    EMOTION_SPECTRUM_MAX,
  ])
)
  .sort((a, b) => a - b)
  .map((value) => Number(roundLabel(value)))

export const mapSchumannAmplitudeToEmotionFrequency = (amplitude: number) => {
  const normalized = clamp(amplitude, 0, 100) / 100
  return (
    EMOTION_SPECTRUM_MIN +
    normalized * (EMOTION_SPECTRUM_MAX - EMOTION_SPECTRUM_MIN)
  )
}

export const emotionZoneForFrequency = (frequency: number) => {
  const clamped = clamp(frequency, EMOTION_SPECTRUM_MIN, EMOTION_SPECTRUM_MAX)
  const zone = EMOTION_ZONES.find((candidate, index) => {
    const [min, max] = candidate.range
    const isLast = index === EMOTION_ZONES.length - 1
    return clamped >= min && (clamped < max || isLast)
  })
  return zone ?? EMOTION_ZONES[EMOTION_ZONES.length - 1]
}

export const formatFrequency = (value: number) => `${roundLabel(value)} Hz`
