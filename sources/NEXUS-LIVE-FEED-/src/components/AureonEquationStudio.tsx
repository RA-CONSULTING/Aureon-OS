import { useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { asCSV, compileIntuition, flattenResults, runAureon, type EquationResult } from '@/lib/aureon/aureon-core';

type Status = 'IDLE' | 'COMPILED' | 'RUN' | 'ERROR';
type ResultWithId = EquationResult & { resultId: string };

type StatusVisual = {
  label: string;
  className: string;
};

const STATUS_STYLE: Record<Status, StatusVisual> = {
  IDLE: {
    label: 'Idle',
    className: 'border-white/20 bg-white/10 text-white/85',
  },
  COMPILED: {
    label: 'Compiled',
    className: 'border-sky-400/50 bg-sky-500/20 text-sky-100 shadow-[0_0_35px_rgba(56,189,248,0.35)]',
  },
  RUN: {
    label: 'Run Complete',
    className: 'border-emerald-400/50 bg-emerald-500/25 text-emerald-100 shadow-[0_0_35px_rgba(16,185,129,0.35)]',
  },
  ERROR: {
    label: 'Error',
    className: 'border-rose-400/50 bg-rose-500/25 text-rose-100 shadow-[0_0_35px_rgba(244,63,94,0.35)]',
  },
};

const intentPlaceholder = `Coherence phasor for planetary songbook; unison threads via Kuramoto; glyph spiral check; echo recognition.`;

function download(name: string, data: string, type = 'text/plain') {
  const blob = new Blob([data], { type });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  URL.revokeObjectURL(a.href);
}

const AureonEquationStudio = () => {
  const [text, setText] = useState<string>(intentPlaceholder);
  const [compiled, setCompiled] = useState<{ equations: string[]; notes?: string } | null>(null);
  const [results, setResults] = useState<ResultWithId[]>([]);
  const [status, setStatus] = useState<Status>('IDLE');
  const [error, setError] = useState<string>('');

  const onCompile = () => {
    try {
      const intent = compileIntuition(text);
      setCompiled({ equations: intent.equations, notes: intent.notes });
      setStatus('COMPILED');
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus('ERROR');
    }
  };

  const onRun = () => {
    try {
      const intent = compileIntuition(text);
      const outcome = runAureon({ intent, data: {} });
      if (!outcome.ok) {
        setError(outcome.errors?.join('; ') ?? 'Unknown');
        setStatus('ERROR');
        return;
      }
      const withIds = outcome.results.map((result, index) => ({
        ...result,
        resultId: `${result.id}-${index}-${Date.now()}`,
      }));
      setResults(withIds);
      setStatus('RUN');
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus('ERROR');
    }
  };

  const onExportCSV = () => {
    const csv = asCSV(flattenResults(results));
    download('aureon_results.csv', csv, 'text/csv');
  };

  const onExportJSON = () => {
    download('aureon_results.json', JSON.stringify(results, null, 2), 'application/json');
  };

  const onCopyTeX = () => {
    if (!results.length) return;
    const tex = results.flatMap((result) => result.tex).join('\n\n');
    void navigator.clipboard.writeText(tex);
  };

  const disableExports = results.length === 0;

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
      <Card className="relative overflow-hidden border-white/10 bg-slate-950/75 text-slate-100 shadow-[0_0_55px_rgba(59,130,246,0.25)]">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.24),_transparent_60%)] opacity-80" />
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_bottom,_rgba(236,72,153,0.2),_transparent_65%)] opacity-75" />
        <CardHeader className="relative z-10 flex flex-col gap-3 pb-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle className="text-xl font-semibold uppercase tracking-[0.26em] text-white">
              Equation Intent Composer
            </CardTitle>
            <p className="mt-1 text-xs text-slate-300/80">
              Weave the intent phrase—the Aureon lattice parses resonance terms into equations and symbolic directives.
            </p>
          </div>
          <Badge className={`rounded-full px-4 py-1 text-[10px] font-semibold uppercase tracking-[0.3em] ${STATUS_STYLE[status].className}`} variant="outline">
            {STATUS_STYLE[status].label}
          </Badge>
        </CardHeader>
        <CardContent className="relative z-10 space-y-4 text-sm text-slate-200/85">
          <textarea
            value={text}
            onChange={(event) => setText(event.target.value)}
            className="h-32 w-full rounded-3xl border border-white/10 bg-slate-950/70 p-4 text-sm text-white shadow-[0_0_35px_rgba(148,163,184,0.25)] outline-none transition focus:border-sky-400/60 focus:shadow-[0_0_45px_rgba(56,189,248,0.35)]"
          />
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              onClick={onCompile}
              className="rounded-full border border-sky-400/60 bg-gradient-to-r from-sky-500/40 via-indigo-500/35 to-fuchsia-500/35 px-5 py-2 text-xs font-semibold uppercase tracking-[0.32em] text-white shadow-[0_0_35px_rgba(59,130,246,0.35)] transition hover:shadow-[0_0_45px_rgba(59,130,246,0.45)]"
            >
              Compile
            </Button>
            <Button
              type="button"
              onClick={onRun}
              className="rounded-full border border-emerald-400/50 bg-gradient-to-r from-emerald-500/40 via-teal-500/35 to-sky-500/35 px-5 py-2 text-xs font-semibold uppercase tracking-[0.32em] text-white shadow-[0_0_35px_rgba(16,185,129,0.35)] transition hover:shadow-[0_0_45px_rgba(16,185,129,0.45)]"
              variant="ghost"
            >
              Run
            </Button>
            <Button
              type="button"
              onClick={onExportCSV}
              disabled={disableExports}
              className="rounded-full border border-white/15 bg-white/5 px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-100 transition disabled:opacity-40"
              variant="ghost"
            >
              Export CSV
            </Button>
            <Button
              type="button"
              onClick={onExportJSON}
              disabled={disableExports}
              className="rounded-full border border-white/15 bg-white/5 px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-100 transition disabled:opacity-40"
              variant="ghost"
            >
              Export JSON
            </Button>
            <Button
              type="button"
              onClick={onCopyTeX}
              disabled={disableExports}
              className="rounded-full border border-white/15 bg-white/5 px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-100 transition disabled:opacity-40"
              variant="ghost"
            >
              Copy TeX
            </Button>
          </div>
          {compiled ? (
            <div className="rounded-3xl border border-white/10 bg-white/5 p-4 text-xs text-slate-200/85">
              <div className="text-[11px] uppercase tracking-[0.28em] text-slate-300/75">Equations</div>
              <p className="mt-2 leading-relaxed text-white">{compiled.equations.join(', ')}</p>
              {compiled.notes ? <p className="mt-2 text-[11px] text-slate-300/80">Notes: {compiled.notes}</p> : null}
            </div>
          ) : null}
          {error ? <div className="rounded-2xl border border-rose-400/40 bg-rose-500/20 px-4 py-2 text-xs text-rose-100">{error}</div> : null}
        </CardContent>
      </Card>

      <Card className="relative overflow-hidden border-white/10 bg-slate-950/75 text-slate-100 shadow-[0_0_55px_rgba(236,72,153,0.25)]">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(236,72,153,0.24),_transparent_60%)] opacity-80" />
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_bottom,_rgba(251,191,36,0.18),_transparent_65%)] opacity-70" />
        <CardHeader className="relative z-10 pb-4">
          <CardTitle className="text-xl font-semibold uppercase tracking-[0.26em] text-white">
            Equation Results & Interpretations
          </CardTitle>
        </CardHeader>
        <CardContent className="relative z-10 space-y-4 text-sm text-slate-200/85">
          {results.length === 0 ? (
            <div className="rounded-3xl border border-white/10 bg-white/5 p-6 text-center text-xs uppercase tracking-[0.32em] text-slate-300/75">
              Run the lattice to materialize results.
            </div>
          ) : (
            results.map((result) => (
              <div key={result.resultId} className="relative overflow-hidden rounded-3xl border border-white/10 bg-slate-950/70 p-5 shadow-[0_0_35px_rgba(148,163,184,0.25)]">
                <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(236,72,153,0.2),_transparent_60%)] opacity-70" />
                <div className="relative z-10 space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="text-sm font-semibold uppercase tracking-[0.24em] text-white">{result.id}</div>
                    <Badge className="rounded-full border-white/15 bg-white/10 px-4 py-1 text-[10px] font-semibold uppercase tracking-[0.3em] text-white/85" variant="outline">
                      Values
                    </Badge>
                  </div>
                  <div className="grid gap-4 text-xs text-slate-200/85 sm:grid-cols-2">
                    <div className="space-y-1">
                      {Object.entries(result.values).map(([key, value]) => (
                        <div key={key} className="flex items-baseline justify-between gap-2 border-b border-white/5 pb-1">
                          <span className="text-[11px] uppercase tracking-[0.28em] text-slate-300/75">{key}</span>
                          <span className="text-white">{Number.isFinite(value) ? Number(value).toFixed(6) : String(value)} {result.units[key] ?? ''}</span>
                        </div>
                      ))}
                    </div>
                    <div className="space-y-1">
                      <div className="text-[11px] uppercase tracking-[0.28em] text-slate-300/75">Meaning</div>
                      <ul className="list-disc space-y-1 pl-4 text-left text-slate-200/90">
                        {result.meaning.map((line, index) => (
                          <li key={index}>{line}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                  <details className="rounded-2xl border border-white/10 bg-white/5 p-3 text-xs">
                    <summary className="cursor-pointer text-[11px] uppercase tracking-[0.32em] text-slate-300/80">
                      TeX Output
                    </summary>
                    <pre className="mt-2 whitespace-pre-wrap text-[11px] leading-relaxed text-slate-200/90">{result.tex.join('\n')}</pre>
                  </details>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default AureonEquationStudio;
