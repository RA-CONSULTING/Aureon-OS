import React, { useState } from 'react';
import LyraResonanceStudio from './LyraResonanceStudio';
import SeroComplianceConsole from './SeroComplianceConsole';
import BioResonanceInterface from './BioResonanceInterface';
import { cn } from '@/lib/utils';

const Actuation: React.FC = () => {
  const [activeTab, setActiveTab] = useState('bio-resonance');

  const tabs = [
    { id: 'bio-resonance', label: 'Bio-Resonance' },
    { id: 'lyra', label: 'Lyra Resonance Studio' },
    { id: 'sero', label: 'Sero Law & Shield' },
  ] as const;

  return (
    <section className="space-y-10 text-slate-100">
      <header className="space-y-4">
        <h2 className="text-2xl font-semibold uppercase tracking-[0.3em] text-white">Actuation Command Deck</h2>
        <p className="text-sm text-slate-300/80">
          Invoke resonance, calibrate the Lyra studio, or review Sero safeguard law. Each tab manifests a distinct pillar of the Harmonia nexus.
        </p>
        <nav className="relative overflow-hidden rounded-3xl border border-white/10 bg-white/5 p-2 shadow-[0_0_40px_rgba(14,165,233,0.25)] backdrop-blur">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.25),_transparent_60%)] opacity-80" />
          <ul className="relative z-10 flex flex-wrap gap-2">
            {tabs.map((tab) => (
              <li key={tab.id} className="flex-1 min-w-[180px]">
                <button
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    'group relative flex w-full items-center justify-center overflow-hidden rounded-2xl px-4 py-2 text-xs font-semibold uppercase tracking-[0.32em] transition',
                    'text-slate-300/85 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400/60',
                    activeTab === tab.id && 'text-white shadow-[0_0_35px_rgba(56,189,248,0.35)]'
                  )}
                >
                  <span
                    className={cn(
                      'pointer-events-none absolute inset-0 translate-y-full rounded-2xl bg-gradient-to-r from-cyan-500/40 via-blue-500/30 to-fuchsia-500/35 opacity-0 transition duration-300 group-hover:translate-y-0 group-hover:opacity-100',
                      activeTab === tab.id && 'translate-y-0 opacity-100'
                    )}
                  />
                  <span className="relative z-10">{tab.label}</span>
                </button>
              </li>
            ))}
          </ul>
        </nav>
      </header>

      <div className="space-y-8">
        {activeTab === 'bio-resonance' && <BioResonanceInterface />}
        {activeTab === 'lyra' && <LyraResonanceStudio />}
        {activeTab === 'sero' && <SeroComplianceConsole />}
      </div>
    </section>
  );
};

export default Actuation;
