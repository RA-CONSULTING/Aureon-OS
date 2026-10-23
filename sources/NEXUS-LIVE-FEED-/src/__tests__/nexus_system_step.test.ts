import { beforeEach, afterEach, describe, expect, it } from "vitest";
import { NexusSystem } from "../nexus_system_simulator.js";

describe("NexusSystem.step", () => {
  let originalRandom: () => number;

  beforeEach(() => {
    originalRandom = Math.random;
    Math.random = () => 0.5;
  });

  afterEach(() => {
    Math.random = originalRandom;
  });

  it("blends an external coherence reading into the ego state", () => {
    const system = new NexusSystem();
    const snapshot = system.step(0.9, null, { deltaT: 0 });

    expect(snapshot.coherence).toBeCloseTo(0.852, 3);
    expect(system.egoDeathSim.coherence).toBeCloseTo(snapshot.coherence, 6);
    expect(snapshot.stress).toBeNull();
  });

  it("applies stress as a coherence penalty and phase expansion", () => {
    const system = new NexusSystem();
    const snapshot = system.step(null, 0.5, { deltaT: 0 });

    expect(snapshot.coherence).toBeLessThan(0.8);
    expect(snapshot.phase).toBeGreaterThan(0.3);
    expect(snapshot.stress).toBeCloseTo(0.5, 6);
  });
});

