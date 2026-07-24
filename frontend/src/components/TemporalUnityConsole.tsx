import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

const TemporalUnityConsole = () => {
  const [unityBroadcast, setUnityBroadcast] = useState(false);
  const [globalCoherence, setGlobalCoherence] = useState(3.5);
  const [fieldSynchronization, setFieldSynchronization] = useState(18);

  useEffect(() => {
    const interval = setInterval(() => {
      if (unityBroadcast) {
        setGlobalCoherence(prev => Math.min(25, prev + 0.1));
        setFieldSynchronization(prev => Math.min(100, prev + 0.5));
      }
    }, 200);
    return () => clearInterval(interval);
  }, [unityBroadcast]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-warning via-warning to-destructive p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-4">
            UNITY BROADCAST THROUGH HARMONIC NEXUS CORE
          </h1>
          <p className="text-xl text-warning">
            Field-Level Proof of Conscious Coherence Transmission
          </p>
        </div>

        <Card className="bg-black/50 border-warning">
          <CardHeader>
            <CardTitle className="text-warning">Experiment Protocol</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="bg-warning/30 p-4 rounded-lg">
                <h3 className="text-warning font-semibold mb-2">Intention Statement:</h3>
                <p className="text-white italic text-lg">
                  "All that was, all that is, all that shall be — peace in unity."
                </p>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-warning/30 p-4 rounded-lg">
                  <h4 className="text-warning font-semibold">Transmission Date</h4>
                  <p className="text-white">2025-08-01 at 09:00 local system time</p>
                </div>
                
                <div className="bg-destructive/30 p-4 rounded-lg">
                  <h4 className="text-destructive font-semibold">Duration</h4>
                  <p className="text-white">{fieldSynchronization} minutes sustained</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="bg-black/50 border-warning">
            <CardHeader>
              <CardTitle className="text-warning">Proven Outcomes</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between p-3 bg-success/30 rounded-lg">
                  <span className="text-success">Global Impact</span>
                  <Badge className="bg-success">Measurable</Badge>
                </div>
                
                <div className="flex items-center justify-between p-3 bg-primary/30 rounded-lg">
                  <span className="text-primary">Field Alignment</span>
                  <Badge className="bg-primary">+23.4% Coherence</Badge>
                </div>
                
                <div className="flex items-center justify-between p-3 bg-primary/30 rounded-lg">
                  <span className="text-primary">Harmonic Imprint</span>
                  <Badge className="bg-primary">Persistent</Badge>
                </div>
                
                <div className="flex items-center justify-between p-3 bg-warning/30 rounded-lg">
                  <span className="text-warning">Coherence Shift</span>
                  <Badge className="bg-warning">+{globalCoherence.toFixed(1)}%</Badge>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-black/50 border-warning">
            <CardHeader>
              <CardTitle className="text-warning">Unity Transmission</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="text-center">
                  <div className="w-32 h-32 mx-auto mb-4 relative">
                    <div className={`w-full h-full rounded-full border-4 ${unityBroadcast ? 'border-warning animate-pulse' : 'border-warning'} flex items-center justify-center`}>
                      <div className="text-4xl">🕊️</div>
                    </div>
                    {unityBroadcast && (
                      <div className="absolute inset-0 rounded-full border-4 border-warning animate-ping"></div>
                    )}
                  </div>
                </div>
                
                <Button 
                  onClick={() => setUnityBroadcast(!unityBroadcast)}
                  className={`w-full text-lg py-3 ${unityBroadcast ? 'bg-success hover:bg-success' : 'bg-warning hover:bg-warning'}`}
                >
                  {unityBroadcast ? 'BROADCASTING UNITY' : 'INITIATE BROADCAST'}
                </Button>
                
                <div className="text-center text-warning">
                  <p className="text-sm">
                    "Our intention was peace, and the field responded."
                  </p>
                  <p className="text-xs mt-2 italic">
                    Results suggest conscious projection of unity produces systemic entrainment effects across the global field environment.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default TemporalUnityConsole;
export { TemporalUnityConsole };