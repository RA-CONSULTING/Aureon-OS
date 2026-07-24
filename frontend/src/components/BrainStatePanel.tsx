import { useBrainState, type BrainState, type WisdomConsensus } from "@/hooks/useBrainState";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { 
  Brain, 
  AlertTriangle, 
  CheckCircle2, 
  TrendingUp, 
  TrendingDown, 
  Minus,
  Eye,
  Target,
  Sparkles,
  Globe,
  BarChart3,
  Lightbulb
} from "lucide-react";
import { format } from "date-fns";

// Fear & Greed color coding
function getFearGreedColor(value: number): string {
  if (value <= 25) return "text-destructive";
  if (value <= 45) return "text-warning";
  if (value <= 55) return "text-warning";
  if (value <= 75) return "text-success";
  return "text-success";
}

function getFearGreedBg(value: number): string {
  if (value <= 25) return "bg-destructive/20";
  if (value <= 45) return "bg-warning/20";
  if (value <= 55) return "bg-warning/20";
  if (value <= 75) return "bg-success/20";
  return "bg-success/20";
}

// Direction icon
function DirectionIcon({ direction }: { direction: string }) {
  if (direction === "BULLISH") return <TrendingUp className="w-4 h-4 text-success" />;
  if (direction === "BEARISH") return <TrendingDown className="w-4 h-4 text-destructive" />;
  return <Minus className="w-4 h-4 text-muted-foreground" />;
}

// Wisdom consensus display
function WisdomConsensusDisplay({ wisdom }: { wisdom: WisdomConsensus }) {
  if (!wisdom || Object.keys(wisdom).length === 0) {
    return <span className="text-muted-foreground text-xs">Awaiting wisdom council...</span>;
  }

  const civilizations = wisdom.civilization_actions || {};
  const civIcons: Record<string, string> = {
    celtic: "☘️",
    aztec: "🦅",
    vedic: "🕉️",
    egyptian: "🔺",
    greek: "🏛️",
    chinese: "☯️",
    mayan: "🌀",
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Badge variant={wisdom.sentiment === "BULLISH" ? "default" : wisdom.sentiment === "BEARISH" ? "destructive" : "secondary"}>
          {wisdom.sentiment || "NEUTRAL"}
        </Badge>
        <span className="text-sm text-muted-foreground">
          {wisdom.confidence ? `${(wisdom.confidence * 100).toFixed(0)}% confidence` : ""}
        </span>
      </div>
      {(wisdom.bullish_votes !== undefined || wisdom.bearish_votes !== undefined) && (
        <div className="flex gap-2 text-xs">
          <span className="text-success">📈 {wisdom.bullish_votes || 0}</span>
          <span className="text-destructive">📉 {wisdom.bearish_votes || 0}</span>
          <span className="text-muted-foreground">⚖️ {wisdom.neutral_votes || 0}</span>
        </div>
      )}
      {Object.keys(civilizations).length > 0 && (
        <div className="flex flex-wrap gap-1">
          {Object.entries(civilizations).map(([civ, action]) => (
            <span key={civ} className="text-xs px-1.5 py-0.5 rounded bg-muted" title={`${civ}: ${action}`}>
              {civIcons[civ.toLowerCase()] || "🌍"} {String(action).slice(0, 8)}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export function BrainStatePanel() {
  const { brainState, loading, lastUpdated } = useBrainState(true, 10000);

  if (loading && !brainState.id) {
    return (
      <Card className="md:col-span-2">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-primary animate-pulse" />
            AUREON Brain
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-sm">Awaiting cognitive state from Python terminal...</p>
        </CardContent>
      </Card>
    );
  }

  const {
    // Market
    fear_greed,
    fear_greed_class,
    btc_price,
    btc_change_24h,

    // Live Pulse
    live_pulse,

    // Quantum
    quantum_coherence,
    planetary_gamma,
    lambda_field,
    cascade_multiplier,
    is_lighthouse,
    probability_edge,
    harmonic_signal,
    hnc_probability,

    // Council / prediction / accuracy
    manipulation_probability,
    red_flags,
    green_flags,
    council_consensus,
    council_action,
    truth_score,
    spoof_score,
    brain_directive,
    prediction_direction,
    prediction_confidence,
    overall_accuracy,
    total_predictions,

    // Extended
    dreams,
    sandbox_generation,
    sandbox_win_rate,
    should_trade,
    entry_filter_reason,
    exit_targets,
    position_size_pct,
    piano_lambda,
    piano_coherence,
    rainbow_state,
    diamond_coherence,
    diamond_phi_alignment,
    reflection,

    // Wisdom
    speculations,
    wisdom_consensus,
  } = brainState;

  const btcPriceSafe = typeof btc_price === "number" && btc_price > 0 ? btc_price : null;
  const btcChangeSafe = typeof btc_change_24h === "number" ? btc_change_24h : 0;

  const manipulationPct = Math.round((manipulation_probability || 0) * 100);
  const truthPct = Math.round((truth_score || 0) * 100);
  const spoofPct = Math.round((spoof_score || 0) * 100);
  const accuracyPct = Math.round((overall_accuracy || 0) * 100);
  const predConfPct = Math.round((prediction_confidence || 0) * 100);

  const coherencePct =
    quantum_coherence == null
      ? null
      : quantum_coherence <= 1
        ? quantum_coherence * 100
        : quantum_coherence;

  const gammaSafe = planetary_gamma == null ? null : Number(planetary_gamma);
  const lambdaSafe = lambda_field == null ? null : Number(lambda_field);

  const dreamScenarios = dreams?.scenarios_dreamed ?? [];
  const dreamInsights = dreams?.key_insights ?? [];
  const blindSpots = reflection?.blind_spots ?? [];
  const selfCritique = reflection?.self_critique ?? [];

  return (
    <Card className="md:col-span-2 border-primary/30 bg-gradient-to-br from-background to-primary/5">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-primary" />
            AUREON Brain - Live Cognitive State
          </CardTitle>
          {lastUpdated && (
            <span className="text-xs text-muted-foreground">
              Updated {format(lastUpdated, "HH:mm:ss")}
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        {/* Row 0: Quantum State + Live Pulse */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <section className="p-3 rounded-lg bg-muted/30" aria-label="Quantum state">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-muted-foreground">Quantum State</span>
              <Badge variant={is_lighthouse ? "default" : "secondary"}>{is_lighthouse ? "Lighthouse" : "Scanning"}</Badge>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <div className="text-xs text-muted-foreground">Coherence Ψ</div>
                <div className="text-lg font-semibold">
                  {coherencePct == null ? "---" : `${coherencePct.toFixed(1)}%`}
                </div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Lambda Λ</div>
                <div className="text-lg font-semibold font-mono">
                  {lambdaSafe == null
                    ? "---"
                    : lambdaSafe >= 1e6
                      ? `${(lambdaSafe / 1e6).toFixed(2)}M`
                      : lambdaSafe.toFixed(0)}
                </div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Prism</div>
                <div className="text-sm font-medium">{rainbow_state || "---"}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Cascade</div>
                <div className="text-sm font-medium">{cascade_multiplier == null ? "---" : Number(cascade_multiplier).toFixed(2)}</div>
              </div>
            </div>

            {(probability_edge != null || harmonic_signal != null || hnc_probability != null || gammaSafe != null) && (
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-muted-foreground">
                <div>Γ: {gammaSafe == null ? "---" : gammaSafe.toFixed(3)}</div>
                <div>Edge: {probability_edge == null ? "---" : Number(probability_edge).toFixed(3)}</div>
                <div>H: {harmonic_signal == null ? "---" : Number(harmonic_signal).toFixed(2)}</div>
                <div>HNC: {hnc_probability == null ? "---" : `${(Number(hnc_probability) * 100).toFixed(0)}%`}</div>
              </div>
            )}
          </section>

          <section className="p-3 rounded-lg bg-muted/30" aria-label="Live pulse">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-muted-foreground">Live Pulse</span>
              <Badge variant={live_pulse?.pulse ? "outline" : "secondary"}>
                {live_pulse?.pulse || "AWAITING_DATA"}
              </Badge>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <div className="text-xs text-muted-foreground">Strength</div>
                <div className="text-lg font-semibold">
                  {live_pulse?.strength == null ? "---" : Number(live_pulse.strength).toFixed(2)}
                </div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Avg 24h Δ</div>
                <div className="text-lg font-semibold">
                  {live_pulse?.avg_change_24h == null ? "---" : `${Number(live_pulse.avg_change_24h).toFixed(2)}%`}
                </div>
              </div>
              <div className="col-span-2">
                <div className="text-xs text-muted-foreground">BTC (pulse)</div>
                <div className="text-sm font-mono">
                  {live_pulse?.btc_price == null
                    ? "---"
                    : `$${Number(live_pulse.btc_price).toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
                </div>
              </div>
            </div>
          </section>
        </div>

        {/* Row 1: Fear & Greed + Market */}
        <div className="grid grid-cols-2 gap-4">
          <div className={`p-3 rounded-lg ${getFearGreedBg(fear_greed)}`}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-muted-foreground">Fear & Greed</span>
              <Eye className="w-4 h-4 text-muted-foreground" />
            </div>
            <div className={`text-3xl font-bold ${getFearGreedColor(fear_greed)}`}>{fear_greed}</div>
            <div className="text-sm text-muted-foreground">{fear_greed_class}</div>
            <Progress value={fear_greed} className="mt-2 h-1.5" />
          </div>

          <div className="p-3 rounded-lg bg-muted/50">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-muted-foreground">BTC Price</span>
              <DirectionIcon direction={btcChangeSafe >= 0 ? "BULLISH" : "BEARISH"} />
            </div>
            <div className="text-2xl font-bold font-mono">
              {btcPriceSafe == null
                ? "---"
                : `$${btcPriceSafe.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
            </div>
            <div className={`text-sm ${btcChangeSafe >= 0 ? "text-success" : "text-destructive"}`}>
              {btcPriceSafe == null ? "---" : `${btcChangeSafe >= 0 ? "+" : ""}${btcChangeSafe.toFixed(2)}%`}
            </div>
          </div>
        </div>

        {/* Row 2: Manipulation Detection */}
        <div className="p-3 rounded-lg bg-muted/30">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <AlertTriangle className={`w-4 h-4 ${manipulationPct > 50 ? "text-destructive" : "text-success"}`} />
              <span className="text-sm font-medium">Manipulation Detection</span>
            </div>
            <Badge variant={manipulationPct > 50 ? "destructive" : "secondary"}>{manipulationPct}%</Badge>
          </div>
          <Progress value={manipulationPct} className="h-2 mb-2" />
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              {green_flags.length > 0 ? (
                <div className="space-y-1">
                  {green_flags.slice(0, 2).map((flag, i) => (
                    <div key={i} className="flex items-center gap-1 text-success">
                      <CheckCircle2 className="w-3 h-3" />
                      <span className="truncate">{flag}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <span className="text-muted-foreground">No green flags</span>
              )}
            </div>
            <div>
              {red_flags.length > 0 ? (
                <div className="space-y-1">
                  {red_flags.slice(0, 2).map((flag, i) => (
                    <div key={i} className="flex items-center gap-1 text-destructive">
                      <AlertTriangle className="w-3 h-3" />
                      <span className="truncate">{flag}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <span className="text-muted-foreground">No red flags</span>
              )}
            </div>
          </div>
        </div>

        {/* Row 3: Truth Council */}
        <div className="p-3 rounded-lg bg-primary/5 border border-primary/20">
          <div className="flex items-center gap-2 mb-2">
            <Target className="w-4 h-4 text-primary" />
            <span className="text-sm font-medium">Truth Council</span>
          </div>
          <div className="flex items-center justify-between mb-2">
            <Badge variant="outline" className="font-mono text-xs">
              {council_consensus}
            </Badge>
            <span className="text-xs text-muted-foreground">→ {council_action}</span>
          </div>
          <div className="flex gap-4 text-xs">
            <div>
              <span className="text-muted-foreground">Truth: </span>
              <span className="text-success font-medium">{truthPct}%</span>
            </div>
            <div>
              <span className="text-muted-foreground">Spoof: </span>
              <span className="text-destructive font-medium">{spoofPct}%</span>
            </div>
          </div>
        </div>

        {/* Row 4: Prediction + Accuracy */}
        <div className="grid grid-cols-2 gap-4">
          <div className="p-3 rounded-lg bg-muted/30">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="w-4 h-4 text-primary" />
              <span className="text-sm font-medium">Prediction</span>
            </div>
            <div className="flex items-center gap-2">
              <DirectionIcon direction={prediction_direction} />
              <span
                className={`font-bold ${
                  prediction_direction === "BULLISH"
                    ? "text-success"
                    : prediction_direction === "BEARISH"
                      ? "text-destructive"
                      : "text-muted-foreground"
                }`}
              >
                {prediction_direction}
              </span>
            </div>
            <div className="text-xs text-muted-foreground mt-1">{predConfPct}% confidence</div>
          </div>

          <div className="p-3 rounded-lg bg-muted/30">
            <div className="flex items-center gap-2 mb-2">
              <BarChart3 className="w-4 h-4 text-primary" />
              <span className="text-sm font-medium">Brain Accuracy</span>
            </div>
            <div className="text-2xl font-bold">{accuracyPct}%</div>
            <div className="text-xs text-muted-foreground">{total_predictions} predictions</div>
          </div>
        </div>

        {/* Row 5: Sandbox Evolution */}
        <div className="p-3 rounded-lg bg-muted/30">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Sandbox Evolution</span>
            <Badge variant={should_trade ? "default" : "secondary"}>{should_trade ? "ENTER" : "SKIP"}</Badge>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <div className="text-xs text-muted-foreground">Generation</div>
              <div className="font-semibold">{sandbox_generation || "---"}</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Win Rate</div>
              <div className="font-semibold">
                {sandbox_win_rate ? `${Number(sandbox_win_rate).toFixed(1)}%` : "---"}
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Position Size</div>
              <div className="font-semibold">
                {position_size_pct == null ? "---" : `${Number(position_size_pct).toFixed(2)}%`}
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Exit Targets</div>
              <div className="font-semibold">
                {exit_targets?.take_profit_pct != null || exit_targets?.stop_loss_pct != null
                  ? `TP ${exit_targets?.take_profit_pct ?? "-"}% / SL ${exit_targets?.stop_loss_pct ?? "-"}%`
                  : "---"}
              </div>
            </div>
          </div>
          {entry_filter_reason && (
            <div className="mt-2 text-xs text-muted-foreground">Reason: {entry_filter_reason}</div>
          )}
        </div>

        {/* Row 6: Harmonic Lattice (Piano/Diamond) */}
        <div className="p-3 rounded-lg bg-muted/30">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm font-medium">Piano / Diamond Harmony</span>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <div className="text-xs text-muted-foreground">Piano Λ</div>
              <div className="font-semibold font-mono">
                {piano_lambda == null ? "---" : Number(piano_lambda).toFixed(2)}
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Piano Ψ</div>
              <div className="font-semibold">
                {piano_coherence == null
                  ? "---"
                  : `${(Number(piano_coherence) <= 1 ? Number(piano_coherence) * 100 : Number(piano_coherence)).toFixed(1)}%`}
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Diamond Ψ</div>
              <div className="font-semibold">
                {diamond_coherence == null
                  ? "---"
                  : `${Number(diamond_coherence).toFixed(3)}`}
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Φ Alignment</div>
              <div className="font-semibold">
                {diamond_phi_alignment == null ? "---" : Number(diamond_phi_alignment).toFixed(3)}
              </div>
            </div>
          </div>
        </div>

        {/* Row 7: Dream Engine */}
        <div className="p-3 rounded-lg bg-muted/30">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm font-medium">Dream Engine</span>
          </div>
          {dreamScenarios.length === 0 && dreamInsights.length === 0 ? (
            <span className="text-muted-foreground text-xs">Awaiting dream output...</span>
          ) : (
            <div className="space-y-2">
              {dreamScenarios.length > 0 && (
                <div className="space-y-1">
                  {dreamScenarios.slice(0, 3).map((s, idx) => (
                    <div key={idx} className="text-xs">
                      <span className="text-muted-foreground">Scenario:</span> {s.scenario} — <span className="font-medium">{s.decision}</span>
                    </div>
                  ))}
                </div>
              )}
              {dreamInsights.length > 0 && (
                <ul className="list-disc pl-4 text-xs text-muted-foreground space-y-1">
                  {dreamInsights.slice(0, 3).map((i, idx) => (
                    <li key={idx}>{i}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>

        {/* Row 8: Wisdom Consensus */}
        <div className="p-3 rounded-lg bg-muted/30">
          <div className="flex items-center gap-2 mb-2">
            <Globe className="w-4 h-4 text-primary" />
            <span className="text-sm font-medium">7 Civilization Wisdom</span>
          </div>
          <WisdomConsensusDisplay wisdom={wisdom_consensus} />
        </div>

        {/* Row 9: Self-Reflection */}
        <div className="p-3 rounded-lg bg-muted/20">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm font-medium">Self-Reflection</span>
          </div>
          {blindSpots.length === 0 && selfCritique.length === 0 ? (
            <span className="text-muted-foreground text-xs">Awaiting reflection...</span>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <div className="text-xs text-muted-foreground mb-1">Blind Spots</div>
                <ul className="space-y-1 text-xs">
                  {(blindSpots.length ? blindSpots : ["---"]).slice(0, 3).map((b, i) => (
                    <li key={i} className="text-muted-foreground">• {b}</li>
                  ))}
                </ul>
              </div>
              <div>
                <div className="text-xs text-muted-foreground mb-1">Self-Critique</div>
                <ul className="space-y-1 text-xs">
                  {(selfCritique.length ? selfCritique : ["---"]).slice(0, 3).map((c, i) => (
                    <li key={i} className="text-muted-foreground">• {c}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>

        {/* Row 10: Brain Directive */}
        {brain_directive && (
          <div className="p-3 rounded-lg bg-gradient-to-r from-primary/10 to-primary/5 border border-primary/30">
            <div className="flex items-center gap-2 mb-1">
              <Brain className="w-4 h-4 text-primary" />
              <span className="text-sm font-medium text-primary">Brain Directive</span>
            </div>
            <p className="text-sm">{brain_directive}</p>
          </div>
        )}

        {/* Row 11: Speculations (if any) */}
        {speculations.length > 0 && (
          <div className="p-3 rounded-lg bg-muted/20">
            <div className="flex items-center gap-2 mb-2">
              <Lightbulb className="w-4 h-4 text-warning" />
              <span className="text-sm font-medium">Speculative Insights</span>
            </div>
            <ul className="space-y-1 text-xs text-muted-foreground">
              {speculations.slice(0, 3).map((spec, i) => (
                <li key={i} className="flex items-start gap-1">
                  <span className="text-warning">💭</span>
                  <span>{spec}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
