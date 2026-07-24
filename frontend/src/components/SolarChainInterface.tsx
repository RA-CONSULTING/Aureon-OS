import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { SolarHarmonicsEngine, PLANETS, Planet } from '@/lib/solar-harmonics';

interface SolarChainInterfaceProps {
  onChainUpdate?: (chain: string[]) => void;
}

export default function SolarChainInterface({ onChainUpdate }: SolarChainInterfaceProps) {
  const [engine] = useState(() => new SolarHarmonicsEngine());
  const [selectedPlanets, setSelectedPlanets] = useState<string[]>([]);
  const [isPlaying, setIsPlaying] = useState(false);
  const [resonanceMatrix, setResonanceMatrix] = useState<Map<string, number>>(new Map());

  useEffect(() => {
    engine.initialize();
    calculateResonanceMatrix();
  }, []);

  useEffect(() => {
    onChainUpdate?.(selectedPlanets);
  }, [selectedPlanets, onChainUpdate]);

  const calculateResonanceMatrix = () => {
    const matrix = new Map<string, number>();
    for (let i = 0; i < PLANETS.length; i++) {
      for (let j = i + 1; j < PLANETS.length; j++) {
        const key = `${PLANETS[i].name}-${PLANETS[j].name}`;
        const resonance = engine.calculateResonance(PLANETS[i].name, PLANETS[j].name);
        matrix.set(key, resonance);
      }
    }
    setResonanceMatrix(matrix);
  };

  const togglePlanet = (planetName: string) => {
    setSelectedPlanets(prev => {
      if (prev.includes(planetName)) {
        return prev.filter(p => p !== planetName);
      } else {
        return [...prev, planetName];
      }
    });
  };

  const playChain = async () => {
    if (selectedPlanets.length === 0) return;
    
    setIsPlaying(true);
    await engine.playChain(selectedPlanets, 400);
    
    setTimeout(() => setIsPlaying(false), selectedPlanets.length * 400 + 3000);
  };

  const clearChain = () => {
    setSelectedPlanets([]);
    setIsPlaying(false);
  };

  const playHarmonicSeries = (rootPlanet: string) => {
    const series = engine.getHarmonicSeries(rootPlanet);
    const planetNames = series.slice(0, 5).map(p => p.name);
    setSelectedPlanets(planetNames);
    setTimeout(() => engine.playChain(planetNames, 300), 100);
  };

  const getResonanceStrength = (planet1: string, planet2: string): number => {
    const key1 = `${planet1}-${planet2}`;
    const key2 = `${planet2}-${planet1}`;
    return resonanceMatrix.get(key1) || resonanceMatrix.get(key2) || 0;
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>🌟 Solar Chain Interface</span>
          <div className="flex gap-2">
            <Button 
              onClick={playChain} 
              disabled={selectedPlanets.length === 0 || isPlaying}
              className="bg-gradient-to-r from-primary to-primary"
            >
              {isPlaying ? 'Playing...' : 'Play Chain'}
            </Button>
            <Button onClick={clearChain} variant="outline">
              Clear
            </Button>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Planet Selection Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {PLANETS.map((planet) => {
            const isSelected = selectedPlanets.includes(planet.name);
            const chainIndex = selectedPlanets.indexOf(planet.name);
            
            return (
              <div
                key={planet.name}
                onClick={() => togglePlanet(planet.name)}
                className={`
                  relative cursor-pointer p-3 rounded-lg border-2 transition-all duration-200
                  ${isSelected 
                    ? 'border-primary bg-primary shadow-lg scale-105' 
                    : 'border-gray-200 hover:border-primary hover:shadow-md'
                  }
                `}
              >
                <div className="flex items-center space-x-2">
                  <div 
                    className="w-4 h-4 rounded-full shadow-sm"
                    style={{ backgroundColor: planet.color }}
                  />
                  <div className="flex-1">
                    <div className="font-semibold text-sm">{planet.name}</div>
                    <div className="text-xs text-gray-600">{planet.freq} Hz</div>
                  </div>
                </div>
                {isSelected && (
                  <Badge 
                    className="absolute -top-2 -right-2 bg-primary text-white"
                    variant="default"
                  >
                    {chainIndex + 1}
                  </Badge>
                )}
              </div>
            );
          })}
        </div>

        {/* Chain Display */}
        {selectedPlanets.length > 0 && (
          <div className="p-4 bg-gradient-to-r from-primary to-primary rounded-lg">
            <h3 className="font-semibold mb-2">Active Chain:</h3>
            <div className="flex flex-wrap gap-2">
              {selectedPlanets.map((planet, index) => (
                <div key={`${planet}-${index}`} className="flex items-center">
                  <Badge variant="secondary" className="bg-primary">
                    {planet}
                  </Badge>
                  {index < selectedPlanets.length - 1 && (
                    <span className="mx-2 text-primary">→</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Quick Harmonic Series */}
        <div className="space-y-2">
          <h3 className="font-semibold">Quick Harmonic Series:</h3>
          <div className="flex flex-wrap gap-2">
            {['Earth', 'Jupiter', 'Saturn'].map(planet => (
              <Button
                key={planet}
                onClick={() => playHarmonicSeries(planet)}
                variant="outline"
                size="sm"
                className="text-xs"
              >
                {planet} Series
              </Button>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}