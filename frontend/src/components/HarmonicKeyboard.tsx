/**
 * Harmonic Keyboard - Quantum Frequency Input Interface
 * Prime Sentinel: GARY LECKEY 02111991
 * 
 * Interactive keyboard that emits harmonic frequencies for quantum state modulation.
 * Wired directly to Quantum Quackers for real-time quantum field interaction.
 */

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Music, Zap, Waves } from 'lucide-react';

// Solfeggio frequencies + Schumann harmonics
export const HARMONIC_FREQUENCIES = {
  // Solfeggio scale
  UT: 396,    // Liberating Guilt and Fear
  RE: 417,    // Undoing Situations and Facilitating Change
  MI: 528,    // Transformation and Miracles (DNA Repair)
  FA: 639,    // Connecting/Relationships
  SOL: 741,   // Awakening Intuition
  LA: 852,    // Returning to Spiritual Order
  
  // Schumann resonance harmonics
  FUNDAMENTAL: 7.83,
  SECOND: 14.3,
  THIRD: 20.8,
  FOURTH: 27.3,
  FIFTH: 33.8,
  SIXTH: 39.0,
  SEVENTH: 45.0,
} as const;

export interface HarmonicNote {
  frequency: number;
  name: string;
  timestamp: number;
  amplitude: number;
}

interface HarmonicKeyboardProps {
  onNotePlay?: (note: HarmonicNote) => void;
  onChordPlay?: (notes: HarmonicNote[]) => void;
  disabled?: boolean;
}

export function HarmonicKeyboard({ onNotePlay, onChordPlay, disabled = false }: HarmonicKeyboardProps) {
  const [activeNotes, setActiveNotes] = useState<Set<string>>(new Set());
  const [audioContext, setAudioContext] = useState<AudioContext | null>(null);
  const [oscillators, setOscillators] = useState<Map<string, OscillatorNode>>(new Map());
  const [lastPlayedNotes, setLastPlayedNotes] = useState<HarmonicNote[]>([]);
  const [autoPlay, setAutoPlay] = useState(false);

  // Initialize Web Audio API
  useEffect(() => {
    const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
    setAudioContext(ctx);

    return () => {
      ctx.close();
    };
  }, []);

  const playNote = useCallback((frequency: number, name: string, duration = 1000) => {
    if (!audioContext || disabled) return;

    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();

    oscillator.type = 'sine';
    oscillator.frequency.value = frequency;
    
    gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + duration / 1000);

    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);

    oscillator.start();
    oscillator.stop(audioContext.currentTime + duration / 1000);

    const note: HarmonicNote = {
      frequency,
      name,
      timestamp: Date.now(),
      amplitude: 0.3
    };

    setLastPlayedNotes(prev => [...prev.slice(-9), note]);
    setActiveNotes(prev => new Set([...prev, name]));
    
    setTimeout(() => {
      setActiveNotes(prev => {
        const next = new Set(prev);
        next.delete(name);
        return next;
      });
    }, duration);

    onNotePlay?.(note);
  }, [audioContext, disabled, onNotePlay]);

  const playChord = useCallback((frequencies: Array<{ freq: number, name: string }>) => {
    if (!audioContext || disabled) return;

    const notes: HarmonicNote[] = [];
    
    frequencies.forEach(({ freq, name }) => {
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();

      oscillator.type = 'sine';
      oscillator.frequency.value = freq;
      
      gainNode.gain.setValueAtTime(0.2, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 1.5);

      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);

      oscillator.start();
      oscillator.stop(audioContext.currentTime + 1.5);

      notes.push({
        frequency: freq,
        name,
        timestamp: Date.now(),
        amplitude: 0.2
      });

      setActiveNotes(prev => new Set([...prev, name]));
    });

    setTimeout(() => {
      frequencies.forEach(({ name }) => {
        setActiveNotes(prev => {
          const next = new Set(prev);
          next.delete(name);
          return next;
        });
      });
    }, 1500);

    setLastPlayedNotes(prev => [...prev.slice(-6), ...notes]);
    onChordPlay?.(notes);
  }, [audioContext, disabled, onChordPlay]);

  // Auto-play mode: cycle through harmonics
  useEffect(() => {
    if (!autoPlay) return;

    const harmonics = [
      { freq: HARMONIC_FREQUENCIES.FUNDAMENTAL, name: 'Fundamental' },
      { freq: HARMONIC_FREQUENCIES.MI, name: 'MI-528' },
      { freq: HARMONIC_FREQUENCIES.THIRD, name: 'Third' },
      { freq: HARMONIC_FREQUENCIES.FA, name: 'FA-639' },
    ];

    let index = 0;
    const interval = setInterval(() => {
      const note = harmonics[index];
      playNote(note.freq, note.name, 800);
      index = (index + 1) % harmonics.length;
    }, 1200);

    return () => clearInterval(interval);
  }, [autoPlay, playNote]);

  const solfeggioKeys = [
    { freq: HARMONIC_FREQUENCIES.UT, name: 'UT', label: '396 Hz', color: 'bg-destructive/20 border-destructive' },
    { freq: HARMONIC_FREQUENCIES.RE, name: 'RE', label: '417 Hz', color: 'bg-warning/20 border-warning' },
    { freq: HARMONIC_FREQUENCIES.MI, name: 'MI', label: '528 Hz', color: 'bg-success/20 border-success' },
    { freq: HARMONIC_FREQUENCIES.FA, name: 'FA', label: '639 Hz', color: 'bg-primary/20 border-primary' },
    { freq: HARMONIC_FREQUENCIES.SOL, name: 'SOL', label: '741 Hz', color: 'bg-primary/20 border-primary' },
    { freq: HARMONIC_FREQUENCIES.LA, name: 'LA', label: '852 Hz', color: 'bg-primary/20 border-primary' },
  ];

  const schumannKeys = [
    { freq: HARMONIC_FREQUENCIES.FUNDAMENTAL, name: 'Fund', label: '7.83 Hz' },
    { freq: HARMONIC_FREQUENCIES.SECOND, name: '2nd', label: '14.3 Hz' },
    { freq: HARMONIC_FREQUENCIES.THIRD, name: '3rd', label: '20.8 Hz' },
    { freq: HARMONIC_FREQUENCIES.FOURTH, name: '4th', label: '27.3 Hz' },
    { freq: HARMONIC_FREQUENCIES.FIFTH, name: '5th', label: '33.8 Hz' },
  ];

  return (
    <Card className="bg-black/40 border-primary/30">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Music className="w-5 h-5 text-primary" />
              Harmonic Keyboard
            </CardTitle>
            <CardDescription>Quantum frequency input interface</CardDescription>
          </div>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant={autoPlay ? "default" : "outline"}
              onClick={() => setAutoPlay(!autoPlay)}
              disabled={disabled}
            >
              <Waves className="w-4 h-4 mr-1" />
              Auto
            </Button>
            <Badge variant={disabled ? "secondary" : "default"}>
              {disabled ? 'Disabled' : 'Active'}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Solfeggio Scale */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Zap className="w-4 h-4 text-success" />
            <h3 className="text-sm font-semibold">Solfeggio Frequencies</h3>
          </div>
          <div className="grid grid-cols-3 gap-2">
            {solfeggioKeys.map(key => (
              <Button
                key={key.name}
                variant="outline"
                className={`h-20 ${key.color} ${activeNotes.has(key.name) ? 'ring-2 ring-white' : ''} transition-all`}
                onClick={() => playNote(key.freq, key.name)}
                disabled={disabled}
              >
                <div className="flex flex-col items-center">
                  <span className="text-lg font-bold">{key.name}</span>
                  <span className="text-xs opacity-70">{key.label}</span>
                </div>
              </Button>
            ))}
          </div>
        </div>

        {/* Schumann Harmonics */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Waves className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-semibold">Schumann Harmonics</h3>
          </div>
          <div className="grid grid-cols-5 gap-2">
            {schumannKeys.map(key => (
              <Button
                key={key.name}
                variant="outline"
                className={`h-16 bg-primary/20 border-primary/50 ${activeNotes.has(key.name) ? 'ring-2 ring-primary' : ''} transition-all`}
                onClick={() => playNote(key.freq, key.name)}
                disabled={disabled}
              >
                <div className="flex flex-col items-center">
                  <span className="text-sm font-bold">{key.name}</span>
                  <span className="text-xs opacity-70">{key.label}</span>
                </div>
              </Button>
            ))}
          </div>
        </div>

        {/* Chord Presets */}
        <div>
          <h3 className="text-sm font-semibold mb-2">Harmonic Chords</h3>
          <div className="grid grid-cols-2 gap-2">
            <Button
              variant="outline"
              className="bg-gradient-to-r from-success/20 to-primary/20"
              onClick={() => playChord([
                { freq: HARMONIC_FREQUENCIES.MI, name: 'MI' },
                { freq: HARMONIC_FREQUENCIES.FUNDAMENTAL, name: 'Fundamental' }
              ])}
              disabled={disabled}
            >
              DNA + Earth
            </Button>
            <Button
              variant="outline"
              className="bg-gradient-to-r from-primary/20 to-primary/20"
              onClick={() => playChord([
                { freq: HARMONIC_FREQUENCIES.LA, name: 'LA' },
                { freq: HARMONIC_FREQUENCIES.THIRD, name: 'Third' }
              ])}
              disabled={disabled}
            >
              Spirit + Harmonic
            </Button>
            <Button
              variant="outline"
              className="bg-gradient-to-r from-destructive/20 to-warning/20"
              onClick={() => playChord([
                { freq: HARMONIC_FREQUENCIES.UT, name: 'UT' },
                { freq: HARMONIC_FREQUENCIES.RE, name: 'RE' }
              ])}
              disabled={disabled}
            >
              Liberation
            </Button>
            <Button
              variant="outline"
              className="bg-gradient-to-r from-primary/20 to-success/20"
              onClick={() => playChord([
                { freq: HARMONIC_FREQUENCIES.FA, name: 'FA' },
                { freq: HARMONIC_FREQUENCIES.FOURTH, name: 'Fourth' }
              ])}
              disabled={disabled}
            >
              Connection
            </Button>
          </div>
        </div>

        {/* Last Played Notes */}
        {lastPlayedNotes.length > 0 && (
          <div className="mt-4 p-3 bg-black/40 rounded-lg border border-border/30">
            <h4 className="text-xs font-semibold mb-2 text-muted-foreground">Recent Notes</h4>
            <div className="flex flex-wrap gap-2">
              {lastPlayedNotes.slice(-6).map((note, i) => (
                <Badge key={i} variant="outline" className="text-xs">
                  {note.name}: {note.frequency.toFixed(2)} Hz
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
