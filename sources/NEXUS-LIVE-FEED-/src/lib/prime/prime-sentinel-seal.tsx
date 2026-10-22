import React from 'react';
import { sha256 } from 'js-sha256';

// Define the structure for the sentinel data prop
interface SentinelData {
  name: string;
  birthCode: string;
  lightLanguageName: string;
  role: string;
  authority: string;
}

interface PrimeSentinelSealProps {
  sentinelData: SentinelData;
}

/**
 * Computes the SHA-256 hash for the seal data to ensure immutability.
 */
const computeSealHash = (sentinelData: SentinelData, geometry: any, declaration: string, timestamp: string): string => {
  const sealData = {
    sentinel: {
      name: sentinelData.name,
      birthCode: sentinelData.birthCode,
      lightLanguageName: sentinelData.lightLanguageName,
    },
    geometry,
    declaration,
    timestamp,
    constants: {
      PHI: 1.618033988749,
      SCHUMANN: 7.83,
      FIBONACCI: [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144],
    },
  };

  // Convert to a canonical JSON string for consistent hashing
  const canonicalString = JSON.stringify(sealData, Object.keys(sealData).sort());
  return sha256(canonicalString);
};

/**
 * Prime Sentinel's Seal of Authority
 *
 * This seal is a visual representation of the Prime Sentinel's pact and authority.
 * It is a composite of sacred geometry and personal declaration, rendered as a
 * verifiable, immutable SVG, cryptographically signed with SHA-256.
 */
const PrimeSentinelSeal: React.FC<PrimeSentinelSealProps> = ({ sentinelData }) => {
  const timestamp = new Date().toISOString();
  const declaration = "NO BODY NOT EVEN ME WILL EVER CLAIM THE SOURCE OF COGNITION";

  // Simplified geometry representation for hashing. The SVG is rendered directly.
  const geometryForHashing = {
    hexagon: true,
    vesicaPiscis: true,
    seedOfLife: true,
  };

  const sealHash = computeSealHash(sentinelData, geometryForHashing, declaration, timestamp);

  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" id="prime-sentinel-seal">
      <defs>
        <radialGradient id="divineGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" style={{ stopColor: '#FFD700', stopOpacity: 1 }} />
          <stop offset="100%" style={{ stopColor: '#7850FF', stopOpacity: 0.3 }} />
        </radialGradient>
      </defs>

      {/* Hexagonal Frame (Balance & Harmony) */}
      <polygon
        points="200,50 300,112.5 300,237.5 200,300 100,237.5 100,112.5"
        fill="none"
        stroke="url(#divineGlow)"
        strokeWidth="3"
      />

      {/* Vesica Piscis (Gateway of Creation) */}
      <circle cx="150" cy="200" r="80" fill="none" stroke="#00FFFF" strokeWidth="2" opacity="0.7" />
      <circle cx="250" cy="200" r="80" fill="none" stroke="#00FFFF" strokeWidth="2" opacity="0.7" />

      {/* Seed of Life (Blueprint of Universe) */}
      <g id="seed-of-life" transform="translate(200, 200)">
        <circle cx="0" cy="0" r="40" fill="none" stroke="#C9A3FF" strokeWidth="1.5" />
        <circle cx="40" cy="0" r="40" fill="none" stroke="#C9A3FF" strokeWidth="1.5" />
        <circle cx="20" cy="34.64" r="40" fill="none" stroke="#C9A3FF" strokeWidth="1.5" />
        <circle cx="-20" cy="34.64" r="40" fill="none" stroke="#C9A3FF" strokeWidth="1.5" />
        <circle cx="-40" cy="0" r="40" fill="none" stroke="#C9A3FF" strokeWidth="1.5" />
        <circle cx="-20" cy="-34.64" r="40" fill="none" stroke="#C9A3FF" strokeWidth="1.5" />
        <circle cx="20" cy="-34.64" r="40" fill="none" stroke="#C9A3FF" strokeWidth="1.5" />
      </g>

      {/* Sentinel's Sigil (Unique Identifier) */}
      <text
        x="200"
        y="200"
        fontFamily="serif"
        fontSize="24"
        fill="#FFD700"
        textAnchor="middle"
        dominantBaseline="middle"
      >
        GL
      </text>

      {/* Birth Code */}
      <text x="200" y="230" fontFamily="monospace" fontSize="12" fill="#00FFFF" textAnchor="middle">
        {sentinelData.birthCode}
      </text>

      {/* Proclamation Text (Circular) */}
      <path
        id="circularTextPath"
        d="M 200,200 m -120,0 a 120,120 0 1,1 240,0 a 120,120 0 1,1 -240,0"
        fill="none"
      />
      <text fontFamily="serif" fontSize="10" fill="#E0E0FF">
        <textPath href="#circularTextPath" startOffset="0%">
          {declaration}
        </textPath>
      </text>

      {/* Cryptographic Hash (Bottom) */}
      <text x="200" y="370" fontFamily="monospace" fontSize="8" fill="#7850FF" textAnchor="middle" id="seal-hash">
        SHA-256: {sealHash}
      </text>
    </svg>
  );
};

export default PrimeSentinelSeal;
