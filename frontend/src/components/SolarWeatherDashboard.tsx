import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useCelestialData } from '@/hooks/useCelestialData';
import { useNoaaSpaceWeather } from '@/hooks/useNoaaSpaceWeather';
import { Sun, Zap, TrendingUp, Activity, Orbit, Wind } from 'lucide-react';

/**
 * Solar Weather — market-coherence view over two real feeds:
 *   • celestial-alignments  → coherence boost + active sacred frequencies
 *   • fetch-noaa-space-weather → real Kp / storm level / solar wind
 * No value is fabricated: when a feed is unavailable the card shows an honest
 * no-data state rather than a plausible-looking guess. Detailed NOAA charts live
 * on the sibling "Space Weather" surface.
 */
export const SolarWeatherDashboard = () => {
  const { celestialBoost, sacredFrequencies, isLoading: celestialLoading } = useCelestialData();
  const { data: noaa, isLoading: noaaLoading } = useNoaaSpaceWeather();

  if (celestialLoading && noaaLoading) {
    return (
      <Card className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-muted rounded w-1/3" />
          <div className="h-32 bg-muted rounded" />
        </div>
      </Card>
    );
  }

  const coherenceImpact = celestialBoost * 100;
  const impactLevel = coherenceImpact > 10 ? 'high' : coherenceImpact > 5 ? 'medium' : 'low';
  const impactColor = impactLevel === 'high' ? 'text-success' : impactLevel === 'medium' ? 'text-warning' : 'text-muted-foreground';

  const kp = noaa?.aurora?.current?.kpIndex ?? noaa?.magnetometer?.current?.kIndex ?? null;
  const stormLevel = noaa?.magnetometer?.stormLevel ?? null;
  const solarWind = noaa?.solarWind?.current ?? null;
  const solarWindStatus = noaa?.solarWind?.status ?? null;
  const kpTone = kp === null ? 'text-muted-foreground' : kp >= 5 ? 'text-destructive' : kp >= 4 ? 'text-warning' : 'text-primary';

  return (
    <div className="space-y-6">
      <Card className="p-6 bg-gradient-to-br from-background to-muted/20 border-primary/20">
        <div className="flex items-center gap-3 mb-6">
          <Sun className="w-8 h-8 text-primary animate-pulse" />
          <div>
            <h2 className="text-2xl font-bold text-foreground">Solar Weather Dashboard</h2>
            <p className="text-sm text-muted-foreground">Celestial coherence &amp; live NOAA space-weather impact</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* Coherence Impact — real (celestial-alignments) */}
          <Card className="p-4 border-primary/30 bg-background/50">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp className={`w-5 h-5 ${impactColor}`} />
              <h3 className="font-semibold text-foreground">Market Coherence Impact</h3>
            </div>
            <div className="space-y-2">
              <div className={`text-3xl font-bold ${impactColor}`}>
                {coherenceImpact > 0 ? '+' : ''}{coherenceImpact.toFixed(1)}%
              </div>
              <Badge variant={impactLevel === 'high' ? 'default' : 'secondary'} className="uppercase">
                {impactLevel} Impact
              </Badge>
              <p className="text-xs text-muted-foreground mt-2">
                {impactLevel === 'high' && 'Strong cosmic alignment enhancing field coherence'}
                {impactLevel === 'medium' && 'Moderate celestial influence on trading signals'}
                {impactLevel === 'low' && 'Minimal space weather impact on coherence'}
              </p>
            </div>
          </Card>

          {/* Solar Wind — real (NOAA) */}
          <Card className="p-4 border-warning/30 bg-background/50">
            <div className="flex items-center gap-2 mb-2">
              <Wind className="w-5 h-5 text-warning" />
              <h3 className="font-semibold text-foreground">Solar Wind</h3>
            </div>
            <div className="space-y-2">
              {solarWind ? (
                <>
                  <div className="text-2xl font-bold text-warning">{Math.round(solarWind.speed)} km/s</div>
                  <Badge variant="outline" className="border-warning/50 text-warning">
                    {solarWindStatus || 'Bz'} {solarWind.bz.toFixed(1)} nT
                  </Badge>
                  <p className="text-xs text-muted-foreground mt-2">
                    Live ACE/DSCOVR solar-wind speed and interplanetary Bz.
                  </p>
                </>
              ) : (
                <>
                  <div className="text-2xl font-bold text-muted-foreground">—</div>
                  <p className="text-xs text-muted-foreground mt-2">No NOAA solar-wind feed connected.</p>
                </>
              )}
            </div>
          </Card>

          {/* Geomagnetic (Kp) — real (NOAA) */}
          <Card className="p-4 border-primary/30 bg-background/50">
            <div className="flex items-center gap-2 mb-2">
              <Activity className="w-5 h-5 text-primary" />
              <h3 className="font-semibold text-foreground">Geomagnetic Activity</h3>
            </div>
            <div className="space-y-2">
              {kp !== null ? (
                <>
                  <div className={`text-2xl font-bold ${kpTone}`}>Kp {kp.toFixed(1)}</div>
                  <Badge variant="outline" className="border-primary/50 text-primary">
                    {stormLevel && stormLevel !== 'None' ? `${stormLevel} storm` : 'Quiet'}
                  </Badge>
                  <p className="text-xs text-muted-foreground mt-2">
                    Live planetary K-index from NOAA SWPC.
                  </p>
                </>
              ) : (
                <>
                  <div className="text-2xl font-bold text-muted-foreground">—</div>
                  <p className="text-xs text-muted-foreground mt-2">No NOAA geomagnetic feed connected.</p>
                </>
              )}
            </div>
          </Card>
        </div>
      </Card>

      {/* Sacred Frequencies — real (celestial-alignments) */}
      {sacredFrequencies.length > 0 && (
        <Card className="p-6 bg-gradient-to-br from-background to-secondary/10 border-secondary/20">
          <div className="flex items-center gap-2 mb-4">
            <Orbit className="w-6 h-6 text-secondary" />
            <h3 className="text-xl font-semibold text-foreground">Active Sacred Frequencies</h3>
          </div>
          <div className="flex flex-wrap gap-2">
            {sacredFrequencies.map((freq) => (
              <Badge key={freq} variant="secondary" className="text-base px-3 py-1">
                {freq} Hz
              </Badge>
            ))}
          </div>
          <p className="text-sm text-muted-foreground mt-3">
            Celestial alignments activating specific Solfeggio frequencies. These harmonics enhance field resonance and trading signal quality.
          </p>
        </Card>
      )}

      {/* Alerts — real (NOAA) */}
      {noaa && (noaa.alerts.solarWindAlert || noaa.alerts.magneticStorm || noaa.alerts.auroraAlert) && (
        <Card className="p-6 bg-gradient-to-br from-background to-warning/5 border-warning/20">
          <div className="flex items-center gap-2 mb-4">
            <Zap className="w-6 h-6 text-warning" />
            <h3 className="text-xl font-semibold text-foreground">Active NOAA Alerts</h3>
          </div>
          <div className="flex flex-wrap gap-2">
            {noaa.alerts.solarWindAlert && (
              <Badge variant="outline" className="border-warning/50 text-warning">High solar wind</Badge>
            )}
            {noaa.alerts.magneticStorm && (
              <Badge variant="outline" className="border-destructive/50 text-destructive">Geomagnetic storm</Badge>
            )}
            {noaa.alerts.auroraAlert && (
              <Badge variant="outline" className="border-primary/50 text-primary">Aurora visible</Badge>
            )}
          </div>
        </Card>
      )}
    </div>
  );
};
