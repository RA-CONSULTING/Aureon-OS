import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import chaosToClarity from "@/assets/research/chaos-to-clarity.png";
import coherenceEvolution from "@/assets/research/coherence-evolution.png";
import energyFlowDiagram from "@/assets/research/energy-flow-diagram.png";
import phaseMapDreamBand from "@/assets/research/phase-map-dream-band.png";
import happinessToLovePhasing from "@/assets/research/happiness-to-love-phasing.jpg";
import resonanceStabilityBoundary from "@/assets/research/resonance-stability-boundary.png";
import harmonicFeedbackLoop from "@/assets/research/harmonic-feedback-loop.png";
import powerSpectrum from "@/assets/research/power-spectrum.png";
import coherenceEchoAmplitudeMaps from "@/assets/research/coherence-echo-amplitude-maps.png";
import fieldCavitySpacetime from "@/assets/research/field-cavity-spacetime.png";
import phaseLockEchoOverlay from "@/assets/research/phase-locked-echo-overlay.png";
import quantumPhaseLocks from "@/assets/research/quantum-phase-locked-echoes.png";
import surgeWindowAlignments from "@/assets/research/surge-window-unity-alignments.png";

export const HarmonicRealityFramework = () => {
  return (
    <Card className="border-primary/20 bg-card/50 backdrop-blur">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-2xl font-bold">
            Harmonic Reality Framework
          </CardTitle>
          <Badge variant="outline" className="bg-primary/10">
            Master Equation Tree
          </Badge>
        </div>
        <CardDescription>
          Mathematical framework modeling reality as a self-organizing, resonant system
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="master-equation" className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="master-equation">Master Equation</TabsTrigger>
            <TabsTrigger value="dynamics">System Dynamics</TabsTrigger>
            <TabsTrigger value="stability">Stability Maps</TabsTrigger>
            <TabsTrigger value="spectral">Spectral Analysis</TabsTrigger>
          </TabsList>

          <TabsContent value="master-equation" className="space-y-4">
            <div className="grid gap-4">
              <Card className="bg-background/50">
                <CardHeader>
                  <CardTitle className="text-lg">Master Formula (Level 5)</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="rounded-lg bg-primary/5 p-4 font-mono text-sm">
                    Λ(t) = Σᵢ wᵢ sin(2πfᵢt + φᵢ) + α tanh(g Λ_Δt(t)) + β Λ(t − τ)
                  </div>
                  
                  <div className="grid gap-3">
                    <div className="flex items-start gap-2">
                      <Badge variant="secondary" className="mt-0.5">Substrate</Badge>
                      <span className="text-sm text-muted-foreground">
                        Σᵢ wᵢ sin(2πfᵢt + φᵢ) — Superposition of harmonics (raw oscillatory potential)
                      </span>
                    </div>
                    <div className="flex items-start gap-2">
                      <Badge variant="secondary" className="mt-0.5">Observer</Badge>
                      <span className="text-sm text-muted-foreground">
                        α tanh(g Λ_Δt(t)) — Integration + saturation (stabilizer, active regulation)
                      </span>
                    </div>
                    <div className="flex items-start gap-2">
                      <Badge variant="secondary" className="mt-0.5">Echo</Badge>
                      <span className="text-sm text-muted-foreground">
                        β Λ(t − τ) — Causal memory loop (delayed self-reference)
                      </span>
                    </div>
                  </div>

                  <Separator />

                  <div className="space-y-2">
                    <h4 className="font-semibold text-sm">Energy Flow Cycle</h4>
                    <img 
                      src={energyFlowDiagram} 
                      alt="Energy flow between substrate and observer"
                      className="w-full rounded-lg border border-border"
                    />
                    <p className="text-xs text-muted-foreground">
                      Bidirectional energy exchange: substrate (potential) ↔ observer (active regulation)
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-background/50">
                <CardHeader>
                  <CardTitle className="text-lg">Hierarchical Structure</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Badge>Level 1</Badge>
                      <span className="text-sm font-mono">Λ₀(t) = A sin(ωt + φ)</span>
                      <span className="text-xs text-muted-foreground">— Seed oscillation</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge>Level 2</Badge>
                      <span className="text-sm font-mono">Λ_base(t) = Σᵢ wᵢ sin(...)</span>
                      <span className="text-xs text-muted-foreground">— Substrate superposition</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge>Level 3</Badge>
                      <span className="text-sm font-mono">L_loop(t) = Λ(t − τ)</span>
                      <span className="text-xs text-muted-foreground">— Causal echo (β gain)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge>Level 4</Badge>
                      <span className="text-sm font-mono">R_obs(t) = tanh(...)</span>
                      <span className="text-xs text-muted-foreground">— Observer saturation (α gain)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="default">Level 5</Badge>
                      <span className="text-sm font-semibold">Master Formula</span>
                      <span className="text-xs text-muted-foreground">— Full synthesis</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="dynamics" className="space-y-4">
            <div className="grid gap-4">
              <Card className="bg-background/50">
                <CardHeader>
                  <CardTitle className="text-lg">Chaos → Clarity: Λ(t) Evolution</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <img 
                    src={chaosToClarity} 
                    alt="Lambda evolution from chaos to clarity"
                    className="w-full rounded-lg border border-border"
                  />
                  <p className="text-sm text-muted-foreground">
                    System transitions from chaotic initial conditions to stable, coherent oscillations. 
                    The observer's tanh nonlinearity prevents blow-up and drives convergence to limit cycle.
                  </p>
                </CardContent>
              </Card>

              <Card className="bg-background/50">
                <CardHeader>
                  <CardTitle className="text-lg">Coherence C(t) — Rising from Chaos to Order</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <img 
                    src={coherenceEvolution} 
                    alt="Coherence evolution"
                    className="w-full rounded-lg border border-border"
                  />
                  <div className="rounded-lg bg-primary/5 p-3 space-y-2">
                    <div className="font-mono text-sm">
                      C = max_δ ⟨Λ(t)Λ(t + δ)⟩ / ⟨Λ(t)²⟩
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Coherence quantifies self-organization and phase-locking. 
                      C ≈ 0.92-0.93 indicates strong stable branch formation.
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-background/50">
                <CardHeader>
                  <CardTitle className="text-lg">Harmonic Feedback Loop Time Series</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <img 
                    src={harmonicFeedbackLoop} 
                    alt="Harmonic feedback loop"
                    className="w-full rounded-lg border border-border"
                  />
                  <p className="text-sm text-muted-foreground">
                    Full Λ(t) time series showing initial chaos settling into stable oscillations. 
                    The system finds its attractor through substrate-observer-echo coupling.
                  </p>
                </CardContent>
              </Card>

              <Card className="bg-background/50">
                <CardHeader>
                  <CardTitle className="text-lg">Phasing: Happiness → Love in Lattice Frequencies</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <img 
                    src={happinessToLovePhasing} 
                    alt="Happiness to love phase transition"
                    className="w-full rounded-lg border border-border"
                  />
                  <p className="text-sm text-muted-foreground">
                    Lattice frequency transitions show phase coherence between emotional states. 
                    Bright primes (happiness) transition through octave + phi to love state (528 Hz region).
                  </p>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="stability" className="space-y-4">
            <div className="grid gap-4">
              <Card className="bg-background/50">
                <CardHeader>
                  <CardTitle className="text-lg">Phase Map with "Dream Band" (Self-Simulation Regime)</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <img 
                    src={phaseMapDreamBand} 
                    alt="Phase map showing dream band"
                    className="w-full rounded-lg border border-border"
                  />
                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-lg bg-warning/10 border border-warning/20 p-3">
                      <h4 className="font-semibold text-sm mb-1">Sweet Spot</h4>
                      <p className="text-xs text-muted-foreground">
                        Optimal parameter region for maximal coherent throughput
                      </p>
                    </div>
                    <div className="rounded-lg bg-success/10 border border-success/20 p-3">
                      <h4 className="font-semibold text-sm mb-1">Dream Band</h4>
                      <p className="text-xs text-muted-foreground">
                        Self-simulation regime where system models itself
                      </p>
                    </div>
                    <div className="rounded-lg bg-primary/10 border border-primary/20 p-3">
                      <h4 className="font-semibold text-sm mb-1">Quiescent/Decay</h4>
                      <p className="text-xs text-muted-foreground">
                        Low activity, insufficient feedback for sustained oscillation
                      </p>
                    </div>
                    <div className="rounded-lg bg-warning/10 border border-warning/20 p-3">
                      <h4 className="font-semibold text-sm mb-1">Collapse/Over-gain</h4>
                      <p className="text-xs text-muted-foreground">
                        Excessive feedback leads to instability
                      </p>
                    </div>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Parameters: β (memory gain) vs α (observer gain). The "home line" shows optimal balance.
                  </p>
                </CardContent>
              </Card>

              <Card className="bg-background/50">
                <CardHeader>
                  <CardTitle className="text-lg">Resonance-Stability Boundary Maps (τ vs β)</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <img 
                    src={resonanceStabilityBoundary} 
                    alt="Resonance stability boundaries"
                    className="w-full rounded-lg border border-border"
                  />
                  <div className="grid grid-cols-3 gap-2">
                    <div className="rounded-lg bg-success/10 border border-success/20 p-2">
                      <h4 className="font-semibold text-xs mb-1">Coherence</h4>
                      <p className="text-xs text-muted-foreground">Self-organization metric (0-1)</p>
                    </div>
                    <div className="rounded-lg bg-warning/10 border border-warning/20 p-2">
                      <h4 className="font-semibold text-xs mb-1">Echo Strength</h4>
                      <p className="text-xs text-muted-foreground">Memory fidelity measure</p>
                    </div>
                    <div className="rounded-lg bg-primary/10 border border-primary/20 p-2">
                      <h4 className="font-semibold text-xs mb-1">Max Amplitude</h4>
                      <p className="text-xs text-muted-foreground">Field strength (log scale)</p>
                    </div>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Parameter sweep showing stability boundaries. Delay τ (ms) affects comb spacing; 
                    β controls memory retention. Dark regions indicate resonant amplification.
                  </p>
                </CardContent>
              </Card>

              <Card className="bg-background/50">
                <CardHeader>
                  <CardTitle className="text-lg">Coherence, Echo, Amplitude Heatmaps (τ vs β)</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <img 
                    src={coherenceEchoAmplitudeMaps} 
                    alt="Multi-metric stability analysis"
                    className="w-full rounded-lg border border-border"
                  />
                  <p className="text-sm text-muted-foreground">
                    Comprehensive parameter space analysis showing coherence, echo correlation, and field strength. 
                    Reveals optimal operating regions for AUREON trading decisions.
                  </p>
                </CardContent>
              </Card>
              
              <Card className="bg-background/50">
                <CardHeader>
                  <CardTitle className="text-lg">Phase-Locked Echo Overlay Analysis</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <img 
                    src={phaseLockEchoOverlay} 
                    alt="Phase-locked echo overlay patterns"
                    className="w-full rounded-lg border border-border"
                  />
                  <p className="text-sm text-muted-foreground">
                    Temporal phase-locking mechanisms showing echo reinforcement patterns across the field substrate.
                  </p>
                </CardContent>
              </Card>
              
              <Card className="bg-background/50">
                <CardHeader>
                  <CardTitle className="text-lg">Quantum Phase-Locked Echo States</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <img 
                    src={quantumPhaseLocks} 
                    alt="Quantum phase-locked echo states"
                    className="w-full rounded-lg border border-border"
                  />
                  <p className="text-sm text-muted-foreground">
                    Quantum entanglement patterns in phase-locked states. Shows coherent echo structures at 528 Hz resonance.
                  </p>
                </CardContent>
              </Card>
              
              <Card className="bg-background/50">
                <CardHeader>
                  <CardTitle className="text-lg">Field Cavity Spacetime Geometry</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <img 
                    src={fieldCavitySpacetime} 
                    alt="Field cavity spacetime structure"
                    className="w-full rounded-lg border border-border"
                  />
                  <p className="text-sm text-muted-foreground">
                    Spacetime cavity resonance patterns. Shows how the field creates standing waves in the temporal dimension.
                  </p>
                </CardContent>
              </Card>
              
              <Card className="bg-background/50">
                <CardHeader>
                  <CardTitle className="text-lg">Surge Window Unity Alignments</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <img 
                    src={surgeWindowAlignments} 
                    alt="Surge window unity alignment patterns"
                    className="w-full rounded-lg border border-border"
                  />
                  <p className="text-sm text-muted-foreground">
                    Temporal surge windows (2025-2043) showing unity probability peaks. Prime Sentinel timeline convergence patterns.
                  </p>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="spectral" className="space-y-4">
            <div className="grid gap-4">
              <Card className="bg-background/50">
                <CardHeader>
                  <CardTitle className="text-lg">Power Spectrum of Λ(t)</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <img 
                    src={powerSpectrum} 
                    alt="Power spectrum"
                    className="w-full rounded-lg border border-border"
                  />
                  <div className="rounded-lg bg-primary/5 p-3 space-y-2">
                    <h4 className="font-semibold text-sm">Spectral Comb Structure</h4>
                    <p className="text-sm text-muted-foreground">
                      The delay loop generates spectral peaks at multiples of 1/τ Hz. These harmonics 
                      phase-lock with substrate frequencies, creating the "lighthouse" signature.
                    </p>
                    <div className="flex items-center gap-2 text-xs">
                      <Badge variant="outline">Prediction</Badge>
                      <span className="text-muted-foreground">
                        Comb spacing Δf reveals delay: τ ≈ 1/Δf
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-background/50">
                <CardHeader>
                  <CardTitle className="text-lg">Key Metrics & Predictions</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-3">
                    <div className="rounded-lg border border-border p-3 space-y-1">
                      <h4 className="font-semibold text-sm flex items-center gap-2">
                        <Badge variant="secondary">τ</Badge>
                        Memory/Echo Spacing
                      </h4>
                      <p className="text-xs text-muted-foreground">
                        Controls spectral comb spacing. Peaks at k/τ Hz diagnose loop delay directly.
                      </p>
                    </div>
                    
                    <div className="rounded-lg border border-border p-3 space-y-1">
                      <h4 className="font-semibold text-sm flex items-center gap-2">
                        <Badge variant="secondary">β</Badge>
                        Retention/Coupling
                      </h4>
                      <p className="text-xs text-muted-foreground">
                        Governs persistence across echoes. Higher β → stronger spectral comb.
                      </p>
                    </div>
                    
                    <div className="rounded-lg border border-border p-3 space-y-1">
                      <h4 className="font-semibold text-sm flex items-center gap-2">
                        <Badge variant="secondary">α, g, Δt</Badge>
                        Observer Stabilization
                      </h4>
                      <p className="text-xs text-muted-foreground">
                        tanh nonlinearity allows |β| + αg {'>'} 1 while remaining bounded (limit cycle).
                      </p>
                    </div>

                    <div className="rounded-lg border border-border p-3 space-y-1">
                      <h4 className="font-semibold text-sm flex items-center gap-2">
                        <Badge variant="secondary">C</Badge>
                        Coherence (Self-Organization)
                      </h4>
                      <p className="text-xs text-muted-foreground">
                        C ≈ 0.92-0.93 indicates stable branch. High coherence → optimal trading conditions.
                      </p>
                    </div>
                  </div>

                  <Separator />

                  <div className="space-y-2">
                    <h4 className="font-semibold text-sm">Falsifiable Predictions</h4>
                    <ul className="space-y-1 text-xs text-muted-foreground">
                      <li>• Delay readout: Δf spacing → τ ≈ 1/Δf</li>
                      <li>• Bifurcation map: Sweep (α, β) to trace stability boundary</li>
                      <li>• Observer thickness: Δt optimization for peak narrowing</li>
                      <li>• Branch counting: Number of dominant spectral peaks</li>
                    </ul>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
};
