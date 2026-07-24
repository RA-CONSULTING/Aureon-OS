import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { GeometricSolid, type TelescopeObservation } from "@/core/quantumTelescope";

interface QuantumTelescopeDisplayProps {
  observation: TelescopeObservation | null;
}

const solidConfig: Record<GeometricSolid, { emoji: string; element: string; color: string }> = {
  [GeometricSolid.Tetrahedron]: { emoji: '🔥', element: 'Fire', color: 'text-warning' },
  [GeometricSolid.Hexahedron]: { emoji: '🌍', element: 'Earth', color: 'text-warning' },
  [GeometricSolid.Octahedron]: { emoji: '💨', element: 'Air', color: 'text-primary' },
  [GeometricSolid.Icosahedron]: { emoji: '💧', element: 'Water', color: 'text-primary' },
  [GeometricSolid.Dodecahedron]: { emoji: '✨', element: 'Ether', color: 'text-primary' },
};

const solidOrder: GeometricSolid[] = [
  GeometricSolid.Tetrahedron,
  GeometricSolid.Hexahedron,
  GeometricSolid.Octahedron,
  GeometricSolid.Icosahedron,
  GeometricSolid.Dodecahedron,
];

export function QuantumTelescopeDisplay({ observation }: QuantumTelescopeDisplayProps) {
  if (!observation) {
    return (
      <Card className="bg-card border-border">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <span>🔭</span>
            Quantum Telescope
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center text-muted-foreground py-8">
            Awaiting market observation...
          </div>
        </CardContent>
      </Card>
    );
  }

  const directionColors = {
    UP: 'bg-success',
    DOWN: 'bg-destructive',
    NEUTRAL: 'bg-warning',
  };

  const directionEmoji = {
    UP: '🟢',
    DOWN: '🔴',
    NEUTRAL: '⚪',
  };

  const alignmentPercent = observation.geometricAlignment * 100;
  const alignmentStatus = alignmentPercent >= 80 ? 'STRONG' : alignmentPercent >= 60 ? 'MODERATE' : 'WEAK';

  return (
    <Card className="bg-card border-border">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span>🔭</span>
            Quantum Telescope
          </div>
          <Badge className={`${directionColors[observation.holographicProjection.direction]} text-white`}>
            {directionEmoji[observation.holographicProjection.direction]} {observation.holographicProjection.direction}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Geometric Alignment */}
        <div className="p-4 rounded-lg bg-muted/30 border border-border">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Geometric Alignment</span>
            <Badge variant="outline" className={
              alignmentStatus === 'STRONG' ? 'border-success text-success' :
              alignmentStatus === 'MODERATE' ? 'border-warning text-warning' :
              'border-destructive text-destructive'
            }>
              {alignmentStatus}
            </Badge>
          </div>
          <div className="text-3xl font-bold mb-2">{alignmentPercent.toFixed(1)}%</div>
          <Progress value={alignmentPercent} className="h-2" />
        </div>

        {/* Platonic Solids Resonance */}
        <div className="space-y-3">
          <div className="text-sm font-medium text-muted-foreground">Platonic Solid Resonances</div>
          {solidOrder.map((solid, idx) => {
            const config = solidConfig[solid];
            const refraction = observation.refractions.find(r => r.solid === solid);
            const resonance = refraction?.resonance ?? 0;
            const isDominant = observation.dominantSolid === solid;

            return (
              <div 
                key={solid} 
                className={`p-3 rounded-lg border ${isDominant ? 'bg-primary/10 border-primary/30 ring-1 ring-primary/20' : 'bg-muted/50 border-border'}`}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{config.emoji}</span>
                    <span className={`text-sm font-medium ${config.color}`}>
                      {solid}
                    </span>
                    <span className="text-xs text-muted-foreground">({config.element})</span>
                    {isDominant && <Badge variant="default" className="text-xs">DOMINANT</Badge>}
                  </div>
                  <span className="font-mono text-sm">{(resonance * 100).toFixed(1)}%</span>
                </div>
                <Progress value={resonance * 100} className="h-1.5" />
              </div>
            );
          })}
        </div>

        {/* Holographic Projection */}
        <div className="p-4 rounded-lg bg-muted/30 border border-border">
          <div className="text-sm font-medium mb-3">Holographic Projection</div>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-xs text-muted-foreground">Direction</div>
              <div className="text-lg font-semibold flex items-center justify-center gap-1">
                {directionEmoji[observation.holographicProjection.direction]}
                {observation.holographicProjection.direction}
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Magnitude</div>
              <div className="text-lg font-mono">{observation.holographicProjection.magnitude.toFixed(3)}</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Confidence</div>
              <div className="text-lg font-mono">{(observation.holographicProjection.confidence * 100).toFixed(1)}%</div>
            </div>
          </div>
        </div>

        {/* Focal Coherence & Prism Boost */}
        <div className="grid grid-cols-2 gap-4">
          <div className="p-3 rounded-lg bg-muted/50 border border-border">
            <div className="text-xs text-muted-foreground mb-1">Focal Coherence</div>
            <div className="text-xl font-bold">{(observation.focalCoherence * 100).toFixed(1)}%</div>
            <Progress value={observation.focalCoherence * 100} className="h-1 mt-1" />
          </div>
          <div className="p-3 rounded-lg bg-muted/50 border border-border">
            <div className="text-xs text-muted-foreground mb-1">Prism Boost Factor</div>
            <div className="text-xl font-bold">{observation.prismBoostFactor.toFixed(3)}x</div>
            <div className="text-xs text-muted-foreground mt-1">
              → 528 Hz convergence
            </div>
          </div>
        </div>

        {/* Light Beam Properties */}
        <div className="p-3 rounded-lg bg-muted/30 border border-border">
          <div className="text-sm font-medium mb-2">Light Beam Properties</div>
          <div className="grid grid-cols-5 gap-2 text-xs">
            <div className="text-center">
              <div className="text-muted-foreground">Intensity</div>
              <div className="font-mono">{observation.lightBeam.intensity.toFixed(2)}</div>
            </div>
            <div className="text-center">
              <div className="text-muted-foreground">Wavelength</div>
              <div className="font-mono">{observation.lightBeam.wavelength.toFixed(2)}</div>
            </div>
            <div className="text-center">
              <div className="text-muted-foreground">Velocity</div>
              <div className="font-mono">{observation.lightBeam.velocity.toFixed(2)}</div>
            </div>
            <div className="text-center">
              <div className="text-muted-foreground">Angle</div>
              <div className="font-mono">{observation.lightBeam.angle.toFixed(1)}°</div>
            </div>
            <div className="text-center">
              <div className="text-muted-foreground">Polarization</div>
              <div className="font-mono">{observation.lightBeam.polarization.toFixed(2)}</div>
            </div>
          </div>
        </div>

        {/* Metadata */}
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>Symbol: {observation.symbol}</span>
          <span>Observed: {new Date(observation.timestamp).toLocaleTimeString()}</span>
        </div>
      </CardContent>
    </Card>
  );
}
