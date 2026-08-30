import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import SolarChainInterface from './SolarChainInterface';
import { PLANETS, SolarHarmonicsEngine } from '@/lib/solar-harmonics';

export default function SolarResonanceAtlas() {
  const [engine] = useState(() => new SolarHarmonicsEngine());
  const [activeChain, setActiveChain] = useState<string[]>([]);
  const [isLiveMode, setIsLiveMode] = useState(false);

  useEffect(() => {
    engine.initialize();
  }, []);

  const handleChainUpdate = (chain: string[]) => {
    setActiveChain(chain);
  };

  const toggleLiveMode = () => {
    setIsLiveMode(!isLiveMode);
    if (!isLiveMode && activeChain.length > 0) {
      // Start continuous harmonic broadcasting
      engine.playChain(activeChain, 1000);
    }
  };

  return (
    <div className="w-full space-y-6">
      {/* Hero Section */}
      <Card className="relative overflow-hidden">
        <div 
          className="absolute inset-0 bg-cover bg-center opacity-20"
          style={{ 
            backgroundImage: 'url(https://d64gsuwffb70l.cloudfront.net/68b21f0dd6dab352ff4244ca_1756649026707_936b5eca.webp)' 
          }}
        />
        <CardHeader className="relative z-10 text-center">
          <CardTitle className="text-2xl font-bold bg-gradient-to-r from-primary to-primary bg-clip-text text-transparent">
            🌟 Solar Resonance Atlas — Harmonic Nexus Charter
          </CardTitle>
          <p className="text-gray-600 mt-2">Chain link the solar system and play its music through the Lattice Nexus Live</p>
          <div className="flex justify-center gap-4 mt-4">
            <Button 
              onClick={toggleLiveMode}
              className={`${isLiveMode ? 'bg-success' : 'bg-primary'} text-white`}
            >
              {isLiveMode ? '🔴 LIVE' : '▶️ Go Live'}
            </Button>
            {activeChain.length > 0 && (
              <Badge variant="secondary" className="px-3 py-1">
                {activeChain.length} Planets Chained
              </Badge>
            )}
          </div>
        </CardHeader>
      </Card>

      {/* Solar Chain Interface */}
      <SolarChainInterface onChainUpdate={handleChainUpdate} />

      {/* Planetary Data Grid */}
      <Card>
        <CardHeader>
          <CardTitle>Planetary Harmonic Registry</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {PLANETS.map((planet, idx) => (
              <div key={idx} className="flex items-center space-x-3 p-3 rounded-lg border hover:shadow-md transition-shadow">
                <div 
                  className="w-4 h-4 rounded-full shadow-sm"
                  style={{ backgroundColor: planet.color }}
                />
                <div className="flex-1">
                  <div className="font-semibold">{planet.name}: {planet.freq} Hz</div>
                  <div className="text-sm text-gray-600">{planet.note} — {planet.desc}</div>
                  <div className="text-xs text-gray-500">
                    {planet.distance} AU • {planet.orbitalPeriod} days • Ratio: {planet.harmonicRatio}
                  </div>
                </div>
                {activeChain.includes(planet.name) && (
                  <Badge className="bg-primary text-primary">
                    #{activeChain.indexOf(planet.name) + 1}
                  </Badge>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Harmonic Nexus Charter */}
      <Card>
        <CardHeader>
          <CardTitle>Harmonic Nexus Charter Articles</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 text-sm">
            <div className="p-3 bg-warning rounded border-l-4 border-warning">
              <strong>Article I — Gaia Fields:</strong> Each celestial body resonates with its unique harmonic signature, contributing to the cosmic symphony.
            </div>
            <div className="p-3 bg-primary rounded border-l-4 border-primary">
              <strong>Article II — Forces in the Hum:</strong> Gravitational, electromagnetic, and quantum forces create harmonic interference patterns across space-time.
            </div>
            <div className="p-3 bg-primary rounded border-l-4 border-primary">
              <strong>Article III — Cosmic Chord:</strong> The Solar System functions as a vast musical instrument, with planetary orbits as strings and solar wind as the bow.
            </div>
            <div className="p-3 bg-success rounded border-l-4 border-success">
              <strong>Article IV — Breath & Fold:</strong> Resonance drift represents the cosmic breath, expanding and contracting through dimensional folds.
            </div>
            <div className="p-3 bg-destructive rounded border-l-4 border-destructive">
              <strong>Article V — Unity:</strong> Universal harmony emerges from the equation: U = Source × Resonance × Observer, binding all consciousness.
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}