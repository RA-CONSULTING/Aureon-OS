export const metrics = {
  quantumCoherence: {
    description: 'Relative phase alignment of quantum events.',
    unit: 'qbits',
    value: () => Math.random()
  },
  harmonicResonance: {
    description: 'Amplitude alignment across frequencies.',
    unit: 'Hz',
    value: () => Math.random() * 100
  },
  schumannResonance: {
    description: 'Global electromagnetic resonances measured in Hertz.',
    unit: 'Hz',
    value: () => 7.83 + Math.random() * 0.1
  },
  rainbowSpectrum: {
    description: 'Representation of spectral energy distribution.',
    unit: 'spectrum',
    value: () => Math.random()
  },
  consciousnessMetric: {
    description: 'Synthetic metric for collective consciousness shifts.',
    unit: 'psi',
    value: () => Math.random()
  }
};

export function sampleMetrics() {
  const timestamp = Date.now();
  const data = {};
  for (const [key, meta] of Object.entries(metrics)) {
    data[key] = {
      value: typeof meta.value === 'function' ? meta.value() : meta.value,
      unit: meta.unit,
      description: meta.description
    };
  }
  return { timestamp, metrics: data };
}
