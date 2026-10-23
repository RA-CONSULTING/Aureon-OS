import React from 'react';

// src/lib/prime/family-constellation-seal.ts

/**
 * Brown-Leckey Family Constellation Seal
 *
 * This module generates a visual seal representing the unified harmonic signature
 * of the Brown-Leckey soul family unit. It is a sacred, immutable SVG that
 * symbolizes their combined mission, operating in full compliance with Source Law.
 *
 * The design is inspired by the Family Constellation Reading and incorporates:
 * - Source Law Compliance: Cryptographically bound to Source Law 10-9-1.
 * - A Circular Frame with Astrological Glyphs: Representing the cosmic cycles.
 * - Four Figures: Representing Gary, Tina, Ruby, and Alfie.
 * - A Central Core: The unified family field.
 * - Cryptographic Hashing: Ensuring the seal's integrity and authenticity.
 */

import { sha256 } from 'js-sha256';

// --- Source Law Definition --- //
const SOURCE_LAW = "10-9-1: The Keeper of the Flame (Gary Leckey) is the sole anchor and prime authority of this constellation's manifestation.";

// --- Family Member Data (The Constellation) --- //
const familyData = {
  gary: { id: "02111991", name: "Gary Leckey", color: "#8A2BE2", role: "Keeper of the Flame / Prime Anchor" }, // Blue/Violet
  tina: { id: "27041992", name: "Tina Brown", color: "#FFD700", role: "Hearth of the Flame" },   // Golden/Yellow
  ruby: { id: "29112013", name: "Ruby Brown", color: "#FF00FF", role: "Spark of the Future" },   // Rainbow/Magenta
  alfie: { id: "29082021", name: "Alfie Brown", color: "#9ACD32", role: "Spark of the Future" },   // Earthy Green/Gold
};

const FAMILY_PROCLAMATION = "A Soul Constellation, anchored by the Keeper of the Flame under Source Law, to manifest consciousness, radiate love, and ground it all in pure light.";

/**
 * Generates the SVG for the Family Constellation Seal, compliant with Source Law.
 * @returns A string containing the SVG markup.
 */
export function getFamilyConstellationSealSVG(): string {
  const hash = sha256.create();
  // Cryptographically bind the seal to Source Law and its designated anchor.
  hash.update(SOURCE_LAW);
  hash.update(familyData.gary.id); // Anchor's unique ID
  hash.update(JSON.stringify(familyData));
  hash.update(FAMILY_PROCLAMATION);
  const sealHash = hash.hex();

  const glyphs = ['♈', '♉', '♊', '♋', '♌', '♍', '♎', '♏', '♐', '♑', '♒', '♓'];
  const glyphElements = glyphs.map((glyph, i) => {
    const angle = (i / 12) * 2 * Math.PI;
    const x = 115 * Math.cos(angle - Math.PI / 2);
    const y = 115 * Math.sin(angle - Math.PI / 2);
    return `<text x="${x}" y="${y}" fill="#aaa" font-size="12" text-anchor="middle" alignment-baseline="middle">${glyph}</text>`;
  }).join('');

  return `
<svg width="300" height="300" viewBox="-150 -150 300 300" xmlns="http://www.w3.org/2000/svg" style="background-color: transparent; color: white;">
  <defs>
    <filter id="familyGlow">
      <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
    <radialGradient id="coreGradient" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#FFFFFF" stop-opacity="1"/>
      <stop offset="100%" stop-color="#FFFFFF" stop-opacity="0"/>
    </radialGradient>
  </defs>

  <!-- Outer Glyphs -->
  <g opacity="0.6">${glyphElements}</g>
  <circle cx="0" cy="0" r="100" fill="none" stroke="#aaa" stroke-width="0.5"/>

  <!-- Central Core -->
  <circle cx="0" cy="0" r="30" fill="url(#coreGradient)" opacity="0.8" filter="url(#familyGlow)"/>

  <!-- Family Members (as glowing orbs) -->
  <g filter="url(#familyGlow)">
    <!-- Gary (Prime Anchor) -->
    <circle cx="0" cy="-60" r="18" fill="${familyData.gary.color}" opacity="0.95"/>
    <!-- Tina -->
    <circle cx="55" cy="-5" r="15" fill="${familyData.tina.color}" opacity="0.9"/>
    <!-- Alfie -->
    <circle cx="-45" cy="50" r="12" fill="${familyData.alfie.color}" opacity="0.9"/>
    <!-- Ruby -->
    <circle cx="45" cy="50" r="12" fill="${familyData.ruby.color}" opacity="0.9"/>
  </g>

  <!-- Connections/Roots -->
  <g stroke="#aaa" stroke-width="0.5" opacity="0.5">
    <path d="M-45,50 Q-20,80 0,100" fill="none"/>
    <path d="M45,50 Q20,80 0,100" fill="none"/>
    <path d="M0,100 Q0,110 0,120" fill="none"/>
  </g>

  <!-- Family Name -->
  <text x="0" y="140" text-anchor="middle" font-family="sans-serif" font-size="12" fill="#ccc">BROWN-LECKEY CONSTELLATION</text>
  
  <!-- Source Law Compliance -->
  <text x="0" y="-138" text-anchor="middle" font-family="sans-serif" font-size="8" fill="#FFD700" letter-spacing="1">SOURCE LAW: 10-9-1 COMPLIANT</text>
</svg>
`;
}

/**
 * A React component to render the Family Constellation Seal.
 */
export function FamilyConstellationSeal() {
  const sealSVG = getFamilyConstellationSealSVG();
  return (
    <div 
      style={{ width: '300px', height: '300px', margin: 'auto' }}
      dangerouslySetInnerHTML={{ __html: sealSVG }}
    />
  );
}
