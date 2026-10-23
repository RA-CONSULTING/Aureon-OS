import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useLiveNexusData } from "@/contexts/LiveNexusDataContext";
import type { RealtimeMetric } from "@/hooks/useRealtimeNexusData";
import { cn } from "@/lib/utils";

const formatMetricValue = (metric: RealtimeMetric) => {
  if (metric.format === "percent") {
    return `${metric.value.toFixed(0)}%`;
  }

  if (metric.format === "count") {
    const suffix = metric.unit ? ` ${metric.unit}` : "";
    return `${metric.value.toFixed(0)}${suffix}`;
  }

  return metric.value.toFixed(2);
};

const formatMetricChange = (metric: RealtimeMetric) => {
  const sign = metric.change >= 0 ? "+" : "";
  if (metric.format === "percent") {
    return `${sign}${metric.change.toFixed(1)}%`;
  }

  if (metric.format === "ratio") {
    return `${sign}${metric.change.toFixed(2)}`;
  }

  const suffix = metric.unit ? ` ${metric.unit}` : "";
  return `${sign}${metric.change.toFixed(0)}${suffix}`;
};

const getMetricProgress = (metric: RealtimeMetric) => {
  if (metric.format === "percent") {
    return Math.max(0, Math.min(1, metric.value / 100));
  }

  if (metric.format === "ratio") {
    return Math.max(0, Math.min(1, metric.value));
  }

  const divisor = metric.target ?? Math.max(metric.value, 100);
  return Math.max(0, Math.min(1, metric.value / divisor));
};

const LiveSupabaseCharts = () => {
  const { metrics, timestamp } = useLiveNexusData();
  const lastUpdated = new Date(timestamp).toLocaleTimeString();

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold text-stone-900">
            Nexus Operational Metrics
          </h2>
          <p className="text-sm text-stone-500">
            Cohesion and resonance telemetry across core subsystems
          </p>
        </div>
        <div className="text-sm text-stone-500">
          Last pulse:
          <span className="ml-1 font-medium text-stone-700">{lastUpdated}</span>
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => {
          const positive = metric.change >= 0;
          const progress = getMetricProgress(metric);

          return (
            <Card key={metric.id} className="border-stone-200">
              <CardHeader className="space-y-3 pb-4">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-medium text-stone-500">
                    {metric.label}
                  </CardTitle>
                  <Badge variant={positive ? "success" : "warning"}>
                    {formatMetricChange(metric)}
                  </Badge>
                </div>
                <div className="text-3xl font-semibold text-stone-900">
                  {formatMetricValue(metric)}
                </div>
                <p className="text-xs text-stone-500">
                  {positive ? "Stabilizing" : "Adjusting"} since last sample
                </p>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="h-2 rounded-full bg-stone-100">
                  <div
                    className={cn(
                      "h-2 rounded-full bg-amber-500 transition-all",
                      positive ? "bg-amber-500" : "bg-rose-500"
                    )}
                    style={{ width: `${Math.round(progress * 100)}%` }}
                  />
                </div>
                {metric.target ? (
                  <p className="mt-2 text-xs text-stone-500">
                    Target {metric.target} {metric.unit ?? ""}
                  </p>
                ) : null}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
};

export default LiveSupabaseCharts;
