/**
 * Every separate dashboard or status page, and the tab that replaces it.
 * Live numbers come from the gateway. This list has no readings.
 */

export interface SeatTab {
  id: string;
  label: string;
  was: string;
}

const gatewayPort = import.meta.env.VITE_OPERATOR_PORT || "8790";
const marketPort = import.meta.env.VITE_MARKET_STATUS_PORT || "8791";

export const SEAT_TABS: SeatTab[] = [
  { id: "local-console", label: "Local console", was: "port 8080 dashboard" },
  { id: "gateway", label: "Operator gateway", was: `operator gateway port ${gatewayPort}` },
  { id: "circulation", label: "Circulation bus", was: "port 8799" },
  { id: "fusion", label: "Fusion seat", was: "port 8765" },
  { id: "market-status", label: "Market status", was: `market status port ${marketPort}` },
  { id: "orca", label: "Orca", was: "port 8888" },
  { id: "neural-canvas", label: "Neural canvas", was: "port 13012" },
  { id: "thought-hub", label: "Thought-action hub", was: "port 13002" },
  { id: "error-sink", label: "Error sink", was: "port 8088" },
  { id: "api-b", label: "API B", was: "port 8766" },
  { id: "frontend", label: "Unified frontend", was: "port 5173" },
  { id: "queen-unified", label: "Queen unified", was: "port 13000 queen unified dashboard" },
  { id: "pro-dashboard", label: "Pro dashboard", was: "port 14000 pro dashboard" },
  { id: "master-hub", label: "Master hub", was: "port 13333 unified master hub" },
  { id: "earth-shield", label: "Earth shield", was: "port 8785 earth shield dashboard" },
  { id: "queen-web", label: "Queen web", was: "port 5000 queen web dashboard" },
  { id: "system-hub", label: "System hub", was: "port 13001 system hub dashboard" },
  { id: "bot-hunter", label: "Bot hunter", was: "port 9999 bot hunter dashboard" },
  { id: "dashboard-api", label: "Dashboard API", was: "port 13334 unified dashboard API" },
  { id: "queen-power", label: "Queen power", was: "port 8080 queen power dashboard" },
  { id: "trader-local", label: "Trader telemetry", was: `unified market trader local dashboard on port ${gatewayPort}` },
  { id: "kraken-local", label: "Kraken telemetry", was: "kraken penny trader local dashboard" },
  { id: "command-center-legacy", label: "Legacy command center", was: "separate command center UI" },
  { id: "live-bridge", label: "Live Bridge", was: "frontend bridge websocket" },
];
