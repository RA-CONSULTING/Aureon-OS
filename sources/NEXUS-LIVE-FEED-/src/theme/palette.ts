export const earthPalette = {
  soil: '#0d132f',
  canyon: '#6D4BFF',
  ember: '#7C3AED',
  sunrise: '#5B8DFF',
  sandstone: '#B7A5FF',
  clay: '#9F5FFF',
  grove: '#4FB6FF',
  moss: '#3FA3FF',
  sage: '#57E3FF',
  mist: '#9AD7FF',
  dusk: '#5A4BFF',
  shadow: '#050b21',
} as const;

type PaletteKey = keyof typeof earthPalette;

type PaletteGroup = [string, string, string];

export const earthToneGroups: Record<
  | 'vitality'
  | 'resonance'
  | 'flow'
  | 'horizon'
  | 'ember'
  | 'dusk'
  | 'aurora',
  PaletteGroup
> = {
  vitality: [earthPalette.canyon, earthPalette.ember, earthPalette.sunrise],
  resonance: [earthPalette.grove, earthPalette.sage, earthPalette.mist],
  flow: [earthPalette.clay, earthPalette.sunrise, earthPalette.sandstone],
  horizon: [earthPalette.moss, earthPalette.grove, earthPalette.mist],
  ember: [earthPalette.soil, earthPalette.canyon, earthPalette.sunrise],
  dusk: [earthPalette.dusk, earthPalette.canyon, earthPalette.sandstone],
  aurora: [earthPalette.grove, earthPalette.clay, earthPalette.sandstone],
};

export const borderStates: Record<'stable' | 'watch' | 'anomaly', string> = {
  stable: earthPalette.grove,
  watch: earthPalette.sunrise,
  anomaly: earthPalette.ember,
};

export const temporalScanBorders: Record<'alpha' | 'beta', string> = {
  alpha: earthPalette.sunrise,
  beta: earthPalette.grove,
};

export const sparklineGroups: PaletteGroup[] = [
  earthToneGroups.vitality,
  earthToneGroups.resonance,
  earthToneGroups.flow,
  earthToneGroups.horizon,
  earthToneGroups.ember,
  earthToneGroups.dusk,
];

export const realtimeSpectrumOrder: PaletteGroup[] = [
  earthToneGroups.vitality,
  earthToneGroups.resonance,
  earthToneGroups.flow,
  earthToneGroups.horizon,
];

export type EarthPaletteKey = PaletteKey;
