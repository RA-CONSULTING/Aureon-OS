// Earth stream monitor. This file never synthesizes telemetry.

export interface SolarWindData {
  velocity: number;
  density: number;
  temperature: number;
  magneticField: number;
  pressure: number;
  timestamp: number;
}

export interface GeomagneticData {
  kpIndex: number;
  apIndex: number;
  dstIndex: number;
  fieldStrength: number;
  inclination: number;
  declination: number;
  timestamp: number;
}

export interface AtmosphericData {
  ionosphericDensity: number;
  electronicContent: number;
  scintillationIndex: number;
  timestamp: number;
}

export interface EarthStreamMetrics {
  solarWind: SolarWindData;
  geomagnetic: GeomagneticData;
  atmospheric: AtmosphericData;
  coherenceIndex: number;
  fieldCoupling: number;
  truthStatus: 'live' | 'real_derived' | 'cached_real' | 'no_data';
  blocker?: string;
}

export class EarthStreamsMonitor {
  private solarWindData: SolarWindData | null = null;
  private geomagneticData: GeomagneticData | null = null;
  private atmosphericData: AtmosphericData | null = null;
  private isActive = false;

  initialize(): void {
    this.solarWindData = null;
    this.geomagneticData = null;
    this.atmosphericData = null;
    this.isActive = true;
  }

  getEarthStreamMetrics(): EarthStreamMetrics | null {
    if (!this.solarWindData || !this.geomagneticData || !this.atmosphericData) {
      return null;
    }

    return {
      solarWind: this.solarWindData,
      geomagnetic: this.geomagneticData,
      atmospheric: this.atmosphericData,
      coherenceIndex: this.calculateCoherenceIndex(),
      fieldCoupling: this.calculateFieldCoupling(),
      truthStatus: 'live',
    };
  }

  private calculateCoherenceIndex(): number {
    if (!this.solarWindData || !this.geomagneticData) return 0;
    const velocityFactor = Math.min(1, this.solarWindData.velocity / 600);
    const densityFactor = Math.min(1, this.solarWindData.density / 10);
    const kpFactor = 1 - this.geomagneticData.kpIndex / 9;
    return velocityFactor * 0.4 + densityFactor * 0.3 + kpFactor * 0.3;
  }

  private calculateFieldCoupling(): number {
    if (!this.solarWindData || !this.geomagneticData || !this.atmosphericData) return 0;
    const solarCoupling = this.solarWindData.magneticField / 10;
    const geomagneticCoupling = this.geomagneticData.fieldStrength / 60000;
    const ionosphericCoupling = 1 - this.atmosphericData.scintillationIndex;
    return Math.min(2.0, solarCoupling + geomagneticCoupling + ionosphericCoupling);
  }

  isMonitoringActive(): boolean {
    return this.isActive;
  }
}

export const earthStreamsMonitor = new EarthStreamsMonitor();

export interface SimpleEarthStreams {
  solarWindVelocity: number | null;
  geomagneticKp: number | null;
  ionosphericDensity: number | null;
  fieldCoupling: number | null;
  truthStatus: 'live' | 'real_derived' | 'cached_real' | 'no_data';
  blocker?: string;
}

export async function getEarthStreams(): Promise<SimpleEarthStreams> {
  const metrics = earthStreamsMonitor.getEarthStreamMetrics();

  if (!metrics) {
    earthStreamsMonitor.initialize();
    return {
      solarWindVelocity: null,
      geomagneticKp: null,
      ionosphericDensity: null,
      fieldCoupling: null,
      truthStatus: 'no_data',
      blocker: 'earth_stream_provider_not_mounted',
    };
  }

  return {
    solarWindVelocity: metrics.solarWind.velocity,
    geomagneticKp: metrics.geomagnetic.kpIndex,
    ionosphericDensity: metrics.atmospheric.ionosphericDensity / 1e10,
    fieldCoupling: metrics.fieldCoupling,
    truthStatus: metrics.truthStatus,
    blocker: metrics.blocker,
  };
}
