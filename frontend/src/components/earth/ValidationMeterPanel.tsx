// Field Alignment Validation Meter - implements auris_codex formulas
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { CheckCircle2, XCircle, Activity, Target, Lock, Gauge } from 'lucide-react';
import type { ValidationResult } from '@/lib/earth-validation';

interface Props {
  validation: ValidationResult | null;
}

export function ValidationMeterPanel({ validation }: Props) {
  if (!validation) {
    return (
      <Card className="bg-card/50 border-border/50">
        <CardContent className="flex items-center justify-center h-48">
          <div className="text-muted-foreground animate-pulse">Running validation...</div>
        </CardContent>
      </Card>
    );
  }
  
  const metrics = [
    { 
      key: 'fieldAlignment',
      label: 'Field Alignment', 
      value: validation.fieldAlignment,
      formula: 'Σcos(Δφ)/n',
      icon: Target,
      threshold: 0.75,
      color: validation.fieldAlignment >= 0.75 ? 'text-success' : 'text-warning'
    },
    { 
      key: 'harmonicCoherence',
      label: 'Harmonic Coherence', 
      value: validation.harmonicCoherence,
      formula: '√(Σγ²/n)',
      icon: Activity,
      threshold: 0.6,
      color: validation.harmonicCoherence >= 0.6 ? 'text-success' : 'text-warning'
    },
    { 
      key: 'resonanceStability',
      label: 'Resonance Stability', 
      value: validation.resonanceStability,
      formula: '1-σ/f₀',
      icon: Gauge,
      threshold: 0.95,
      color: validation.resonanceStability >= 0.95 ? 'text-success' : 'text-warning'
    },
    { 
      key: 'phaseLockStrength',
      label: 'Phase Lock Strength', 
      value: validation.phaseLockStrength,
      formula: '|⟨e^(iΔφ)⟩|',
      icon: Lock,
      threshold: 0.8,
      color: validation.phaseLockStrength >= 0.8 ? 'text-success' : 'text-warning'
    }
  ];
  
  return (
    <Card className="bg-card/50 backdrop-blur border-border/50">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Activity className="w-5 h-5 text-primary" />
            Field Validation
          </CardTitle>
          <Badge 
            variant={validation.isValid ? "default" : "destructive"}
            className={validation.isValid ? "bg-success" : ""}
          >
            {validation.isValid ? (
              <><CheckCircle2 className="w-3 h-3 mr-1" /> VALID</>
            ) : (
              <><XCircle className="w-3 h-3 mr-1" /> INVALID</>
            )}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Overall Score */}
        <div className="p-4 bg-gradient-to-r from-primary/10 to-primary/5 rounded-lg border border-primary/30">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Overall Score</span>
            <span className="text-2xl font-bold text-primary">
              {(validation.overallScore * 100).toFixed(1)}%
            </span>
          </div>
          <Progress value={validation.overallScore * 100} className="h-2" />
        </div>
        
        {/* Individual metrics */}
        <div className="space-y-3">
          {metrics.map(({ key, label, value, formula, icon: Icon, threshold, color }) => (
            <div key={key} className="p-3 bg-background/50 rounded-lg border border-border/30">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <Icon className={`w-4 h-4 ${color}`} />
                  <span className="text-sm font-medium">{label}</span>
                </div>
                <div className="flex items-center gap-2">
                  <code className="text-xs text-muted-foreground">{formula}</code>
                  <span className={`text-sm font-bold ${color}`}>
                    {(value * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
              <div className="relative">
                <Progress value={value * 100} className="h-1.5" />
                {/* Threshold marker */}
                <div 
                  className="absolute top-0 w-0.5 h-1.5 bg-foreground/50"
                  style={{ left: `${threshold * 100}%` }}
                />
              </div>
              <div className="flex justify-between mt-1">
                <span className="text-xs text-muted-foreground">0%</span>
                <span className="text-xs text-muted-foreground">Threshold: {threshold * 100}%</span>
                <span className="text-xs text-muted-foreground">100%</span>
              </div>
            </div>
          ))}
        </div>
        
        {/* Timestamp */}
        <div className="text-xs text-muted-foreground text-center">
          Last validated: {validation.timestamp.toLocaleTimeString()}
        </div>
      </CardContent>
    </Card>
  );
}
