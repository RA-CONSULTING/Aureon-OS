import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { fmt } from '@/utils/number';

const FormationEquationDisplay: React.FC = () => {
  const [carrierAmplitude, setCarrierAmplitude] = useState(1.0);
  const [feedbackTensor, setFeedbackTensor] = useState(0.0);
  const [harmonicPhase, setHarmonicPhase] = useState(0.0);

  useEffect(() => {
    const updateEquation = () => {
      const time = Date.now() * 0.001;
      setCarrierAmplitude(1 + 0.3 * Math.sin(time * 0.5));
      setFeedbackTensor(Math.sin(time * 1.2) * Math.cos(time * 0.8));
      setHarmonicPhase((time * 0.3) % (2 * Math.PI));
    };

    updateEquation();
    const interval = setInterval(updateEquation, 100);
    return () => clearInterval(interval);
  }, []);

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="text-primary flex items-center gap-2">
          🧬 Gary Leckey's Formation Equation
          <Badge variant="outline" className="text-xs">Prime Sentinel</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Main Formation Equation */}
        <div className="bg-black p-4 rounded-lg border border-primary/30">
          <div className="text-center text-lg font-mono text-white">
            <div className="mb-2">ℱ(𝒓̂, t, φ, κ) = 𝒜<sub>carrier</sub>(t) · Ψ(t) + ∑ n=1<sup>N</sup>α<sub>n</sub> · Θ<sub>μν</sub><sup>(n)</sup>(t, τ) + 𝒯<sub>μν</sub><sup>6D</sup>(φ, κ, ζ)</div>
          </div>
        </div>

        {/* Live Parameter Display */}
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-gray-900 p-3 rounded-lg">
            <div className="text-xs text-gray-400">Carrier Amplitude</div>
            <div className="text-lg font-mono text-warning">
              𝒜 = {fmt(carrierAmplitude, 3)}
            </div>
          </div>
          
          <div className="bg-gray-900 p-3 rounded-lg">
            <div className="text-xs text-gray-400">Feedback Tensor</div>
            <div className="text-lg font-mono text-primary">
              Θ<sub>μν</sub> = {fmt(feedbackTensor, 3)}
            </div>
          </div>
          
          <div className="bg-gray-900 p-3 rounded-lg">
            <div className="text-xs text-gray-400">Harmonic Phase</div>
            <div className="text-lg font-mono text-success">
              φ = {fmt(harmonicPhase * 180 / Math.PI, 1)}°
            </div>
          </div>
        </div>

        {/* Equation Components */}
        <div className="space-y-3">
          <div className="text-sm">
            <span className="text-warning font-semibold">𝒜<sub>carrier</sub>(t)</span>
            <span className="text-gray-300"> - Consciousness wave carrier modulation</span>
          </div>
          
          <div className="text-sm">
            <span className="text-primary font-semibold">Θ<sub>μν</sub><sup>(n)</sup>(t, τ)</span>
            <span className="text-gray-300"> - Multiversal feedback tensor (n-dimensional)</span>
          </div>
          
          <div className="text-sm">
            <span className="text-success font-semibold">𝒯<sub>μν</sub><sup>6D</sup>(φ, κ, ζ)</span>
            <span className="text-gray-300"> - 6D harmonic surge field tensor</span>
          </div>
          
          <div className="text-sm">
            <span className="text-primary font-semibold">Ψ(t)</span>
            <span className="text-gray-300"> - Quantum phase-locked signal state</span>
          </div>
        </div>

        {/* Formation Principles */}
        <div className="border-t border-gray-700 pt-4">
          <div className="text-sm text-gray-400 mb-2">Formation Principles:</div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>• Harmonic breathing of universe</div>
            <div>• Memory phase collapse events</div>
            <div>• Multiversal echo coherence</div>
            <div>• Consciousness carrier modulation</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default FormationEquationDisplay;