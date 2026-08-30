import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Moon, Sun, Star, Sparkles, Orbit } from 'lucide-react';
import { supabase } from '@/integrations/supabase/client';

type CelestialData = {
  timestamp: string;
  moon: {
    phase: number;
    name: string;
    power: number;
    influence: string;
    illumination: number;
  };
  solar: {
    activity: number;
    phase: string;
    power: number;
    cycleDay: number;
    recentFlares?: Array<{
      class: string;
      time: string;
      source: string;
      power: number;
    }>;
    dominantFlare?: {
      class: string;
      time: string;
      power: number;
      hoursSince: number;
    } | null;
  };
  planetary: {
    alignmentScore: number;
    alignedPlanets: string[];
    power: number;
  };
  seasonal: {
    name: string;
    proximity: number;
    power: number;
    daysUntil: number;
  };
  cosmic: {
    overallPower: number;
    coherenceBoost: number;
    sacredFrequencies: number[];
  };
};

export const CelestialAlignments = () => {
  const [celestialData, setCelestialData] = useState<CelestialData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchCelestialData = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const { data, error: functionError } = await supabase.functions.invoke('celestial-alignments', {
        body: {},
      });

      if (functionError) throw functionError;
      if (data.error) throw new Error(data.error);

      setCelestialData(data);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch celestial data';
      setError(errorMessage);
      console.error('Celestial alignments error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCelestialData();
    
    // Refresh every 10 minutes
    const interval = setInterval(fetchCelestialData, 600000);
    return () => clearInterval(interval);
  }, []);

  if (isLoading && !celestialData) {
    return (
      <Card className="bg-card shadow-card">
        <CardContent className="p-8 text-center">
          <Sparkles className="h-12 w-12 mx-auto mb-4 text-primary animate-pulse" />
          <p className="text-sm text-muted-foreground">Calculating cosmic alignments...</p>
        </CardContent>
      </Card>
    );
  }

  if (error || !celestialData) {
    return (
      <Card className="bg-card shadow-card">
        <CardContent className="p-8 text-center">
          <Star className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
          <p className="text-sm text-destructive">{error || 'No data available'}</p>
        </CardContent>
      </Card>
    );
  }

  const getPowerColor = (power: number) => {
    if (power >= 1.7) return 'text-primary';
    if (power >= 1.4) return 'text-primary';
    if (power >= 1.2) return 'text-success';
    return 'text-muted-foreground';
  };

  return (
    <Card className="bg-card shadow-card">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span className="text-2xl">✨</span>
          Celestial Alignments
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          Astronomical influences on Stargate frequencies
        </p>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Overall Cosmic Power */}
        <div className="p-4 rounded-lg border-2 border-primary/30 bg-primary/5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              <span className="font-semibold">Cosmic Power Multiplier</span>
            </div>
            <Badge variant="default" className="text-lg">
              {celestialData.cosmic.overallPower.toFixed(2)}x
            </Badge>
          </div>
          <Progress value={(celestialData.cosmic.overallPower - 1) * 100} className="h-3 mb-2" />
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Coherence Boost</span>
            <span className={`font-mono font-bold ${getPowerColor(celestialData.cosmic.overallPower)}`}>
              +{(celestialData.cosmic.coherenceBoost * 100).toFixed(1)}%
            </span>
          </div>
        </div>

        {/* Active Sacred Frequencies */}
        {celestialData.cosmic.sacredFrequencies.length > 0 && (
          <div className="p-4 rounded-lg border border-border bg-muted/20">
            <div className="flex items-center gap-2 mb-3">
              <Orbit className="h-4 w-4 text-primary" />
              <span className="text-sm font-semibold">Active Sacred Frequencies</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {celestialData.cosmic.sacredFrequencies.map((freq) => (
                <Badge key={freq} variant="secondary" className="font-mono">
                  {freq}Hz
                </Badge>
              ))}
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Moon Phase */}
          <div className="p-4 rounded-lg border border-border bg-muted/20">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Moon className="h-4 w-4 text-primary" />
                <span className="text-sm font-semibold">Lunar Phase</span>
              </div>
              <Badge className={getPowerColor(celestialData.moon.power)}>
                {celestialData.moon.power.toFixed(1)}x
              </Badge>
            </div>
            <p className="font-bold mb-1">{celestialData.moon.name}</p>
            <p className="text-xs text-muted-foreground mb-2">{celestialData.moon.influence}</p>
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Illumination</span>
              <span className="font-mono">{celestialData.moon.illumination.toFixed(0)}%</span>
            </div>
          </div>

          {/* Solar Activity */}
          <div className="p-4 rounded-lg border border-border bg-muted/20">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Sun className="h-4 w-4 text-primary" />
                <span className="text-sm font-semibold">Solar Activity</span>
              </div>
              <Badge className={getPowerColor(celestialData.solar.power)}>
                {celestialData.solar.power.toFixed(1)}x
              </Badge>
            </div>
            <p className="font-bold mb-1">{celestialData.solar.phase}</p>
            <Progress value={celestialData.solar.activity * 100} className="h-2 mb-2" />
            
            {celestialData.solar.dominantFlare ? (
              <div className="mt-2 p-2 rounded bg-warning/10 border border-warning/20">
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="font-bold text-warning">
                    {celestialData.solar.dominantFlare.class} FLARE DETECTED
                  </span>
                  <span className="text-warning">
                    {celestialData.solar.dominantFlare.power.toFixed(1)}x
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">
                  {celestialData.solar.dominantFlare.hoursSince}h ago • 
                  {celestialData.solar.dominantFlare.class.startsWith('X') ? ' EXTREME EVENT' : ' Active'}
                </p>
              </div>
            ) : (
              <div className="flex items-center justify-between text-xs mt-2">
                <span className="text-muted-foreground">Cycle Day</span>
                <span className="font-mono">{celestialData.solar.cycleDay}/4018</span>
              </div>
            )}
            
            {celestialData.solar.recentFlares && celestialData.solar.recentFlares.length > 0 && (
              <div className="mt-2">
                <p className="text-xs text-muted-foreground mb-1">
                  Recent flares (48h):
                </p>
                <div className="flex flex-wrap gap-1">
                  {celestialData.solar.recentFlares.slice(0, 5).map((flare, i) => (
                    <Badge 
                      key={i} 
                      variant="outline" 
                      className={`text-xs ${
                        flare.class.startsWith('X') ? 'border-warning text-warning' :
                        flare.class.startsWith('M') ? 'border-warning text-warning' :
                        'border-muted'
                      }`}
                    >
                      {flare.class}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Planetary Alignment */}
          <div className="p-4 rounded-lg border border-border bg-muted/20">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Orbit className="h-4 w-4 text-primary" />
                <span className="text-sm font-semibold">Planetary Alignment</span>
              </div>
              <Badge className={getPowerColor(celestialData.planetary.power)}>
                {celestialData.planetary.power.toFixed(1)}x
              </Badge>
            </div>
            <Progress value={celestialData.planetary.alignmentScore * 100} className="h-2 mb-2" />
            {celestialData.planetary.alignedPlanets.length > 0 ? (
              <div className="flex flex-wrap gap-1 mt-2">
                {celestialData.planetary.alignedPlanets.map((planet) => (
                  <Badge key={planet} variant="outline" className="text-xs">
                    {planet}
                  </Badge>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">No major alignments</p>
            )}
          </div>

          {/* Seasonal Gateway */}
          <div className="p-4 rounded-lg border border-border bg-muted/20">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Star className="h-4 w-4 text-primary" />
                <span className="text-sm font-semibold">Seasonal Gateway</span>
              </div>
              <Badge className={getPowerColor(celestialData.seasonal.power)}>
                {celestialData.seasonal.power.toFixed(1)}x
              </Badge>
            </div>
            <p className="font-bold mb-1">{celestialData.seasonal.name}</p>
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">
                {celestialData.seasonal.proximity > 0.7 ? 'Active Window' : 'Days Until'}
              </span>
              <span className="font-mono">
                {celestialData.seasonal.proximity > 0.7 
                  ? `${(celestialData.seasonal.proximity * 100).toFixed(0)}%` 
                  : `${celestialData.seasonal.daysUntil}d`}
              </span>
            </div>
          </div>
        </div>

        <div className="p-3 rounded-lg bg-primary/5 border border-primary/20">
          <p className="text-xs text-muted-foreground leading-relaxed">
            <span className="font-semibold">💫 Cosmic Integration:</span> Real-time NASA solar flare 
            data combined with astronomical alignments amplify Stargate node frequencies. X-class solar 
            flares provide extreme power multipliers (up to 5.5x for X10+ events), creating unprecedented 
            coherence windows. Full moons, planetary conjunctions, and seasonal gateways multiply trading 
            signal strength during sacred alignments. System updates every 10 minutes with live space weather.
          </p>
        </div>
      </CardContent>
    </Card>
  );
};
