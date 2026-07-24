import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Slider } from './ui/slider';
import { Badge } from './ui/badge';
import { Zap, Shield, AlertTriangle, CheckCircle } from 'lucide-react';

export default function PrimeSurgeControls() {
  const [surgeActive, setSurgeActive] = useState(false);
  const [surgeIntensity, setSurgeIntensity] = useState([1.0]);
  const [primeAlignment, setPrimeAlignment] = useState(0.85);
  const [guardRails, setGuardRails] = useState(true);

  const handleSurgeToggle = () => {
    if (!surgeActive) {
      setSurgeActive(true);
      // Auto-disable after 30 seconds
      setTimeout(() => setSurgeActive(false), 30000);
    } else {
      setSurgeActive(false);
    }
  };

  return (
    <Card className="bg-black/40 border-primary/30">
      <CardHeader>
        <CardTitle className="text-primary flex items-center gap-2">
          <Zap className="w-5 h-5" />
          Prime & Surge Windows
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Prime Alignment Status */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <div className="text-sm text-primary">Prime Alignment</div>
            <div className="flex items-center gap-2">
              <div className={`text-2xl font-mono ${primeAlignment >= 0.8 ? 'text-success' : primeAlignment >= 0.6 ? 'text-warning' : 'text-destructive'}`}>
                {primeAlignment.toFixed(3)}
              </div>
              {primeAlignment >= 0.8 && <CheckCircle className="w-5 h-5 text-success" />}
            </div>
          </div>
          
          <div className="space-y-2">
            <div className="text-sm text-primary">Phase Ordering</div>
            <Badge variant={primeAlignment >= 0.75 ? "default" : "destructive"} className="bg-primary">
              {primeAlignment >= 0.75 ? "Stable" : "Unstable"}
            </Badge>
          </div>
        </div>

        {/* Surge Controls */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="text-sm text-primary">Surge Window</div>
            <div className="flex items-center gap-2">
              <Shield className={`w-4 h-4 ${guardRails ? 'text-success' : 'text-destructive'}`} />
              <span className="text-xs text-primary">
                {guardRails ? 'Guards Active' : 'Guards Off'}
              </span>
            </div>
          </div>
          
          <div className="space-y-2">
            <div className="text-xs text-primary">Surge Intensity</div>
            <Slider
              value={surgeIntensity}
              onValueChange={setSurgeIntensity}
              max={3.0}
              min={0.5}
              step={0.1}
              className="w-full"
              disabled={surgeActive}
            />
            <div className="text-xs text-primary text-center">
              {surgeIntensity[0].toFixed(1)}x
            </div>
          </div>

          <Button
            onClick={handleSurgeToggle}
            className={`w-full ${surgeActive ? 'bg-destructive hover:bg-destructive' : 'bg-primary hover:bg-primary'}`}
            disabled={primeAlignment < 0.6}
          >
            {surgeActive ? (
              <>
                <AlertTriangle className="w-4 h-4 mr-2" />
                Stop Surge
              </>
            ) : (
              <>
                <Zap className="w-4 h-4 mr-2" />
                Initiate Surge
              </>
            )}
          </Button>
          
          {primeAlignment < 0.6 && (
            <div className="text-xs text-warning text-center">
              Prime alignment too low for surge activation
            </div>
          )}
        </div>

        {/* Safety Info */}
        <div className="bg-primary/30 p-3 rounded-lg text-xs text-primary">
          <div className="font-semibold mb-1">Safety Notes:</div>
          <ul className="space-y-1 list-disc list-inside">
            <li>Surges auto-terminate after 30 seconds</li>
            <li>Guard rails prevent spectral corruption</li>
            <li>Prime alignment ≥0.6 required for activation</li>
            <li>Monitor TSV gain to avoid clipping</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}