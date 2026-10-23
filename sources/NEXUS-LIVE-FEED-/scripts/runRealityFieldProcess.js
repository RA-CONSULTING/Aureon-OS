import path from 'path';
import { promises as fs } from 'fs';
import { fileURLToPath } from 'url';

import { NexusSystem } from '../src/nexus_system_simulator.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function runProcessTree() {
  const nexus = new NexusSystem({
    numObservers: 7,
    dimensionality: 4,
  });

  const process = nexus.simulateProcessTree({
    steps: 200,
    deltaT: 0.1,
    seed: 1441,
  });

  const outDir = path.join(__dirname, '..', 'data');
  await fs.mkdir(outDir, { recursive: true });
  const outPath = path.join(outDir, 'reality_field_process.json');
  await fs.writeFile(outPath, JSON.stringify(process, null, 2), 'utf8');

  const { foundation, simulation } = process;
  const metrics = simulation.metrics ?? {};

  console.log('🧠 Reality Field Process Tree Execution Complete');
  console.log('----------------------------------------------');
  console.log(`Observers in lattice: ${foundation?.unityEvent?.observers ?? 'n/a'}`);
  console.log(`Unity target coherence: ${foundation?.unityEvent?.coherenceTarget ?? 'n/a'}`);
  console.log(`Unity phase threshold: ${foundation?.unityEvent?.phaseThreshold ?? 'n/a'} rad`);
  console.log('');
  console.log(`Unity event step: ${simulation.unityEventStep ?? 'not reached'}`);
  console.log(`Guardian anchor step: ${simulation.anchorStep ?? 'not anchored'}`);
  console.log(`Final coherence: ${metrics.finalCoherence?.toFixed(6) ?? 'n/a'}`);
  console.log(`Final phase spread: ${metrics.finalPhase?.toFixed(6) ?? 'n/a'} rad`);
  const loveConstantDisplay = metrics.loveConstantEstimate != null
    ? metrics.loveConstantEstimate.toFixed(3)
    : metrics.finalPhase === 0
      ? '∞ (coherence dominates entropy)'
      : 'n/a';

  console.log(`Reality field amplitude: ${metrics.finalRealityField?.toFixed(6) ?? 'n/a'}`);
  console.log(`Love constant estimate (Λₗ): ${loveConstantDisplay}`);
  console.log('');
  console.log(`Process telemetry saved to ${outPath}`);
}

runProcessTree().catch((error) => {
  console.error('❌ Reality Field process tree execution failed.');
  console.error(error);
  process.exit(1);
});
