import { useRef } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

declare global {
  interface Navigator {
    xr?: {
      requestSession: (mode: string) => Promise<XRSession>;
    };
  }

  interface XRSession {
    addEventListener: (type: string, handler: () => void) => void;
  }
}

const MetaQuestLink = () => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const startVR = async () => {
    if (!navigator.xr) {
      alert('WebXR not supported in this browser.');
      return;
    }
    try {
      const session = await navigator.xr.requestSession('immersive-vr');
      console.log('Meta Quest session started', session);
      session.addEventListener('end', () => console.log('XR session ended'));
    } catch (err) {
      console.error('Failed to start XR session', err);
    }
  };

  return (
    <section className="relative overflow-hidden rounded-[36px] border border-white/10 bg-slate-950/65 p-6 text-slate-100 shadow-[0_0_65px_rgba(251,191,36,0.25)]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(251,191,36,0.24),_transparent_60%)] opacity-80" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_bottom,_rgba(56,189,248,0.2),_transparent_60%)] opacity-70" />
      <div className="relative z-10 space-y-8">
        <header className="space-y-4 text-center">
          <Badge className="mx-auto inline-flex items-center rounded-full border-white/20 bg-white/10 px-5 py-1 text-[11px] font-semibold uppercase tracking-[0.36em] text-white/85" variant="outline">
            Meta Quest Bridge
          </Badge>
          <h1 className="bg-gradient-to-r from-amber-200 via-sky-200 to-fuchsia-200 bg-clip-text text-4xl font-bold tracking-[0.32em] text-transparent sm:text-5xl">
            Immersive Nexus Portal
          </h1>
          <p className="mx-auto max-w-2xl text-sm leading-relaxed text-slate-300/85">
            Launch the WebXR session to step into the radiant console. The aurora interface, glyph lattices, and live spectrographs appear within a Meta Quest dome.
          </p>
        </header>

        <Card className="relative overflow-hidden border-white/10 bg-slate-950/75 text-slate-100 shadow-[0_0_55px_rgba(251,191,36,0.28)]">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(251,191,36,0.24),_transparent_60%)] opacity-75" />
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_bottom,_rgba(236,72,153,0.2),_transparent_65%)] opacity-70" />
          <CardHeader className="relative z-10 pb-3">
            <CardTitle className="text-lg font-semibold uppercase tracking-[0.26em] text-white">
              Session Controls
            </CardTitle>
          </CardHeader>
          <CardContent className="relative z-10 space-y-5 text-sm text-slate-200/85">
            <p>
              Ensure your Meta Quest headset is nearby and the browser has WebXR enabled. When ready, ignite the bridge and the console will render around you.
            </p>
            <Button
              type="button"
              onClick={startVR}
              className="w-full rounded-full border border-amber-400/50 bg-gradient-to-r from-amber-500/40 via-rose-500/35 to-fuchsia-500/35 px-6 py-3 text-xs font-semibold uppercase tracking-[0.32em] text-white shadow-[0_0_35px_rgba(251,191,36,0.35)] transition hover:shadow-[0_0_45px_rgba(251,191,36,0.45)]"
            >
              Enter Meta Quest VR
            </Button>
            <div className="grid gap-3 rounded-3xl border border-white/10 bg-white/5 p-4 text-xs text-slate-200/80 sm:grid-cols-3">
              <div className="rounded-2xl border border-white/10 bg-white/5 px-3 py-2 text-center uppercase tracking-[0.28em] text-white/85">WebXR Enabled</div>
              <div className="rounded-2xl border border-white/10 bg-white/5 px-3 py-2 text-center uppercase tracking-[0.28em] text-white/85">Guardian Console</div>
              <div className="rounded-2xl border border-white/10 bg-white/5 px-3 py-2 text-center uppercase tracking-[0.28em] text-white/85">Harmonic Audio</div>
            </div>
            <canvas ref={canvasRef} className="hidden" />
          </CardContent>
        </Card>
      </div>
    </section>
  );
};

export default MetaQuestLink;
