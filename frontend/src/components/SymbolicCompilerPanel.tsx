import React, { useState } from 'react';
// import { motion, AnimatePresence } from 'framer-motion';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';

interface ResonanceOutput {
  intent: string;
  frequency: number;
  decay: number;
  harmonics: number[];
  waveform: number[];
}

export const SymbolicCompilerPanel: React.FC<{ tool: string }> = ({ tool }) => {
  const [intentText, setIntentText] = useState('');
  const [isCompiling, setIsCompiling] = useState(false);
  const [output, setOutput] = useState<ResonanceOutput | null>(null);
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);

  const presetIntents = {
    hope: "Send waves of hope and optimism to all beings",
    compassion: "Broadcast loving compassion and understanding",
    healing: "Channel healing energy for physical and emotional wellness",
    courage: "Inspire courage and strength in times of challenge",
    peace: "Radiate peace and harmony across all dimensions",
    wisdom: "Share ancient wisdom and clarity of mind"
  };

  const compileIntent = async (text: string) => {
    setIsCompiling(true);
    
    // Simulate compilation process
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    // Generate synthetic resonance output
    const words = text.toLowerCase().split(' ');
    const baseFreq = 432 + (words.length * 7.83); // Base on Schumann + word count
    const decay = Math.max(0.1, Math.min(0.9, words.length * 0.05));
    
    // Generate harmonics based on emotional content
    const emotionalWords = ['love', 'peace', 'hope', 'healing', 'joy', 'compassion'];
    const emotionScore = words.filter(w => emotionalWords.includes(w)).length;
    const harmonics = [baseFreq, baseFreq * 1.618, baseFreq * 2.618, baseFreq * 4.236]
      .slice(0, 2 + emotionScore);
    
    // Generate waveform data points
    const waveform = Array.from({ length: 100 }, (_, i) => {
      const t = i / 100;
      return harmonics.reduce((sum, freq, idx) => {
        return sum + Math.sin(t * freq * 0.01) * Math.exp(-t * decay) * (1 / (idx + 1));
      }, 0);
    });

    setOutput({
      intent: text,
      frequency: baseFreq,
      decay,
      harmonics,
      waveform
    });
    
    setIsCompiling(false);
  };

  const renderIntentCompiler = () => (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h4 className="font-semibold text-slate-700">Broadcast Resonance Compiler</h4>
        <Button 
          onClick={() => compileIntent(intentText)} 
          disabled={!intentText.trim() || isCompiling}
          size="sm"
        >
          {isCompiling ? 'Compiling...' : 'Compile & Broadcast'}
        </Button>
      </div>
      
      <Textarea
        placeholder="Enter your intent in natural language (e.g., 'Send peace and healing energy to all beings')"
        value={intentText}
        onChange={(e) => setIntentText(e.target.value)}
        rows={3}
        className="resize-none"
      />
      
      {isCompiling && (
        <div className="flex items-center gap-3 p-3 bg-primary rounded-lg border border-primary">
          <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <span className="text-primary text-sm">
            Processing intent → harmonic frequencies → waveform synthesis...
          </span>
        </div>
      )}
      
      {output && (
        <div className="space-y-4 p-4 bg-success rounded-lg border border-success">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-success rounded-full animate-pulse" />
            <span className="text-success font-medium">Resonance Broadcast Active</span>
          </div>
          
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <div className="text-slate-600 font-medium">Base Frequency</div>
              <div className="text-lg font-mono">{output.frequency.toFixed(2)} Hz</div>
            </div>
            <div>
              <div className="text-slate-600 font-medium">Decay Rate</div>
              <div className="text-lg font-mono">{output.decay.toFixed(3)}</div>
            </div>
          </div>
          
          <div>
            <div className="text-slate-600 font-medium mb-2">Harmonic Series</div>
            <div className="flex gap-2 flex-wrap">
              {output.harmonics.map((freq, idx) => (
                <span key={idx} className="px-2 py-1 bg-white rounded text-xs font-mono">
                  {freq.toFixed(1)} Hz
                </span>
              ))}
            </div>
          </div>
          
          <div>
            <div className="text-slate-600 font-medium mb-2">Waveform Preview</div>
            <div className="h-16 bg-white rounded border flex items-center px-2">
              <svg width="100%" height="60" className="text-success">
                <polyline
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  points={output.waveform.map((y, x) => 
                    `${(x / output.waveform.length) * 100}%,${30 + y * 20}`
                  ).join(' ')}
                />
              </svg>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  const renderPresetIntents = () => (
    <div className="space-y-4">
      <h4 className="font-semibold text-slate-700">Preset Intent Library</h4>
      
      <div className="grid grid-cols-2 gap-3">
        {Object.entries(presetIntents).map(([key, intent]) => (
          <Button
            key={key}
            variant={selectedPreset === key ? "default" : "outline"}
            onClick={() => {
              setSelectedPreset(key);
              setIntentText(intent);
            }}
            className="h-auto p-3 text-left justify-start"
          >
            <div>
              <div className="font-medium capitalize">{key}</div>
              <div className="text-xs text-slate-500 mt-1 line-clamp-2">
                {intent}
              </div>
            </div>
          </Button>
        ))}
      </div>
      
      {selectedPreset && (
        <div className="p-3 bg-slate-50 rounded-lg">
          <div className="text-sm text-slate-600 mb-2">Selected Intent:</div>
          <div className="text-sm">{presetIntents[selectedPreset as keyof typeof presetIntents]}</div>
        </div>
      )}
    </div>
  );

  switch (tool) {
    case 'intent':
      return <Card>{renderIntentCompiler()}</Card>;
    case 'presets':
      return <Card>{renderPresetIntents()}</Card>;
    default:
      return <Card><div className="p-8 text-center text-slate-500">Select a compiler tool</div></Card>;
  }
};