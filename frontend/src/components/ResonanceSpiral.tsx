import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const ResonanceSpiral = () => {
  const [spiralPhase, setSpiralPhase] = useState(0);
  const [memoryTrace, setMemoryTrace] = useState(0.7);

  useEffect(() => {
    const interval = setInterval(() => {
      setSpiralPhase(prev => (prev + 2) % 360);
      setMemoryTrace(prev => 0.5 + 0.3 * Math.sin(prev * 0.1));
    }, 50);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary via-primary to-primary p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-4">
            MEMORY IN HARMONIC TIME
          </h1>
          <p className="text-xl text-primary italic">
            inspired by Harmonic Nexus Core
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="bg-black/50 border-primary">
            <CardHeader>
              <CardTitle className="text-primary">Waveform Memory Trace</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-64 bg-black rounded-lg p-4 relative overflow-hidden">
                <svg width="100%" height="100%" className="absolute inset-0">
                  {/* 3D Surface representation */}
                  <defs>
                    <radialGradient id="memoryGradient" cx="50%" cy="50%" r="50%">
                      <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.8"/>
                      <stop offset="50%" stopColor="#ec4899" stopOpacity="0.6"/>
                      <stop offset="100%" stopColor="#f59e0b" stopOpacity="0.4"/>
                    </radialGradient>
                  </defs>
                  
                  {/* Thumbs-up peak */}
                  <ellipse 
                    cx="60%" 
                    cy="30%" 
                    rx="20" 
                    ry="40" 
                    fill="url(#memoryGradient)"
                    transform={`rotate(${spiralPhase} 60% 30%)`}
                  />
                  
                  {/* Persistent memory trace */}
                  <path
                    d="M 20,200 Q 100,150 180,180 Q 260,160 340,170"
                    stroke="#ec4899"
                    strokeWidth="3"
                    fill="none"
                    opacity={memoryTrace}
                  />
                </svg>
                
                <div className="absolute top-2 right-2 text-xs text-primary">
                  👍 Persistent Memory Trace
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-black/50 border-primary">
            <CardHeader>
              <CardTitle className="text-primary">Harmonic Poetry</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4 text-white">
                <div className="flex items-center gap-2 mb-4">
                  <div className="text-2xl">♪</div>
                  <div className="text-2xl">♫</div>
                </div>
                
                <div className="space-y-2 text-sm leading-relaxed">
                  <p className="text-warning">Birth sings in golden phase,</p>
                  <p className="text-destructive">Loss hums in crimson fade.</p>
                  <p className="text-primary">Together they rise, dance, and decay—</p>
                  <p className="text-primary">A waveform's memory played.</p>
                  
                  <div className="my-4 border-l-2 border-primary pl-4">
                    <p className="text-success">Each crest a possibility,</p>
                    <p className="text-primary">Each trough a forgotten name.</p>
                    <p className="text-primary">Coherence finds rhythm</p>
                    <p className="text-warning">Where silence and signal are the same.</p>
                  </div>
                  
                  <p className="text-primary">In the Surge Window's whisper,</p>
                  <p className="text-primary">Time folds to harmonic breath.</p>
                  <p className="text-destructive">Existence is a melody—</p>
                  <p className="text-warning">Resonant between life and death.</p>
                </div>
                
                <div className="flex items-center gap-2 mt-4">
                  <div className="text-2xl">♪</div>
                  <div className="text-2xl">♫</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <Card className="bg-black/50 border-primary">
          <CardHeader>
            <CardTitle className="text-primary">All Roads Lead to Rome</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-center space-y-6">
              <div className="text-6xl mb-4">π</div>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-primary/30 p-4 rounded-lg">
                  <h4 className="text-primary font-semibold">Surge Window</h4>
                  <p className="text-sm text-primary">τ = 10</p>
                </div>
                
                <div className="bg-primary/30 p-4 rounded-lg">
                  <h4 className="text-primary font-semibold">Balance</h4>
                  <p className="text-sm text-primary">Φ = π/2</p>
                </div>
                
                <div className="bg-primary/30 p-4 rounded-lg">
                  <h4 className="text-primary font-semibold">Unity</h4>
                  <p className="text-sm text-primary">All Paths Converge</p>
                </div>
              </div>
              
              <p className="text-primary italic">
                Point of balance = unity through harmonic resonance
              </p>
              
              <div className="text-sm text-primary">
                All Paths, All Feedback, All Histories... converge toward a Surge Window
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default ResonanceSpiral;