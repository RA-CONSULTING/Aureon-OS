import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface HarmonicTier {
  name: string;
  frequency: number;
  tier: string;
  attribute: string;
  effect: string;
  color?: string;
}

interface HarmonicTierDisplayProps {
  primeFrequencies: Record<string, HarmonicTier>;
  shadowFrequencies: Record<string, HarmonicTier>;
  currentEmotion?: string;
}

const HarmonicTierDisplay: React.FC<HarmonicTierDisplayProps> = ({
  primeFrequencies,
  shadowFrequencies,
  currentEmotion
}) => {
  const getTierColor = (tier: string) => {
    const tierColors: Record<string, string> = {
      'Crown Prime': '#9333EA',
      'Third-Eye Prime': '#7C3AED',
      'Heart Prime': '#10B981',
      'Visionary Tier': '#3B82F6',
      'Social Prime': '#F59E0B',
      'Gaia Tier': '#059669',
      'Root Prime': '#DC2626',
      'Sacral Tier': '#EA580C',
      'Root Harmonic': '#B91C1C',
      'Root Shadow': '#7F1D1D',
      'Sacral Shadow': '#9A3412',
      'Heart Shadow': '#166534',
      'Root Collapse': '#450A0A',
      'Sacral Collapse': '#7C2D12'
    };
    return tierColors[tier] || '#6B7280';
  };

  const renderFrequencyCard = (emotion: string, data: HarmonicTier, isActive: boolean) => (
    <Card 
      key={emotion}
      className={`transition-all duration-300 ${
        isActive ? 'ring-2 ring-primary shadow-lg scale-105' : 'hover:shadow-md'
      }`}
    >
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center justify-between">
          <span className="capitalize">{emotion}</span>
          <Badge 
            style={{ backgroundColor: getTierColor(data.tier) }}
            className="text-white text-xs"
          >
            {data.frequency} Hz
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="space-y-2 text-xs">
          <div>
            <strong>Tier:</strong> {data.tier}
          </div>
          <div>
            <strong>Attribute:</strong> {data.attribute}
          </div>
          <div className="text-gray-600">
            <strong>Effect:</strong> {data.effect}
          </div>
        </div>
      </CardContent>
    </Card>
  );

  return (
    <div className="space-y-6">
      {/* Prime Frequencies */}
      <div>
        <h3 className="text-lg font-semibold mb-3 text-success">
          ✨ Prime Frequencies (Positive States)
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {Object.entries(primeFrequencies).map(([emotion, data]) =>
            renderFrequencyCard(emotion, data, currentEmotion === emotion)
          )}
        </div>
      </div>

      {/* Shadow Frequencies */}
      <div>
        <h3 className="text-lg font-semibold mb-3 text-destructive">
          🌑 Shadow Frequencies (Challenge States)
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {Object.entries(shadowFrequencies).map(([emotion, data]) =>
            renderFrequencyCard(emotion, data, currentEmotion === emotion)
          )}
        </div>
      </div>

      {/* Frequency Band Legend */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">🎵 Harmonic Tier System</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-primary"></div>
              <span>Crown Prime (800-1000+ Hz)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-primary"></div>
              <span>Third-Eye Prime (700-850 Hz)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-success"></div>
              <span>Heart Prime (500-650 Hz)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-primary"></div>
              <span>Visionary Tier (400-750 Hz)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-warning"></div>
              <span>Social Prime (600-650 Hz)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-success"></div>
              <span>Gaia Tier (400-450 Hz)</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default HarmonicTierDisplay;