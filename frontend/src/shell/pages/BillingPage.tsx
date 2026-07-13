/**
 * Billing & Support — the honest money page.
 *
 * Gas-tank balance (Supabase, via useGasTank when signed in), platform
 * billing/metering state from GET /api/billing/status, and the
 * support-the-project links. Free access; nothing here gates usage.
 */

import { useEffect, useState } from "react";
import { CreditCard, Fuel, Heart } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { supabase } from "@/integrations/supabase/client";
import { useGasTank } from "@/hooks/useGasTank";
import { SUPPORT_PAYMENT_URLS } from "@/hooks/useSupportProject";

interface BillingStatus {
  configured?: boolean;
  missing_env?: string[];
  tenancy_bridge?: string;
  metering?: { sink?: string; pending?: number; flushed?: number; dropped?: number; flush_failures?: number };
  charge_endpoint?: { enabled?: boolean };
  model?: string;
}

function GasTankCard({ userId }: { userId: string }) {
  const gasTank = useGasTank(userId);
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardDescription className="flex items-center gap-1.5">
          <Fuel className="h-3.5 w-3.5" /> Gas tank
        </CardDescription>
        <CardTitle className="text-2xl">£{Number(gasTank.balance ?? 0).toFixed(2)}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-1 text-xs text-muted-foreground">
        <p>status: {gasTank.status} · membership: {gasTank.membershipType}</p>
        <p>total fees paid: £{Number(gasTank.totalFeesPaid ?? 0).toFixed(2)}</p>
      </CardContent>
    </Card>
  );
}

export default function BillingPage() {
  const [status, setStatus] = useState<BillingStatus | null | undefined>(undefined);
  const [userId, setUserId] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/billing/status", { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : null))
      .then(setStatus)
      .catch(() => setStatus(null));
    supabase.auth.getSession().then(({ data }) => setUserId(data.session?.user?.id ?? null));
  }, []);

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <CreditCard className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-semibold tracking-tight">Billing & Support</h1>
        </div>
        <p className="text-sm text-muted-foreground">
          Aureon runs free. The gas tank is a prepaid wallet charged only as a
          performance fee on profit above your high-water mark; usage metering is
          record-only. The platform never initiates payments.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {userId ? (
          <GasTankCard userId={userId} />
        ) : (
          <Card>
            <CardHeader className="pb-2">
              <CardDescription className="flex items-center gap-1.5">
                <Fuel className="h-3.5 w-3.5" /> Gas tank
              </CardDescription>
              <CardTitle className="text-lg text-muted-foreground">Sign in to view</CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-muted-foreground">
              Your balance lives in your Supabase account.
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Platform billing state</CardDescription>
            <CardTitle className="text-lg">
              {status === undefined ? (
                <Skeleton className="h-6 w-32" />
              ) : status === null ? (
                <span className="text-muted-foreground">gateway offline</span>
              ) : (
                <span className="flex flex-wrap gap-1.5">
                  <Badge variant="outline">metering: {status.metering?.sink ?? "?"}</Badge>
                  <Badge variant="outline">
                    charge-fee: {status.charge_endpoint?.enabled ? "enabled" : "off"}
                  </Badge>
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-xs text-muted-foreground">
            {status?.metering && (
              <p>
                events — flushed: {status.metering.flushed ?? 0} · pending: {status.metering.pending ?? 0} ·
                dropped: {status.metering.dropped ?? 0}
              </p>
            )}
            {status && !status.configured && (
              <p>Supabase billing backend not configured{status.missing_env?.length ? ` (missing: ${status.missing_env.join(", ")})` : ""}.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="border-primary/30">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <Heart className="h-4 w-4 text-primary" /> Support the project
          </CardTitle>
          <CardDescription>
            Aureon is free-access, open-source software. If it earns its keep, support keeps it running.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {SUPPORT_PAYMENT_URLS.map((url, i) => (
            <Button key={url} size="sm" variant={i === 0 ? "default" : "outline"} asChild>
              <a href={url} target="_blank" rel="noopener noreferrer">
                Support via SumUp{SUPPORT_PAYMENT_URLS.length > 1 ? ` (${i + 1})` : ""}
              </a>
            </Button>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
