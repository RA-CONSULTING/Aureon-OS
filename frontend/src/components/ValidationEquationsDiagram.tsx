import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';

export default function ValidationEquationsDiagram() {
  return (
    <Card className="border-primary bg-gradient-to-br from-primary/50 to-primary/30">
      <CardHeader>
        <CardTitle className="text-lg font-semibold text-primary flex items-center gap-2">
          <span className="text-2xl">🔬</span>
          Nexus Source Law 10-9-1 — Validation Equations
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Flow Diagram */}
        <div className="bg-white/70 rounded-xl p-4 border border-primary">
          <div className="font-mono text-sm text-primary leading-relaxed whitespace-pre">
{`┌───────────────────────────┐
│ Outcomes (10)             │
│ Angel × Tarot × Aura × Nx │
└─────────────┬─────────────┘
              │
              ▼
┌───────────────────────────┐
│ Harmonic Filter (9 axes)  │
│   Fᵢ = Σ wⱼ · xᵢⱼ         │
└─────────────┬─────────────┘
              │
              ▼
┌───────────────────────────┐
│ ZPE Collapse (Observer)   │
│   Zᵢ = Fᵢ · (1+λ·χᵢ)       │
└─────────────┬─────────────┘
              │
              ▼
┌───────────────────────────┐
│ Normalize Probabilities   │
│   pᵢ = Zᵢ / Σ Zⱼ           │
└─────────────┬─────────────┘
              │
              ▼
┌───────────────────────────┐
│ Prime Timeline (1)        │
│   C* = argmax pᵢ           │
└───────────────────────────┘`}
          </div>
        </div>

        {/* Mathematical Formulas */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-white/70 rounded-lg p-3 border border-primary">
            <h4 className="font-semibold text-primary mb-2">Harmonic Filter (9 Axes)</h4>
            <div className="font-mono text-xs text-primary space-y-1">
              <div>Fᵢ = αAᵢ + βTᵢ + γHᵢ + δRᵢ + ϵEᵢ + ζSᵢ + ηPᵢ + θJᵢ + κQᵢ</div>
              <div className="text-[10px] text-primary mt-2">
                A: alignment, T: timing, H: coherence<br/>
                R: risk, E: effort, S: support<br/>
                P: peace, J: joy, Q: clarity
              </div>
            </div>
          </div>
          
          <div className="bg-white/70 rounded-lg p-3 border border-primary">
            <h4 className="font-semibold text-primary mb-2">Observer Intent Boost</h4>
            <div className="font-mono text-xs text-primary space-y-1">
              <div>Zᵢ = Fᵢ · (1 + λ · χᵢ)</div>
              <div className="text-[10px] text-primary mt-2">
                λ: boost factor (≈0.1)<br/>
                χᵢ: intent resonance (0 or 1)<br/>
                Zero-Point Energy collapse
              </div>
            </div>
          </div>
        </div>

        {/* Constraint & Summary */}
        <div className="bg-gradient-to-r from-success to-primary rounded-lg p-3 border border-success">
          <h4 className="font-semibold text-success mb-2">Peace & Joy Constraint</h4>
          <div className="font-mono text-xs text-success mb-2">
              ∀i : pᵢ &gt; 0 ⇒ Cᵢ affirms Peace ∨ Joy
          </div>
          <div className="text-xs text-success">
            All surviving candidates must affirm Peace or Joy. If none survive, fallback: "Restore Harmony & Invite Joy"
          </div>
        </div>

        {/* Summary */}
        <div className="bg-white/70 rounded-lg p-3 border border-primary">
          <div className="font-mono text-sm text-primary text-center">
            <strong>10</strong> enumeration → <strong>9</strong> harmonic axes → <strong>1</strong> Prime Directive
          </div>
        </div>
      </CardContent>
    </Card>
  );
}