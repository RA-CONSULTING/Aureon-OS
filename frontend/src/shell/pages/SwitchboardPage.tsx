/**
 * Feature Switchboard — turn every system feature on/off at human discretion.
 *
 * Instance-owned flags, stored encrypted on the server and applied to the
 * environment at each daemon's boot. Safe flags are simple toggles; hard-boundary
 * flags (live trading, armed local actions, soul-act, billing charge, sovereign
 * mode) require a typed-confirm arming gesture and carry a prominent warning —
 * flipping one only records the human's intent, it never removes a downstream
 * gate (conscience veto, approval queue, runtime dry-run all stay in force).
 *
 * Reads GET /api/switchboard; writes POST /api/switchboard/<id>.
 */

import { useEffect, useState } from "react";
import { SlidersHorizontal, Loader2, ShieldAlert } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { LiveDataNotice } from "@/shell/Page";

interface Flag {
  id: string;
  env_var: string;
  label: string;
  group: string;
  kind: "safe" | "hard_boundary";
  effect: "live" | "restart";
  effect_note: string;
  description: string;
  default: boolean;
  enabled: boolean;
  stored: boolean | null;
  source: "store" | "env" | "default";
  armed: boolean;
  decided_at: number | null;
  pending_restart: boolean | null;
}

interface Group {
  label: string;
  flags: Flag[];
}

interface Summary {
  total: number;
  enabled: number;
  armed: number;
  pending_restart: number;
  hard_boundary_total: number;
}

export default function SwitchboardPage() {
  // undefined = loading, null = gateway offline, array = data
  const [groups, setGroups] = useState<Group[] | null | undefined>(undefined);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [saving, setSaving] = useState<string | null>(null);
  const [arm, setArm] = useState<Flag | null>(null); // hard-boundary confirm dialog
  const [armText, setArmText] = useState("");

  async function load() {
    try {
      const r = await fetch("/api/switchboard");
      if (!r.ok) throw new Error(String(r.status));
      const data = await r.json();
      setGroups(data.groups ?? []);
      setSummary(data.summary ?? null);
    } catch {
      setGroups(null);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function post(flag: Flag, enabled: boolean, confirm?: string) {
    setSaving(flag.id);
    try {
      const body: Record<string, unknown> = { enabled };
      if (confirm) body.confirm = confirm;
      const r = await fetch(`/api/switchboard/${flag.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const v = await r.json();
      if (!r.ok) throw new Error(v?.error?.message || String(r.status));
      toast.success(`${flag.label} ${enabled ? "on" : "off"}`, { description: v.applied });
      await load();
    } catch (e) {
      toast.error(`Could not change ${flag.label}`, { description: String((e as Error).message) });
    } finally {
      setSaving(null);
    }
  }

  function onToggle(flag: Flag, next: boolean) {
    // Arming a hard-boundary flag needs the typed-confirm ceremony; disabling never does.
    if (flag.kind === "hard_boundary" && next) {
      setArm(flag);
      setArmText("");
      return;
    }
    post(flag, next);
  }

  function confirmArm() {
    if (!arm) return;
    const flag = arm;
    setArm(null);
    post(flag, true, flag.id);
  }

  function effectBadge(f: Flag) {
    return f.effect === "live" ? (
      <Badge className="bg-success hover:bg-success">live</Badge>
    ) : (
      <Badge variant="outline">restart</Badge>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <SlidersHorizontal className="h-6 w-6 text-primary" />
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Switchboard</h1>
          <p className="text-sm text-muted-foreground">
            Turn every system feature on or off at your discretion. Choices are stored encrypted on
            the server and picked up by each service at boot. Arming a hard-boundary feature only
            records your intent — every safety gate stays in force.
          </p>
        </div>
      </div>

      <LiveDataNotice />

      {summary && (
        <div className="flex flex-wrap gap-2 text-sm">
          <Badge variant="secondary">{summary.enabled}/{summary.total} enabled</Badge>
          <Badge
            className={
              summary.armed > 0
                ? "bg-destructive hover:bg-destructive"
                : "bg-success hover:bg-success"
            }
          >
            {summary.armed} armed / {summary.hard_boundary_total} hard-boundary
          </Badge>
          {summary.pending_restart > 0 && (
            <Badge variant="outline" className="border-warning/50 text-warning">
              {summary.pending_restart} pending restart
            </Badge>
          )}
        </div>
      )}

      {groups === undefined && (
        <div className="grid gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-40 w-full" />
          ))}
        </div>
      )}

      {groups === null && (
        <Card>
          <CardHeader>
            <CardTitle>Gateway offline</CardTitle>
            <CardDescription>
              The operator API is not reachable. Start the operator (or open the deployed URL) and
              retry.
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      {Array.isArray(groups) &&
        groups.map((group) => {
          const hard = group.label === "Hard Boundary";
          return (
            <Card key={group.label} className={hard ? "border-destructive/50" : undefined}>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-lg">
                  {hard && <ShieldAlert className="h-5 w-5 text-destructive" />}
                  {group.label}
                </CardTitle>
                {hard && (
                  <CardDescription className="text-destructive">
                    Consequential features. Arming one records your decision only — the conscience
                    veto, the approval queue (records, never executes), and the runtime dry-run gates
                    all stay in force. No internal score can arm these; only you can.
                  </CardDescription>
                )}
              </CardHeader>
              <CardContent className="divide-y">
                {group.flags.map((f) => (
                  <div key={f.id} className="flex items-start justify-between gap-4 py-3 first:pt-0">
                    <div className="min-w-0 space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium">{f.label}</span>
                        {effectBadge(f)}
                        {f.armed && (
                          <Badge className="bg-destructive hover:bg-destructive">armed</Badge>
                        )}
                        {f.pending_restart === true && (
                          <Badge
                            variant="outline"
                            className="border-warning/50 text-warning"
                            title="Saved — but the consuming process must restart to pick it up"
                          >
                            pending restart
                          </Badge>
                        )}
                        <code className="text-[11px] text-muted-foreground">{f.env_var}</code>
                      </div>
                      <p className="text-sm text-muted-foreground">{f.description}</p>
                      <p className="text-xs text-muted-foreground">
                        {f.effect_note} · source: {f.source}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2 pt-0.5">
                      {saving === f.id && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
                      <Switch
                        checked={f.enabled}
                        disabled={saving === f.id}
                        onCheckedChange={(v) => onToggle(f, v)}
                        aria-label={`Toggle ${f.label}`}
                      />
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          );
        })}

      <AlertDialog open={arm !== null} onOpenChange={(o) => !o && setArm(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <ShieldAlert className="h-5 w-5 text-destructive" />
              Arm {arm?.label}?
            </AlertDialogTitle>
            <AlertDialogDescription>
              {arm?.description} Arming records your intent in the environment — it does not remove
              any safety gate. To confirm, type <code className="font-semibold">{arm?.id}</code> below.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="space-y-1.5">
            <Label htmlFor="arm-confirm">Type the flag id to confirm</Label>
            <Input
              id="arm-confirm"
              value={armText}
              autoComplete="off"
              placeholder={arm?.id}
              onChange={(e) => setArmText(e.target.value)}
            />
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              disabled={armText.trim() !== arm?.id}
              onClick={confirmArm}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Arm
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
