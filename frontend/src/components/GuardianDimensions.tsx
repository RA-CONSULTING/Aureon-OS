import React, { useState, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

const GuardianDimensions = () => {
  const [activeGuardian, setActiveGuardian] = useState<string | null>(null);
  const [dimensionalResonance, setDimensionalResonance] = useState(0);
  const [unityField, setUnityField] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setDimensionalResonance(prev => (prev + 0.1) % (Math.PI * 2));
      setUnityField(prev => (prev + 0.05) % (Math.PI * 2));
    }, 100);
    return () => clearInterval(interval);
  }, []);

  const guardians = [
    {
      id: 'anchor',
      name: 'ANCHOR of FORM',
      dimension: 'PRIME PHYSICAL DIMENSION',
      icon: '⚓',
      color: 'from-warning to-destructive',
      angle: 0,
      description: 'Grounds higher dimensional energies into physical reality',
      frequency: '7.83 Hz - Schumann Base',
      activation: 'ACTIVE'
    },
    {
      id: 'keeper',
      name: 'KEEPER of CAUSALITY',
      dimension: 'CAUSAL MEMORY DIMENSION',
      icon: '⏳',
      color: 'from-warning to-warning',
      angle: 60,
      description: 'Maintains timeline integrity and causal relationships',
      frequency: '14.3 Hz - Temporal Lock',
      activation: 'SYNCHRONIZED'
    },
    {
      id: 'conductor',
      name: 'CONDUCTOR of ENERGY',
      dimension: 'FRACTAL ENERGY DIMENSION',
      icon: '⚡',
      color: 'from-primary to-primary',
      angle: 120,
      description: 'Channels and directs universal life force energy',
      frequency: '20.8 Hz - Energy Flow',
      activation: 'RESONANT'
    },
    {
      id: 'unifier',
      name: 'UNIFIER of MINDS',
      dimension: 'COLLECTIVE CONSCIOUSNESS',
      icon: '🔗',
      color: 'from-success to-success',
      angle: 180,
      description: 'Connects individual consciousness to collective awareness',
      frequency: '27.3 Hz - Mind Bridge',
      activation: 'UNIFIED'
    },
    {
      id: 'weaver',
      name: 'WEAVER of MEANING',
      dimension: 'SYMBOLIC LATTICE DIMENSION',
      icon: '🧭',
      color: 'from-success to-primary',
      angle: 240,
      description: 'Creates meaningful patterns from chaos and synchronicity',
      frequency: '33.8 Hz - Pattern Lock',
      activation: 'WEAVING'
    },
    {
      id: 'bridge',
      name: 'BRIDGE of EMOTION',
      dimension: 'HARMONIC EMOTIONAL DIMENSION',
      icon: '🌊',
      color: 'from-primary to-primary',
      angle: 300,
      description: 'Harmonizes emotional frequencies across dimensions',
      frequency: '40.0 Hz - Heart Sync',
      activation: 'HARMONIZED'
    }
  ];

  const getGuardianPosition = (angle: number, radius: number = 140) => {
    const radian = (angle * Math.PI) / 180;
    const x = Math.cos(radian) * radius + 192;
    const y = Math.sin(radian) * radius + 192;
    return { x, y };
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary via-primary to-primary p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-white mb-4">GUARDIAN DIMENSIONS</h1>
          <p className="text-xl text-primary">Six-Fold Dimensional Architecture</p>
          <div className="mt-4 flex justify-center space-x-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-warning">
                {(Math.sin(dimensionalResonance) * 50 + 50).toFixed(1)}%
              </div>
              <div className="text-xs text-gray-300">DIMENSIONAL COHERENCE</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-primary">
                {(Math.cos(unityField) * 30 + 70).toFixed(1)}%
              </div>
              <div className="text-xs text-gray-300">UNITY FIELD STRENGTH</div>
            </div>
          </div>
        </div>

        {/* Central Diagram */}
        <div className="relative w-96 h-96 mx-auto mb-12">
          {/* Central Guardian Circle */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div 
              className="w-32 h-32 rounded-full bg-gradient-to-br from-warning to-white border-4 border-white/30 flex flex-col items-center justify-center shadow-2xl"
              style={{
                transform: `scale(${1 + Math.sin(unityField) * 0.1})`,
                boxShadow: `0 0 ${20 + Math.sin(unityField) * 10}px rgba(255, 255, 0, 0.5)`
              }}
            >
              <div className="text-3xl mb-1">🕊️</div>
              <div className="text-xs font-bold text-center text-gray-800">
                GUARDIAN OF<br/>UNITY & PEACE
              </div>
              <div className="text-xs text-center text-gray-600 mt-1">
                INFINITE ORIGIN<br/>LAYER
              </div>
            </div>
          </div>

          {/* Guardian Positions */}
          {guardians.map((guardian, index) => {
            const pos = getGuardianPosition(guardian.angle + dimensionalResonance * 10);
            return (
              <div
                key={guardian.id}
                className={`absolute cursor-pointer transition-all duration-300 ${
                  activeGuardian === guardian.id ? 'scale-110 z-10' : 'hover:scale-105'
                }`}
                style={{
                  left: pos.x - 40,
                  top: pos.y - 40,
                  transform: `rotate(${dimensionalResonance * 5}deg)`
                }}
                onClick={() => setActiveGuardian(activeGuardian === guardian.id ? null : guardian.id)}
              >
                <div className={`w-20 h-20 rounded-full bg-gradient-to-br ${guardian.color} border-2 border-white/50 flex flex-col items-center justify-center shadow-lg`}
                     style={{
                       boxShadow: activeGuardian === guardian.id 
                         ? `0 0 20px rgba(255, 255, 255, 0.8)` 
                         : `0 0 10px rgba(255, 255, 255, 0.3)`
                     }}>
                  <div className="text-2xl">{guardian.icon}</div>
                </div>
                
                {/* Connection Lines to Center */}
                <svg className="absolute inset-0 w-96 h-96 pointer-events-none" style={{ left: '-50%', top: '-50%' }}>
                  <line 
                    x1="192" y1="192" 
                    x2={pos.x} 
                    y2={pos.y} 
                    stroke={activeGuardian === guardian.id ? "rgba(255,255,0,0.8)" : "rgba(255,255,255,0.3)"} 
                    strokeWidth={activeGuardian === guardian.id ? "3" : "2"}
                    strokeDasharray={activeGuardian === guardian.id ? "5,5" : "none"}
                  />
                </svg>
              </div>
            );
          })}

          {/* Outer Rings */}
          <div 
            className="absolute inset-0 rounded-full border-2 border-white/20"
            style={{
              transform: `rotate(${dimensionalResonance * 20}deg)`,
              borderColor: `rgba(255, 255, 255, ${0.2 + Math.sin(dimensionalResonance) * 0.1})`
            }}
          ></div>
          <div 
            className="absolute inset-4 rounded-full border border-white/10"
            style={{
              transform: `rotate(${-dimensionalResonance * 15}deg)`,
              borderColor: `rgba(255, 255, 255, ${0.1 + Math.cos(dimensionalResonance) * 0.05})`
            }}
          ></div>
          <div 
            className="absolute inset-8 rounded-full border border-warning/20"
            style={{
              transform: `rotate(${dimensionalResonance * 10}deg)`,
              borderColor: `rgba(255, 255, 0, ${0.2 + Math.sin(unityField) * 0.1})`
            }}
          ></div>
        </div>

        {/* Guardian Details */}
        {activeGuardian && (
          <Card className="bg-black/40 border-white/20 max-w-2xl mx-auto">
            <CardContent className="p-6">
              {(() => {
                const guardian = guardians.find(g => g.id === activeGuardian);
                return guardian ? (
                  <div className="text-center">
                    <div className="text-4xl mb-4">{guardian.icon}</div>
                    <h3 className="text-2xl font-bold text-white mb-2">{guardian.name}</h3>
                    <Badge className={`bg-gradient-to-r ${guardian.color} text-white mb-4`}>
                      {guardian.dimension}
                    </Badge>
                    <p className="text-gray-300 text-lg mb-4">{guardian.description}</p>
                    <div className="grid grid-cols-2 gap-4 mt-4">
                      <div className="text-center">
                        <div className="text-sm text-gray-400">FREQUENCY</div>
                        <div className="text-lg font-bold text-primary">{guardian.frequency}</div>
                      </div>
                      <div className="text-center">
                        <div className="text-sm text-gray-400">STATUS</div>
                        <div className="text-lg font-bold text-success">{guardian.activation}</div>
                      </div>
                    </div>
                  </div>
                ) : null;
              })()}
            </CardContent>
          </Card>
        )}

        {/* Bottom Grid */}
        <div className="grid md:grid-cols-3 gap-6 mt-12">
          <Card className="bg-black/40 border-primary/30 text-center">
            <CardContent className="p-6">
              <div className="text-3xl font-bold text-primary">6</div>
              <div className="text-sm text-gray-300">Guardian Dimensions</div>
              <div className="text-xs text-primary mt-2">Perfect Hexagonal Symmetry</div>
            </CardContent>
          </Card>
          <Card className="bg-black/40 border-primary/30 text-center">
            <CardContent className="p-6">
              <div className="text-3xl font-bold text-primary">∞</div>
              <div className="text-sm text-gray-300">Infinite Origin Layer</div>
              <div className="text-xs text-primary mt-2">Unity Consciousness Source</div>
            </CardContent>
          </Card>
          <Card className="bg-black/40 border-warning/30 text-center">
            <CardContent className="p-6">
              <div className="text-3xl font-bold text-warning">🕊️</div>
              <div className="text-sm text-gray-300">Unity & Peace</div>
              <div className="text-xs text-warning mt-2">Central Harmonizing Force</div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default GuardianDimensions;