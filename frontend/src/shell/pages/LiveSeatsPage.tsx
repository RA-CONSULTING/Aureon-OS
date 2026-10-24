/**
 * Live seat tabs. Each tab polls the gateway and draws only numbers that
 * arrived in that reading. A down source stays empty, with the reason.
 */

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SEAT_TABS, type SeatTab } from "../seatManifest";
import { operatorPort } from "@/config/serviceEndpoints";

interface Reading {
  id?: string;
  available?: boolean;
  reason?: string | null;
  fetched_at?: string | null;
  was?: string;
  upstream?: string | null;
  payload?: unknown;
  live_trading?: boolean;
}

interface NumericLeaf {
  label: string;
  value: number;
}

function numericLeaves(value: unknown, prefix = ""): NumericLeaf[] {
  if (typeof value === "number" && Number.isFinite(value)) {
    return prefix ? [{ label: prefix, value }] : [];
  }
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return [];
  }
  const rows: NumericLeaf[] = [];
  for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
    const label = prefix ? `${prefix}.${key}` : key;
    if (typeof item === "number" && Number.isFinite(item)) {
      rows.push({ label, value: item });
    } else if (item && typeof item === "object" && !Array.isArray(item)) {
      rows.push(...numericLeaves(item, label));
    }
  }
  return rows.slice(0, 12);
}

function ReadingChart({ payload }: { payload: unknown }) {
  const rows = useMemo(() => numericLeaves(payload), [payload]);
  if (!rows.length) {
    return <p className="text-sm text-muted-foreground">No numeric series in this reading.</p>;
  }
  const peak = Math.max(...rows.map((row) => Math.abs(row.value)), 1);
  const width = 560;
  const height = 28 * rows.length;
  return (
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Numeric fields from this reading" className="w-full">
      {rows.map((row, index) => {
        const bar = Math.max(2, (Math.abs(row.value) / peak) * 280);
        const y = index * 28;
        return (
          <g key={row.label}>
            <text x="0" y={y + 16} fill="currentColor" fontSize="11">
              {row.label}
            </text>
            <rect x="250" y={y + 6} width={bar} height="12" fill="currentColor" opacity="0.75" />
            <text x={260 + bar} y={y + 16} fill="currentColor" fontSize="11">
              {String(row.value)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function SeatPanel({ seat }: { seat: SeatTab }) {
  const [reading, setReading] = useState<Reading | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let stop = false;
    const pull = async () => {
      try {
        const response = await fetch(`/api/seats/${seat.id}`, { cache: "no-store" });
        const body = (await response.json()) as Reading;
        if (!stop) {
          setReading(body);
          setError(response.ok ? null : body.reason || `HTTP ${response.status}`);
        }
      } catch (exc) {
        if (!stop) {
          setReading(null);
          setError(exc instanceof Error ? exc.message : "gateway did not answer");
        }
      }
    };
    void pull();
    const timer = window.setInterval(() => void pull(), 2000);
    return () => {
      stop = true;
      window.clearInterval(timer);
    };
  }, [seat.id]);

  const available = reading?.available === true && !error;
  return (
    <Card data-seat={seat.id} data-fetched-at={reading?.fetched_at || ""}>
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-2">
          {seat.label}
          <Badge variant={available ? "default" : "outline"}>{available ? "live" : "unavailable"}</Badge>
        </CardTitle>
        <CardDescription>
          {seat.was}. Refreshes through the gateway. {reading?.upstream || "no separate upstream"}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <p data-timestamp={reading?.fetched_at || ""}>
          fetched_at: {reading?.fetched_at || "not yet"}
        </p>
        {!available && (
          <p data-reason="true">{error || reading?.reason || "source did not answer"}</p>
        )}
        {available && <ReadingChart payload={reading?.payload} />}
        {available && reading?.payload && (
          <pre className="max-h-64 overflow-auto rounded-md bg-muted p-3 text-xs">
            {JSON.stringify(reading.payload, null, 2)}
          </pre>
        )}
      </CardContent>
    </Card>
  );
}

export default function LiveSeatsPage() {
  const [params, setParams] = useSearchParams();
  const requested = params.get("seat") || SEAT_TABS[0].id;
  const active = SEAT_TABS.some((seat) => seat.id === requested) ? requested : SEAT_TABS[0].id;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge>PAPER UNTIL EXCHANGE KEYS</Badge>
        <Badge variant="outline">live readings only</Badge>
      </div>
      <div>
        <h1 className="text-2xl font-medium tracking-tight">Live seats</h1>
        <p className="text-sm text-muted-foreground">
          Every separate dashboard is a tab here. The gateway on {operatorPort} proxies the buses and APIs.
          A quiet source shows why it is empty.
        </p>
      </div>
      <Tabs
        value={active}
        onValueChange={(value) => {
          const next = new URLSearchParams(params);
          next.set("seat", value);
          setParams(next, { replace: true });
        }}
      >
        <TabsList className="flex h-auto flex-wrap justify-start">
          {SEAT_TABS.map((seat) => (
            <TabsTrigger key={seat.id} value={seat.id}>
              {seat.label}
            </TabsTrigger>
          ))}
        </TabsList>
        {SEAT_TABS.map((seat) => (
          <TabsContent key={seat.id} value={seat.id}>
            {active === seat.id ? <SeatPanel seat={seat} /> : null}
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}
