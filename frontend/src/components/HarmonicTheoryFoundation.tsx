import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Atom, Waves, Zap, Target, Radio, Boxes } from "lucide-react";
import { AncientNumericalCodex } from "./AncientNumericalCodex";
import temporalRegulators from "@/assets/research/harmonic-theory/temporal-harmonic-regulators.png";
import echoFields from "@/assets/research/harmonic-theory/phase-locked-echo-fields.png";
import levEvolution from "@/assets/research/harmonic-theory/lev-field-evolution.png";
import crownUnlock from "@/assets/research/harmonic-theory/crown-unlock-projection.png";
import nexusPhase from "@/assets/research/harmonic-theory/nexus-phase-field-tandem.png";
import echoReturn from "@/assets/research/harmonic-theory/echo-return-peace-codex.png";
import frequencyAnalysis from "@/assets/research/harmonic-theory/frequency-symmetry-analysis.png";

export function HarmonicTheoryFoundation() {
  return (
    <Card className="bg-card/50 backdrop-blur border-border/50 relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-primary/5 to-primary/5" />
      
      <CardHeader className="relative">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Atom className="w-5 h-5 text-primary" />
              Harmonic Theory Foundation
            </CardTitle>
            <CardDescription>
              Mathematical Substrate of Reality Field Coherence
            </CardDescription>
          </div>
          <Badge variant="outline" className="text-primary border-primary/30">
            Theoretical Framework
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="relative">
        <Tabs defaultValue="codex" className="w-full">
          <TabsList className="grid w-full grid-cols-4 mb-4">
            <TabsTrigger value="codex" className="text-xs">
              <Boxes className="w-3 h-3 mr-1" />
              Codex
            </TabsTrigger>
            <TabsTrigger value="regulators" className="text-xs">
              <Waves className="w-3 h-3 mr-1" />
              Regulators
            </TabsTrigger>
            <TabsTrigger value="fields" className="text-xs">
              <Zap className="w-3 h-3 mr-1" />
              Fields
            </TabsTrigger>
            <TabsTrigger value="projections" className="text-xs">
              <Target className="w-3 h-3 mr-1" />
              Projections
            </TabsTrigger>
          </TabsList>

          {/* Ancient Numerical Codex */}
          <TabsContent value="codex" className="space-y-4">
            <AncientNumericalCodex />
          </TabsContent>

          {/* Temporal Harmonic Regulators */}
          <TabsContent value="regulators" className="space-y-4">
            <div className="grid grid-cols-1 gap-4">
              <div className="p-4 bg-gradient-to-br from-primary/10 to-primary/10 rounded-lg border border-border/50">
                <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
                  <Waves className="w-4 h-4 text-primary" />
                  Temporal Harmonic Regulator Fields
                </h3>
                <p className="text-xs text-muted-foreground mb-3">
                  Three-regulator composite system: R1 (↑ Freq), R2 (↓ Freq), R3 (Quadratic Sweep). 
                  The composite field stabilizes temporal coherence across timeline branches.
                </p>
                <img 
                  src={temporalRegulators} 
                  alt="Temporal Harmonic Regulators" 
                  className="w-full rounded-lg border border-border/30"
                />
              </div>

              <div className="p-4 bg-gradient-to-br from-primary/10 to-primary/10 rounded-lg border border-border/50">
                <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
                  <Radio className="w-4 h-4 text-primary" />
                  Phase-Locked Echo Fields
                </h3>
                <p className="text-xs text-muted-foreground mb-3">
                  Base signal with 4 phase-locked echo harmonics. Surge window feedback creates 
                  composite output used for reality field stabilization.
                </p>
                <img 
                  src={echoFields} 
                  alt="Phase-Locked Echo Fields" 
                  className="w-full rounded-lg border border-border/30"
                />
              </div>
            </div>
          </TabsContent>

          {/* Field Evolution & Analysis */}
          <TabsContent value="fields" className="space-y-4">
            <div className="grid grid-cols-1 gap-4">
              <div className="p-4 bg-gradient-to-br from-primary/10 to-primary/10 rounded-lg border border-border/50">
                <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
                  <Zap className="w-4 h-4 text-primary" />
                  LEV Field Evolution (Auris v5)
                </h3>
                <p className="text-xs text-muted-foreground mb-3">
                  Symbolic LEV (Local Energy Variance) field snapshots at t=50, t=500, t=950. 
                  Demonstrates temporal evolution of substrate coherence patterns.
                </p>
                <img 
                  src={levEvolution} 
                  alt="LEV Field Evolution" 
                  className="w-full rounded-lg border border-border/30"
                />
              </div>

              <div className="p-4 bg-gradient-to-br from-primary/10 to-primary/10 rounded-lg border border-border/50">
                <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
                  <Target className="w-4 h-4 text-primary" />
                  Frequency Symmetry Analysis
                </h3>
                <p className="text-xs text-muted-foreground mb-3">
                  Grayscale mandala, FFT magnitude spectrum, color frequency palette, and 
                  rotational symmetry detection. Blue-dominant frequency indicates 528 Hz alignment.
                </p>
                <img 
                  src={frequencyAnalysis} 
                  alt="Frequency Symmetry Analysis" 
                  className="w-full rounded-lg border border-border/30"
                />
              </div>
            </div>
          </TabsContent>

          {/* Projections & Multiversial Coordinates */}
          <TabsContent value="projections" className="space-y-4">
            <div className="grid grid-cols-1 gap-4">
              <div className="p-4 bg-gradient-to-br from-warning/10 to-warning/10 rounded-lg border border-border/50">
                <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
                  <Target className="w-4 h-4 text-warning" />
                  Crown Unlock Field Projection (Ω)
                </h3>
                <p className="text-xs text-muted-foreground mb-3">
                  Radial Omega field projection showing crown chakra unlock patterns. Eight-fold 
                  symmetry indicates dimensional alignment across reality substrates.
                </p>
                <img 
                  src={crownUnlock} 
                  alt="Crown Unlock Field Projection" 
                  className="w-full rounded-lg border border-border/30"
                />
              </div>

              <div className="p-4 bg-gradient-to-br from-success/10 to-primary/10 rounded-lg border border-border/50">
                <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
                  <Atom className="w-4 h-4 text-success" />
                  Harmonic Nexus Phase Field (Tandem View)
                </h3>
                <p className="text-xs text-muted-foreground mb-3">
                  3D tandem-view visualization of the Harmonic Nexus phase field substrate. 
                  The saddle point represents the coherence minimum that must be maintained above threshold.
                </p>
                <img 
                  src={nexusPhase} 
                  alt="Harmonic Nexus Phase Field" 
                  className="w-full rounded-lg border border-border/30"
                />
              </div>

              <div className="p-4 bg-gradient-to-br from-primary/10 to-primary/10 rounded-lg border border-border/50">
                <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
                  <Radio className="w-4 h-4 text-primary" />
                  Echo Return Field (Peace Codex Pulse)
                </h3>
                <p className="text-xs text-muted-foreground mb-3">
                  Multiversial coordinate space showing echo return amplitude from the Peace Codex 
                  pulse. Central spike indicates prime timeline anchor point.
                </p>
                <img 
                  src={echoReturn} 
                  alt="Echo Return Field" 
                  className="w-full rounded-lg border border-border/30"
                />
              </div>
            </div>
          </TabsContent>
        </Tabs>

        {/* Theory Summary */}
        <div className="mt-4 p-4 bg-gradient-to-r from-primary/10 via-primary/10 to-primary/10 rounded-lg border border-border/50">
          <p className="text-sm text-muted-foreground">
            <span className="font-medium text-foreground">Unified Theory:</span>{' '}
            These visualizations represent the mathematical and energetic substrate of the 
            Harmonic Nexus Core. Temporal harmonic regulators stabilize timeline coherence, 
            phase-locked echo fields maintain dimensional integrity, and Omega field projections 
            ensure crown chakra alignment with the prime timeline. The composite system achieves 
            reality field coherence through multi-scale harmonic resonance.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
