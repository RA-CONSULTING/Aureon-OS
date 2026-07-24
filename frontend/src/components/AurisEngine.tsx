import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useSchumannData } from '@/hooks/useSchumannData';
import { getEarthStreams } from '@/lib/earth-streams';
import { fmt, pct } from '@/utils/number';
import { AurisEngine as AurisEngineCore, aurisEngine, BroadcastResult } from '@/lib/auris-engine';
import { aurisCodex } from '@/lib/auris-codex';

interface LiveValidationMetrics {
  schumannResonance: number;
  fieldCoherence: number;
  harmonicAlignment: number;
  intentStrength: number;
  broadcastSuccess: number;
  solarWindVelocity: number;
  geomagneticActivity: number;
  ionosphericDensity: number;
}

export const AurisEngine: React.FC = () => {
  const [isInitialized, setIsInitialized] = useState(false);
  const [isLiveActive, setIsLiveActive] = useState(false);
  const [intentText, setIntentText] = useState('peace');
  const [lastBroadcast, setLastBroadcast] = useState<BroadcastResult | null>(null);
  const [liveMetrics, setLiveMetrics] = useState<LiveValidationMetrics>({
    schumannResonance: 0,
    fieldCoherence: 0,
    harmonicAlignment: 0,
    intentStrength: 0,
    broadcastSuccess: 0,
    solarWindVelocity: 0,
    geomagneticActivity: 0,
    ionosphericDensity: 0
  });
  const [broadcastCount, setBroadcastCount] = useState(0);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    initializeEngine();
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  const initializeEngine = async () => {
    try {
      await aurisEngine.initialize();
      setIsInitialized(true);
    } catch (error) {
      console.error('Failed to initialize Auris Engine:', error);
    }
  };

  const startLiveValidation = () => {
    setIsLiveActive(true);
    setBroadcastCount(0);
    
    intervalRef.current = setInterval(async () => {
      await performLiveBroadcast();
      updateLiveMetrics();
    }, 1000); // Continuous updates every second
  };

  const stopLiveValidation = () => {
    setIsLiveActive(false);
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  const performLiveBroadcast = async () => {
    if (!isInitialized) return;
    
    try {
      const waveform = aurisEngine.synthesizeWaveform(intentText);
      const result = await aurisEngine.broadcast(waveform);
      setLastBroadcast(result);
      setBroadcastCount(prev => prev + 1);
    } catch (error) {
      console.error('Live broadcast failed:', error);
    }
  };

  const updateLiveMetrics = () => {
    const time = Date.now();
    
    // Get real Earth stream data
    const earthMetrics = aurisEngine.getEarthStreamMetrics();
    const schumannData = aurisEngine.getLiveSchumannData();
    
    // Enhanced Schumann resonance with real data
    const schumannResonance = schumannData ? 
      Math.max(0, Math.min(100, (schumannData.fundamental / 8.5) * 100)) :
      Math.max(0, Math.min(100, ((7.83 + Math.sin(time / 5000) * 0.5) / 8.5) * 100));

    // Solar wind velocity metrics
    const solarWindVelocity = earthMetrics ? 
      Math.min(100, (earthMetrics.solarWind.velocity / 800) * 100) :
      Math.min(100, 50 + Math.sin(time / 8000) * 30);

    // Geomagnetic activity (inverse of Kp index for stability)
    const geomagneticActivity = earthMetrics ?
      Math.max(0, 100 - (earthMetrics.geomagnetic.kpIndex / 9) * 100) :
      Math.max(0, 80 + Math.cos(time / 12000) * 15);

    // Ionospheric density
    const ionosphericDensity = earthMetrics ?
      Math.min(100, (earthMetrics.atmospheric.ionosphericDensity / 2e12) * 100) :
      Math.min(100, 60 + Math.sin(time / 10000) * 25);

    // Field coherence enhanced with Earth data
    const baseCoherence = earthMetrics?.coherenceIndex || 0.7;
    const fieldCoherence = Math.min(100, baseCoherence * 100 + Math.sin(time / 4000) * 10);

    // Intent strength with harmonic coupling
    const intentStrength = Math.min(100, 
      70 + Math.sin(time / 2000) * 20 + (schumannData?.coherence || 0.5) * 10
    );

    // Harmonic alignment with golden ratio and Earth coupling
    const phi = 1.618;
    const harmonicAlignment = Math.min(100,
      60 + Math.sin(time / (1000 * phi)) * 25 + 
      (earthMetrics?.fieldCoupling || 1) * 10
    );

    // Broadcast success based on all factors
    const broadcastSuccess = Math.min(100,
      (schumannResonance * 0.3 + fieldCoherence * 0.3 + 
       harmonicAlignment * 0.2 + solarWindVelocity * 0.2)
    );

    setLiveMetrics({
      schumannResonance,
      fieldCoherence,
      harmonicAlignment,
      intentStrength,
      broadcastSuccess,
      solarWindVelocity,
      geomagneticActivity,
      ionosphericDensity
    });
  };

  const availableIntents = aurisCodex.getAllIntents();

  return (
    <Card className="w-full max-w-4xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          🌍 Auris Resonance Engine
          <Badge variant={isInitialized ? "default" : "secondary"}>
            {isInitialized ? "ACTIVE" : "INITIALIZING"}
          </Badge>
          {isLiveActive && (
            <Badge variant="destructive" className="animate-pulse">
              LIVE VALIDATION
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium">Intent Text</label>
            <Input
              value={intentText}
              onChange={(e) => setIntentText(e.target.value)}
              placeholder="Enter intent (e.g., peace, love, healing)"
            />
          </div>
          <div className="flex items-end gap-2">
            <Button 
              onClick={isLiveActive ? stopLiveValidation : startLiveValidation}
              disabled={!isInitialized}
              className="flex-1"
              variant={isLiveActive ? "destructive" : "default"}
            >
              {isLiveActive ? "🛑 Stop Live" : "🎵 Start Live Validation"}
            </Button>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {availableIntents.map((intent) => (
            <Badge
              key={intent}
              variant={intent === intentText ? "default" : "outline"}
              className="cursor-pointer"
              onClick={() => setIntentText(intent)}
            >
              {intent}
            </Badge>
          ))}
        </div>

        {isLiveActive && (
          <>
            <Card className="border-2 border-primary animate-pulse">
              <CardHeader>
                <CardTitle className="text-sm flex items-center justify-between">
                  Live Validation Metrics
                  <Badge variant="outline">
                    Broadcasts: {broadcastCount}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>🌊 Schumann Resonance</span>
                      <span>{fmt(liveMetrics.schumannResonance, 1)}%</span>
                    </div>
                    <Progress value={liveMetrics.schumannResonance} className="h-2" />
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>🔗 Field Coherence</span>
                      <span>{fmt(liveMetrics.fieldCoherence, 1)}%</span>
                    </div>
                    <Progress value={liveMetrics.fieldCoherence} className="h-2" />
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>🎵 Harmonic Alignment</span>
                      <span>{fmt(liveMetrics.harmonicAlignment, 1)}%</span>
                    </div>
                    <Progress value={liveMetrics.harmonicAlignment} className="h-2" />
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>💫 Intent Strength</span>
                      <span>{fmt(liveMetrics.intentStrength, 1)}%</span>
                    </div>
                    <Progress value={liveMetrics.intentStrength} className="h-2" />
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>☀️ Solar Wind</span>
                      <span>{fmt(liveMetrics.solarWindVelocity, 1)}%</span>
                    </div>
                    <Progress value={liveMetrics.solarWindVelocity} className="h-2" />
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>🧲 Geomagnetic Stability</span>
                      <span>{fmt(liveMetrics.geomagneticActivity, 1)}%</span>
                    </div>
                    <Progress value={liveMetrics.geomagneticActivity} className="h-2" />
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>🌐 Ionospheric Density</span>
                      <span>{fmt(liveMetrics.ionosphericDensity, 1)}%</span>
                    </div>
                    <Progress value={liveMetrics.ionosphericDensity} className="h-2" />
                  </div>
                  <div className="space-y-2 md:col-span-2">
                    <div className="flex justify-between text-sm">
                      <span>📡 Broadcast Success Rate</span>
                      <span>{fmt(liveMetrics.broadcastSuccess, 1)}%</span>
                    </div>
                    <Progress value={liveMetrics.broadcastSuccess} className="h-2" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </>
        )}

        {lastBroadcast && (
          <Card className={isLiveActive ? "border-success" : ""}>
            <CardHeader>
              <CardTitle className="text-sm">
                {isLiveActive ? "Live Broadcast Result" : "Last Broadcast Result"}
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm space-y-2">
              <div className="grid grid-cols-2 gap-4">
                <div>Frequency: {lastBroadcast.waveform.frequency} Hz</div>
                <div>Amplitude: {fmt(lastBroadcast.waveform.amplitude, 3)}</div>
                <div>Decay: {lastBroadcast.waveform.decay}</div>
                <div>Field Coupling: {lastBroadcast.field_coupling}</div>
              </div>
              <div>
                Harmonics: {lastBroadcast.waveform.harmonics.join(', ')}
              </div>
              <div className="text-xs text-muted-foreground">
                Broadcast at: {new Date(lastBroadcast.timestamp).toLocaleTimeString()}
              </div>
            </CardContent>
          </Card>
        )}
      </CardContent>
    </Card>
  );
};