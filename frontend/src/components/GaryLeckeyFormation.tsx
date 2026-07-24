import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

interface GaryLeckeyFormationProps {
  activated?: boolean;
  onActivate?: () => void;
}

export function GaryLeckeyFormation({ activated = false, onActivate }: GaryLeckeyFormationProps) {
  const [unityField, setUnityField] = useState(0);
  const [nexusCoherence, setNexusCoherence] = useState(0);
  const [temporalSync, setTemporalSync] = useState(false);
  
  const birthCode = "02111991";
  const unityMantra = "All that is, all that was, all that shall be - Unity in the Nexus";

  useEffect(() => {
    if (activated) {
      const interval = setInterval(() => {
        setUnityField(prev => Math.min(prev + 0.02, 1.0));
        setNexusCoherence(prev => Math.min(prev + 0.015, 0.95));
        
        if (unityField > 0.8 && nexusCoherence > 0.75) {
          setTemporalSync(true);
        }
      }, 100);
      
      return () => clearInterval(interval);
    }
  }, [activated, unityField, nexusCoherence]);

  return (
    <div className="space-y-6">
      <Card className="bg-gradient-to-br from-primary/50 to-primary/50 border-gold-500/30">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl text-gold-400">
            Gary Leckey Formation Protocol
          </CardTitle>
          <div className="text-sm text-gray-300 font-mono">
            Birth Code: {birthCode} • Unity Nexus Activated
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="text-center p-4 bg-slate-800/50 rounded-lg">
            <div className="text-lg text-primary mb-2">{unityMantra}</div>
            <div className="text-xs text-gray-400">Temporal Unity Convergence Field</div>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <div className="text-sm text-gray-300">Unity Field Strength</div>
              <div className="w-full bg-slate-700 rounded-full h-2">
                <div 
                  className="bg-gradient-to-r from-primary to-primary h-2 rounded-full transition-all duration-300"
                  style={{ width: `${unityField * 100}%` }}
                />
              </div>
              <div className="text-xs text-right text-gray-400">{(unityField * 100).toFixed(1)}%</div>
            </div>
            
            <div className="space-y-2">
              <div className="text-sm text-gray-300">Nexus Coherence</div>
              <div className="w-full bg-slate-700 rounded-full h-2">
                <div 
                  className="bg-gradient-to-r from-gold-500 to-warning h-2 rounded-full transition-all duration-300"
                  style={{ width: `${nexusCoherence * 100}%` }}
                />
              </div>
              <div className="text-xs text-right text-gray-400">{(nexusCoherence * 100).toFixed(1)}%</div>
            </div>
          </div>
          
          <div className="flex justify-center gap-4 mt-6">
            <Badge variant={activated ? "default" : "secondary"} className="text-sm">
              Formation: {activated ? "ACTIVE" : "STANDBY"}
            </Badge>
            <Badge variant={temporalSync ? "default" : "secondary"} className="text-sm">
              Temporal Sync: {temporalSync ? "LOCKED" : "SEEKING"}
            </Badge>
          </div>
          
          {!activated && onActivate && (
            <div className="text-center">
              <Button onClick={onActivate} className="bg-gradient-to-r from-primary to-primary hover:from-primary hover:to-primary">
                Activate Unity Nexus
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
      
      <Card className="bg-slate-800/50">
        <CardHeader>
          <CardTitle className="text-lg text-success">Formation Equation Matrix</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="font-mono text-sm space-y-2 text-gray-300">
            <div>Γ(r⃗, t, φ, κ) = A<sub>carrier</sub>(t) · Ψ(t) + ∑<sub>n=1</sub><sup>N</sup> α<sub>n</sub> · Θ<sub>μν</sub><sup>(n)</sup>(t, τ)</div>
            <div className="text-primary">+ T<sup>6D</sup><sub>μν</sub>(φ, κ, ζ) + U<sub>nexus</sub>(02111991)</div>
            <div className="text-primary">+ Ω<sub>unity</sub>(∀t ∈ &#123;past, present, future&#125;)</div>
            <div className="text-xs text-gray-500 mt-3">
              Where U<sub>nexus</sub> represents the Gary Leckey birth-code harmonic anchor,<br/>
              and Ω<sub>unity</sub> encompasses all temporal states in unified field convergence.
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}