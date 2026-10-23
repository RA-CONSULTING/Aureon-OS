import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ModeMatrix } from "@/lib/modeMatrix";

interface ModeMatrixPanelProps {
  matrix: ModeMatrix;
}

const titleFor = (key: string) =>
  key
    .split("_")
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");

const ModeMatrixPanel = ({ matrix }: ModeMatrixPanelProps) => (
  <Card className="relative overflow-hidden border-white/10 bg-slate-950/70 text-slate-100 shadow-[0_0_45px_rgba(56,189,248,0.25)]">
    <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.2),_transparent_65%)] opacity-80" />
    <CardHeader className="relative z-10 pb-4">
      <CardTitle className="text-xl font-semibold tracking-[0.28em] text-white">Mode Synchronization Matrix</CardTitle>
      <p className="mt-2 text-sm text-slate-300/85">
        Version {matrix.version} · Trigger pathways mapped to the observatory outputs and safeguarded by the Sentinel hooks.
      </p>
    </CardHeader>
    <CardContent className="relative z-10 space-y-6">
      <div className="grid gap-4 lg:grid-cols-2">
        {matrix.modes.map((mode) => (
          <div
            key={mode.id}
            className="group relative flex flex-col gap-3 overflow-hidden rounded-2xl border border-white/10 bg-white/5 p-[1px]"
          >
            <div className="pointer-events-none absolute inset-0 rounded-2xl bg-white/10 opacity-0 transition duration-500 group-hover:opacity-100" />
            <div className="relative z-10 flex flex-col gap-4 rounded-[calc(1rem-2px)] bg-slate-950/80 p-5">
              <div className="flex flex-col gap-1">
                <span className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-300/80">{mode.id}</span>
                <span className="text-sm text-slate-300/75">
                  Guardian pathways engage when triggers align with this mode&apos;s resonance signature.
                </span>
              </div>
              <div className="space-y-2 text-xs">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="info" className="uppercase tracking-[0.25em]">Triggers</Badge>
                  {mode.triggers.map((trigger) => (
                    <Badge key={`${mode.id}-trigger-${trigger}`} variant="secondary" className="tracking-[0.15em]">
                      {trigger}
                    </Badge>
                  ))}
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="success" className="uppercase tracking-[0.25em]">Outputs</Badge>
                  {mode.outputs.map((output) => (
                    <Badge key={`${mode.id}-output-${output}`} variant="outline" className="tracking-[0.15em]">
                      {output}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-sky-400/30 bg-sky-500/10 p-4 backdrop-blur">
          <h3 className="text-sm font-semibold uppercase tracking-[0.26em] text-sky-100">Safety Hooks</h3>
          <p className="mt-1 text-xs text-slate-300/80">
            Hard floors and explainability mandates ensure phase guardians remain within acceptable coherence bands.
          </p>
          <dl className="mt-3 space-y-2 text-sm text-slate-100">
            {Object.entries(matrix.safety_hooks).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between gap-2">
                <dt className="text-[11px] uppercase tracking-[0.28em] text-slate-300/75">{titleFor(key)}</dt>
                <dd className="text-sm font-semibold text-white">
                  {typeof value === "boolean" ? (value ? "Enabled" : "Disabled") : value}
                </dd>
              </div>
            ))}
          </dl>
        </div>
        <div className="rounded-2xl border border-fuchsia-400/30 bg-fuchsia-500/10 p-4 backdrop-blur">
          <h3 className="text-sm font-semibold uppercase tracking-[0.26em] text-fuchsia-100">Interfaces</h3>
          <p className="mt-1 text-xs text-slate-300/80">
            Compiler and ethics references linked for quick inspection of symbolic and governance layers.
          </p>
          <dl className="mt-3 space-y-2 text-sm text-slate-100">
            {Object.entries(matrix.interfaces).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between gap-2">
                <dt className="text-[11px] uppercase tracking-[0.28em] text-slate-300/75">{titleFor(key)}</dt>
                <dd className="text-sm font-semibold text-white">{value}</dd>
              </div>
            ))}
          </dl>
        </div>
      </div>
    </CardContent>
  </Card>
);

export default ModeMatrixPanel;
