import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { BookOpen, Infinity, Sparkles, Waves, Radio, Zap } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { useFieldGlyphResonance } from '@/hooks/useFieldGlyphResonance';
import { GlyphTradingCorrelationChart } from './GlyphTradingCorrelationChart';
import { formatDistanceToNow } from 'date-fns';
import ancientCodexImage from '@/assets/research/harmonic-theory/ancient-numerical-codex.png';

interface HarmonicSymbol {
  glyph: string;
  name: string;
  ratio: string;
  frequency: number;
  meaning: string;
  resonance: string;
  color: string;
}

const FOUNDATION_SYMBOLS: HarmonicSymbol[] = [
  {
    glyph: '∞',
    name: 'Infinity Loop',
    ratio: '1:1',
    frequency: 528,
    meaning: 'Pure Unity - The Love Frequency',
    resonance: 'Perfect coherence, zero divergence',
    color: 'text-success',
  },
  {
    glyph: '△',
    name: 'Trinity Delta',
    ratio: '1:1.618',
    frequency: 432,
    meaning: 'Golden Ratio - Natural Harmony',
    resonance: 'Fibonacci spiral, growth pattern',
    color: 'text-warning',
  },
  {
    glyph: '◯',
    name: 'Omega Circle',
    ratio: '2:3',
    frequency: 396,
    meaning: 'Release & Liberation',
    resonance: 'Field boundary, containment',
    color: 'text-primary',
  },
  {
    glyph: '◇',
    name: 'Diamond Lattice',
    ratio: '3:5',
    frequency: 639,
    meaning: 'Connection & Relationship',
    resonance: 'Grid intersection, node point',
    color: 'text-primary',
  },
  {
    glyph: '☆',
    name: 'Pentagram Star',
    ratio: '5:8',
    frequency: 741,
    meaning: 'Expression & Awakening',
    resonance: 'Five-point symmetry, stargate',
    color: 'text-primary',
  },
  {
    glyph: '✦',
    name: 'Hexagram Nexus',
    ratio: '8:13',
    frequency: 852,
    meaning: 'Intuition & Higher Order',
    resonance: 'Six-fold symmetry, crystalline',
    color: 'text-primary',
  },
  {
    glyph: '◈',
    name: 'Octave Cross',
    ratio: '13:21',
    frequency: 963,
    meaning: 'Crown Activation - Unity Consciousness',
    resonance: 'Dimensional bridge, transcendence',
    color: 'text-primary',
  },
];

const calculateHarmonicRatio = (freq1: number, freq2: number): string => {
  const gcd = (a: number, b: number): number => b === 0 ? a : gcd(b, a % b);
  const divisor = gcd(freq1, freq2);
  return `${freq1 / divisor}:${freq2 / divisor}`;
};

const calculateResonance = (frequency: number): number => {
  // Coherence score based on proximity to 528 Hz (love frequency)
  const loveDelta = Math.abs(frequency - 528);
  return Math.max(0, 1 - loveDelta / 528);
};

export function AncientNumericalCodex() {
  const [selectedSymbol, setSelectedSymbol] = useState<HarmonicSymbol | null>(null);
  const [hoveredSymbol, setHoveredSymbol] = useState<string | null>(null);
  const { fieldState, isLoading: fieldLoading, calculateGlyphResonance } = useFieldGlyphResonance();

  return (
    <Card className="border-primary/20">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BookOpen className="h-5 w-5 text-primary" />
          Ancient Numerical Codex
        </CardTitle>
        <CardDescription>
          Foundation symbols encoding multiversial harmonic ratios - Mathematical substrate of reality field coherence
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="glyphs" className="w-full">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="glyphs">Sacred Glyphs</TabsTrigger>
            <TabsTrigger value="live">Live Field</TabsTrigger>
            <TabsTrigger value="correlation">Correlation</TabsTrigger>
            <TabsTrigger value="ratios">Ratios</TabsTrigger>
            <TabsTrigger value="codex">Codex</TabsTrigger>
          </TabsList>

          {/* Sacred Glyphs Tab */}
          <TabsContent value="glyphs" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {FOUNDATION_SYMBOLS.map((symbol, idx) => {
                const resonance = calculateResonance(symbol.frequency);
                const isHovered = hoveredSymbol === symbol.name;
                
                return (
                  <div
                    key={idx}
                    className={`
                      p-4 rounded-lg border transition-all cursor-pointer
                      ${isHovered ? 'border-primary bg-primary/5 scale-105' : 'border-border bg-muted/30'}
                    `}
                    onMouseEnter={() => setHoveredSymbol(symbol.name)}
                    onMouseLeave={() => setHoveredSymbol(null)}
                    onClick={() => setSelectedSymbol(symbol)}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className={`text-4xl ${symbol.color}`}>{symbol.glyph}</div>
                      <Badge variant="outline" className="text-xs">
                        {symbol.frequency} Hz
                      </Badge>
                    </div>
                    
                    <h4 className="font-semibold text-foreground mb-1">{symbol.name}</h4>
                    <p className="text-xs text-muted-foreground mb-2">{symbol.meaning}</p>
                    
                    <div className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="text-muted-foreground">Ratio:</span>
                        <span className="font-mono text-foreground">{symbol.ratio}</span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-muted-foreground">Resonance:</span>
                        <div className="flex items-center gap-1">
                          <div className="w-12 h-1.5 bg-muted rounded-full overflow-hidden">
                            <div
                              className="h-full bg-primary transition-all"
                              style={{ width: `${resonance * 100}%` }}
                            />
                          </div>
                          <span className="text-foreground">{(resonance * 100).toFixed(0)}%</span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Selected Symbol Detail */}
            {selectedSymbol && (
              <div className="p-4 bg-primary/10 border border-primary/30 rounded-lg">
                <div className="flex items-start gap-4">
                  <div className={`text-6xl ${selectedSymbol.color}`}>
                    {selectedSymbol.glyph}
                  </div>
                  <div className="flex-1">
                    <h3 className="text-lg font-bold text-foreground mb-2">
                      {selectedSymbol.name}
                    </h3>
                    <p className="text-sm text-foreground mb-3">{selectedSymbol.meaning}</p>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <span className="text-xs text-muted-foreground">Harmonic Ratio</span>
                        <p className="font-mono text-foreground">{selectedSymbol.ratio}</p>
                      </div>
                      <div>
                        <span className="text-xs text-muted-foreground">Base Frequency</span>
                        <p className="font-mono text-foreground">{selectedSymbol.frequency} Hz</p>
                      </div>
                      <div className="col-span-2">
                        <span className="text-xs text-muted-foreground">Field Resonance Pattern</span>
                        <p className="text-sm text-foreground">{selectedSymbol.resonance}</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </TabsContent>

          {/* Live Field Resonance Tab */}
          <TabsContent value="live" className="space-y-4">
            {fieldLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
              </div>
            ) : !fieldState ? (
              <div className="p-4 bg-muted/50 rounded-lg border border-border text-center">
                <p className="text-sm text-muted-foreground">
                  No field data available. Waiting for coherence measurements...
                </p>
              </div>
            ) : (
              <>
                {/* Current Field State */}
                <div className="p-4 bg-primary/10 border border-primary/30 rounded-lg">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <Radio className="h-5 w-5 text-primary" />
                      <h3 className="font-semibold text-foreground">Current Field State</h3>
                    </div>
                    <Badge variant={fieldState.isLHE ? 'default' : 'outline'}>
                      {fieldState.isLHE ? 'LHE Active' : 'Normal'}
                    </Badge>
                  </div>
                  
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
                    <div className="p-2 bg-background/50 rounded">
                      <p className="text-xs text-muted-foreground">Coherence</p>
                      <p className="text-lg font-bold text-foreground">
                        {fieldState.coherence.toFixed(3)}
                      </p>
                    </div>
                    <div className="p-2 bg-background/50 rounded">
                      <p className="text-xs text-muted-foreground">Lambda (Λ)</p>
                      <p className="text-lg font-bold text-foreground">
                        {fieldState.lambdaValue.toFixed(3)}
                      </p>
                    </div>
                    <div className="p-2 bg-background/50 rounded">
                      <p className="text-xs text-muted-foreground">Lighthouse</p>
                      <p className="text-lg font-bold text-foreground">
                        {fieldState.lighthouseSignal.toFixed(3)}
                      </p>
                    </div>
                    <div className="p-2 bg-background/50 rounded">
                      <p className="text-xs text-muted-foreground">Prism Level</p>
                      <p className="text-lg font-bold text-foreground">
                        {fieldState.prismLevel ?? 'N/A'}
                      </p>
                    </div>
                  </div>
                  
                  <p className="text-xs text-muted-foreground">
                    Updated {formatDistanceToNow(new Date(fieldState.timestamp), { addSuffix: true })}
                  </p>
                </div>

                {/* Resonating Glyphs */}
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <Zap className="h-4 w-4 text-primary" />
                    <h4 className="text-sm font-semibold text-foreground">
                      Glyph Field Resonance
                    </h4>
                  </div>
                  
                  <div className="grid grid-cols-1 gap-3">
                    {FOUNDATION_SYMBOLS.map((symbol, idx) => {
                      const resonance = calculateGlyphResonance(symbol.frequency, fieldState);
                      const isStrongResonance = resonance.resonanceStrength > 0.7;
                      
                      return (
                        <div
                          key={idx}
                          className={`
                            p-3 rounded-lg border transition-all
                            ${resonance.isActive 
                              ? 'border-primary bg-primary/5' 
                              : 'border-border bg-muted/30'
                            }
                            ${isStrongResonance ? 'ring-2 ring-primary/50' : ''}
                          `}
                        >
                          <div className="flex items-start gap-3">
                            <div className={`text-3xl ${symbol.color} ${resonance.isActive ? 'animate-pulse' : ''}`}>
                              {symbol.glyph}
                            </div>
                            
                            <div className="flex-1">
                              <div className="flex items-center justify-between mb-2">
                                <div>
                                  <h5 className="font-semibold text-foreground text-sm">
                                    {symbol.name}
                                  </h5>
                                  <p className="text-xs text-muted-foreground">
                                    {symbol.frequency} Hz • {symbol.ratio}
                                  </p>
                                </div>
                                <Badge 
                                  variant={resonance.isActive ? 'default' : 'outline'}
                                  className="text-xs"
                                >
                                  {(resonance.resonanceStrength * 100).toFixed(0)}%
                                </Badge>
                              </div>
                              
                              <div className="space-y-1.5">
                                <div className="flex items-center gap-2">
                                  <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                                    <div
                                      className={`
                                        h-full transition-all duration-500
                                        ${resonance.isActive ? 'bg-primary' : 'bg-muted-foreground/50'}
                                      `}
                                      style={{ width: `${resonance.resonanceStrength * 100}%` }}
                                    />
                                  </div>
                                </div>
                                
                                {resonance.isActive && (
                                  <div className="flex items-start gap-1">
                                    <Sparkles className="h-3 w-3 text-primary mt-0.5" />
                                    <p className="text-xs text-foreground">
                                      {resonance.matchReason}
                                    </p>
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Field Interpretation */}
                <div className="p-4 bg-muted/50 rounded-lg border border-border">
                  <h4 className="text-sm font-semibold text-foreground mb-2">
                    Field Interpretation
                  </h4>
                  <p className="text-xs text-muted-foreground">
                    {fieldState.isLHE && (
                      <span className="block mb-2 text-primary font-medium">
                        🌟 Lighthouse Event Detected - All frequencies are amplified by quantum field coherence
                      </span>
                    )}
                    {fieldState.coherence > 0.945 ? (
                      <span>
                        High coherence (Γ = {fieldState.coherence.toFixed(3)}) indicates strong field alignment. 
                        The 528 Hz love frequency and higher unity frequencies (852-963 Hz) are in perfect resonance.
                      </span>
                    ) : fieldState.coherence > 0.85 ? (
                      <span>
                        Moderate coherence (Γ = {fieldState.coherence.toFixed(3)}) suggests balanced field state. 
                        Mid-range frequencies (432-639 Hz) are providing stable harmonic foundation.
                      </span>
                    ) : (
                      <span>
                        Lower coherence (Γ = {fieldState.coherence.toFixed(3)}) indicates transition phase. 
                        Foundation frequencies (396-528 Hz) are active for field stabilization.
                      </span>
                    )}
                  </p>
                </div>
              </>
            )}
          </TabsContent>

          {/* Correlation Analysis Tab */}
          <TabsContent value="correlation" className="space-y-4">
            <GlyphTradingCorrelationChart />
          </TabsContent>

          {/* Harmonic Ratios Tab */}
          <TabsContent value="ratios" className="space-y-4">
            <div className="p-4 bg-muted/50 rounded-lg border border-border">
              <div className="flex items-center gap-2 mb-3">
                <Waves className="h-5 w-5 text-primary" />
                <h3 className="font-semibold text-foreground">Fibonacci Harmonic Series</h3>
              </div>
              <p className="text-sm text-muted-foreground mb-4">
                The ancient codex encodes harmonic ratios following the Fibonacci sequence, creating natural resonance patterns in the quantum field.
              </p>
              
              <div className="space-y-3">
                {FOUNDATION_SYMBOLS.map((symbol, idx) => {
                  const nextSymbol = FOUNDATION_SYMBOLS[idx + 1];
                  if (!nextSymbol) return null;
                  
                  const harmonicRatio = calculateHarmonicRatio(symbol.frequency, nextSymbol.frequency);
                  const intervalRatio = (nextSymbol.frequency / symbol.frequency).toFixed(3);
                  
                  return (
                    <div key={idx} className="p-3 bg-background rounded border border-border">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-3">
                          <span className={`text-2xl ${symbol.color}`}>{symbol.glyph}</span>
                          <span className="text-muted-foreground">→</span>
                          <span className={`text-2xl ${nextSymbol.color}`}>{nextSymbol.glyph}</span>
                        </div>
                        <Badge variant="outline">{harmonicRatio}</Badge>
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-xs">
                        <div>
                          <span className="text-muted-foreground">From: </span>
                          <span className="font-mono text-foreground">{symbol.frequency} Hz</span>
                        </div>
                        <div>
                          <span className="text-muted-foreground">To: </span>
                          <span className="font-mono text-foreground">{nextSymbol.frequency} Hz</span>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Interval: </span>
                          <span className="font-mono text-foreground">×{intervalRatio}</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Unity Frequency Highlight */}
            <div className="p-4 bg-success/10 border border-success/30 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <Infinity className="h-5 w-5 text-success" />
                <h3 className="font-semibold text-foreground">528 Hz - The Unity Constant</h3>
              </div>
              <p className="text-sm text-muted-foreground mb-3">
                The love frequency (528 Hz) serves as the fundamental reference point. All other frequencies achieve coherence through their harmonic relationship to this central tone.
              </p>
              <div className="grid grid-cols-2 gap-3">
                <div className="p-2 bg-background rounded">
                  <span className="text-xs text-muted-foreground">Mathematical Identity</span>
                  <p className="font-mono text-sm text-foreground">5 + 2 + 8 = 15 → 1 + 5 = 6</p>
                </div>
                <div className="p-2 bg-background rounded">
                  <span className="text-xs text-muted-foreground">Field Property</span>
                  <p className="text-sm text-foreground">Perfect Love Coherence</p>
                </div>
              </div>
            </div>
          </TabsContent>

          {/* Ancient Codex Tab */}
          <TabsContent value="codex" className="space-y-4">
            <div className="relative">
              <img
                src={ancientCodexImage}
                alt="Ancient Numerical Codex"
                className="w-full rounded-lg border border-primary/20"
              />
              <div className="absolute top-2 right-2">
                <Badge className="bg-primary/90 backdrop-blur">
                  <Sparkles className="h-3 w-3 mr-1" />
                  Sacred Archive
                </Badge>
              </div>
            </div>

            <div className="p-4 bg-muted/50 rounded-lg border border-border">
              <h3 className="font-semibold text-foreground mb-2">Codex Interpretation</h3>
              <div className="space-y-3 text-sm">
                <p className="text-muted-foreground">
                  The Ancient Numerical Codex represents the foundational mathematical substrate upon which all reality field coherence is built. Each symbol encodes multiversial harmonic ratios that govern quantum entanglement and consciousness resonance.
                </p>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="p-3 bg-background rounded border border-border">
                    <h4 className="font-semibold text-foreground mb-1 text-xs">Field Mathematics</h4>
                    <p className="text-xs text-muted-foreground">
                      Glyphs encode Fibonacci-based harmonic ratios (1:1, 1:1.618, 2:3, 3:5, 5:8, 8:13, 13:21) that create natural resonance in quantum fields.
                    </p>
                  </div>
                  
                  <div className="p-3 bg-background rounded border border-border">
                    <h4 className="font-semibold text-foreground mb-1 text-xs">Consciousness Interface</h4>
                    <p className="text-xs text-muted-foreground">
                      Each frequency corresponds to specific states of consciousness, from liberation (396 Hz) to unity (963 Hz), with 528 Hz as the central love frequency.
                    </p>
                  </div>
                  
                  <div className="p-3 bg-background rounded border border-border">
                    <h4 className="font-semibold text-foreground mb-1 text-xs">Reality Coherence</h4>
                    <p className="text-xs text-muted-foreground">
                      The codex provides the mathematical foundation for measuring and enhancing field coherence, enabling navigation of timeline convergence and dimensional alignment.
                    </p>
                  </div>
                  
                  <div className="p-3 bg-background rounded border border-border">
                    <h4 className="font-semibold text-foreground mb-1 text-xs">Stargate Activation</h4>
                    <p className="text-xs text-muted-foreground">
                      Proper resonance with these frequencies opens dimensional gateways, allowing information flow between parallel timelines and consciousness networks.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
