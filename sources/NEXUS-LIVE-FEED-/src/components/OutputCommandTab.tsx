import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import type { AuditRecord } from '@/lib/sero/sero-core';
import KeyStatus from './KeyStatus';

type VaultStatus = Record<string, { present: boolean; masked: string }>;

const formatRelativeTime = (iso?: string) => {
  if (!iso) return 'timestamp pending';
  const value = new Date(iso).getTime();
  if (!Number.isFinite(value)) return 'timestamp pending';
  const deltaMs = Date.now() - value;
  if (deltaMs < 30_000) return 'just now';
  const minutes = Math.floor(deltaMs / 60_000);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
};

type OutputCommandTabProps = {
  latestAudit: AuditRecord[];
  vaultStatus: VaultStatus | null;
  vaultError: string | null;
};

const OutputCommandTab = ({ latestAudit, vaultStatus, vaultError }: OutputCommandTabProps) => (
  <div className="grid gap-6 text-slate-100 lg:grid-cols-2">
    <Card className="relative overflow-hidden border-white/10 bg-slate-950/75 shadow-[0_0_45px_rgba(253,224,71,0.25)]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(253,224,71,0.25),_transparent_65%)] opacity-80" />
      <CardHeader className="relative z-10 pb-4">
        <CardTitle className="text-xl font-semibold tracking-[0.28em] text-white">Command Activity</CardTitle>
        <p className="mt-2 text-sm text-slate-300/85">
          Stewardship audit events stream here—intent, operator, temporal stamp, and score resonance.
        </p>
      </CardHeader>
      <CardContent className="relative z-10 space-y-4">
        {latestAudit.length === 0 ? (
          <p className="rounded-2xl border border-white/10 bg-white/5 px-4 py-6 text-sm text-slate-300/80">
            No stewardship commands executed in this session. Use the Actuation console to initiate one.
          </p>
        ) : (
          latestAudit.map((entry) => {
            const scoreWidth = Math.round((entry.evaluation?.score ?? 0) * 100);
            const scoreTone = scoreWidth >= 70 ? 'from-emerald-400 via-teal-400 to-sky-400' : 'from-amber-400 via-orange-400 to-rose-400';
            return (
              <div key={entry.audit_id} className="group relative overflow-hidden rounded-2xl border border-white/10 bg-white/5 p-[1px]">
                <div className="pointer-events-none absolute inset-0 rounded-2xl bg-white/10 opacity-0 transition duration-500 group-hover:opacity-100" />
                <div className="relative h-full rounded-[calc(1rem-2px)] bg-slate-950/80 p-4">
                  <div className="relative z-10 flex items-center justify-between">
                    <div className="text-sm font-semibold uppercase tracking-[0.22em] text-white">{entry.request.subsystem}</div>
                    <Badge className="px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.3em]" variant={entry.decision === 'ALLOW' ? 'success' : 'warning'}>
                      {entry.decision}
                    </Badge>
                  </div>
                  <div className="relative z-10 mt-1 text-xs text-slate-300/80">{entry.request.intent}</div>
                  <div className="relative z-10 mt-3 flex items-center justify-between text-[11px] uppercase tracking-[0.28em] text-slate-400">
                    <span>{entry.request.operator?.name ?? 'Unknown operator'}</span>
                    <span>{formatRelativeTime(entry.request.ts)}</span>
                  </div>
                  <div className="relative z-10 mt-4 h-2 rounded-full bg-slate-800/80">
                    <div
                      className={cn('h-2 rounded-full shadow-[0_0_18px_rgba(253,224,71,0.35)]', `bg-gradient-to-r ${scoreTone}`)}
                      style={{ width: `${scoreWidth}%` }}
                    />
                  </div>
                </div>
              </div>
            );
          })
        )}
      </CardContent>
    </Card>

    <Card className="relative overflow-hidden border-white/10 bg-slate-950/75 shadow-[0_0_45px_rgba(59,130,246,0.25)]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.2),_transparent_60%)] opacity-80" />
      <CardHeader className="relative z-10 pb-4">
        <CardTitle className="text-xl font-semibold tracking-[0.28em] text-white">Access &amp; Credentials</CardTitle>
        <p className="mt-2 text-sm text-slate-300/85">
          Environment flags mirror live, while vault entries reveal their masked sigils.
        </p>
      </CardHeader>
      <CardContent className="relative z-10 space-y-5">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.32em] text-slate-300/75">Environment Flags</div>
          <div className="mt-3 overflow-hidden rounded-2xl border border-white/10 bg-white/5 p-4">
            <KeyStatus />
          </div>
        </div>
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.32em] text-slate-300/75">Key Vault</div>
          <div className="mt-3 space-y-2">
            {vaultError ? (
              <p className="rounded-xl border border-rose-400/60 bg-rose-500/15 px-3 py-2 text-xs text-rose-100">{vaultError}</p>
            ) : !vaultStatus ? (
              <p className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs text-slate-300/80">Requesting key status…</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {Object.entries(vaultStatus).map(([name, status]) => (
                  <li
                    key={name}
                    className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-3 py-2"
                  >
                    <span className="font-semibold uppercase tracking-[0.22em] text-white/90">{name}</span>
                    <span className={cn('text-xs font-mono tracking-[0.4em]', status.present ? 'text-emerald-200' : 'text-rose-200')}>
                      {status.masked}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
        <p className="text-xs text-slate-300/75">
          Access logs rotate every 24 hours. Stewardship counsel can revoke any credential from the Sero console.
        </p>
      </CardContent>
    </Card>
  </div>
);

export default OutputCommandTab;
