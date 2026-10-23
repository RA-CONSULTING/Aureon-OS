import React from 'react';
import { Badge } from '@/components/ui/badge';
import { useSero } from '../contexts/SeroProvider';

const ACTION_BUTTON =
  'inline-flex items-center justify-center rounded-xl border border-white/15 bg-white/10 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.3em] text-slate-100 transition hover:border-cyan-300/60 hover:bg-cyan-500/20';

const CONTROL_CARD =
  'relative overflow-hidden rounded-2xl border border-white/10 bg-slate-950/80 p-4 shadow-[0_0_30px_rgba(59,130,246,0.12)]';

const SeroComplianceConsole: React.FC = () => {
  const { config, updateConfig, audit, directives } = useSero();

  const formatScore = (score: number) => `${Math.round(score * 100)}%`;

  const directiveFlag = (flag: boolean, on = 'REQUIRED', off = 'ADVISORY') =>
    flag ? on : off;

  return (
    <section className="relative overflow-hidden rounded-3xl border border-white/10 bg-slate-950/70 p-6 text-slate-100 shadow-[0_0_45px_rgba(37,99,235,0.25)]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(37,99,235,0.22),_transparent_60%)] opacity-80" />
      <div className="relative z-10 grid gap-8">
        <header className="space-y-3">
          <h3 className="text-xl font-semibold uppercase tracking-[0.3em] text-white">Sero Law &amp; Shield Configuration</h3>
          <p className="text-sm text-slate-300/80">
            Configure the guardian lattice—simulation gates, dual consent, provenance, and minimum score thresholds.
          </p>
          <div className="flex flex-wrap gap-2 text-[11px] uppercase tracking-[0.28em]">
            <Badge className="px-3 py-1" variant="outline">Min Score · {formatScore(config.minCompositeScore)}</Badge>
            <Badge className="px-3 py-1" variant={config.allowSimulationOnly ? 'warning' : 'success'}>
              Sim Only · {config.allowSimulationOnly ? 'Enabled' : 'Live'}
            </Badge>
            <Badge className="px-3 py-1" variant={config.requireDualConsent ? 'success' : 'warning'}>
              Dual Consent · {config.requireDualConsent ? 'Required' : 'Bypass'}
            </Badge>
            <Badge className="px-3 py-1" variant={config.publicProvenanceRequired ? 'success' : 'secondary'}>
              Provenance · {config.publicProvenanceRequired ? 'Public' : 'Optional'}
            </Badge>
          </div>
        </header>

        <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-white/5 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-[0.3em] text-white/85">
              Prime Guardian Directives
            </span>
            <Badge className="px-3 py-1 text-[10px]" variant="outline">
              Γ ≥ {directives.minGamma.toFixed(2)}
            </Badge>
            <Badge className="px-3 py-1 text-[10px]" variant="outline">
              Log ≥ {directives.minLogRateHz} Hz
            </Badge>
          </div>
          <p className="mt-2 text-[11px] leading-relaxed text-slate-300/80">
            {directives.primeDirective || 'Prime directive not declared.'}
          </p>
          <div className="mt-3 grid gap-2 text-[10px] uppercase tracking-[0.28em] text-slate-300/70 sm:grid-cols-2 xl:grid-cols-3">
            <span>Energy Budget · {directiveFlag(directives.respectEnergyBudget)}</span>
            <span>Transparency · {directiveFlag(directives.requireTransparency)}</span>
            <span>Graceful Failure · {directiveFlag(directives.requireGracefulFailure)}</span>
            <span>No Weaponization · {directiveFlag(directives.enforceNoWeaponization, 'ENFORCED', 'ADVISORY')}</span>
            <span>Auto-Retune · {directiveFlag(directives.requireAutoRetune)}</span>
            <span>Safe-Idle · {directiveFlag(directives.requireSafeIdle)}</span>
            <span>Explainability · {directiveFlag(directives.explainabilityRequired)}</span>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div className={`${CONTROL_CARD} bg-gradient-to-br from-sky-500/15 via-transparent to-transparent`}>
            <span className="text-xs font-semibold uppercase tracking-[0.3em] text-white/85">Sim-Only Mode</span>
            <div className="mt-4 flex gap-2">
              <button className={ACTION_BUTTON} onClick={() => updateConfig({ allowSimulationOnly: true })}>
                Simulate
              </button>
              <button className={ACTION_BUTTON} onClick={() => updateConfig({ allowSimulationOnly: false })}>
                Live
              </button>
            </div>
          </div>
          <div className={`${CONTROL_CARD} bg-gradient-to-br from-emerald-500/15 via-transparent to-transparent`}>
            <span className="text-xs font-semibold uppercase tracking-[0.3em] text-white/85">Dual Consent</span>
            <div className="mt-4 flex gap-2">
              <button className={ACTION_BUTTON} onClick={() => updateConfig({ requireDualConsent: true })}>
                Require
              </button>
              <button className={ACTION_BUTTON} onClick={() => updateConfig({ requireDualConsent: false })}>
                Bypass
              </button>
            </div>
          </div>
          <div className={`${CONTROL_CARD} bg-gradient-to-br from-rose-500/15 via-transparent to-transparent`}>
            <span className="text-xs font-semibold uppercase tracking-[0.3em] text-white/85">Public Provenance</span>
            <div className="mt-4 flex gap-2">
              <button className={ACTION_BUTTON} onClick={() => updateConfig({ publicProvenanceRequired: true })}>
                Require
              </button>
              <button className={ACTION_BUTTON} onClick={() => updateConfig({ publicProvenanceRequired: false })}>
                Optional
              </button>
            </div>
          </div>
          <div className={`${CONTROL_CARD} bg-gradient-to-br from-amber-500/15 via-transparent to-transparent`}>
            <span className="text-xs font-semibold uppercase tracking-[0.3em] text-white/85">Minimum Score</span>
            <div className="mt-4 flex gap-2">
              <button className={ACTION_BUTTON} onClick={() => updateConfig({ minCompositeScore: 0.8 })}>
                80%
              </button>
              <button className={ACTION_BUTTON} onClick={() => updateConfig({ minCompositeScore: 0.9 })}>
                90%
              </button>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold uppercase tracking-[0.3em] text-white">Audit Trail</h4>
            <span className="text-[11px] uppercase tracking-[0.32em] text-slate-300/70">{audit.length} Entries</span>
          </div>
          <div className="grid max-h-[28rem] gap-4 overflow-y-auto pr-1">
            {audit.length === 0 ? (
              <p className="rounded-2xl border border-white/10 bg-white/5 px-4 py-6 text-sm text-slate-300/75">
                No entries yet. Propose an action to populate this chronicle.
              </p>
            ) : (
              audit.map((entry) => (
                <article
                  key={entry.audit_id}
                  className="group relative overflow-hidden rounded-2xl border border-white/10 bg-white/5 p-[1px]"
                >
                  <div className="pointer-events-none absolute inset-0 rounded-2xl bg-white/10 opacity-0 transition duration-500 group-hover:opacity-100" />
                  <div className="relative rounded-[calc(1rem-2px)] bg-slate-950/80 p-4">
                    <div className="flex flex-wrap items-center gap-3">
                      <h5 className="text-sm font-semibold uppercase tracking-[0.24em] text-white">
                        {entry.request.intent}
                      </h5>
                      <Badge className="px-3 py-1 text-[10px]" variant={entry.decision === 'ALLOW' ? 'success' : 'warning'}>
                        {entry.decision}
                      </Badge>
                      <Badge className="px-3 py-1 text-[10px]" variant="outline">
                        {formatScore(entry.evaluation.score)}
                      </Badge>
                    </div>
                    <div className="mt-2 text-xs text-slate-300/80">{entry.ts}</div>
                    <div className="mt-3 flex flex-wrap gap-2 text-[10px] uppercase tracking-[0.3em]">
                      {entry.evaluation.verdicts.map((verdict, index) => (
                        <Badge
                          key={`${entry.audit_id}-${index}`}
                          className="px-2 py-0.5"
                          variant={verdict.pass ? 'success' : 'destructive'}
                        >
                          {verdict.code}
                          {!verdict.pass ? ' ✖' : ''}
                        </Badge>
                      ))}
                    </div>
                    <details className="mt-4 text-xs text-slate-300/75">
                      <summary className="cursor-pointer text-[11px] uppercase tracking-[0.32em] text-slate-200">
                        Details
                      </summary>
                      <pre className="mt-3 max-h-48 overflow-auto rounded-2xl border border-white/10 bg-slate-950/90 p-3 text-[11px] leading-relaxed text-slate-200/80">
                        {JSON.stringify(entry, null, 2)}
                      </pre>
                    </details>
                  </div>
                </article>
              ))
            )}
          </div>
        </div>
      </div>
    </section>
  );
};

export default SeroComplianceConsole;
