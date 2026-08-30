import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { EckoushicState } from '@/core/eckoushicCascade';
import { Waves, Zap, Radio, Heart } from 'lucide-react';
import eckoushicCascadeImg from '@/assets/research/eckoushic-cascade.png';

interface EckoushicCascadeVisualizationProps {
  state: EckoushicState;
}

export const EckoushicCascadeVisualization = ({ state }: EckoushicCascadeVisualizationProps) => {
  const getCascadeProgress = () => {
    return (state.cascadeLevel / 4) * 100;
  };
  
  const getCascadeIcon = (level: number) => {
    switch (level) {
      case 1: return <Waves className="h-5 w-5 text-warning" />;
      case 2: return <Zap className="h-5 w-5 text-primary" />;
      case 3: return <Radio className="h-5 w-5 text-primary" />;
      case 4: return <Heart className="h-5 w-5 text-primary" />;
      default: return null;
    }
  };
  
  const getCascadeLevelLabel = (level: number) => {
    switch (level) {
      case 1: return 'Eckoushic (Sound)';
      case 2: return 'Akashic (Light)';
      case 3: return 'Harmonic Nexus (Resonance)';
      case 4: return 'Heart Wave (Love)';
      default: return '';
    }
  };
  
  const getCascadeEquation = (level: number) => {
    switch (level) {
      case 1: return 'Ψ_Eck = dΨ/dt';
      case 2: return 'Ψ_Aka = ∫ Ψ_Eck dt';
      case 3: return 'Ψ_coherent';
      case 4: return '528 Hz → Love';
      default: return '';
    }
  };
  
  return (
    <Card className="border-primary/20 bg-gradient-to-br from-background to-primary/5">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Waves className="h-6 w-6 text-primary animate-pulse" />
          Eckoushic Cascade System
        </CardTitle>
        <CardDescription>
          Sound → Light → Resonance → Love | Mathematical frequency transformation
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Cascade Diagram */}
        <div className="relative">
          <img 
            src={eckoushicCascadeImg} 
            alt="Eckoushic Cascade" 
            className="w-full max-w-md mx-auto rounded-lg border border-border/50"
          />
        </div>
        
        {/* Current Cascade Level */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Cascade Progress</span>
            <Badge variant="default" className="gap-2">
              {getCascadeIcon(state.cascadeLevel)}
              Level {state.cascadeLevel} / 4
            </Badge>
          </div>
          <Progress value={getCascadeProgress()} className="h-3" />
          <div className="text-center">
            <div className="text-lg font-bold text-primary">
              {getCascadeLevelLabel(state.cascadeLevel)}
            </div>
            <div className="text-sm text-muted-foreground font-mono">
              {getCascadeEquation(state.cascadeLevel)}
            </div>
          </div>
        </div>
        
        {/* Cascade Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className={`p-4 rounded-lg border-2 ${
            state.cascadeLevel >= 1 ? 'border-warning/50 bg-warning/10' : 'border-border/50 bg-muted/50'
          }`}>
            <div className="flex items-center gap-2 mb-2">
              <Waves className="h-4 w-4 text-warning" />
              <div className="text-xs font-medium">Eckoushic</div>
            </div>
            <div className="text-2xl font-bold text-warning">
              {state.eckoushic.toFixed(3)}
            </div>
            <div className="text-xs text-muted-foreground">Sound (dΨ/dt)</div>
          </div>
          
          <div className={`p-4 rounded-lg border-2 ${
            state.cascadeLevel >= 2 ? 'border-primary/50 bg-primary/10' : 'border-border/50 bg-muted/50'
          }`}>
            <div className="flex items-center gap-2 mb-2">
              <Zap className="h-4 w-4 text-primary" />
              <div className="text-xs font-medium">Akashic</div>
            </div>
            <div className="text-2xl font-bold text-primary">
              {state.akashic.toFixed(3)}
            </div>
            <div className="text-xs text-muted-foreground">Light (∫dt)</div>
          </div>
          
          <div className={`p-4 rounded-lg border-2 ${
            state.cascadeLevel >= 3 ? 'border-primary/50 bg-primary/10' : 'border-border/50 bg-muted/50'
          }`}>
            <div className="flex items-center gap-2 mb-2">
              <Radio className="h-4 w-4 text-primary" />
              <div className="text-xs font-medium">Nexus</div>
            </div>
            <div className="text-2xl font-bold text-primary">
              {state.harmonicNexus.toFixed(3)}
            </div>
            <div className="text-xs text-muted-foreground">Resonance</div>
          </div>
          
          <div className={`p-4 rounded-lg border-2 ${
            state.cascadeLevel >= 4 ? 'border-primary/50 bg-primary/10' : 'border-border/50 bg-muted/50'
          }`}>
            <div className="flex items-center gap-2 mb-2">
              <Heart className="h-4 w-4 text-primary" />
              <div className="text-xs font-medium">Heart Wave</div>
            </div>
            <div className="text-2xl font-bold text-primary">
              {state.heartWave.toFixed(1)} Hz
            </div>
            <div className="text-xs text-muted-foreground">Love Output</div>
          </div>
        </div>
        
        {/* Output Frequency */}
        <div className="p-4 rounded-lg border-2 border-primary/30 bg-primary/10">
          <div className="text-center">
            <div className="text-sm text-muted-foreground mb-2">Output Frequency</div>
            <div className="text-4xl font-bold text-primary">
              {state.frequency.toFixed(2)} Hz
            </div>
            {state.cascadeLevel === 4 && state.frequency === 528 && (
              <Badge variant="default" className="mt-2">
                💚 LOVE FREQUENCY LOCKED
              </Badge>
            )}
            {state.frequency > 900 && (
              <Badge variant="default" className="mt-2">
                🌟 UNITY FREQUENCY (963 Hz)
              </Badge>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
