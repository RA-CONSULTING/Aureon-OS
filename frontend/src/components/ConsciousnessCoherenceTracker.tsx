import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Brain, Heart, Activity, Sparkles, Wifi, WifiOff } from "lucide-react";
import { useSchumannResonance } from "@/hooks/useSchumannResonance";
import { useCelestialData } from "@/hooks/useCelestialData";
import { useBiometricSensors } from "@/hooks/useBiometricSensors";
import { useConsciousnessHistory } from "@/hooks/useConsciousnessHistory";
import { useSentinelConfig } from "@/hooks/useSentinelConfig";
import { useEffect, useRef } from "react";

interface ConsciousnessCoherenceTrackerProps {
  currentCoherence: number;
}

export function ConsciousnessCoherenceTracker({ currentCoherence }: ConsciousnessCoherenceTrackerProps) {
  const { config } = useSentinelConfig();
  const { schumannData, isConnected: schumannConnected } = useSchumannResonance();
  const { celestialBoost } = useCelestialData();
  const { biometricData, isConnected: biometricConnected } = useBiometricSensors();
  const { saveDataPoint } = useConsciousnessHistory();
  const lastSaveTime = useRef<number>(0);

  // Calculate total consciousness field coherence
  const schumannBoost = schumannData?.coherenceBoost || 0;
  const totalBoost = celestialBoost + schumannBoost;
  const enhancedCoherence = currentCoherence * (1 + totalBoost);

  // Use real biometric data from sensors when available
  const hrv = biometricData?.hrv || 45 + (schumannBoost * 200);
  const alpha = biometricData?.alpha || 0.4 + (celestialBoost * 2);
  const theta = biometricData?.theta || 0.3 + (schumannBoost * 1.5);
  const heartRate = biometricData?.heartRate || 72;

  const getCoherenceLevel = (coherence: number) => {
    if (coherence >= 0.9) return { level: 'TRANSCENDENT', color: 'text-primary', bg: 'bg-primary/20' };
    if (coherence >= 0.7) return { level: 'PEAK', color: 'text-success', bg: 'bg-success/20' };
    if (coherence >= 0.5) return { level: 'ELEVATED', color: 'text-primary', bg: 'bg-primary/20' };
    if (coherence >= 0.3) return { level: 'ACTIVE', color: 'text-warning', bg: 'bg-warning/20' };
    return { level: 'FORMING', color: 'text-warning', bg: 'bg-warning/20' };
  };

  const coherenceStatus = getCoherenceLevel(enhancedCoherence);

  // Save data point every 5 minutes
  useEffect(() => {
    const now = Date.now();
    const fiveMinutes = 5 * 60 * 1000;
    
    if (schumannData && now - lastSaveTime.current >= fiveMinutes) {
      saveDataPoint(schumannData, biometricData, celestialBoost, enhancedCoherence);
      lastSaveTime.current = now;
    }
  }, [schumannData, biometricData, celestialBoost, enhancedCoherence, saveDataPoint]);

  return (
    <Card className="bg-card/50 backdrop-blur border-border/50 relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-primary/5 to-success/5" />
      
      <CardHeader className="relative">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Brain className="w-5 h-5 text-primary" />
              Consciousness Field Coherence
            </CardTitle>
            <CardDescription>
              {config ? `Prime Sentinel: ${config.sentinel_name}` : 'Multi-dimensional consciousness alignment tracking'}
            </CardDescription>
          </div>
          <Badge className={`${coherenceStatus.color} ${coherenceStatus.bg} border-0 text-lg px-4 py-2`}>
            {coherenceStatus.level}
          </Badge>
        </div>
        
        {/* Sensor Status Bar */}
        <div className="flex items-center gap-4 mt-4 p-3 bg-background/50 rounded-lg border border-border/50">
          <div className="flex items-center gap-2">
            <Activity className={`w-4 h-4 ${schumannConnected ? 'text-success' : 'text-destructive'}`} />
            <span className="text-xs font-medium">
              Schumann: {schumannConnected ? 'ONLINE' : 'OFFLINE'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Heart className={`w-4 h-4 ${biometricConnected ? 'text-success' : 'text-destructive'}`} />
            <span className="text-xs font-medium">
              Biometrics: {biometricConnected ? 'ONLINE' : 'OFFLINE'}
            </span>
          </div>
        </div>
      </CardHeader>

      <CardContent className="relative space-y-4">
        {/* Main Coherence Display */}
        <div className="flex items-center justify-center p-6 bg-gradient-to-br from-primary/10 to-primary/10 rounded-lg border border-border/50">
          <div className="text-center">
            <div className="flex items-center justify-center gap-2 mb-2">
              <Sparkles className="w-6 h-6 text-primary" />
              <span className="text-sm text-muted-foreground font-medium">Total Field Coherence</span>
            </div>
            <div className="text-5xl font-bold bg-gradient-to-r from-primary to-primary bg-clip-text text-transparent">
              {(enhancedCoherence * 100).toFixed(2)}%
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              Base: {(currentCoherence * 100).toFixed(2)}% • Boost: +{(totalBoost * 100).toFixed(1)}%
            </div>
          </div>
        </div>

        {/* Boost Sources */}
        <div className="grid grid-cols-2 gap-4">
          <div className={`p-4 bg-background/50 rounded-lg border ${schumannConnected ? 'border-success/30' : 'border-border/50'}`}>
            <div className="flex items-center gap-2 mb-2">
              <Activity className={`w-4 h-4 ${schumannConnected ? 'text-success' : 'text-muted-foreground'}`} />
              <span className="text-xs text-muted-foreground">Schumann Boost</span>
              {schumannConnected && <Wifi className="w-3 h-3 text-success ml-auto" />}
              {!schumannConnected && <WifiOff className="w-3 h-3 text-destructive ml-auto" />}
            </div>
            <div className={`text-2xl font-bold ${schumannConnected ? 'text-success' : 'text-muted-foreground'}`}>
              +{(schumannBoost * 100).toFixed(1)}%
            </div>
            <Progress value={(schumannBoost / 0.12) * 100} className="mt-2 h-1" />
            <p className="text-xs text-muted-foreground mt-1">
              {schumannData?.fundamentalHz.toFixed(2) || '—'} Hz
            </p>
          </div>

          <div className="p-4 bg-background/50 rounded-lg border border-border/50">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="w-4 h-4 text-primary" />
              <span className="text-xs text-muted-foreground">Celestial Boost</span>
            </div>
            <div className="text-2xl font-bold text-primary">+{(celestialBoost * 100).toFixed(1)}%</div>
            <Progress value={(celestialBoost / 0.15) * 100} className="mt-2 h-1" />
            <p className="text-xs text-muted-foreground mt-1">
              Cosmic alignment
            </p>
          </div>
        </div>

        {/* Real Biometric Indicators */}
        <div className="p-4 bg-muted/50 rounded-lg">
          <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <Heart className="w-4 h-4 text-destructive" />
            Consciousness Biometrics
            {biometricConnected ? (
              <Wifi className="w-3 h-3 text-success ml-auto" />
            ) : (
              <WifiOff className="w-3 h-3 text-muted-foreground ml-auto" />
            )}
          </h4>
          
          <div className="grid grid-cols-4 gap-3">
            <div className="text-center">
              <div className="text-xs text-muted-foreground mb-1">HRV</div>
              <div className="text-lg font-bold">{hrv.toFixed(0)}</div>
              <div className="text-xs text-success">ms</div>
            </div>
            
            <div className="text-center">
              <div className="text-xs text-muted-foreground mb-1">HR</div>
              <div className="text-lg font-bold">{heartRate}</div>
              <div className="text-xs text-destructive">BPM</div>
            </div>
            
            <div className="text-center">
              <div className="text-xs text-muted-foreground mb-1">Alpha</div>
              <div className="text-lg font-bold">{(alpha * 100).toFixed(0)}%</div>
              <div className="text-xs text-primary">8-13 Hz</div>
            </div>
            
            <div className="text-center">
              <div className="text-xs text-muted-foreground mb-1">Theta</div>
              <div className="text-lg font-bold">{(theta * 100).toFixed(0)}%</div>
              <div className="text-xs text-primary">4-8 Hz</div>
            </div>
          </div>

          {!biometricConnected && (
            <div className="mt-3 p-2 bg-destructive/10 border border-destructive/30 rounded text-xs text-destructive">
              ⚠️ Biometric sensors disconnected. Connect HRV monitor and EEG headset to ws://localhost:8788/biometrics
            </div>
          )}
        </div>

        {/* Connection Warnings */}
        {!schumannConnected && (
          <div className="p-4 bg-destructive/10 border border-destructive/30 rounded-lg">
            <p className="text-sm text-destructive font-medium">
              ⚠️ Schumann Resonance sensor offline. Connect to Earth Live Data server at ws://localhost:8787/schumann
            </p>
          </div>
        )}

        {schumannConnected && biometricConnected && (
          <div className="p-4 bg-success/10 border border-success/30 rounded-lg">
            <p className="text-sm text-success font-medium">
              ✅ All Earth Live Data sensors online and streaming real-time consciousness field data
            </p>
          </div>
        )}

        {/* Coherence Level Descriptions */}
        <div className="p-4 bg-muted/50 rounded-lg">
          <h4 className="text-sm font-semibold mb-2">Coherence Levels</h4>
          <ul className="text-xs text-muted-foreground space-y-1">
            <li>• <strong className="text-primary">Transcendent (90%+)</strong>: Unity consciousness, optimal trading</li>
            <li>• <strong className="text-success">Peak (70-89%)</strong>: High alignment, LHE probability elevated</li>
            <li>• <strong className="text-primary">Elevated (50-69%)</strong>: Strong coherence, good signal quality</li>
            <li>• <strong className="text-warning">Active (30-49%)</strong>: Building coherence, monitor closely</li>
            <li>• <strong className="text-warning">Forming (&lt;30%)</strong>: Low coherence, wait for alignment</li>
          </ul>
        </div>

        {/* Real-time Insights */}
        {enhancedCoherence >= 0.9 && (
          <div className="p-4 bg-primary/10 border border-primary/30 rounded-lg">
            <p className="text-sm text-primary font-medium">
              ⚡ Transcendent consciousness coherence achieved! Earth resonance, celestial alignments, 
              and field dynamics are in perfect harmony. Optimal window for high-confidence trades.
            </p>
          </div>
        )}

        <div className="pt-2 border-t border-border/50">
          <p className="text-xs text-muted-foreground text-center">
            Real-time consciousness field monitoring • Schumann Resonance • Celestial Alignment
          </p>
        </div>
      </CardContent>
    </Card>
  );
}