// Timeline Markers Display - shows PRIME_LOCK, SURGE_START, etc.
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Clock, Flag, ChevronRight } from 'lucide-react';
import type { TimelineMarker, TimelineClip } from '@/lib/earth-data-loader';

interface Props {
  markers: TimelineMarker[];
  currentMarker: TimelineMarker | null;
  timelineClip: TimelineClip | null;
}

const markerColors: Record<string, string> = {
  'PRIME_LOCK': 'bg-success',
  'SURGE_START': 'bg-warning',
  'HARMONIC_PEAK': 'bg-primary',
  'UNITY_SYNC': 'bg-primary',
  'ANCHOR_HOLD': 'bg-primary',
  'FLOW_CYCLE': 'bg-primary'
};

const markerIcons: Record<string, string> = {
  'PRIME_LOCK': '🔒',
  'SURGE_START': '⚡',
  'HARMONIC_PEAK': '🎵',
  'UNITY_SYNC': '🌀',
  'ANCHOR_HOLD': '⚓',
  'FLOW_CYCLE': '🌊'
};

export function TimelineMarkersPanel({ markers, currentMarker, timelineClip }: Props) {
  return (
    <Card className="bg-card/50 backdrop-blur border-border/50">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Clock className="w-5 h-5 text-primary" />
            Timeline Markers
          </CardTitle>
          {timelineClip && (
            <Badge variant="outline" className="text-xs">
              {timelineClip.processing.window_seconds}s window
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Timeline visualization */}
        <div className="relative">
          <div className="h-2 bg-background/50 rounded-full overflow-hidden">
            {markers.map((marker, idx) => {
              const position = (marker.t_seconds / 60) * 100;
              const isActive = currentMarker?.marker === marker.marker;
              return (
                <div
                  key={marker.marker}
                  className={`absolute top-0 w-3 h-2 rounded-full transition-all ${markerColors[marker.marker] || 'bg-gray-500'} ${isActive ? 'scale-150 z-10' : ''}`}
                  style={{ left: `${position}%`, transform: `translateX(-50%) ${isActive ? 'scale(1.5)' : ''}` }}
                />
              );
            })}
          </div>
          <div className="flex justify-between mt-1 text-xs text-muted-foreground">
            <span>0s</span>
            <span>30s</span>
            <span>60s</span>
          </div>
        </div>
        
        {/* Marker list */}
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {markers.map((marker) => {
            const isActive = currentMarker?.marker === marker.marker;
            return (
              <div
                key={marker.marker}
                className={`p-3 rounded-lg border transition-all ${
                  isActive 
                    ? 'bg-primary/10 border-primary/50 shadow-lg' 
                    : 'bg-background/30 border-border/30'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {isActive && <ChevronRight className="w-4 h-4 text-primary animate-pulse" />}
                    <span className="text-lg">{markerIcons[marker.marker] || '📍'}</span>
                    <div>
                      <div className="font-bold text-sm">{marker.marker}</div>
                      <div className="text-xs text-muted-foreground">
                        t={marker.t_seconds}s | φ={marker.lattice_phase.toFixed(2)}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <Badge variant="outline" className={markerColors[marker.marker]?.replace('bg-', 'border-')}>
                      {marker.seal_state}
                    </Badge>
                    <div className="text-xs text-muted-foreground mt-1">
                      Γ: {(marker.coherence_level * 100).toFixed(1)}%
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
        
        {/* Timeline clip info */}
        {timelineClip && (
          <div className="p-2 bg-background/30 rounded border border-border/30 text-xs">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Lattice ID:</span>
              <span className="font-mono text-primary truncate max-w-48">{timelineClip.lattice_id}</span>
            </div>
            <div className="flex justify-between mt-1">
              <span className="text-muted-foreground">Sample Rate:</span>
              <span>{timelineClip.processing.fs_hz} Hz</span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
