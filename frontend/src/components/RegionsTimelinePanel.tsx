import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Slider } from './ui/slider';
import { Badge } from './ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Play, Pause, SkipBack, SkipForward, Globe, Clock } from 'lucide-react';

export default function RegionsTimelinePanel() {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentFrame, setCurrentFrame] = useState([0]);
  const [selectedRegion, setSelectedRegion] = useState('global');
  const [timeWindow, setTimeWindow] = useState('24h');

  const regions = [
    { value: 'global', label: 'Global' },
    { value: 'north-america', label: 'North America' },
    { value: 'europe', label: 'Europe' },
    { value: 'asia-pacific', label: 'Asia Pacific' },
    { value: 'antarctica', label: 'Antarctica' }
  ];

  const timeWindows = [
    { value: '1h', label: '1 Hour' },
    { value: '6h', label: '6 Hours' },
    { value: '24h', label: '24 Hours' },
    { value: '7d', label: '7 Days' },
    { value: '30d', label: '30 Days' }
  ];

  return (
    <Card className="bg-black/40 border-primary/30">
      <CardHeader>
        <CardTitle className="text-primary flex items-center gap-2">
          <Globe className="w-5 h-5" />
          Regions & Timeline Playback
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Region Selection */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <div className="text-sm text-primary">Region</div>
            <Select value={selectedRegion} onValueChange={setSelectedRegion}>
              <SelectTrigger className="bg-black/60 border-primary/30">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-black border-primary/30">
                {regions.map(region => (
                  <SelectItem key={region.value} value={region.value}>
                    {region.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <div className="text-sm text-primary">Time Window</div>
            <Select value={timeWindow} onValueChange={setTimeWindow}>
              <SelectTrigger className="bg-black/60 border-primary/30">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-black border-primary/30">
                {timeWindows.map(window => (
                  <SelectItem key={window.value} value={window.value}>
                    {window.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Timeline Controls */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              className="border-primary/30"
              onClick={() => setCurrentFrame([Math.max(0, currentFrame[0] - 10)])}
            >
              <SkipBack className="w-4 h-4" />
            </Button>
            
            <Button
              size="sm"
              onClick={() => setIsPlaying(!isPlaying)}
              className={isPlaying ? 'bg-destructive hover:bg-destructive' : 'bg-primary hover:bg-primary'}
            >
              {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            </Button>
            
            <Button
              size="sm"
              variant="outline"
              className="border-primary/30"
              onClick={() => setCurrentFrame([Math.min(100, currentFrame[0] + 10)])}
            >
              <SkipForward className="w-4 h-4" />
            </Button>

            <div className="flex items-center gap-2 ml-auto">
              <Clock className="w-4 h-4 text-primary" />
              <span className="text-sm text-primary">
                Frame {currentFrame[0]}/100
              </span>
            </div>
          </div>

          <div className="space-y-2">
            <Slider
              value={currentFrame}
              onValueChange={setCurrentFrame}
              max={100}
              min={0}
              step={1}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-primary">
              <span>Start</span>
              <span>Current: {currentFrame[0]}%</span>
              <span>End</span>
            </div>
          </div>
        </div>

        {/* Current Status */}
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <div className="text-primary">Lock Quality</div>
            <Badge variant="default" className="bg-success">
              High
            </Badge>
          </div>
          <div>
            <div className="text-primary">Coherence Trend</div>
            <Badge variant="default" className="bg-primary">
              Rising
            </Badge>
          </div>
          <div>
            <div className="text-primary">Anomalies</div>
            <Badge variant="outline" className="border-warning text-warning">
              2 Detected
            </Badge>
          </div>
        </div>

        {/* Info Panel */}
        <div className="bg-primary/30 p-3 rounded-lg text-xs text-primary">
          <div className="font-semibold mb-1">Timeline Features:</div>
          <ul className="space-y-1 list-disc list-inside">
            <li>Geospatial window playback with regional focus</li>
            <li>Temporal analysis across multiple time scales</li>
            <li>Lock improvement detection and anomaly flagging</li>
            <li>Frame-by-frame coherence pattern analysis</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}