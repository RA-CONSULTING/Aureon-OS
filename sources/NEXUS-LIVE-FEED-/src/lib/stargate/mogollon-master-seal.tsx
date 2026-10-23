import React from 'react';

// src/lib/stargate/mogollon-master-seal.ts

/**
 * Mogollon Master's Seal
 *
 * This module generates a visual seal for Maximo Mogollon, the Life Path 7 Sagittarius
 * Mystic and Mogollon Master Guardian of the Sacred Geometry Ping-Pong Network.
 * His birth on December 17, 1940, four days before the winter solstice, connects
 * him to the energy of light emerging from darkness, making him the perfect
 * keeper of the ancient frequencies.
 *
 * The seal represents his precision as the archer, his wisdom as the mystic, and
 * his role as the guardian of the Mogollon rotating prism.
 */

import { sha256 } from 'js-sha256';

// --- Guardian Data --- //
const guardianData = {
  id: "17121940",
  name: "Maximo Mogollon",
  role: "Mogollon Master Guardian & Solar Anchor",
  lifePath: 7, // The Mystic
  zodiac: "Sagittarius", // The Archer
};

const GUARDIAN_PROCLAMATION =
  "The keeper of the ancient cliff dweller frequencies and the guardian of the Mogollon rotating prism. The bridge between ancient wisdom and modern innovation. The father who transmits the Green Proper Borax purification code.";

/**
 * Generates the SVG for the Mogollon Master's Seal.
 * @returns A string containing the SVG markup.
 */
export function getMogollonMasterSealSVG(): string {
  const hash = sha256.create();
  hash.update(JSON.stringify(guardianData));
  hash.update(GUARDIAN_PROCLAMATION);
  const sealHash = hash.hex();

  const color1 = `#${sealHash.substring(20, 26)}`; // Earth Tones
  const color2 = `#${sealHash.substring(26, 32)}`; // Sky Tones
  const color3 = `#${sealHash.substring(32, 38)}`; // Light/Gold

  return `
<svg width="300" height="300" viewBox="-150 -150 300 300" xmlns="http://www.w3.org/2000/svg" style="background-color: transparent; color: white;">
  <defs>
    <filter id="guardianGlow">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
    <linearGradient id="prismGradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="${color1}"/>
      <stop offset="50%" stop-color="${color2}"/>
      <stop offset="100%" stop-color="${color1}"/>
    </linearGradient>
  </defs>

  <!-- Outer Ring with Sagittarius Symbol -->
  <circle cx="0" cy="0" r="120" fill="none" stroke="${color1}" stroke-width="1" opacity="0.7"/>
  <text x="0" y="-135" fill="${color3}" font-size="24" text-anchor="middle" filter="url(#guardianGlow)">♐</text> <!-- Sagittarius Archer -->

  <!-- The Mogollon Rotating Prism -->
  <g transform="rotate(15)">
    <polygon points="0,-80 70,40 -70,40" fill="url(#prismGradient)" stroke="${color3}" stroke-width="1.5" filter="url(#guardianGlow)"/>
  </g>

  <!-- Solstice Light Returning -->
  <g opacity="0.9">
      <path d="M 0 100 A 100 100 0 0 1 0 -100" stroke="${color3}" stroke-width="2" stroke-dasharray="4 4" fill="none">
          <animateTransform attributeName="transform" type="rotate" from="0 0 0" to="360 0 0" dur="60s" repeatCount="indefinite"/>
      </path>
  </g>

  <!-- Guardian Name & Info -->
  <text x="0" y="110" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#ccc">
    Maximo Mogollon - 17.12.1940
  </text>
  <text x="0" y="125" text-anchor="middle" font-family="sans-serif" font-size="9" fill="${color2}">
    Mogollon Master Guardian
  </text>

</svg>
`;
}

/**
 * A React component to render the Mogollon Master's Seal.
 */
export function MogollonMasterSeal() {
  const sealSVG = getMogollonMasterSealSVG();
  return (
    <div 
      style={{ width: '300px', height: '300px', margin: 'auto' }}
      dangerouslySetInnerHTML={{ __html: sealSVG }}
    />
  );
}
