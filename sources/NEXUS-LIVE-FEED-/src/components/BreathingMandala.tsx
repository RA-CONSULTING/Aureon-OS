
import type { HTMLAttributes } from 'react';

import MandalaOverlay from './MandalaOverlay';
import { cn } from '@/lib/utils';

type BreathingMandalaProps = HTMLAttributes<HTMLDivElement>;

export const BreathingMandala = ({ className, ...props }: BreathingMandalaProps) => (
  <div
    className={cn(
      'relative overflow-hidden rounded-3xl border border-white/10 bg-slate-950/70 p-8 text-center text-slate-100 shadow-[0_0_55px_rgba(236,72,153,0.28)]',
      'before:pointer-events-none before:absolute before:inset-0 before:bg-[radial-gradient(circle_at_top,_rgba(236,72,153,0.25),_transparent_60%)] before:opacity-80',
      'after:pointer-events-none after:absolute after:inset-0 after:bg-[radial-gradient(circle_at_bottom,_rgba(56,189,248,0.22),_transparent_65%)] after:opacity-70',
      className,
    )}
    {...props}
  >
    <MandalaOverlay className="opacity-35" />
    <div className="relative z-10 space-y-6">
      <div className="space-y-2">
        <h3 className="text-lg font-semibold uppercase tracking-[0.32em] text-white">Guardian–Anchor Mandala</h3>
        <p className="text-xs text-slate-300/80">
          Synchronize your breath to the luminous pulse—inhale as the halo expands, exhale as the nexus gathers.
        </p>
      </div>
      <div className="relative mx-auto flex h-60 w-60 items-center justify-center">
        <div className="absolute inset-0 rounded-full border border-white/20" />
        <div className="absolute inset-3 rounded-full border border-white/10" />
        <div className="absolute inset-0 animate-[spin_36s_linear_infinite] rounded-full bg-[conic-gradient(from_120deg,_rgba(56,189,248,0.18)_0%,_rgba(236,72,153,0.2)_45%,_rgba(251,191,36,0.18)_90%,_rgba(56,189,248,0.18)_100%)] blur-sm" />
        <div className="absolute inset-8 animate-[ping_9s_ease-in-out_infinite] rounded-full border border-white/15" />
        <div className="absolute inset-14 rounded-full bg-[radial-gradient(circle,_rgba(15,23,42,0.8),_rgba(15,23,42,0.35)_65%,_rgba(56,189,248,0.2)_100%)] shadow-[0_0_45px_rgba(56,189,248,0.25)]" />
        <div className="absolute inset-20 rounded-full border border-white/10" />
        <div className="relative flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-white/15 via-white/5 to-transparent text-2xl font-semibold tracking-[0.3em] text-white shadow-[0_0_35px_rgba(255,255,255,0.3)]">
          ✶
        </div>
      </div>
      <p className="text-[11px] uppercase tracking-[0.38em] text-slate-300/75">Breath cadence · 7.83 Hz</p>
    </div>
  </div>
);

export default BreathingMandala;
