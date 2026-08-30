import React, { useState, useEffect, useCallback } from 'react';
import { fmt, fmtHz } from '@/utils/number';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Textarea } from './ui/textarea';

interface FrequencySignature {
  frequencies: number[];
  decay: number;
  amplitude: number;
  harmonics: number[];
}

interface CompiledWaveform {
  intent: string;
  signature: FrequencySignature;
  synthesis_time: number;
  waveform_id: string;
}

export const AurisSymbolicCompiler: React.FC<{
  onWaveformGenerated?: (waveform: CompiledWaveform) => void;
}> = ({ onWaveformGenerated }) => {
  const [intentPhrase, setIntentPhrase] = useState('');
  const [compiledWaveform, setCompiledWaveform] = useState<CompiledWaveform | null>(null);
  const [isCompiling, setIsCompiling] = useState(false);
  const [codex, setCodex] = useState<any>(null);

  const loadCodex = useCallback(async () => {
    try {
      const response = await fetch('/auris_codex.json');
      const data = await response.json();
      setCodex(data);
    } catch (error) {
      console.error('Failed to load Auris Codex:', error);
    }
  }, []);

  React.useEffect(() => {
    loadCodex();
  }, [loadCodex]);

  const compileIntent = useCallback(async () => {
    if (!intentPhrase.trim() || !codex) return;
    
    setIsCompiling(true);
    
    // Tokenize the intent phrase
    const tokens = intentPhrase.toLowerCase().split(/\s+/);
    const mappings = codex.intent_mappings;
    
    // Find matching intents
    const matchedIntents = tokens.filter(token => mappings[token]);
    
    if (matchedIntents.length === 0) {
      setIsCompiling(false);
      return;
    }
    
    // Synthesize frequency signature
    let combinedFreqs: number[] = [];
    let avgDecay = 0;
    let avgAmplitude = 0;
    let combinedHarmonics: number[] = [];
    
    matchedIntents.forEach(intent => {
      const mapping = mappings[intent];
      combinedFreqs = [...combinedFreqs, ...mapping.frequencies];
      avgDecay += mapping.decay;
      avgAmplitude += mapping.amplitude;
      combinedHarmonics = [...combinedHarmonics, ...mapping.harmonics];
    });
    
    avgDecay /= matchedIntents.length;
    avgAmplitude /= matchedIntents.length;
    
    const waveform: CompiledWaveform = {
      intent: intentPhrase,
      signature: {
        frequencies: [...new Set(combinedFreqs)].slice(0, 5),
        decay: avgDecay,
        amplitude: avgAmplitude,
        harmonics: combinedHarmonics.slice(0, 3)
      },
      synthesis_time: Date.now(),
      waveform_id: `auris_${Date.now()}`
    };
    
    setCompiledWaveform(waveform);
    onWaveformGenerated?.(waveform);
    setIsCompiling(false);
  }, [intentPhrase, codex, onWaveformGenerated]);

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <div className="w-2 h-2 bg-primary rounded-full animate-pulse"></div>
          Auris Symbolic Compiler
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">Intent Phrase</label>
          <Textarea
            value={intentPhrase}
            onChange={(e) => setIntentPhrase(e.target.value)}
            placeholder="e.g., Gary Leckey 02111991 aura validation harmony"
            className="min-h-[80px]"
          />
        </div>
        
        <Button 
          onClick={compileIntent}
          disabled={!intentPhrase.trim() || isCompiling}
          className="w-full"
        >
          {isCompiling ? 'Compiling...' : 'Synthesize Waveform'}
        </Button>
        
        {compiledWaveform && (
          <div className="space-y-3 p-3 bg-slate-50 rounded-lg">
            <div className="flex items-center justify-between">
              <Badge variant="secondary">Compiled</Badge>
              <span className="text-xs text-muted-foreground">
                ID: {compiledWaveform.waveform_id}
              </span>
            </div>
            
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="font-medium">Frequencies:</span>
                  {compiledWaveform.signature.frequencies.map(f => fmt(f, 2)).join(', ')} Hz
                </div>
              </div>
              <div>
                <span className="font-medium">Decay:</span>
                <div className="text-xs text-muted-foreground">
                  {fmt(compiledWaveform.signature.decay, 3)}
                </div>
              </div>
              <div>
                <span className="font-medium">Amplitude:</span>
                <div className="text-xs text-muted-foreground">
                  {fmt(compiledWaveform.signature.amplitude, 2)}
                </div>
              </div>
              <div>
                <span className="font-medium">Harmonics:</span>
                <div className="text-xs text-muted-foreground">
                  {compiledWaveform.signature.harmonics.map(h => fmt(h, 2)).join(', ')}
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};