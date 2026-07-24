import { useHiveState } from "@/hooks/useHiveState";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { 
  Crown, 
  Shield, 
  Radio,
  AlertTriangle,
  CheckCircle2,
  Clock
} from "lucide-react";
import { format } from "date-fns";

// Mood-based color schemes
function getMoodColor(mood: string): string {
  const moodLower = mood.toLowerCase();
  if (moodLower.includes("confident") || moodLower.includes("aggressive")) return "text-success";
  if (moodLower.includes("cautious") || moodLower.includes("defensive")) return "text-warning";
  if (moodLower.includes("alert") || moodLower.includes("veto")) return "text-destructive";
  return "text-primary";
}

function getMoodBg(mood: string): string {
  const moodLower = mood.toLowerCase();
  if (moodLower.includes("confident") || moodLower.includes("aggressive")) return "bg-success/20";
  if (moodLower.includes("cautious") || moodLower.includes("defensive")) return "bg-warning/20";
  if (moodLower.includes("alert") || moodLower.includes("veto")) return "bg-destructive/20";
  return "bg-primary/20";
}

function getMoodIcon(mood: string) {
  const moodLower = mood.toLowerCase();
  if (moodLower.includes("confident") || moodLower.includes("aggressive")) {
    return <CheckCircle2 className="w-5 h-5 text-success" />;
  }
  if (moodLower.includes("cautious") || moodLower.includes("defensive")) {
    return <Shield className="w-5 h-5 text-warning" />;
  }
  if (moodLower.includes("alert") || moodLower.includes("veto")) {
    return <AlertTriangle className="w-5 h-5 text-destructive" />;
  }
  return <Radio className="w-5 h-5 text-primary" />;
}

export function HiveStatePanel() {
  const { hiveState, loading, lastUpdated } = useHiveState(true, 5000);

  if (loading && !hiveState.updated_at) {
    return (
      <Card className="border-primary/30 bg-gradient-to-br from-background to-primary/5">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Crown className="w-5 h-5 text-primary animate-pulse" />
            Queen Hive Mind
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-sm">Awaiting Queen's voice...</p>
        </CardContent>
      </Card>
    );
  }

  const {
    mood,
    active_scanner,
    coherence_score,
    veto_count,
    last_veto_reason,
    message_log,
    updated_at,
  } = hiveState;

  const coherencePct = Math.round(coherence_score * 100);

  return (
    <Card className="border-primary/30 bg-gradient-to-br from-background to-primary/5">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Crown className="w-5 h-5 text-primary" />
            Queen Hive Mind
          </CardTitle>
          {lastUpdated && (
            <span className="text-xs text-muted-foreground flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {format(lastUpdated, "HH:mm:ss")}
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Mood & Scanner Status */}
        <div className="grid grid-cols-2 gap-3">
          <div className={`p-3 rounded-lg ${getMoodBg(mood)}`}>
            <div className="flex items-center gap-2 mb-2">
              {getMoodIcon(mood)}
              <span className="text-xs font-medium text-muted-foreground">Mood</span>
            </div>
            <div className={`text-lg font-bold ${getMoodColor(mood)}`}>
              {mood}
            </div>
          </div>

          <div className="p-3 rounded-lg bg-muted/30">
            <div className="flex items-center gap-2 mb-2">
              <Radio className="w-4 h-4 text-primary" />
              <span className="text-xs font-medium text-muted-foreground">Scanner</span>
            </div>
            <div className="text-sm font-medium truncate" title={active_scanner}>
              {active_scanner}
            </div>
          </div>
        </div>

        {/* Coherence Score */}
        <div className="p-3 rounded-lg bg-muted/30">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-muted-foreground">Branch Coherence</span>
            <Badge variant={coherencePct >= 70 ? "default" : coherencePct >= 40 ? "secondary" : "destructive"}>
              {coherencePct}%
            </Badge>
          </div>
          <Progress value={coherencePct} className="h-2" />
        </div>

        {/* Veto Stats */}
        <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-destructive" />
              <span className="text-sm font-medium">Veto Gate</span>
            </div>
            <Badge variant="destructive" className="font-mono">
              {veto_count} vetoes
            </Badge>
          </div>
          <div className="text-xs text-muted-foreground">
            Last: <span className="text-destructive">{last_veto_reason}</span>
          </div>
        </div>

        {/* Queen's Voice Log */}
        <div className="p-3 rounded-lg bg-primary/5 border border-primary/20">
          <div className="flex items-center gap-2 mb-2">
            <Crown className="w-4 h-4 text-primary" />
            <span className="text-sm font-medium">Queen's Voice</span>
          </div>
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {message_log && message_log.length > 0 ? (
              message_log.slice().reverse().map((msg, idx) => (
                <div key={idx} className="text-xs text-muted-foreground bg-muted/30 p-2 rounded">
                  {msg}
                </div>
              ))
            ) : (
              <div className="text-xs text-muted-foreground italic">
                No messages yet...
              </div>
            )}
          </div>
        </div>

        {/* Timestamp */}
        {updated_at && (
          <div className="text-xs text-muted-foreground text-center pt-2 border-t border-border">
            State updated: {format(new Date(updated_at), "MMM d, HH:mm:ss")}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
