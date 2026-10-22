
import React from 'react';

// This complex path defines a single, six-lobed petal shape.
// It's designed to be rotated and layered to create the full mandala.
const petalPath = "M0,-25 C 25,-40 45,-65 25,-85 C 5,-105 -5,-105 -25,-85 C -45,-65 -25,-40 0,-25";

// Defines the properties for each concentric layer of the mandala
const layers = [
  { color: 'cyan',    strokeWidth: 2,   scale: 0.45 },
  { color: 'magenta', strokeWidth: 1.8, scale: 0.60 },
  { color: '#FFD700', strokeWidth: 1.6, scale: 0.75 }, // Gold
  { color: '#C0C0C0', strokeWidth: 1.4, scale: 0.90 }, // Silver
  { color: 'teal',    strokeWidth: 1.2, scale: 1.05 },
  { color: 'darkorchid',  strokeWidth: 1,   scale: 1.20 },
];

const numPetals = 6;
const angleStep = 360 / numPetals;

export const ExpandingVectorMandala = () => {
  return (
    <div className="flex justify-center items-center my-8" title="Guardian-Anchor Expanding Vector Mandala">
      <svg width="250" height="250" viewBox="-120 -120 240 240" xmlns="http://www.w3.org/2000/svg">
        {/* Background */}
        <rect x="-120" y="-120" width="240" height="240" fill="black" />
        
        {/* Rotating group for all petals */}
        <g>
          {Array.from({ length: numPetals }).map((_, i) => (
            <g key={i} transform={`rotate(${i * angleStep})`}>
              {/* Render each concentric layer for the current petal */}
              {layers.map((layer, j) => (
                <path
                  key={j}
                  d={petalPath}
                  fill="none"
                  stroke={layer.color}
                  strokeWidth={layer.strokeWidth}
                  transform={`scale(${layer.scale})`}
                />
              ))}
            </g>
          ))}
        </g>
        
        {/* Central Nexus Point */}
        <text x="0" y="6" fill="white" fontSize="24" textAnchor="middle" fontWeight="bold">
          ✕
        </text>
      </svg>
    </div>
  );
};
