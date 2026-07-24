/**
 * Approvals — the director's desk.
 *
 * The big plays Aureon prepared and is holding for your call. Polls
 * GET /api/approvals; Approve / Reject POST to /api/approvals/<id>. Approving
 * RECORDS your decision (the human gate) — it does not itself execute the live move
 * (the trade / payment / filing stays your deliberate step). You can also decide by
 * replying to the email Aureon sends.
 */

import { useCallback, useEffect, useState } from "react";
import { ListChecks, ShieldCheck, Check, X } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { LiveDataNotice } from "@/shell/Page";

interface Item {
  id: string;
  kind: string;
  summary: string;
  prepared_by: string;
  risk: string;
  status: "pending" | "approved" | "rejected";
  note?: string;
}

interface Desk {
  pending: Item[];
  recent: Item[];
  counts?: Record<string, number>;
}

export default function ApprovalsPage() {
  const [data, setData] = useState<Desk | null | undefined>(undefined);
  const [busy, setBusy] = useState<string | null>(null);

  const poll = useCallback(async () => {
    try {
      const r = await fetch("/api/approvals");
      if (!r.ok) throw new Error(String(r.status));
      setData(await r.json());
    } catch {
      setData((p) => (p === undefined ? null : p));
    }
  }, []);

  useEffect(() => {
    poll();
    const t = window.setInterval(poll, 5000);
    return () => window.clearInterval(t);
  }, [poll]);

  async function decide(id: string, decision: "approve" | "reject") {
    setBusy(id);
    try {
      const r = await fetch(`/api/approvals/${id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision }),
      });
      if (!r.ok) throw new Error(String(r.status));
      toast.success(`Recorded: ${decision}d`);
      await poll();
    } catch {
      toast.error("Could not record the decision");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <ListChecks className="h-6 w-6 text-primary" />
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Approvals</h1>
          <p className="text-sm text-muted-foreground">
            The director's desk — the big plays Aureon prepared and is holding for your call.
          </p>
        </div>
      </div>

      <LiveDataNotice />

      <div className="flex items-start gap-2 rounded-md border px-3 py-2 text-[11px] text-muted-foreground">
        <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0" />
        <span>
          Approving <strong>records your decision</strong> — the human gate. It does not itself
          execute the live move; the trade, payment, or filing stays your deliberate step. You can
          also decide by replying to the email Aureon sends.
        </span>
      </div>

      {data === undefined && (
        <div className="space-y-3">{Array.from({ length: 2 }).map((_, i) => <Skeleton key={i} className="h-24 w-full" />)}</div>
      )}
      {data === null && (
        <Card><CardHeader><CardTitle>Gateway offline</CardTitle></CardHeader>
          <CardContent className="text-sm text-muted-foreground">Start the operator and retry — this page polls /api/approvals.</CardContent></Card>
      )}

      {data && data.pending?.length === 0 && (
        <Card>
          <CardHeader><CardTitle className="text-base">Desk clear</CardTitle></CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Nothing awaiting your decision. Aureon runs the day-to-day itself and will place any big play here.
          </CardContent>
        </Card>
      )}

      {data && data.pending?.map((it) => (
        <Card key={it.id}>
          <CardHeader className="pb-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <CardTitle className="text-base capitalize">{it.kind}</CardTitle>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="text-[10px]">risk {it.risk}</Badge>
                <Badge variant="outline" className="text-[10px]">by {it.prepared_by}</Badge>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm">{it.summary}</p>
            <div className="flex gap-2">
              <Button size="sm" disabled={busy === it.id} onClick={() => decide(it.id, "approve")}>
                <Check className="mr-1 h-4 w-4" /> Approve
              </Button>
              <Button size="sm" variant="outline" disabled={busy === it.id} onClick={() => decide(it.id, "reject")}>
                <X className="mr-1 h-4 w-4" /> Reject
              </Button>
            </div>
          </CardContent>
        </Card>
      ))}

      {data && data.recent && data.recent.some((r) => r.status !== "pending") && (
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm">Recent decisions</CardTitle></CardHeader>
          <CardContent className="space-y-1.5">
            {data.recent.filter((r) => r.status !== "pending").slice(0, 8).map((r) => (
              <div key={r.id} className="flex items-center justify-between gap-2 rounded-md border px-3 py-1.5 text-sm">
                <span className="min-w-0 truncate"><span className="capitalize">{r.kind}</span> — {r.summary}</span>
                <Badge variant="outline" className={`text-[10px] ${r.status === "approved" ? "text-success" : "text-destructive"}`}>
                  {r.status}
                </Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
