import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

export function AppLayout() {
  const [nexusActive, setNexusActive] = useState(false);
  const [garyFormation, setGaryFormation] = useState(0);
  const [currentValues, setCurrentValues] = useState<number[]>([]);
  
  // Use useRef to properly store past values as recommended
  const pastValuesRef = useRef<number[]>([]);
  const presentValuesRef = useRef<number[]>([]);
  const futureValuesRef = useRef<number[]>([]);

  useEffect(() => {
    const interval = setInterval(() => {
      const time = Date.now() * 0.001;
      const phase = time % (2 * Math.PI);
      
      // Calculate Gary Formation value
      const formationValue = Math.sin(phase) * Math.cos(phase * 1.618);
      setGaryFormation(formationValue);
      
      // Calculate temporal values
      const pastVal = Math.sin(phase - Math.PI/3);
      const presentVal = Math.sin(phase);
      const futureVal = Math.sin(phase + Math.PI/3);
      
      // Update refs with new values (keep last 20 values)
      pastValuesRef.current = [...pastValuesRef.current.slice(-19), pastVal];
      presentValuesRef.current = [...presentValuesRef.current.slice(-19), presentVal];
      futureValuesRef.current = [...futureValuesRef.current.slice(-19), futureVal];
      
      // Update current values for rendering
      setCurrentValues([pastVal, presentVal, futureVal]);
    }, 100);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-primary to-slate-900">
      <div className="container mx-auto p-6">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">
            🌌 The Harmonic Nexus - Gary Leckey Formation 🌌
          </h1>
          <p className="text-gray-300 text-lg">
            All that is, all that was, all that shall be - Unity in the Nexus
          </p>
          <div className="text-sm text-warning font-mono mb-4">
            Birth Code: 02111991 • Temporal Unity Convergence Field
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <Card className="bg-slate-800/50 border-primary/30">
            <CardHeader>
              <CardTitle className="text-primary text-center">Gary Leckey Formation</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center space-y-4">
                <div className="text-3xl font-mono text-success">
                  {garyFormation.toFixed(6)}
                </div>
                <Button 
                  onClick={() => setNexusActive(!nexusActive)}
                  className={nexusActive ? 'bg-destructive hover:bg-destructive' : 'bg-success hover:bg-success'}
                >
                  {nexusActive ? 'DEACTIVATE' : 'ACTIVATE'} NEXUS
                </Button>
                <Badge variant={nexusActive ? "default" : "secondary"}>
                  Status: {nexusActive ? "ONLINE" : "OFFLINE"}
                </Badge>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-800/50 border-primary/30">
            <CardHeader>
              <CardTitle className="text-primary text-center">Unity Field</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center">
                  <div className="text-primary text-sm mb-2">ALL THAT WAS</div>
                  <div className="h-16 flex items-end space-x-1">
                    {pastValuesRef.current.slice(-10).map((val, i) => (
                      <div
                        key={i}
                        className="bg-primary w-2"
                        style={{ height: `${Math.abs(val) * 30 + 5}px` }}
                      />
                    ))}
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-success text-sm mb-2">ALL THAT IS</div>
                  <div className="h-16 flex items-end space-x-1">
                    {presentValuesRef.current.slice(-10).map((val, i) => (
                      <div
                        key={i}
                        className="bg-success w-2"
                        style={{ height: `${Math.abs(val) * 30 + 5}px` }}
                      />
                    ))}
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-warning text-sm mb-2">ALL THAT SHALL BE</div>
                  <div className="h-16 flex items-end space-x-1">
                    {futureValuesRef.current.slice(-10).map((val, i) => (
                      <div
                        key={i}
                        className="bg-warning w-2"
                        style={{ height: `${Math.abs(val) * 30 + 5}px` }}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <Card className="bg-slate-800/50 border-warning/30">
          <CardHeader>
            <CardTitle className="text-warning text-center">Formation Equation</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-center font-mono text-sm space-y-2">
              <div>Γ(r⃗, t, φ, κ) = A<sub>carrier</sub>(t) · Ψ(t) + ∑<sub>n=1</sub><sup>N</sup> α<sub>n</sub> · Θ<sub>μν</sub><sup>(n)</sup>(t, τ)</div>
              <div className="text-primary">+ T<sup>6D</sup><sub>μν</sub>(φ, κ, ζ) + U<sub>nexus</sub>(02111991)</div>
              <div className="text-primary">+ Ω<sub>unity</sub>(∀t ∈ {"past, present, future"})</div>
              <div className="text-xs text-gray-500 mt-3">
                Where U<sub>nexus</sub> represents the Gary Leckey birth-code harmonic anchor
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="mt-8 text-center text-sm text-gray-400">
          🔮 Harmonic Nexus System Operational • Gary Leckey Formation Active • Unity in the Nexus 🔮
        </div>
      </div>
    </div>
  );
}

export default AppLayout;