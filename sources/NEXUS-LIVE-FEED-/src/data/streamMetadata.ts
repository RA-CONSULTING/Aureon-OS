export type SensorState = 'Stable' | 'Watch' | 'Anomaly';

export const STREAM_METADATA: Record<string, { location: string; capacity: number }> = {
  phenomena: { location: 'Witness Array · Cusco Grid', capacity: 180 },
  temporal: { location: 'Temporal Anchor Lab · Reykjavik', capacity: 140 },
  geometry: { location: 'Sacred Geometry Observatory · Chartres', capacity: 120 },
  celestial: { location: 'Orbital Relay · Lagrange L1', capacity: 36 },
  geomagnetic: { location: 'Geomagnetic Vault · Mauna Kea Apex', capacity: 80 },
};

export const SENSOR_STATE_NOTES: Record<SensorState, string> = {
  Stable: 'Field drift < 0.5%',
  Watch: 'Harmonic balancing underway',
  Anomaly: 'Escalate for manual review',
};
