import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { supabase } from "@/integrations/supabase/client";
import { useSchumannResonance } from "@/hooks/useSchumannResonance";
import { Activity, Radio, Waves, TrendingUp, AlertTriangle, CheckCircle2, XCircle } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, Legend } from "recharts";

interface EarthquakeEvent {
  id: string;
  magnitude: number;
  location: string;
  depth: number;
  timestamp: string;
  latitude: number;
  longitude: number;
  significance: number;
}

interface SeismicData {
  timestamp: string;
  events: EarthquakeEvent[];
  statistics: {
    totalEvents: number;
    significantEvents: number;
    majorEvents: number;
    avgMagnitude: number;
    avgDepth: number;
    stabilityIndex: number;
    last24hCount: number;
  };
  activityLevel: string;
  alerts: {
    highActivity: boolean;
    majorEvent: boolean;
    clusterDetected: boolean;
  };
}

export const EarthResonanceDashboard = () => {
  const [seismicData, setSeismicData] = useState<SeismicData | null>(null);
  const [isLoadingSeismic, setIsLoadingSeismic] = useState(true);
  const { schumannData, isConnected } = useSchumannResonance();

  const fetchSeismicData = async () => {
    try {
      const { data, error } = await supabase.functions.invoke('fetch-usgs-seismic-data');
      if (error) throw error;
      setSeismicData(data);
    } catch (error) {
      console.error('Error fetching seismic data:', error);
    } finally {
      setIsLoadingSeismic(false);
    }
  };

  useEffect(() => {
    fetchSeismicData();
    const interval = setInterval(fetchSeismicData, 15 * 60 * 1000); // Update every 15 minutes
    return () => clearInterval(interval);
  }, []);

  if (isLoadingSeismic || !schumannData) {
    return (
      <Card className="p-6">
        <div className="flex items-center justify-center h-96">
          <div className="text-muted-foreground">Loading Earth resonance data...</div>
        </div>
      </Card>
    );
  }

  // Calculate cross-system validation
  const validation = {
    seismicStable: seismicData?.statistics.stabilityIndex && seismicData.statistics.stabilityIndex > 0.7,
    schumannStable: schumannData && schumannData.fundamentalHz >= 7.5 && schumannData.fundamentalHz <= 8.5,
    coherenceHigh: schumannData && schumannData.coherenceBoost > 0.8,
    combinedScore: 0,
  };

  validation.combinedScore = (
    (validation.seismicStable ? 1 : 0) +
    (validation.schumannStable ? 1 : 0) +
    (validation.coherenceHigh ? 1 : 0)
  ) / 3;

  // Calculate Earth Field Coherence (cross-validation metric)
  const earthFieldCoherence = seismicData && schumannData ? 
    (seismicData.statistics.stabilityIndex + schumannData.quality) / 2 : 0;

  // Prepare radar chart data for system validation
  const radarData = [
    {
      system: 'Seismic',
      stability: (seismicData?.statistics.stabilityIndex || 0) * 100,
      fullMark: 100,
    },
    {
      system: 'Schumann',
      stability: (schumannData?.quality || 0) * 100,
      fullMark: 100,
    },
    {
      system: 'Coherence',
      stability: (schumannData?.coherenceBoost || 0) * 100,
      fullMark: 100,
    },
    {
      system: 'Earth Field',
      stability: earthFieldCoherence * 100,
      fullMark: 100,
    },
  ];

  // Prepare time series correlation data
  const correlationData = seismicData?.events.slice(0, 20).reverse().map((event, idx) => ({
    timestamp: new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    magnitude: event.magnitude,
    depth: event.depth / 10, // Scale for visibility
    schumannFreq: schumannData?.fundamentalHz || 0,
    schumannAmp: (schumannData?.amplitude || 0) * 10, // Scale for visibility
  })) || [];

  const getActivityColor = (level: string) => {
    switch (level) {
      case 'EXTREME': return 'destructive';
      case 'HIGH': return 'destructive';
      case 'MODERATE': return 'default';
      default: return 'outline';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <Radio className="h-6 w-6 text-primary" />
          Earth Resonance Dashboard
        </h2>
        <p className="text-sm text-muted-foreground">
          Deep Earth-Field correlations: USGS seismic activity × Schumann resonance × Trading coherence
        </p>
      </div>

      {/* Cross-System Validation */}
      <Card className="p-6 border-primary">
        <h3 className="font-semibold mb-4 flex items-center gap-2">
          <CheckCircle2 className="h-5 w-5 text-primary" />
          Multi-System Validation
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
          <div className="text-center">
            <div className="text-3xl font-bold mb-1">
              {(validation.combinedScore * 100).toFixed(0)}%
            </div>
            <div className="text-sm text-muted-foreground">Combined Score</div>
          </div>
          <div className="flex items-center justify-center gap-2">
            {validation.seismicStable ? (
              <CheckCircle2 className="h-5 w-5 text-success" />
            ) : (
              <XCircle className="h-5 w-5 text-destructive" />
            )}
            <span className="text-sm">Seismic Stable</span>
          </div>
          <div className="flex items-center justify-center gap-2">
            {validation.schumannStable ? (
              <CheckCircle2 className="h-5 w-5 text-success" />
            ) : (
              <XCircle className="h-5 w-5 text-destructive" />
            )}
            <span className="text-sm">Schumann Nominal</span>
          </div>
          <div className="flex items-center justify-center gap-2">
            {validation.coherenceHigh ? (
              <CheckCircle2 className="h-5 w-5 text-success" />
            ) : (
              <XCircle className="h-5 w-5 text-destructive" />
            )}
            <span className="text-sm">High Coherence</span>
          </div>
        </div>

        {/* Radar Chart for System Validation */}
        <ResponsiveContainer width="100%" height={300}>
          <RadarChart data={radarData}>
            <PolarGrid />
            <PolarAngleAxis dataKey="system" />
            <PolarRadiusAxis angle={90} domain={[0, 100]} />
            <Radar name="Stability Index" dataKey="stability" stroke="hsl(var(--primary))" fill="hsl(var(--primary))" fillOpacity={0.6} />
            <Legend />
          </RadarChart>
        </ResponsiveContainer>

        <div className="mt-4 p-3 bg-muted rounded-lg">
          <p className="text-sm">
            <strong>Earth Field Coherence:</strong> {(earthFieldCoherence * 100).toFixed(1)}% 
            {earthFieldCoherence > 0.8 && "  Optimal conditions for high-coherence trading"}
          </p>
        </div>
      </Card>

      {/* Current Status Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Seismic Activity */}
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <Activity className="h-5 w-5 text-primary" />
            <h3 className="font-semibold">Seismic Activity</h3>
          </div>
          {seismicData && (
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Activity Level</span>
                <Badge variant={getActivityColor(seismicData.activityLevel) as any}>
                  {seismicData.activityLevel}
                </Badge>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Events (7d)</span>
                <span className="font-mono font-bold">{seismicData.statistics.totalEvents}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Avg Magnitude</span>
                <span className="font-mono">{seismicData.statistics.avgMagnitude.toFixed(1)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Stability Index</span>
                <span className="font-mono">{(seismicData.statistics.stabilityIndex * 100).toFixed(0)}%</span>
              </div>
              {seismicData.alerts.majorEvent && (
                <div className="flex items-center gap-1 text-destructive text-sm mt-2">
                  <AlertTriangle className="h-4 w-4" />
                  Major event detected
                </div>
              )}
            </div>
          )}
        </Card>

        {/* Schumann Resonance */}
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <Waves className="h-5 w-5 text-primary" />
            <h3 className="font-semibold">Schumann Resonance</h3>
          </div>
          {schumannData && (
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Phase</span>
                <Badge variant="outline">{schumannData.resonancePhase}</Badge>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Frequency</span>
                <span className="font-mono font-bold">{schumannData.fundamentalHz.toFixed(2)} Hz</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Amplitude</span>
                <span className="font-mono">{schumannData.amplitude.toFixed(2)} pT</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Quality</span>
                <span className="font-mono">{(schumannData.quality * 100).toFixed(0)}%</span>
              </div>
            </div>
          )}
        </Card>

        {/* Earth Field Coherence */}
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className="h-5 w-5 text-primary" />
            <h3 className="font-semibold">Field Coherence</h3>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Earth Field</span>
              <span className="font-mono font-bold">{(earthFieldCoherence * 100).toFixed(0)}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Schumann Boost</span>
              <span className="font-mono">{((schumannData?.coherenceBoost || 0) * 100).toFixed(0)}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Seismic Stability</span>
              <span className="font-mono">{((seismicData?.statistics.stabilityIndex || 0) * 100).toFixed(0)}%</span>
            </div>
            <div className="mt-4 p-2 bg-primary/10 rounded text-center">
              <div className="text-xs text-muted-foreground mb-1">Optimal Trading Window</div>
              <div className="text-lg font-bold">
                {validation.combinedScore > 0.7 ? "ACTIVE " : "WAIT "}
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Recent Earthquake Events */}
      {seismicData && seismicData.events.length > 0 && (
        <Card className="p-6">
          <h3 className="font-semibold mb-4">Recent Significant Earthquakes</h3>
          <div className="space-y-3">
            {seismicData.events.slice(0, 5).map((event) => (
              <div key={event.id} className="flex items-center justify-between p-3 bg-muted rounded-lg">
                <div className="flex-1">
                  <div className="font-medium">{event.location}</div>
                  <div className="text-sm text-muted-foreground">
                    {new Date(event.timestamp).toLocaleString()} • Depth: {event.depth.toFixed(0)}km
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold">M{event.magnitude.toFixed(1)}</div>
                  <div className="text-xs text-muted-foreground">
                    Lat: {event.latitude.toFixed(2)}, Lon: {event.longitude.toFixed(2)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Correlation Time Series */}
      <Card className="p-6">
        <h3 className="font-semibold mb-4">Seismic × Schumann Correlation (Recent Events)</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={correlationData}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
            <XAxis dataKey="timestamp" fontSize={12} />
            <YAxis yAxisId="left" fontSize={12} />
            <YAxis yAxisId="right" orientation="right" fontSize={12} />
            <Tooltip />
            <Legend />
            <Line yAxisId="left" type="monotone" dataKey="magnitude" stroke="hsl(var(--destructive))" strokeWidth={2} name="Magnitude" />
            <Line yAxisId="right" type="monotone" dataKey="schumannFreq" stroke="hsl(var(--primary))" strokeWidth={2} name="Schumann Freq (Hz)" />
            <Line yAxisId="right" type="monotone" dataKey="schumannAmp" stroke="hsl(var(--chart-2))" strokeWidth={2} name="Schumann Amp (×10 pT)" />
          </LineChart>
        </ResponsiveContainer>
        <p className="text-xs text-muted-foreground mt-2">
          Real-time correlation between seismic events and Schumann resonance. Validates Earth field coherence.
        </p>
      </Card>

      {/* Insights */}
      <Card className="p-6">
        <h3 className="font-semibold mb-4"> Earth Resonance Insights</h3>
        <div className="space-y-3">
          <div className="border-l-4 border-primary pl-4">
            <p className="text-sm font-medium">Cross-System Validation</p>
            <p className="text-xs text-muted-foreground mt-1">
              When seismic stability, Schumann resonance, and trading coherence all align (score &gt; 70%), 
              the Earth field is in optimal resonance for high-confidence trading signals.
            </p>
          </div>
          
          {validation.seismicStable && validation.schumannStable && validation.coherenceHigh && (
            <div className="border-l-4 border-success pl-4">
              <p className="text-sm font-medium"> Perfect Alignment Detected</p>
              <p className="text-xs text-muted-foreground mt-1">
                All systems validating each other! This is an optimal window for high-probability trades. 
                The Earth field coherence of {(earthFieldCoherence * 100).toFixed(0)}% indicates strong resonance.
              </p>
            </div>
          )}
          
          {seismicData?.alerts.highActivity && (
            <div className="border-l-4 border-destructive pl-4">
              <p className="text-sm font-medium"> Elevated Seismic Activity</p>
              <p className="text-xs text-muted-foreground mt-1">
                Increased seismic events detected. This may correlate with market volatility. 
                Monitor Schumann resonance for stability confirmation.
              </p>
            </div>
          )}

          <div className="border-l-4 border-primary pl-4">
            <p className="text-sm font-medium"> Deep Earth Resonance Theory</p>
            <p className="text-xs text-muted-foreground mt-1">
              Seismic activity and Schumann resonance both originate from Earth's electromagnetic field. 
              When they harmonize with trading coherence, it suggests a fundamental alignment in natural systems.
            </p>
          </div>
        </div>
      </Card>

      {/* Footer */}
      <div className="text-xs text-muted-foreground text-center">
        USGS earthquake data • Schumann resonance monitoring • Updates every 15 minutes
      </div>
    </div>
  );
};
