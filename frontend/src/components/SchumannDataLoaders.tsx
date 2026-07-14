// Data Loaders for Schumann Lattice Timeline
// ------------------------------------------
// ZIP and CSV loaders for earth-live-data integration

import { TensorDatum } from './SchumannLatticePatch';

export interface TimelineFrame {
  t: number;                    // timestamp
  schumannHz: number[];        // frequency array
  tensorField: TensorDatum[];  // tensor data
}

// -----------------------------
// ZIP Loader for earth-live-data
// -----------------------------
export async function loadZipFrames(_file: File): Promise<TimelineFrame[]> {
  // ZIP parsing is not implemented yet. We deliberately return NO frames rather
  // than fabricating random data that would render as if it were real
  // earth-live-data. Use the CSV loader for real frames until ZIP support lands.
  console.warn(
    'SchumannDataLoaders.loadZipFrames: ZIP import not implemented — no frames ' +
    'loaded (returning empty; use a .csv export instead).'
  );
  return [];
}

// -----------------------------
// CSV Loader
// -----------------------------
export async function csvToFrames(file: File): Promise<TimelineFrame[]> {
  try {
    const text = await file.text();
    const lines = text.split('\n').filter(line => line.trim());
    const frames: TimelineFrame[] = [];
    
    // Skip header if present
    const dataLines = lines[0].includes('timestamp') ? lines.slice(1) : lines;
    
    for (const line of dataLines) {
      const cols = line.split(',').map(s => s.trim());
      if (cols.length < 6) continue;
      
      const t = parseInt(cols[0]) || Date.now();
      const schumannHz = [
        parseFloat(cols[1]) || 7.83,
        parseFloat(cols[2]) || 14.3,
        parseFloat(cols[3]) || 20.8,
        parseFloat(cols[4]) || 27.3,
        parseFloat(cols[5]) || 33.8
      ];

      // Tensor field is not present in the CSV schema — leave it empty rather
      // than fabricating random tensor values. The lattice renders the real
      // frequency frames; the tensor overlay stays empty until a source supplies it.
      const tensorField: TensorDatum[] = [];

      frames.push({ t, schumannHz, tensorField });
    }
    
    return frames;
  } catch (error) {
    console.error('Error parsing CSV:', error);
    return [];
  }
}

// -----------------------------
// Utility: Parse Tensor Array from JSON
// -----------------------------
export function parseTensorArray(jsonData: any[]): TensorDatum[] {
  return jsonData.map(item => ({
    phi: item.phi || item.phase || 0,
    kappa: item.kappa || item.curvature || 1,
    psi: item.psi || item.weight || 1,
    TSV: item.TSV || item.coherence || 0
  }));
}