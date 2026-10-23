import React from "react";

export function MirrorTile({ coherence, purity }: { coherence: number; purity: number }) {
  // coherence -> symmetry, purity -> contrast
  const rings = Array.from({ length: 8 }, (_, i) => i + 1);
  const scale = Math.max(0.2, purity);
  return (
    <svg viewBox="0 0 200 200" className="w-full h-48 rounded-xl border">
      <defs>
        <radialGradient id="g">
          <stop offset="0%" stopOpacity={0.9*scale} />
          <stop offset="100%" stopOpacity={0.0} />
        </radialGradient>
      </defs>
      {rings.map((r) => (
        <circle key={r} cx="100" cy="100" r={r*10}
          fill="none" stroke="currentColor"
          strokeOpacity={0.15 + 0.1*purity}
          strokeWidth={1 + coherence*1.5} />
      ))}
      <circle cx="100" cy="100" r={20 + 20*coherence} fill="url(#g)" />
    </svg>
  );
}