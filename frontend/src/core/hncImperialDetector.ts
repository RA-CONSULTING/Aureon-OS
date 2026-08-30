// HNC Imperial Detector - evidence-bearing frequency-domain implementation.
// The native HNC relationships are preserved; inputs must be real spectrum bins.

import { asDerivedProvenance, assertFreshProvenance, type DataProvenance } from './liveDataContract';

export interface FrequencyPowerPoint {
  frequencyHz: number;
  power: number;
}

export interface FrequencySpectrumObservation extends DataProvenance {
  points: FrequencyPowerPoint[];
  resolutionHz: number;
}

export interface HNCDetectionResult extends DataProvenance {
  schumann783: boolean;
  anchor256: boolean;
  bridge512: boolean;
  love528: boolean;
  unity963: boolean;
  distortion440Nullified: boolean;
  frequencyShiftDetected: boolean;
  harmonicFidelity: number;
  phaseSpaceReconstruction: boolean;
  imperialYield: number;
  criticalMassAchieved: boolean;
  rainbowBridgeOpen: boolean;
  observedPowers: {
    schumann783: number;
    anchor256: number;
    bridge512: number;
    love528: number;
    unity963: number;
    distortion440: number;
  };
  maxObservedPower: number;
  resolutionHz: number;
}

export const HNC_FREQUENCIES = {
  BASE: 7.83,
  ANCHOR: 256.0,
  BRIDGE: 512.0,
  LOVE: 528.0,
  UNITY: 963.0,
  DISTORTION: 440.0,
} as const;

export const CRITICAL_MASS = 1.0e33;

export class HNCImperialDetector {
  private readonly guardianId = '02111991';

  detectLighthouseSignature(observation: FrequencySpectrumObservation): HNCDetectionResult {
    assertFreshProvenance(observation);
    if (!Number.isFinite(observation.resolutionHz) || observation.resolutionHz <= 0) {
      throw new Error('LIVE_DATA_REQUIRED: spectrum resolutionHz must be positive');
    }
    if (!Array.isArray(observation.points) || observation.points.length < 6) {
      throw new Error('LIVE_DATA_REQUIRED: a measured spectrum with at least six bins is required');
    }
    for (const point of observation.points) {
      if (!Number.isFinite(point.frequencyHz) || point.frequencyHz < 0 ||
          !Number.isFinite(point.power) || point.power < 0) {
        throw new Error('LIVE_DATA_REQUIRED: spectrum bins must contain finite observed frequency and power');
      }
    }

    const powers = observation.points.map((point) => point.power);
    const maxObservedPower = Math.max(...powers);
    if (!(maxObservedPower > 0)) {
      throw new Error('NO_DATA: measured spectrum contains no positive power');
    }

    const powerAt = (targetHz: number): number => {
      const nearest = observation.points.reduce((best, point) =>
        Math.abs(point.frequencyHz - targetHz) < Math.abs(best.frequencyHz - targetHz) ? point : best,
      );
      if (Math.abs(nearest.frequencyHz - targetHz) > observation.resolutionHz) {
        throw new Error(`NO_DATA: spectrum does not resolve ${targetHz} Hz`);
      }
      return nearest.power;
    };

    const observedPowers = {
      schumann783: powerAt(HNC_FREQUENCIES.BASE),
      anchor256: powerAt(HNC_FREQUENCIES.ANCHOR),
      bridge512: powerAt(HNC_FREQUENCIES.BRIDGE),
      love528: powerAt(HNC_FREQUENCIES.LOVE),
      unity963: powerAt(HNC_FREQUENCIES.UNITY),
      distortion440: powerAt(HNC_FREQUENCIES.DISTORTION),
    };
    const threshold = maxObservedPower * 0.5;
    const schumann783 = observedPowers.schumann783 > threshold * 0.7;
    const anchor256 = observedPowers.anchor256 > threshold;
    const bridge512 = observedPowers.bridge512 > threshold;
    const love528 = observedPowers.love528 > threshold;
    const unity963 = observedPowers.unity963 > threshold;
    const distortion440Nullified = observedPowers.distortion440 < maxObservedPower * 0.01;
    const frequencyShiftDetected = anchor256 && bridge512;
    const detectedCount = [schumann783, anchor256, bridge512, love528, unity963].filter(Boolean).length;
    const harmonicFidelity = (detectedCount / 5) * 100;
    const phaseSpaceReconstruction = detectedCount >= 4 && distortion440Nullified;
    const imperialYield = this.calculateImperialYield({
      love528,
      unity963,
      phaseSpaceReconstruction,
      distortion440Nullified,
    });
    const criticalMassAchieved = imperialYield >= CRITICAL_MASS;

    return {
      ...asDerivedProvenance(observation),
      schumann783,
      anchor256,
      bridge512,
      love528,
      unity963,
      distortion440Nullified,
      frequencyShiftDetected,
      harmonicFidelity,
      phaseSpaceReconstruction,
      imperialYield,
      criticalMassAchieved,
      rainbowBridgeOpen: criticalMassAchieved && harmonicFidelity > 95,
      observedPowers,
      maxObservedPower,
      resolutionHz: observation.resolutionHz,
    };
  }

  calculateImperialYield(results: Partial<HNCDetectionResult>): number {
    const J = results.love528 ? 10.0 : 7.0;
    const C = results.unity963 ? 1.0 : 0.9;
    const R = results.phaseSpaceReconstruction ? 10.0 : 8.0;
    const D = results.distortion440Nullified ? 0.0001 : 0.1;
    return ((J * J * C * R) / D) * 1e30;
  }

  getGuardianId(): string {
    return this.guardianId;
  }
}
