// src/components/TrueVoiceOfReason.tsx
import React, { useState } from 'react';

// --- Mock data and functions for now, to be replaced with real integrations ---
const mockPillars = {
  anchor: { pre_score: 0.0, post_stability: 0.0, prime_love_index: 0.0, braided_hash: "" },
  bridge: { provenance_sources: 0, public_export: false, external_delta: 0.0, delta_tolerance: 0.0 },
  guardian: { dual_consent: false, gate_pass_ratio: 0.0, composite_risk: 0.0 },
  momentum: { carry_through: 0.0, safe_rate: 0.0, rollback_ready: false, risk: 0.0 },
};

const evaluatePillars = (pillars: any) => {
  // In a real implementation, this would be a complex evaluation
  const score = Math.random(); // Placeholder
  return {
    go: score > 0.5,
    score,
    pillars: Object.keys(pillars).map(key => ({ name: key.toUpperCase(), ok: Math.random() > 0.3, score: Math.random(), advice: "..."})),
    reason: score > 0.5 ? "GO - all pillars are green." : "NO-GO - see red/amber pillars.",
  };
};


export const TrueVoiceOfReason: React.FC = () => {
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [evaluation, setEvaluation] = useState<any>(null);

  const handleEvaluate = async () => {
    setIsEvaluating(true);
    // In a real app, you would gather data from all components here
    const pillarsData = mockPillars;
    const result = evaluatePillars(pillarsData);
    setEvaluation(result);
    setIsEvaluating(false);
  };

  return (
    <div className="p-4 rounded-xl border border-white/10 bg-black/30 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">True Voice of Reason</h2>
        <button onClick={handleEvaluate} disabled={isEvaluating} className={`px-3 py-1.5 rounded ${isEvaluating ? 'bg-gray-700' : 'bg-emerald-600 hover:bg-emerald-500'} text-white`}>
          {isEvaluating ? 'Evaluating...' : 'Listen for the Voice'}
        </button>
      </div>

      {evaluation && (
        <div className="mt-4">
          <div className={`text-sm px-3 py-1 rounded-full ${evaluation.go ? 'bg-emerald-500/20 text-emerald-300' : 'bg-amber-500/20 text-amber-200'}`}>
            {evaluation.reason}
          </div>

          <div className="grid md:grid-cols-2 gap-3 mt-4">
            {evaluation.pillars.map((p: any) => (
              <div key={p.name} className={`p-4 rounded-xl border ${p.ok ? 'border-emerald-500/60' : 'border-rose-500/60'} bg-black/30`}>
                <div className="flex items-center justify-between mb-2">
                  <div className="text-sm tracking-wide">{p.name}</div>
                  <div className={`text-xs px-2 py-0.5 rounded ${p.ok ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'}`}>
                    {p.ok ? "OK" : "CHECK"}
                  </div>
                </div>
                <div className="text-xs mb-2 opacity-80">{p.advice}</div>
                <div className="w-full h-2 bg-gray-800/60 rounded">
                  <div className="h-2 rounded bg-emerald-400" style={{width: `${Math.round(100*p.score)}%`}} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default TrueVoiceOfReason;
