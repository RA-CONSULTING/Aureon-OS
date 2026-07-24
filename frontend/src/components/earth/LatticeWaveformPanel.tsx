// Raw Sensor Waveform Display (Ex, Ey, Bx, By, Bz)
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Zap, Magnet } from 'lucide-react';
import type { LatticeTimeseries } from '@/lib/earth-data-loader';

interface Props {
  currentLattice: LatticeTimeseries | null;
  magneticField: {
    Bx: number;
    By: number;
    Bz: number;
    magnitude: number;
  } | null;
  electricField: {
    Ex: number;
    Ey: number;
    magnitude: number;
  } | null;
}

export function LatticeWaveformPanel({ currentLattice, magneticField, electricField }: Props) {
  if (!currentLattice) {
    return (
      <Card className="bg-card/50 border-border/50">
        <CardContent className="flex items-center justify-center h-48">
          <div className="text-muted-foreground animate-pulse">Loading lattice data...</div>
        </CardContent>
      </Card>
    );
  }
  
  return (
    <Card className="bg-card/50 backdrop-blur border-border/50">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Magnet className="w-5 h-5 text-primary" />
            Lattice Sensor Array
          </CardTitle>
          <Badge variant="outline">
            Station: {currentLattice.station_id || 'GAIA-UK-01'}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Electric Field */}
        <div className="p-3 bg-background/50 rounded-lg border border-warning/30">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="w-4 h-4 text-warning" />
            <span className="text-sm font-semibold">Electric Field</span>
            <span className="text-xs text-muted-foreground ml-auto">V/m</span>
          </div>
          <div className="grid grid-cols-3 gap-2">
            <div className="p-2 bg-background/30 rounded text-center">
              <div className="text-xs text-muted-foreground">Ex</div>
              <div className="text-lg font-bold text-warning">{currentLattice.Ex.toFixed(4)}</div>
            </div>
            <div className="p-2 bg-background/30 rounded text-center">
              <div className="text-xs text-muted-foreground">Ey</div>
              <div className="text-lg font-bold text-warning">{currentLattice.Ey.toFixed(4)}</div>
            </div>
            <div className="p-2 bg-warning/20 rounded text-center border border-warning/30">
              <div className="text-xs text-warning">|E|</div>
              <div className="text-lg font-bold text-warning">
                {electricField?.magnitude.toFixed(4) || '0'}
              </div>
            </div>
          </div>
        </div>
        
        {/* Magnetic Field */}
        <div className="p-3 bg-background/50 rounded-lg border border-primary/30">
          <div className="flex items-center gap-2 mb-2">
            <Magnet className="w-4 h-4 text-primary" />
            <span className="text-sm font-semibold">Magnetic Field</span>
            <span className="text-xs text-muted-foreground ml-auto">pT</span>
          </div>
          <div className="grid grid-cols-4 gap-2">
            <div className="p-2 bg-background/30 rounded text-center">
              <div className="text-xs text-muted-foreground">Bx</div>
              <div className="text-lg font-bold text-primary">{currentLattice.Bx.toFixed(2)}</div>
            </div>
            <div className="p-2 bg-background/30 rounded text-center">
              <div className="text-xs text-muted-foreground">By</div>
              <div className="text-lg font-bold text-primary">{currentLattice.By.toFixed(2)}</div>
            </div>
            <div className="p-2 bg-background/30 rounded text-center">
              <div className="text-xs text-muted-foreground">Bz</div>
              <div className="text-lg font-bold text-primary">{currentLattice.Bz.toFixed(2)}</div>
            </div>
            <div className="p-2 bg-primary/20 rounded text-center border border-primary/30">
              <div className="text-xs text-primary">|B|</div>
              <div className="text-lg font-bold text-primary">
                {magneticField?.magnitude.toFixed(2) || '0'}
              </div>
            </div>
          </div>
        </div>
        
        {/* Metadata */}
        <div className="grid grid-cols-3 gap-2 text-xs">
          <div className="p-2 bg-background/30 rounded text-center">
            <div className="text-muted-foreground">Gain</div>
            <div className="font-bold">{currentLattice.gain}</div>
          </div>
          <div className="p-2 bg-background/30 rounded text-center">
            <div className="text-muted-foreground">QF</div>
            <div className="font-bold">{currentLattice.qf}</div>
          </div>
          <div className="p-2 bg-background/30 rounded text-center">
            <div className="text-muted-foreground">GPS</div>
            <div className="font-bold text-success">SYNC</div>
          </div>
        </div>
        
        <div className="text-xs text-muted-foreground text-center">
          {currentLattice.timestamp_utc}
        </div>
      </CardContent>
    </Card>
  );
}
