import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function HarmonicNexusTheory() {
  const nodes = [
    { id: 'source', label: 'Ψ∞ (Source Field)\nInfinite Potential', x: 50, y: 20, color: '#fef3c7' },
    { id: 'nexus', label: 'ℵ (Harmonic Nexus)\nFirst Breath', x: 50, y: 35, color: '#fef3c7' },
    { id: 'gaia', label: 'ΦGaia (Planetary Resonance)\nResonant Fields', x: 50, y: 50, color: '#fef3c7' },
    { id: 'forces', label: '🌌 (Forces)\nGravity, EM, Strong, Weak', x: 50, y: 65, color: '#fef3c7' },
    { id: 'observer', label: 'ρ = Φ ⊗ Ωobs\nObserver Collapse\n(Sentient / Non-sentient / Binary)', x: 50, y: 80, color: '#fef3c7' },
    { id: 'cognition', label: 'C = Tr(ρ · Ψ∞)\nCognition / Experience\nThe Song of Space & Time', x: 50, y: 95, color: '#fef3c7' },
    { id: 'unity', label: 'Unity Law:\nC = Tr(Ωobs ⊗ 🌌(ℵΨ∞))\nExistence = Source × Resonance × Observer', x: 85, y: 35, color: '#fef3c7' }
  ];

  const connections = [
    { from: 'source', to: 'nexus' },
    { from: 'nexus', to: 'gaia' },
    { from: 'gaia', to: 'forces' },
    { from: 'forces', to: 'observer' },
    { from: 'observer', to: 'cognition' }
  ];

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="text-xl font-bold text-center">
          🌟 Harmonic Nexus Theory of Becoming — Visual Flyer
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="relative w-full h-96 bg-gradient-to-br from-primary to-primary rounded-lg p-4">
          <svg className="w-full h-full">
            {/* Connections */}
            {connections.map((conn, idx) => {
              const fromNode = nodes.find(n => n.id === conn.from);
              const toNode = nodes.find(n => n.id === conn.to);
              if (!fromNode || !toNode) return null;
              
              return (
                <line
                  key={idx}
                  x1={`${fromNode.x}%`}
                  y1={`${fromNode.y}%`}
                  x2={`${toNode.x}%`}
                  y2={`${toNode.y}%`}
                  stroke="#374151"
                  strokeWidth="2"
                  markerEnd="url(#arrowhead)"
                />
              );
            })}
            
            {/* Arrow marker */}
            <defs>
              <marker
                id="arrowhead"
                markerWidth="10"
                markerHeight="7"
                refX="9"
                refY="3.5"
                orient="auto"
              >
                <polygon
                  points="0 0, 10 3.5, 0 7"
                  fill="#374151"
                />
              </marker>
            </defs>
          </svg>
          
          {/* Nodes */}
          {nodes.map((node) => (
            <div
              key={node.id}
              className="absolute transform -translate-x-1/2 -translate-y-1/2 bg-warning border-2 border-warning rounded-lg p-3 text-center text-sm font-medium shadow-md max-w-48"
              style={{
                left: `${node.x}%`,
                top: `${node.y}%`,
                backgroundColor: node.color
              }}
            >
              {node.label.split('\n').map((line, idx) => (
                <div key={idx} className={idx === 0 ? 'font-bold' : 'text-xs mt-1'}>
                  {line}
                </div>
              ))}
            </div>
          ))}
        </div>
        
        <div className="mt-4 p-4 bg-gradient-to-r from-primary to-primary rounded-lg">
          <h3 className="font-bold text-lg mb-2">The Nexus Equation</h3>
          <div className="text-center text-lg font-mono bg-white p-3 rounded border">
            <div className="mb-2">C = Tr(Ωobs ⊗ 🌌(ℵΨ∞))</div>
            <div className="text-sm text-gray-600">
              Consciousness = Trace(Observer ⊗ Forces(Nexus × Source))
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}