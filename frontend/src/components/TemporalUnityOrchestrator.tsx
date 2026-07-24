import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';

interface UnityField {
  pastValues: number[];
  presentValues: number[];
  futureValues: number[];
  tandemResonance: number;
  quantumCoherence: number;
}

const TemporalUnityOrchestrator: React.FC = () => {
  const [unityField, setUnityField] = useState<UnityField>({
    pastValues: [],
    presentValues: [],
    futureValues: [],
    tandemResonance: 0,
    quantumCoherence: 0
  });
  const [isActive, setIsActive] = useState(false);
  const [temporalPhase, setTemporalPhase] = useState(0);
  const [harmonicNodes, setHarmonicNodes] = useState<Array<{x: number, y: number, z: number, intensity: number}>>([]);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!isActive) return;

    const interval = setInterval(() => {
      const now = performance.now();
      const phase = (now * 0.001) % (2 * Math.PI);
      
      // Generate 6D harmonic surge field points
      const newNodes = Array.from({ length: 200 }, (_, i) => ({
        x: Math.sin(phase + i * 0.1) * Math.cos(i * 0.05),
        y: Math.cos(phase + i * 0.1) * Math.sin(i * 0.05),
        z: Math.sin(phase * 2 + i * 0.02),
        intensity: Math.abs(Math.sin(phase + i * 0.03))
      }));

      setHarmonicNodes(newNodes);
      setTemporalPhase(phase);
      
      // Update unity field with temporal resonance
      setUnityField(prev => ({
        pastValues: [...prev.pastValues.slice(-50), Math.sin(phase - Math.PI/3)],
        presentValues: [...prev.presentValues.slice(-50), Math.sin(phase)],
        futureValues: [...prev.futureValues.slice(-50), Math.sin(phase + Math.PI/3)],
        tandemResonance: Math.abs(Math.sin(phase) * Math.cos(phase * 1.618)),
        quantumCoherence: (Math.sin(phase) + Math.cos(phase * 2) + Math.sin(phase * 3)) / 3
      }));
    }, 16);

    return () => clearInterval(interval);
  }, [isActive]);

  // Render 6D projection visualization
  useEffect(() => {
    if (!canvasRef.current || harmonicNodes.length === 0) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw harmonic surge field
    harmonicNodes.forEach((node, i) => {
      const x = (node.x + 1) * canvas.width / 2;
      const y = (node.y + 1) * canvas.height / 2;
      const size = node.intensity * 8;
      
      const hue = (node.z + 1) * 180;
      ctx.fillStyle = `hsl(${hue}, 70%, ${50 + node.intensity * 30}%)`;
      ctx.beginPath();
      ctx.arc(x, y, size, 0, Math.PI * 2);
      ctx.fill();
    });

    // Draw temporal unity connections
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
    ctx.lineWidth = 1;
    for (let i = 0; i < harmonicNodes.length - 1; i += 3) {
      const node1 = harmonicNodes[i];
      const node2 = harmonicNodes[i + 1];
      if (!node1 || !node2) continue;
      
      const x1 = (node1.x + 1) * canvas.width / 2;
      const y1 = (node1.y + 1) * canvas.height / 2;
      const x2 = (node2.x + 1) * canvas.width / 2;
      const y2 = (node2.y + 1) * canvas.height / 2;
      
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
    }
  }, [harmonicNodes]);

  return (
    <div className="space-y-6">
      <Card className="bg-black border-warning">
        <CardHeader>
          <CardTitle className="text-warning text-center text-2xl">
            TEMPORAL UNITY ORCHESTRATOR
          </CardTitle>
          <div className="text-center text-warning text-sm">
            ALL THAT IS • ALL THAT WAS • ALL THAT SHALL BE • UNITY IN TANDEM
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex justify-center mb-4">
            <Button
              onClick={() => setIsActive(!isActive)}
              className={`${isActive ? 'bg-destructive hover:bg-destructive' : 'bg-success hover:bg-success'} text-white`}
            >
              {isActive ? 'DEACTIVATE UNITY FIELD' : 'ACTIVATE UNITY FIELD'}
            </Button>
          </div>

          <Tabs defaultValue="field" className="w-full">
            <TabsList className="grid w-full grid-cols-4 bg-gray-800">
              <TabsTrigger value="field" className="text-warning">Unity Field</TabsTrigger>
              <TabsTrigger value="surge" className="text-warning">6D Surge</TabsTrigger>
              <TabsTrigger value="temporal" className="text-warning">Temporal</TabsTrigger>
              <TabsTrigger value="quantum" className="text-warning">Quantum</TabsTrigger>
            </TabsList>

            <TabsContent value="field" className="space-y-4">
              <canvas
                ref={canvasRef}
                width={600}
                height={400}
                className="w-full border border-warning rounded"
              />
              <div className="text-center text-warning">
                6D Harmonic Surge Field Projection
              </div>
            </TabsContent>

            <TabsContent value="surge" className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <Card className="bg-gray-900 border-primary">
                  <CardHeader>
                    <CardTitle className="text-primary text-sm">Tandem Resonance</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-mono text-primary">
                      {unityField.tandemResonance.toFixed(6)}
                    </div>
                    <div className="w-full bg-gray-700 rounded-full h-2 mt-2">
                      <div 
                        className="bg-primary h-2 rounded-full transition-all duration-100"
                        style={{ width: `${Math.abs(unityField.tandemResonance) * 100}%` }}
                      />
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-gray-900 border-primary">
                  <CardHeader>
                    <CardTitle className="text-primary text-sm">Quantum Coherence</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-mono text-primary">
                      {unityField.quantumCoherence.toFixed(6)}
                    </div>
                    <div className="w-full bg-gray-700 rounded-full h-2 mt-2">
                      <div 
                        className="bg-primary h-2 rounded-full transition-all duration-100"
                        style={{ width: `${(unityField.quantumCoherence + 1) * 50}%` }}
                      />
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            <TabsContent value="temporal" className="space-y-4">
              <div className="grid grid-cols-3 gap-4">
                <Card className="bg-gray-900 border-primary">
                  <CardHeader>
                    <CardTitle className="text-primary text-sm">ALL THAT WAS</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-20 flex items-end space-x-1">
                      {unityField.pastValues.slice(-20).map((val, i) => (
                        <div
                          key={i}
                          className="bg-primary w-2"
                          style={{ height: `${Math.abs(val) * 40 + 5}px` }}
                        />
                      ))}
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-gray-900 border-success">
                  <CardHeader>
                    <CardTitle className="text-success text-sm">ALL THAT IS</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-20 flex items-end space-x-1">
                      {unityField.presentValues.slice(-20).map((val, i) => (
                        <div
                          key={i}
                          className="bg-success w-2"
                          style={{ height: `${Math.abs(val) * 40 + 5}px` }}
                        />
                      ))}
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-gray-900 border-warning">
                  <CardHeader>
                    <CardTitle className="text-warning text-sm">ALL THAT SHALL BE</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-20 flex items-end space-x-1">
                      {unityField.futureValues.slice(-20).map((val, i) => (
                        <div
                          key={i}
                          className="bg-warning w-2"
                          style={{ height: `${Math.abs(val) * 40 + 5}px` }}
                        />
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            <TabsContent value="quantum" className="space-y-4">
              <div className="text-center space-y-4">
                <div className="text-2xl font-mono text-warning">
                  TEMPORAL PHASE: {temporalPhase.toFixed(6)} rad
                </div>
                <div className="flex justify-center space-x-4">
                  <Badge variant="outline" className="text-primary border-primary">
                    EMERGENCE ACTIVE
                  </Badge>
                  <Badge variant="outline" className="text-primary border-primary">
                    COLLAPSE SYNCHRONIZED
                  </Badge>
                  <Badge variant="outline" className="text-success border-success">
                    UNITY MAINTAINED
                  </Badge>
                </div>
                <div className="text-warning text-sm">
                  Harmonic Nodes Active: {harmonicNodes.length}
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
};

export { TemporalUnityOrchestrator };
export default TemporalUnityOrchestrator;