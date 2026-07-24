import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Clock, Calendar, Moon, Sun, Sparkles, TrendingUp } from "lucide-react";
import { useTemporalAlignment } from "@/hooks/useTemporalAlignment";
import { useSentinelConfig } from "@/hooks/useSentinelConfig";
import { format } from "date-fns";
import surgeWindowAlignments from "@/assets/research/surge-window-unity-alignments.png";

export function TemporalAlignmentTracker() {
  const { config } = useSentinelConfig();
  const { alignment, loading } = useTemporalAlignment(config?.sentinel_birthdate);

  if (loading || !alignment) {
    return (
      <Card className="bg-card/50 backdrop-blur border-border/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-muted-foreground animate-pulse" />
            Temporal Alignment Tracker
          </CardTitle>
          <CardDescription>Calculating temporal resonance patterns...</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const getAlignmentLevel = (score: number) => {
    if (score >= 0.8) return { level: 'PEAK RESONANCE', color: 'text-primary', bg: 'bg-primary/20' };
    if (score >= 0.6) return { level: 'HIGH ALIGNMENT', color: 'text-primary', bg: 'bg-primary/20' };
    if (score >= 0.4) return { level: 'MODERATE', color: 'text-warning', bg: 'bg-warning/20' };
    return { level: 'LOW ALIGNMENT', color: 'text-warning', bg: 'bg-warning/20' };
  };

  const getCyclePhaseColor = (phase: string) => {
    switch (phase) {
      case 'peak': return 'text-success';
      case 'ascending': return 'text-primary';
      case 'descending': return 'text-warning';
      case 'trough': return 'text-destructive';
      default: return 'text-gray-500';
    }
  };

  const alignmentStatus = getAlignmentLevel(alignment.currentAlignment);
  const daysToNext = Math.ceil((alignment.nextOptimal.getTime() - Date.now()) / (1000 * 60 * 60 * 24));

  return (
    <Card className="bg-card/50 backdrop-blur border-border/50 relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-primary/5 to-primary/5" />
      
      <CardHeader className="relative">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-primary" />
              Temporal Alignment Tracker
            </CardTitle>
            <CardDescription>
              {config ? `Sentinel: ${config.sentinel_name} • Born: ${format(new Date(config.sentinel_birthdate), 'MMM dd, yyyy')}` : 'Temporal pattern analysis'}
            </CardDescription>
          </div>
          <Badge className={`${alignmentStatus.color} ${alignmentStatus.bg} border-0 text-sm px-3 py-1`}>
            {alignmentStatus.level}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="relative space-y-4">
        {/* Current Alignment Display */}
        <div className="flex items-center justify-center p-6 bg-gradient-to-br from-primary/10 to-primary/10 rounded-lg border border-border/50">
          <div className="text-center">
            <div className="flex items-center justify-center gap-2 mb-2">
              <Sparkles className="w-6 h-6 text-primary" />
              <span className="text-sm text-muted-foreground font-medium">Current Temporal Alignment</span>
            </div>
            <div className="text-5xl font-bold bg-gradient-to-r from-primary to-primary bg-clip-text text-transparent">
              {(alignment.currentAlignment * 100).toFixed(1)}%
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              Cycle Resonance: {(alignment.cycleResonance * 100).toFixed(1)}%
            </div>
          </div>
        </div>

        {/* Birth Pattern vs Current Pattern */}
        <div className="grid grid-cols-2 gap-4">
          <div className="p-4 bg-background/50 rounded-lg border border-border/50">
            <div className="flex items-center gap-2 mb-3">
              <Calendar className="w-4 h-4 text-primary" />
              <span className="text-xs text-muted-foreground font-medium">Birth Pattern</span>
            </div>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Day/Month:</span>
                <span className="font-mono">{alignment.birthPattern.day}/{alignment.birthPattern.month}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Day of Year:</span>
                <span className="font-mono">{alignment.birthPattern.dayOfYear}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Lunar Phase:</span>
                <span className="font-mono">{(alignment.birthPattern.lunarCycle * 100).toFixed(0)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Harmonic:</span>
                <span className="font-mono">{(alignment.birthPattern.harmonicPhase * 100).toFixed(0)}%</span>
              </div>
            </div>
          </div>

          <div className="p-4 bg-background/50 rounded-lg border border-border/50">
            <div className="flex items-center gap-2 mb-3">
              <Clock className="w-4 h-4 text-primary" />
              <span className="text-xs text-muted-foreground font-medium">Current Pattern</span>
            </div>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Day/Month:</span>
                <span className="font-mono">{alignment.currentPattern.day}/{alignment.currentPattern.month}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Day of Year:</span>
                <span className="font-mono">{alignment.currentPattern.dayOfYear}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Lunar Phase:</span>
                <span className="font-mono">{(alignment.currentPattern.lunarCycle * 100).toFixed(0)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Harmonic:</span>
                <span className="font-mono">{(alignment.currentPattern.harmonicPhase * 100).toFixed(0)}%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Cycle Indicators */}
        <div className="grid grid-cols-2 gap-4">
          <div className="p-3 bg-background/50 rounded-lg border border-border/50">
            <div className="flex items-center gap-2 mb-2">
              <Moon className="w-4 h-4 text-primary" />
              <span className="text-xs text-muted-foreground">Lunar Cycle</span>
            </div>
            <Progress value={alignment.currentPattern.lunarCycle * 100} className="h-2" />
            <div className="text-xs text-muted-foreground mt-1">
              {(alignment.currentPattern.lunarCycle * 100).toFixed(1)}% through cycle
            </div>
          </div>

          <div className="p-3 bg-background/50 rounded-lg border border-border/50">
            <div className="flex items-center gap-2 mb-2">
              <Sun className="w-4 h-4 text-warning" />
              <span className="text-xs text-muted-foreground">Solar Cycle</span>
            </div>
            <Progress value={alignment.currentPattern.solarCycle * 100} className="h-2" />
            <div className="text-xs text-muted-foreground mt-1">
              {(alignment.currentPattern.solarCycle * 100).toFixed(1)}% through year
            </div>
          </div>
        </div>

        {/* Next Optimal Window */}
        <div className="p-4 bg-gradient-to-br from-primary/10 to-primary/10 rounded-lg border border-border/50">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-primary" />
              <span className="text-sm font-medium">Next Peak Alignment</span>
            </div>
            <Badge variant="outline" className="text-xs">
              {daysToNext} {daysToNext === 1 ? 'day' : 'days'}
            </Badge>
          </div>
          <div className="text-2xl font-bold bg-gradient-to-r from-primary to-primary bg-clip-text text-transparent">
            {format(alignment.nextOptimal, 'MMM dd, yyyy')}
          </div>
          <div className="text-xs text-muted-foreground mt-1">
            {format(alignment.nextOptimal, 'h:mm a')}
          </div>
        </div>

        {/* Historical Optimal Windows */}
        {alignment.optimalWindows.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-primary" />
              <span className="text-sm font-medium">Recent Peak Windows</span>
            </div>
            <div className="space-y-2 max-h-60 overflow-y-auto">
              {alignment.optimalWindows.slice(0, 5).map((window, index) => (
                <div
                  key={index}
                  className="p-3 bg-background/50 rounded-lg border border-border/50 flex items-center justify-between"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-medium">
                        {format(window.timestamp, 'MMM dd, yyyy HH:mm')}
                      </span>
                      <Badge variant="outline" className={`text-xs ${getCyclePhaseColor(window.cyclePhase)}`}>
                        {window.cyclePhase}
                      </Badge>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Pattern: {window.pattern} • Coherence: {(window.coherence * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div className="text-right ml-3">
                    <div className="text-lg font-bold text-primary">
                      {(window.alignmentScore * 100).toFixed(0)}%
                    </div>
                    <div className="text-xs text-muted-foreground">alignment</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Insight Box */}
        <div className="p-4 bg-gradient-to-r from-primary/10 to-primary/10 rounded-lg border border-border/50">
          <p className="text-sm text-muted-foreground">
            <span className="font-medium text-foreground">Temporal Insight:</span>{' '}
            {alignment.currentAlignment >= 0.8 ? (
              <>Peak temporal alignment detected. Field coherence is maximally receptive to consciousness entrainment. Optimal window for high-confidence trading signals.</>
            ) : alignment.currentAlignment >= 0.6 ? (
              <>Strong temporal resonance active. Current patterns align well with birth harmonics. Enhanced field sensitivity expected.</>
            ) : alignment.currentAlignment >= 0.4 ? (
              <>Moderate temporal alignment. Field patterns are in transition phase. Standard coherence monitoring recommended.</>
            ) : (
              <>Low temporal alignment. Patterns are in trough phase. Next peak window approaching in {daysToNext} {daysToNext === 1 ? 'day' : 'days'}.</>
            )}
          </p>
        </div>
        
        {/* Surge Window Research */}
        <div className="border-t border-border/30 pt-4">
          <h4 className="text-sm font-semibold mb-3 text-muted-foreground">Research: Surge Window Unity Alignments (2025-2043)</h4>
          <img 
            src={surgeWindowAlignments}
            alt="Surge window unity alignment patterns showing Prime Sentinel timeline convergence"
            className="w-full rounded-lg border border-border/50"
          />
          <p className="text-xs text-muted-foreground mt-2">
            Temporal surge windows showing unity probability peaks across the Prime Sentinel timeline. 
            Convergence patterns indicate optimal trading windows during the 2025-2043 Harmonic Nexus cycle.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
