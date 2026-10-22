import React from 'react';

// --- Triptych Sigil of the Waters of Initiation ---
// This sigil represents the unified archetype of Wisdom living in Water, Spirals, and Vessels.
// It braids together three core traditions:
// 1. Celtic Salmon of Knowledge: The fish, representing wisdom gained through contact.
// 2. Amazonian River Spirits: The flowing water/energy, representing the sacred, life-giving river.
// 3. Mogollon Sacred Vessels: The chalice with geometric patterns, the container of life and teaching.
// The flaming heart and Flower of Life background represent Universal Blessing and the interconnectedness of all things.

const SigilSVG: React.FC = () => {
  const colors = {
    background: '#F3F0E9',
    black: '#1A1A1A',
    gold: '#C0A060',
  };

  return (
    <svg 
      width="100%" 
      height="100%" 
      viewBox="0 0 400 400"
      xmlns="http://www.w3.org/2000/svg" 
      style={{ background: 'transparent' }}
    >
      <defs>
        <pattern id="flowerOfLife" patternUnits="userSpaceOnUse" width="60" height="103.8">
          <g fill="none" stroke={colors.gold} strokeWidth="0.5" opacity="0.4">
            <path d="M30,51.9 a30,30 0 1,0 0,0.001" />
            <path d="M0,0 a30,30 0 1,0 60,0" />
            <path d="M0,103.8 a30,30 0 1,0 60,0" />
            <path d="M-30,51.9 a30,30 0 1,0 60,0" />
          </g>
        </pattern>
      </defs>

      {/* Background and Flower of Life */}
      <circle cx="200" cy="200" r="195" fill={colors.background} />
      <circle cx="200" cy="200" r="160" fill="url(#flowerOfLife)" />

      {/* Outer Rings */}
      <circle cx="200" cy="200" r="180" stroke={colors.black} strokeWidth="12" fill="none" />
      <circle cx="200" cy="200" r="160" stroke={colors.black} strokeWidth="2" fill="none" />
      <circle cx="200" cy="200" r="155" stroke={colors.gold} strokeWidth="1.5" fill="none" opacity="0.8" />

      {/* Celtic Knot Border - Simplified representation */}
      <g stroke={colors.black} strokeWidth="3" fill="none">
        <path d="M 200, 20 A 180,180 0 0 1 380,200" />
        <path d="M 380, 200 A 180,180 0 0 1 200,380" />
        <path d="M 200, 380 A 180,180 0 0 1 20,200" />
        <path d="M 20, 200 A 180,180 0 0 1 200,20" />
        <path d="M 200, 26 A 174,174 0 0 1 374,200" />
        <path d="M 374, 200 A 174,174 0 0 1 200,374" />
        <path d="M 200, 374 A 174,174 0 0 1 26,200" />
        <path d="M 26, 200 A 174,174 0 0 1 200,26" />
      </g>
      
    </svg>
  );
};

const TriptychSigil = () => {
  return (
    <div style={{ width: '400px', height: '400px', margin: 'auto' }}>
      <SigilSVG />
    </div>
  );
};

export default TriptychSigil;
