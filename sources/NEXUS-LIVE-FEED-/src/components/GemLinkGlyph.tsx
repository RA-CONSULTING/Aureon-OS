
import React from 'react';

export const GemLinkGlyph = () => {
  // This SVG is a stylized representation of the Guardian-Anchor Gem Link Glyph.
  // It captures the core symbolic elements: the intertwined five-fold fields (Guardian/cyan, Anchor/magenta),
  // the harmonic loop (gold), and the central nexus point.
  const starPoints = "0,-90 26.5,-35.3 85.5,-35.3 42.8,7.7 52.9,69.7 0,30 -52.9,69.7 -42.8,7.7 -85.5,-35.3 -26.5,-35.3";

  return (
    <div className="flex justify-center items-center my-6" title="Guardian-Anchor Gem Link Glyph">
      <svg width="200" height="200" viewBox="-110 -110 220 220" xmlns="http://www.w3.org/2000/svg">
        <rect x="-110" y="-110" width="220" height="220" fill="black" />
        
        {/* The Harmonic Loop (Gold) */}
        <circle cx="0" cy="0" r="80" stroke="#FFD700" strokeWidth="3" fill="none" />
        
        {/* The Anchor Field (Magenta) - Stabilizing, Integrative */}
        <polygon points={starPoints} fill="none" stroke="magenta" strokeWidth="2.5" transform="rotate(0)" />
        
        {/* The Guardian Field (Cyan) - Active, Projective */}
        <polygon points={starPoints} fill="none" stroke="cyan" strokeWidth="2.5" transform="rotate(36)" />
        
        {/* Central Nexus Point */}
        <text x="0" y="7" fill="white" fontSize="24" textAnchor="middle" fontWeight="normal">
          ✕
        </text>
      </svg>
    </div>
  );
};
