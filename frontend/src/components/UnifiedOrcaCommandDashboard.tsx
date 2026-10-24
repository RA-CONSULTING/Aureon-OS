import React, { useEffect, useState, useCallback } from "react";

/**
 * Orca command tab. Readings come from the Orca seat through the operator
 * gateway. This tab does not send a command and it does not place an order.
 */

const UnifiedOrcaCommandDashboard: React.FC = () => {
  const [seat, setSeat] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchUnifiedState = useCallback(async () => {
    try {
      const response = await fetch("/api/seats/orca", { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`gateway seat HTTP ${response.status}`);
      }
      const reading = await response.json();
      setSeat(reading);
      setError(reading?.available ? null : String(reading?.reason || "orca seat unavailable"));
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUnifiedState();
    const interval = setInterval(fetchUnifiedState, 2000);
    return () => clearInterval(interval);
  }, [fetchUnifiedState]);

  if (loading && !seat) {
    return (
      <div className="flex items-center justify-center min-h-[240px] bg-card text-foreground">
        <p className="text-muted-foreground">Loading the Orca seat…</p>
      </div>
    );
  }

  const payload =
    seat && typeof seat.payload === "object" && seat.payload
      ? (seat.payload as Record<string, unknown>)
      : null;

  return (
    <div className="bg-background text-foreground p-4 space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Orca</h1>
        <p className="text-sm text-muted-foreground">
          This tab reads the Orca seat through the operator gateway. It does not send a command and it does not place an order.
        </p>
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}
      <div className="rounded border border-border p-4 space-y-2 text-sm">
        <p>available: {String(seat?.available ?? false)}</p>
        <p>reason: {String(seat?.reason || (seat?.available ? "seat answered" : "no reading"))}</p>
        <p>live trading: {String(payload?.live_trading ?? false)}</p>
        <p>orders: {payload && "orders" in payload ? String(payload.orders) : "none reported"}</p>
        <p>{String(payload?.dashboard || payload?.service || "")}</p>
      </div>
      <button
        type="button"
        onClick={() => fetchUnifiedState()}
        className="py-2 px-3 rounded text-sm bg-primary text-primary-foreground"
      >
        Refresh
      </button>
    </div>
  );
};

export default UnifiedOrcaCommandDashboard;
