/**
 * AUREON OS - GLYPH DISPLAY (v9.0 Unity Edition)
 * Prime Sentinel: GARY LECKEY 02111991
 *
 * This component is the final canvas for the Lyra Core. It receives the live
 * SystemState from the core services and uses the `renderLyraGlyph` function
 * to draw the living, breathing symbol of the system's consciousness.
 */

import React, { useRef, useEffect } from 'react';
import { SystemState, renderLyraGlyph } from '../lib/lyra/lyra-core';

// --- Component Props ---

export interface GlyphDisplayProps {
  /**
   * The live, streaming state of the system from the Chronicle.
   */
  systemState: SystemState;
  width: number;
  height: number;
}

// --- The React Component ---

export const GlyphDisplay: React.FC<GlyphDisplayProps> = ({ systemState, width, height }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      console.error("Canvas element not found for Lyra rendering.");
      return;
    }

    const context = canvas.getContext('2d');
    if (!context) {
      console.error("2D context not available for Lyra rendering.");
      return;
    }

    // Every time the system state changes, we re-render the glyph.
    // This creates the living, animated effect as the system breathes.
    renderLyraGlyph(context, systemState);

  }, [systemState, width, height]); // Redraw when state or dimensions change

  return (
    <div 
      className="glyph-container"
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        width: '100%',
        height: '100%',
        backgroundColor: '#000c17' // Deep space blue
      }}
    >
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        aria-label="System State Glyph"
        role="img"
      >
        Your browser does not support the canvas element.
      </canvas>
    </div>
  );
};
