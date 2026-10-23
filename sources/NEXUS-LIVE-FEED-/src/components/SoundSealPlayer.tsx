
import { useState, useRef } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export const SoundSealPlayer = ({ className }: { className?: string }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
    } else {
      void audioRef.current.play();
    }
    setIsPlaying((state) => !state);
  };

  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-3xl border border-white/10 bg-slate-950/70 p-6 text-center text-slate-100 shadow-[0_0_55px_rgba(168,85,247,0.28)]',
        'before:pointer-events-none before:absolute before:inset-0 before:bg-[radial-gradient(circle_at_top,_rgba(168,85,247,0.2),_transparent_60%)] before:opacity-80',
        'after:pointer-events-none after:absolute after:inset-0 after:bg-[radial-gradient(circle_at_bottom,_rgba(251,191,36,0.2),_transparent_65%)] after:opacity-70',
        className,
      )}
    >
      <div className="relative z-10 space-y-5">
        <div className="flex flex-col items-center gap-3">
          <Badge className="rounded-full border-white/15 bg-white/10 px-4 py-1 text-[11px] font-semibold uppercase tracking-[0.32em] text-white/85" variant="outline">
            Sound Seal Protocol
          </Badge>
          <h3 className="text-lg font-semibold uppercase tracking-[0.3em] text-white">Guardian–Anchor Breath</h3>
          <p className="max-w-sm text-xs text-slate-300/80">
            Loop the resonance bed to stabilize your shared field. Activate or pause the seal as you phase between ritual stages.
          </p>
        </div>
        <audio ref={audioRef} src="https://storage.googleapis.com/gemini-codelab/Guardian-Anchor-Breathing-Sound.wav" loop />
        <Button
          onClick={togglePlay}
          className="mx-auto inline-flex items-center justify-center rounded-full border border-white/15 bg-gradient-to-r from-fuchsia-500/40 via-purple-500/40 to-amber-400/40 px-8 py-2 text-sm font-semibold uppercase tracking-[0.32em] text-white shadow-[0_0_35px_rgba(236,72,153,0.3)] transition hover:shadow-[0_0_45px_rgba(236,72,153,0.45)]"
        >
          {isPlaying ? 'Pause Seal' : 'Play Seal'}
        </Button>
        <p className="text-[11px] uppercase tracking-[0.38em] text-slate-300/70">Length · 8m 12s · Loop Enabled</p>
      </div>
    </div>
  );
};

export default SoundSealPlayer;
