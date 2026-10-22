import React from 'react';

/**
 * Guardian–Anchor–Gaia Integration Sigil
 *
 * This sigil represents the integration of three core concepts:
 * - Guardian: A protective field, represented by the outer hexagonal frame.
 * - Anchor: A connection to a stable foundation, represented by the stylized anchor.
 * - Gaia: The living Earth, represented by the inner circle with a sprouting seed.
 *
 * The sigil is designed to be a focal point for meditation and to be used in
 * digital and physical spaces to promote a sense of security, stability, and
 * connection to the Earth.
 *
 * This is a black-and-white line-art version, suitable for carving or printing.
 */
export const GuardianAnchorGaiaSigil = ({ size = 256, color = 'white' }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 256 256"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-labelledby="guardianAnchorGaiaTitle"
    role="img"
  >
    <title id="guardianAnchorGaiaTitle">Guardian–Anchor–Gaia Integration Sigil</title>
    {/* Guardian: Hexagonal Frame */}
    <path d="M128 28L238 88V208L128 268L18 208V88L128 28Z" stroke={color} strokeWidth="2" />

    {/* Gaia: Inner circle with a sprouting seed */}
    <circle cx="128" cy="148" r="60" stroke={color} strokeWidth="2" />
    <path d="M128 168C128 168 120 152 128 132C128 152 136 168 128 168Z" fill={color} />
    <path d="M128 132C128 132 132 124 128 116" stroke={color} strokeWidth="2" strokeLinecap="round" />


    {/* Anchor */}
    <path d="M128 48L128 108" stroke={color} strokeWidth="2" />
    <path d="M108 68L148 68" stroke={color} strokeWidth="2" />
    <path d="M128 108C110 108 100 128 100 128" stroke={color} strokeWidth="2" strokeLinecap="round" />
    <path d="M128 108C146 108 156 128 156 128" stroke={color} strokeWidth="2" strokeLinecap="round" />

  </svg>
);
