/**
 * AmbientSoundscape - Web Audio API ambient atmosphere
 *
 * Harmonic drone tuned to gaiaFrequency, sub bass pulsing with psi,
 * trade chimes, tension layer from fear, coherence shimmer.
 * Must not autoplay - requires user activation.
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import type { NarratorEventType } from './NarratorEngine';
import { finiteOrNull } from '@/lib/reading';

interface AmbientSoundscapeProps {
  coherence: number | null;
  psi: number | null;
  fearLevel: number | null;
  gaiaFrequency: number | null;
  activeEvent: NarratorEventType | null;
}

export function AmbientSoundscape({
  coherence,
  psi,
  fearLevel,
  gaiaFrequency,
  activeEvent,
}: AmbientSoundscapeProps) {
  const [enabled, setEnabled] = useState(false);
  const ctxRef = useRef<AudioContext | null>(null);
  const masterGainRef = useRef<GainNode | null>(null);
  const droneOscRef = useRef<OscillatorNode | null>(null);
  const droneGainRef = useRef<GainNode | null>(null);
  const subOscRef = useRef<OscillatorNode | null>(null);
  const subGainRef = useRef<GainNode | null>(null);
  const shimmerOscRef = useRef<OscillatorNode | null>(null);
  const shimmerGainRef = useRef<GainNode | null>(null);
  const noiseSourceRef = useRef<AudioBufferSourceNode | null>(null);
  const noiseGainRef = useRef<GainNode | null>(null);
  const lastEventRef = useRef<NarratorEventType | null>(null);

  // Create the audio graph
  const initAudio = useCallback(() => {
    if (ctxRef.current) return;

    const ctx = new AudioContext();
    ctxRef.current = ctx;

    // Master gain
    const master = ctx.createGain();
    master.gain.value = 0.15;
    master.connect(ctx.destination);
    masterGainRef.current = master;

    // Harmonic drone (sine at gaiaFrequency, typically 432Hz)
    const droneGain = ctx.createGain();
    droneGain.gain.value = 0;
    droneGain.connect(master);
    droneGainRef.current = droneGain;

    const drone = ctx.createOscillator();
    drone.type = 'sine';
    const tunedHz = finiteOrNull(gaiaFrequency);
    if (tunedHz != null) drone.frequency.value = tunedHz;
    drone.connect(droneGain);
    drone.start();
    droneOscRef.current = drone;

    // Sub bass (55Hz)
    const subGain = ctx.createGain();
    subGain.gain.value = 0;
    subGain.connect(master);
    subGainRef.current = subGain;

    const sub = ctx.createOscillator();
    sub.type = 'sine';
    sub.frequency.value = 55;
    sub.connect(subGain);
    sub.start();
    subOscRef.current = sub;

    // Coherence shimmer (very high, very quiet)
    const shimmerGain = ctx.createGain();
    shimmerGain.gain.value = 0;
    shimmerGain.connect(master);
    shimmerGainRef.current = shimmerGain;

    const shimmer = ctx.createOscillator();
    shimmer.type = 'sine';
    shimmer.frequency.value = 2000;
    shimmer.connect(shimmerGain);
    shimmer.start();
    shimmerOscRef.current = shimmer;

    // Tension noise layer (filtered white noise)
    const noiseGain = ctx.createGain();
    noiseGain.gain.value = 0;
    const filter = ctx.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.value = 200;
    noiseGain.connect(filter);
    filter.connect(master);
    noiseGainRef.current = noiseGain;

    // Generate white noise buffer
    const bufferSize = ctx.sampleRate * 2;
    const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      data[i] = Math.random() * 2 - 1;
    }
    const noise = ctx.createBufferSource();
    noise.buffer = buffer;
    noise.loop = true;
    noise.connect(noiseGain);
    noise.start();
    noiseSourceRef.current = noise;
  }, [gaiaFrequency]);

  // Toggle audio
  const toggleAudio = useCallback(() => {
    if (enabled) {
      // Fade out and stop
      if (masterGainRef.current && ctxRef.current) {
        masterGainRef.current.gain.linearRampToValueAtTime(0, ctxRef.current.currentTime + 0.5);
        setTimeout(() => {
          ctxRef.current?.close();
          ctxRef.current = null;
          masterGainRef.current = null;
          droneOscRef.current = null;
          droneGainRef.current = null;
          subOscRef.current = null;
          subGainRef.current = null;
          shimmerOscRef.current = null;
          shimmerGainRef.current = null;
          noiseSourceRef.current = null;
          noiseGainRef.current = null;
        }, 600);
      }
      setEnabled(false);
    } else {
      initAudio();
      setEnabled(true);
    }
  }, [enabled, initAudio]);

  // Update audio parameters from data
  useEffect(() => {
    if (!enabled || !ctxRef.current) return;

    const interval = setInterval(() => {
      const ctx = ctxRef.current;
      if (!ctx) return;
      const t = ctx.currentTime;

      const coherenceLevel = finiteOrNull(coherence);
      const psiLevel = finiteOrNull(psi);
      const fear = finiteOrNull(fearLevel);
      const tunedHz = finiteOrNull(gaiaFrequency);

      if (droneGainRef.current && coherenceLevel != null) {
        droneGainRef.current.gain.linearRampToValueAtTime(
          coherenceLevel * 0.15, t + 0.3
        );
      }

      if (droneOscRef.current && tunedHz != null) {
        droneOscRef.current.frequency.linearRampToValueAtTime(
          tunedHz, t + 0.5
        );
      }

      if (subGainRef.current && psiLevel != null) {
        subGainRef.current.gain.linearRampToValueAtTime(
          psiLevel * 0.08, t + 0.3
        );
      }

      if (shimmerGainRef.current && coherenceLevel != null) {
        shimmerGainRef.current.gain.linearRampToValueAtTime(
          coherenceLevel * 0.02, t + 0.3
        );
      }

      if (noiseGainRef.current && fear != null) {
        noiseGainRef.current.gain.linearRampToValueAtTime(
          fear * 0.08, t + 0.3
        );
      }
    }, 200);

    return () => clearInterval(interval);
  }, [enabled, coherence, psi, fearLevel, gaiaFrequency]);

  // Trade chimes on events
  useEffect(() => {
    if (!enabled || !ctxRef.current || !activeEvent) return;
    if (activeEvent === lastEventRef.current) return;
    lastEventRef.current = activeEvent;

    if (activeEvent !== 'trade_buy' && activeEvent !== 'trade_sell') return;

    const ctx = ctxRef.current;
    const master = masterGainRef.current;
    if (!ctx || !master) return;

    const isBuy = activeEvent === 'trade_buy';

    // Create a short chime
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.connect(gain);
    gain.connect(master);

    const t = ctx.currentTime;

    if (isBuy) {
      // Ascending tone: 660 → 880
      osc.frequency.setValueAtTime(660, t);
      osc.frequency.linearRampToValueAtTime(880, t + 0.15);
    } else {
      // Descending tone: 880 → 660
      osc.frequency.setValueAtTime(880, t);
      osc.frequency.linearRampToValueAtTime(660, t + 0.15);
    }

    gain.gain.setValueAtTime(0.12, t);
    gain.gain.exponentialRampToValueAtTime(0.001, t + 0.4);

    osc.start(t);
    osc.stop(t + 0.5);
  }, [enabled, activeEvent]);

  // Cleanup
  useEffect(() => {
    return () => {
      ctxRef.current?.close();
    };
  }, []);

  return (
    <button
      onClick={toggleAudio}
      className="absolute bottom-4 left-4 z-20 px-3 py-1.5 rounded-lg backdrop-blur-xl bg-black/30 border border-white/[0.08] text-white/40 text-xs hover:text-white/70 hover:bg-black/50 transition-all pointer-events-auto cursor-pointer flex items-center gap-1.5"
      style={{ bottom: '60px', left: '50%', transform: 'translateX(-50%)' }}
    >
      <span style={{ fontSize: '10px' }}>{enabled ? '🔊' : '🔇'}</span>
      <span className="uppercase tracking-wider text-[10px]">
        {enabled ? 'Audio On' : 'Enable Audio'}
      </span>
    </button>
  );
}
