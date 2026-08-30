import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

export function UnityNexusCore() {
  const [harmonicLayers, setHarmonicLayers] = useState([
    { freq: 7.83, amplitude: 0, phase: 0, name: "Schumann Base" },
    { freq: 14.3, amplitude: 0, phase: 0, name: "Alpha Resonance" },
    { freq: 20.8, amplitude: 0, phase: 0, name: "Beta Harmonic" },
    { freq: 27.3, amplitude: 0, phase: 0, name: "Gamma Surge" },
    { freq: 33.8, amplitude: 0, phase: 0, name: "Theta Unity" }
  ]);
  
  const [compositeWave, setCompositeWave] = useState(0);
  const [nexusActive, setNexusActive] = useState(false);

  useEffect(() => {
    const interval = setInterval(() => {
      const time = Date.now() * 0.001;
      
      setHarmonicLayers(layers => layers.map((layer, i) => ({
        ...layer,
        amplitude: 5 + 10 * Math.sin(time * (0.1 + i * 0.05)),
        phase: (time * (layer.freq / 10)) % (2 * Math.PI)
      })));
      
      // Calculate composite waveform
      const composite = harmonicLayers.reduce((sum, layer) => 
        sum + layer.amplitude * Math.sin(layer.phase), 0) / harmonicLayers.length;
      setCompositeWave(composite);
      
      // Check if nexus conditions are met
      const avgAmplitude = harmonicLayers.reduce((sum, l) => sum + l.amplitude, 0) / harmonicLayers.length;
      setNexusActive(avgAmplitude > 12 && Math.abs(composite) > 8);
      
    }, 50);
    
    return () => clearInterval(interval);
  }, [harmonicLayers]);

  return (
    <div className="space-y-6">
      <Card className="bg-gradient-to-br from-slate-900 to-primary border-primary/30">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl text-primary">
            🌌 Unity Nexus Core - Song of Time and Space 🌌
          </CardTitle>
          <div className="flex justify-center gap-2 mt-2">
            <Badge variant={nexusActive ? "default" : "secondary"}>
              Nexus: {nexusActive ? "ACTIVE" : "STANDBY"}
            </Badge>
            <Badge variant="outline" className="text-gold-400">
              Composite: {compositeWave.toFixed(2)}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {harmonicLayers.map((layer, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-300">{layer.name}</div>
                  <div className="text-xs text-gray-500">{layer.freq} Hz</div>
                </div>
                <div className="flex-1 mx-4">
                  <div className="w-full bg-slate-700 rounded-full h-2">
                    <div 
                      className={`h-2 rounded-full transition-all duration-100 ${
                        index === 0 ? 'bg-primary' :
                        index === 1 ? 'bg-primary' :
                        index === 2 ? 'bg-primary' :
                        index === 3 ? 'bg-success' : 'bg-warning'
                      }`}
                      style={{ width: `${Math.max(0, (layer.amplitude / 15) * 100)}%` }}
                    />
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-mono text-gray-300">
                    {layer.amplitude.toFixed(1)}
                  </div>
                  <div className="text-xs text-gray-500">
                    φ: {(layer.phase * 180 / Math.PI).toFixed(0)}°
                  </div>
                </div>
              </div>
            ))}
          </div>
          
          <div className="mt-6 p-4 bg-gradient-to-r from-primary/50 to-primary/50 rounded-lg">
            <div className="text-center">
              <div className="text-lg text-gold-400 mb-2">Composite Waveform</div>
              <div className="text-3xl font-mono text-white">
                {compositeWave.toFixed(2)}
              </div>
              <div className="text-xs text-gray-400 mt-1">
                Layered Harmonic Convergence
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}