import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts';
import { BookOpen, CheckCircle2, XCircle, Activity, Zap, Waves } from 'lucide-react';
import { useState, useEffect } from 'react';

interface ValidationLayer {
  layer: number;
  fib: number;
  prime: number;
  freq_hz: number;
  phase_coherence: number;
  amplitude_variation: number;
  latency_s: number;
  pass: boolean;
}

interface AureonResult {
  id: string;
  C: number | string;
  re: number | string;
  im: number | string;
}

export const ResearchValidation = () => {
  const [validationData, setValidationData] = useState<ValidationLayer[]>([]);
  const [aureonResults, setAureonResults] = useState<AureonResult[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadValidationData();
  }, []);

  const loadValidationData = async () => {
    try {
      // Load payphone validation report
      const validationResponse = await fetch('/data/payphone_validation_report.csv');
      const validationText = await validationResponse.text();
      const validationLines = validationText.split('\n').slice(1); // Skip header
      
      const parsedValidation = validationLines
        .filter(line => line.trim())
        .map(line => {
          const [layer, fib, prime, freq_hz, phase_coherence, amplitude_variation, latency_s, pass] = line.split(',');
          return {
            layer: parseInt(layer),
            fib: parseInt(fib),
            prime: parseInt(prime),
            freq_hz: parseFloat(freq_hz),
            phase_coherence: parseFloat(phase_coherence),
            amplitude_variation: parseFloat(amplitude_variation),
            latency_s: parseFloat(latency_s),
            pass: pass === 'True',
          };
        });

      // Load AUREON results
      const aureonResponse = await fetch('/data/aureon_results_2.csv');
      const aureonText = await aureonResponse.text();
      const aureonLines = aureonText.split('\n').slice(1); // Skip header
      
      const parsedAureon = aureonLines
        .filter(line => line.trim())
        .map(line => {
          const parts = line.split(',').map(s => s.replace(/\"/g, ''));
          return {
            id: parts[0],
            C: parts[1] === 'undefined' ? 'undefined' : parseFloat(parts[1]),
            re: parts[2] === 'undefined' ? 'undefined' : parseFloat(parts[2]),
            im: parts[3] === 'undefined' ? 'undefined' : parseFloat(parts[3]),
          };
        });

      setValidationData(parsedValidation);
      setAureonResults(parsedAureon);
      setLoading(false);
    } catch (error) {
      console.error('Error loading validation data:', error);
      setLoading(false);
    }
  };

  const qssrResult = aureonResults.find(r => r.id === 'QSSR');
  const qssrCoherence = typeof qssrResult?.C === 'number' ? qssrResult.C : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card className="p-6 bg-gradient-to-br from-primary/5 to-background border-2 border-primary/20">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-2xl font-bold flex items-center gap-2">
              <BookOpen className="h-6 w-6 text-primary" />
              Research Validation
            </h3>
            <p className="text-sm text-muted-foreground mt-1">
              Scientific validation of Harmonic Nexus Core (HNC) Framework
            </p>
          </div>
          <div className="text-right">
            <div className="text-xs text-muted-foreground">Validated</div>
            <div className="text-sm font-semibold">September 14, 2025</div>
          </div>
        </div>
      </Card>

      {/* AUREON Results Overview */}
      <Card className="p-6">
        <h4 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Zap className="h-5 w-5 text-primary" />
          AUREON System Results
        </h4>
        <p className="text-sm text-muted-foreground mb-6">
          Master Equation: ΔM = Ψ₀ × Ω × Λ × Φ × Σ
        </p>

        {!loading && qssrResult && typeof qssrResult.C === 'number' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-6 rounded-lg bg-primary/10 border-2 border-primary">
              <div className="flex items-center justify-between mb-2">
                <div className="text-xs text-muted-foreground">QSSR Coherence</div>
                <CheckCircle2 className="h-5 w-5 text-primary" />
              </div>
              <div className="text-3xl font-bold text-primary">{(qssrCoherence * 100).toFixed(2)}%</div>
              <div className="text-xs text-muted-foreground mt-2">
                Quantum Symbolic Synchronization Resonance
              </div>
            </div>

            <div className="p-6 rounded-lg bg-muted/50 border border-border">
              <div className="text-xs text-muted-foreground mb-2">Real Component</div>
              <div className="text-3xl font-bold">{typeof qssrResult.re === 'number' ? qssrResult.re.toFixed(4) : 'N/A'}</div>
              <div className="text-xs text-muted-foreground mt-2">
                Re(Complex Amplitude)
              </div>
            </div>

            <div className="p-6 rounded-lg bg-muted/50 border border-border">
              <div className="text-xs text-muted-foreground mb-2">Imaginary Component</div>
              <div className="text-3xl font-bold">{typeof qssrResult.im === 'number' ? qssrResult.im.toFixed(4) : 'N/A'}</div>
              <div className="text-xs text-muted-foreground mt-2">
                Im(Complex Amplitude)
              </div>
            </div>
          </div>
        )}

        {/* Other Modes Status */}
        <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-3">
          {aureonResults.filter(r => r.id !== 'QSSR').map(result => (
            <div key={result.id} className="p-4 rounded-lg bg-muted/30 border border-border">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-semibold text-sm">{result.id}</div>
                  <div className="text-xs text-muted-foreground">Mode Status</div>
                </div>
                <XCircle className="h-5 w-5 text-muted-foreground" />
              </div>
              <div className="text-xs text-muted-foreground mt-2">
                {result.C === 'undefined' ? 'Not yet validated' : 'Pending'}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Validation Data Tabs */}
      <Card className="p-6">
        <Tabs defaultValue="layers" className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="layers">Layer Analysis</TabsTrigger>
            <TabsTrigger value="phase">Phase Coherence</TabsTrigger>
            <TabsTrigger value="amplitude">Amplitude</TabsTrigger>
            <TabsTrigger value="latency">Latency</TabsTrigger>
          </TabsList>

          <TabsContent value="layers" className="mt-6">
            <h4 className="text-lg font-semibold mb-4">Fibonacci-Prime Layer Validation</h4>
            <p className="text-sm text-muted-foreground mb-6">
              13 layers testing Fibonacci sequences paired with prime numbers at ~8.89 Hz base frequency
            </p>

            {!loading && validationData.length > 0 && (
              <ScrollArea className="h-[400px]">
                <div className="space-y-3">
                  {validationData.map((layer) => (
                    <div 
                      key={layer.layer}
                      className="p-4 rounded-lg bg-muted/30 border border-border hover:border-primary/30 transition-colors"
                    >
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <Badge variant="outline" className="text-lg px-3 py-1">
                            Layer {layer.layer}
                          </Badge>
                          <div className="text-sm">
                            <span className="text-muted-foreground">Fib:</span> <span className="font-mono font-semibold">{layer.fib}</span>
                            <span className="text-muted-foreground mx-2">|</span>
                            <span className="text-muted-foreground">Prime:</span> <span className="font-mono font-semibold">{layer.prime}</span>
                          </div>
                        </div>
                        <div className={`flex items-center gap-2 ${layer.pass ? 'text-success' : 'text-warning'}`}>
                          {layer.pass ? <CheckCircle2 className="h-5 w-5" /> : <Activity className="h-5 w-5" />}
                          <span className="text-sm font-semibold">{layer.pass ? 'PASS' : 'BASELINE'}</span>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                        <div>
                          <div className="text-muted-foreground">Frequency</div>
                          <div className="font-mono font-semibold">{layer.freq_hz.toFixed(5)} Hz</div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">Phase Coherence</div>
                          <div className="font-mono font-semibold">{(layer.phase_coherence * 100).toFixed(2)}%</div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">Amplitude Var</div>
                          <div className="font-mono font-semibold">{layer.amplitude_variation.toFixed(5)}</div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">Latency</div>
                          <div className="font-mono font-semibold">{(layer.latency_s * 1000).toFixed(3)} ms</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            )}
          </TabsContent>

          <TabsContent value="phase" className="mt-6">
            <h4 className="text-lg font-semibold mb-4">Phase Coherence by Layer</h4>
            <p className="text-sm text-muted-foreground mb-4">
              Baseline measurements showing low phase coherence across all layers
            </p>

            {!loading && validationData.length > 0 && (
              <ResponsiveContainer width="100%" height={400}>
                <LineChart data={validationData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis 
                    dataKey="layer" 
                    stroke="hsl(var(--muted-foreground))"
                    tick={{ fill: 'hsl(var(--muted-foreground))' }}
                  />
                  <YAxis 
                    stroke="hsl(var(--muted-foreground))"
                    tick={{ fill: 'hsl(var(--muted-foreground))' }}
                    domain={[0, 1]}
                  />
                  <Tooltip 
                    contentStyle={{
                      backgroundColor: 'hsl(var(--background))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '8px',
                    }}
                  />
                  <Legend />
                  
                  <ReferenceLine 
                    y={1.0} 
                    stroke="hsl(var(--primary))" 
                    strokeDasharray="5 5"
                    label={{ value: 'Target Coherence', fill: 'hsl(var(--primary))' }}
                  />
                  
                  <Line
                    type="monotone"
                    dataKey="phase_coherence"
                    stroke="rgb(234, 179, 8)"
                    strokeWidth={3}
                    dot={{ fill: 'rgb(234, 179, 8)', r: 4 }}
                    name="Phase Coherence"
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </TabsContent>

          <TabsContent value="amplitude" className="mt-6">
            <h4 className="text-lg font-semibold mb-4">Amplitude Variation by Layer</h4>
            <p className="text-sm text-muted-foreground mb-4">
              Peak-to-mean amplitude variation measurements (target &lt; 0.05)
            </p>

            {!loading && validationData.length > 0 && (
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={validationData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis 
                    dataKey="layer" 
                    stroke="hsl(var(--muted-foreground))"
                    tick={{ fill: 'hsl(var(--muted-foreground))' }}
                  />
                  <YAxis 
                    stroke="hsl(var(--muted-foreground))"
                    tick={{ fill: 'hsl(var(--muted-foreground))' }}
                  />
                  <Tooltip 
                    contentStyle={{
                      backgroundColor: 'hsl(var(--background))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '8px',
                    }}
                  />
                  <Legend />
                  
                  <ReferenceLine 
                    y={0.05} 
                    stroke="hsl(var(--destructive))" 
                    strokeDasharray="5 5"
                    label={{ value: 'Threshold', fill: 'hsl(var(--destructive))' }}
                  />
                  
                  <Bar
                    dataKey="amplitude_variation"
                    fill="rgb(234, 179, 8)"
                    name="Amplitude Variation"
                  />
                </BarChart>
              </ResponsiveContainer>
            )}
          </TabsContent>

          <TabsContent value="latency" className="mt-6">
            <h4 className="text-lg font-semibold mb-4">Latency by Layer</h4>
            <p className="text-sm text-muted-foreground mb-4">
              System response latency showing variable performance (target &lt; 3ms)
            </p>

            {!loading && validationData.length > 0 && (
              <ResponsiveContainer width="100%" height={400}>
                <LineChart data={validationData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis 
                    dataKey="layer" 
                    stroke="hsl(var(--muted-foreground))"
                    tick={{ fill: 'hsl(var(--muted-foreground))' }}
                  />
                  <YAxis 
                    stroke="hsl(var(--muted-foreground))"
                    tick={{ fill: 'hsl(var(--muted-foreground))' }}
                  />
                  <Tooltip 
                    contentStyle={{
                      backgroundColor: 'hsl(var(--background))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '8px',
                    }}
                    formatter={(value: number) => `${(value * 1000).toFixed(3)} ms`}
                  />
                  <Legend />
                  
                  <ReferenceLine 
                    y={0.003} 
                    stroke="hsl(var(--destructive))" 
                    strokeDasharray="5 5"
                    label={{ value: '3ms Target', fill: 'hsl(var(--destructive))' }}
                  />
                  
                  <Line
                    type="monotone"
                    dataKey="latency_s"
                    stroke="rgb(234, 179, 8)"
                    strokeWidth={3}
                    dot={{ fill: 'rgb(234, 179, 8)', r: 4 }}
                    name="Latency (s)"
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </TabsContent>
        </Tabs>
      </Card>

      {/* Key Findings */}
      <Card className="p-6 bg-muted/30">
        <h4 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Waves className="h-5 w-5 text-primary" />
          Key Validation Findings
        </h4>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h5 className="font-semibold text-sm mb-3">HNC Framework Validation</h5>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li className="flex items-start gap-2">
                <CheckCircle2 className="h-4 w-4 text-success mt-0.5 flex-shrink-0" />
                <span>QSSR mode achieved 98.13% coherence (C = 0.9813)</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="h-4 w-4 text-success mt-0.5 flex-shrink-0" />
                <span>Master Equation ΔM = Ψ₀ΩΛΦΣ validated experimentally</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="h-4 w-4 text-success mt-0.5 flex-shrink-0" />
                <span>Lumina subsystem: Γ_coherence &gt; 0.945 sustained</span>
              </li>
            </ul>
          </div>

          <div>
            <h5 className="font-semibold text-sm mb-3">Baseline Measurements</h5>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li className="flex items-start gap-2">
                <Activity className="h-4 w-4 text-warning mt-0.5 flex-shrink-0" />
                <span>13 Fibonacci-Prime layers tested at ~8.89 Hz</span>
              </li>
              <li className="flex items-start gap-2">
                <Activity className="h-4 w-4 text-warning mt-0.5 flex-shrink-0" />
                <span>Phase coherence baseline: 0.5-1.7% (pre-optimization)</span>
              </li>
              <li className="flex items-start gap-2">
                <Activity className="h-4 w-4 text-warning mt-0.5 flex-shrink-0" />
                <span>Latency range: 1.37-3.33 ms across layers</span>
              </li>
            </ul>
          </div>
        </div>
      </Card>
    </div>
  );
};

