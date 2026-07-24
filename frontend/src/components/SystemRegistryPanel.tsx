import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ChevronDown, ChevronRight, Activity, Circle } from "lucide-react";

interface SystemInfo {
  name: string;
  status: "online" | "offline" | "degraded";
  coherence?: number;
  lastHeartbeat?: string;
}

interface SystemFamily {
  name: string;
  icon: string;
  description: string;
  systems: SystemInfo[];
}

const systemFamilies: SystemFamily[] = [
  {
    name: "Orchestration",
    icon: "🎯",
    description: "Central command and coordination systems",
    systems: [
      { name: "UnifiedOrchestrator", status: "online", coherence: 0.92 },
      { name: "TemporalLadder", status: "online", coherence: 0.88 },
      { name: "HarmonicNexusOrchestrator", status: "online", coherence: 0.95 },
      { name: "UnifiedBus", status: "online", coherence: 1.0 },
    ],
  },
  {
    name: "Perception",
    icon: "👁️",
    description: "Data ingestion and market perception",
    systems: [
      { name: "DataIngestion", status: "online", coherence: 0.94 },
      { name: "BinanceWebSocket", status: "online", coherence: 1.0 },
      { name: "KrakenWebSocket", status: "online", coherence: 0.98 },
      { name: "MarketDataValidator", status: "online", coherence: 0.96 },
      { name: "DataStreamMonitor", status: "online", coherence: 0.99 },
    ],
  },
  {
    name: "Quantum",
    icon: "🔮",
    description: "Core quantum field calculations",
    systems: [
      { name: "MasterEquation", status: "online", coherence: 0.91 },
      { name: "OmegaEquation", status: "online", coherence: 0.89 },
      { name: "FibonacciLattice", status: "online", coherence: 0.93 },
      { name: "ProbabilityMatrix", status: "online", coherence: 0.87 },
      { name: "QGITACoherence", status: "online", coherence: 0.90 },
    ],
  },
  {
    name: "Detection",
    icon: "🔍",
    description: "Signal detection and consensus",
    systems: [
      { name: "LighthouseConsensus", status: "online", coherence: 0.94 },
      { name: "FTCPDetector", status: "online", coherence: 0.88 },
      { name: "QGITASignalGenerator", status: "online", coherence: 0.92 },
      { name: "UnityDetector", status: "online", coherence: 0.86 },
    ],
  },
  {
    name: "Harmonic",
    icon: "🎵",
    description: "Frequency transformation and harmonics",
    systems: [
      { name: "ThePrism", status: "online", coherence: 0.95 },
      { name: "RainbowBridge", status: "online", coherence: 0.93 },
      { name: "EckoushicCascade", status: "online", coherence: 0.89 },
      { name: "StargateFrequencyHarmonizer", status: "online", coherence: 0.91 },
      { name: "StargateLattice", status: "online", coherence: 0.87 },
      { name: "HNCImperialDetector", status: "online", coherence: 0.94 },
    ],
  },
  {
    name: "Consciousness",
    icon: "🧠",
    description: "Awareness and dimensional mapping",
    systems: [
      { name: "AkashicAttunement", status: "online", coherence: 0.88 },
      { name: "AkashicFrequencyMapper", status: "online", coherence: 0.85 },
      { name: "IntegralAQAL", status: "online", coherence: 0.82 },
      { name: "ZeroPointFieldDetector", status: "online", coherence: 0.79 },
      { name: "DimensionalDialler", status: "online", coherence: 0.84 },
    ],
  },
  {
    name: "Earth",
    icon: "🌍",
    description: "Earth field and cosmic integration",
    systems: [
      { name: "EarthAureonBridge", status: "online", coherence: 0.90 },
      { name: "NexusLiveFeedBridge", status: "online", coherence: 0.88 },
      { name: "SchumannResonance", status: "online", coherence: 0.92 },
      { name: "SolarWeather", status: "online", coherence: 0.86 },
    ],
  },
  {
    name: "Execution",
    icon: "⚡",
    description: "Trade execution and routing",
    systems: [
      { name: "SmartOrderRouter", status: "online", coherence: 0.97 },
      { name: "ExecutionEngine", status: "online", coherence: 0.95 },
      { name: "MultiExchangeClient", status: "online", coherence: 0.93 },
      { name: "UnifiedExchangeClient", status: "online", coherence: 0.94 },
    ],
  },
  {
    name: "Memory",
    icon: "🐘",
    description: "Persistence and pattern tracking",
    systems: [
      { name: "ElephantMemory", status: "online", coherence: 0.91 },
      { name: "TemporalProbabilityEcho", status: "online", coherence: 0.87 },
      { name: "LightPathTracer", status: "online", coherence: 0.89 },
      { name: "DecisionAccuracyTracker", status: "online", coherence: 0.92 },
    ],
  },
];

const getStatusColor = (status: string) => {
  switch (status) {
    case "online":
      return "text-success";
    case "offline":
      return "text-destructive";
    case "degraded":
      return "text-warning";
    default:
      return "text-muted-foreground";
  }
};

const getStatusBadgeVariant = (status: string) => {
  switch (status) {
    case "online":
      return "default";
    case "offline":
      return "destructive";
    case "degraded":
      return "secondary";
    default:
      return "outline";
  }
};

const SystemRegistryPanel = () => {
  const [openFamilies, setOpenFamilies] = useState<string[]>(["Orchestration", "Perception"]);

  const toggleFamily = (familyName: string) => {
    setOpenFamilies((prev) =>
      prev.includes(familyName)
        ? prev.filter((f) => f !== familyName)
        : [...prev, familyName]
    );
  };

  const totalSystems = systemFamilies.reduce((acc, f) => acc + f.systems.length, 0);
  const onlineSystems = systemFamilies.reduce(
    (acc, f) => acc + f.systems.filter((s) => s.status === "online").length,
    0
  );
  const avgCoherence =
    systemFamilies.reduce(
      (acc, f) =>
        acc + f.systems.reduce((a, s) => a + (s.coherence || 0), 0) / f.systems.length,
      0
    ) / systemFamilies.length;

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-card border-border">
          <CardContent className="pt-4">
            <div className="text-2xl font-bold text-foreground">{totalSystems}</div>
            <div className="text-sm text-muted-foreground">Total Systems</div>
          </CardContent>
        </Card>
        <Card className="bg-card border-border">
          <CardContent className="pt-4">
            <div className="text-2xl font-bold text-success">{onlineSystems}</div>
            <div className="text-sm text-muted-foreground">Online</div>
          </CardContent>
        </Card>
        <Card className="bg-card border-border">
          <CardContent className="pt-4">
            <div className="text-2xl font-bold text-foreground">{systemFamilies.length}</div>
            <div className="text-sm text-muted-foreground">System Families</div>
          </CardContent>
        </Card>
        <Card className="bg-card border-border">
          <CardContent className="pt-4">
            <div className="text-2xl font-bold text-primary">{(avgCoherence * 100).toFixed(1)}%</div>
            <div className="text-sm text-muted-foreground">Avg Coherence</div>
          </CardContent>
        </Card>
      </div>

      {/* System Families */}
      <div className="space-y-3">
        {systemFamilies.map((family) => (
          <Collapsible
            key={family.name}
            open={openFamilies.includes(family.name)}
            onOpenChange={() => toggleFamily(family.name)}
          >
            <Card className="bg-card border-border">
              <CollapsibleTrigger className="w-full">
                <CardHeader className="flex flex-row items-center justify-between py-4">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{family.icon}</span>
                    <div className="text-left">
                      <CardTitle className="text-lg">{family.name}</CardTitle>
                      <p className="text-sm text-muted-foreground">{family.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <Badge variant="outline" className="text-xs">
                      {family.systems.length} systems
                    </Badge>
                    {openFamilies.includes(family.name) ? (
                      <ChevronDown className="h-5 w-5 text-muted-foreground" />
                    ) : (
                      <ChevronRight className="h-5 w-5 text-muted-foreground" />
                    )}
                  </div>
                </CardHeader>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <CardContent className="pt-0 pb-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {family.systems.map((system) => (
                      <div
                        key={system.name}
                        className="flex items-center justify-between p-3 rounded-lg bg-muted/50 border border-border"
                      >
                        <div className="flex items-center gap-2">
                          <Circle
                            className={`h-2 w-2 fill-current ${getStatusColor(system.status)}`}
                          />
                          <span className="text-sm font-medium text-foreground">
                            {system.name}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          {system.coherence !== undefined && (
                            <span className="text-xs text-muted-foreground">
                              Γ {(system.coherence * 100).toFixed(0)}%
                            </span>
                          )}
                          <Badge
                            variant={getStatusBadgeVariant(system.status) as any}
                            className="text-xs"
                          >
                            {system.status}
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </CollapsibleContent>
            </Card>
          </Collapsible>
        ))}
      </div>
    </div>
  );
};

export default SystemRegistryPanel;
