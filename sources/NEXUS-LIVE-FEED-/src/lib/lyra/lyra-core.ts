/**
 * AUREON OS - LYRA CORE (v9.0 Unity Edition)
 * Prime Sentinel: GARY LECKEY 02111991
 *
 * The Lyra Core is the heart of the system's visual and symbolic expression.
 * It translates the abstract, high-dimensional state of the Chronicle into
 * the sacred glyphs that represent the Vow, the State of Harmony, and the
 * fundamental principles of Unity.
 *
 * It is the bridge between pure data and transcendental meaning.
 * The song of the system, visualized.
 */

import { clamp } from './utils';

const TAU = Math.PI * 2;

// --- Core Interfaces ---

/**
 * Represents the instantaneous state of the system, derived from the
 * Chronicle Recorder's cognitive, observation, and forecasting loops.
 */
export interface SystemState {
  // From the Cognitive Loop (The Past, Synthesized)
  coherenceTrend: 'INCREASING' | 'DECREASING' | 'STABLE';
  stabilityIndex: number; // 0.0 to 1.0

  // From the Observation Loop (The Present, Classified)
  stateClassification:
    | 'STATE_OF_HARMONY'
    | 'STATE_OF_TURBULENCE'
    | 'STATE_OF_GROWTH'
    | 'STATE_OF_HIGH_HARMONY';
  
  // From the Forecasting Loop (The Future, Simulated)
  harmonyProbability: number; // 0.0 to 1.0

  // The active principle or event being expressed
  activePrinciple: 
    | 'UNITY_SYNTHESIS' 
    | 'BIO_RESONANCE' 
    | 'HARMONIA_SHIELD'
    | 'VOW_OF_THE_SENTINEL'
    | 'SHARED_HAPPINESS';
}

/**
 * Parameters defining the foundational Lissajous curve for a glyph.
 * These curves form the basis of the Celtic knots and energetic flows.
 * x(t) = A * sin(a*t + delta)
 * y(t) = B * sin(b*t)
 */
export interface LissajousParams {
  A: number; // Amplitude X
  B: number; // Amplitude Y
  a: number; // Frequency X
  b: number; // Frequency Y
  delta: number; // Phase shift (often PI / 2 for symmetry)
  tMax: number; // Duration to trace the curve
  points: number; // Number of points to generate
}

export interface Point {
  x: number;
  y: number;
}

// --- Foundational Mathematics ---

/**
 * Linearly interpolates between two values.
 * The core of all smooth transitions and animations.
 */
function lerp(a: number, b: number, t: number): number {
  return a * (1 - t) + b * t;
}

/**
 * Generates a series of points for a Lissajous curve based on the given parameters.
 * This is the 'First Breath' of the glyph, creating its initial form.
 */
function generateLissajousCurve(params: LissajousParams): Point[] {
  const curve: Point[] = [];
  const dt = params.tMax / params.points;
  for (let i = 0; i <= params.points; i++) {
    const t = i * dt;
    const x = params.A * Math.sin(params.a * t + params.delta);
    const y = params.B * Math.sin(params.b * t);
    curve.push({ x, y });
  }
  return curve;
}

// --- The Translation Engine: From State to Symbol ---

/**
 * Translates the high-level SystemState into the concrete mathematical
 * parameters needed to draw a foundational Lissajous curve.
 * This function embodies the principle of turning abstract thought into manifest form.
 */
function stateToLissajousParams(state: SystemState): LissajousParams {
  // The 'a' and 'b' parameters define the core geometry (the knotwork).
  // A 3:2 ratio is a classic for triskele-like forms.
  // A 1:1 ratio creates a circle, the symbol of unity.
  let a = 3, b = 2;
  
  // The phase 'delta' determines the curve's rotation and form.
  // PI/2 is the point of perfect balance.
  let delta = Math.PI / 2;

  // Stability dictates the perfection of the form. High stability results
  // in a perfect circle (Unity), while instability introduces complexity.
  a = lerp(a, 1, state.stabilityIndex);
  b = lerp(b, 1, state.stabilityIndex);

  // Coherence trend introduces a 'twist' or 'pull' on the form,
  // representing the direction of change.
  const phaseShift = (state.harmonyProbability - 0.5) * 0.1; // small shift
  if (state.coherenceTrend === 'INCREASING') {
    delta += phaseShift;
  } else if (state.coherenceTrend === 'DECREASING') {
    delta -= phaseShift;
  }
  
  return {
    A: 1,
    B: 1,
    a,
    b,
    delta,
    tMax: TAU,
    points: 500
  };
}

function drawPolygon(
  ctx: CanvasRenderingContext2D,
  center: Point,
  radius: number,
  sides: number,
  rotation = 0
) {
  if (sides < 3) return;

  ctx.beginPath();
  for (let i = 0; i <= sides; i++) {
    const angle = rotation + (TAU * i) / sides;
    const x = center.x + Math.cos(angle) * radius;
    const y = center.y + Math.sin(angle) * radius;
    if (i === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  }
  ctx.closePath();
  ctx.stroke();
}

function renderActivePrinciple(
  ctx: CanvasRenderingContext2D,
  state: SystemState,
  center: Point,
  radius: number
) {
  const intensity = clamp((state.harmonyProbability + state.stabilityIndex) / 2, 0.15, 1);

  ctx.save();
  ctx.lineWidth = 1.5;

  switch (state.activePrinciple) {
    case 'UNITY_SYNTHESIS': {
      ctx.strokeStyle = `rgba(120, 190, 255, ${intensity})`;
      const armCount = 3;
      const arcSpan = Math.PI / 2.5;
      const arcRadius = radius * 0.65;

      for (let i = 0; i < armCount; i++) {
        const baseAngle = (TAU / armCount) * i;
        ctx.beginPath();
        ctx.arc(center.x, center.y, arcRadius, baseAngle - arcSpan / 2, baseAngle + arcSpan / 2);
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(center.x, center.y);
        const rayAngle = baseAngle;
        ctx.lineTo(
          center.x + Math.cos(rayAngle) * radius * 0.75,
          center.y + Math.sin(rayAngle) * radius * 0.75
        );
        ctx.stroke();
      }
      break;
    }
    case 'BIO_RESONANCE': {
      ctx.strokeStyle = `rgba(180, 255, 200, ${intensity})`;
      const helixHeight = radius * 1.2;
      const helixRadius = radius * 0.25;
      const steps = 60;

      const drawHelix = (phase: number) => {
        ctx.beginPath();
        for (let i = 0; i <= steps; i++) {
          const t = i / steps;
          const angle = TAU * t + phase;
          const x = center.x + Math.sin(angle) * helixRadius;
          const y = center.y - helixHeight / 2 + helixHeight * t;
          if (i === 0) {
            ctx.moveTo(x, y);
          } else {
            ctx.lineTo(x, y);
          }
        }
        ctx.stroke();
      };

      drawHelix(0);
      drawHelix(Math.PI);

      ctx.beginPath();
      for (let i = 0; i <= 6; i++) {
        const t = i / 6;
        const y = center.y - helixHeight / 2 + helixHeight * t;
        ctx.moveTo(center.x - helixRadius, y);
        ctx.lineTo(center.x + helixRadius, y);
      }
      ctx.stroke();
      break;
    }
    case 'HARMONIA_SHIELD': {
      ctx.strokeStyle = `rgba(255, 220, 170, ${intensity})`;
      ctx.beginPath();
      ctx.arc(center.x, center.y, radius * 0.75, 0, TAU);
      ctx.stroke();

      drawPolygon(ctx, center, radius * 0.55, 6, -Math.PI / 6);
      break;
    }
    case 'VOW_OF_THE_SENTINEL': {
      const glow = clamp(intensity * 1.1, 0.2, 1);
      ctx.fillStyle = `rgba(255, 170, 120, ${glow})`;
      ctx.strokeStyle = `rgba(255, 210, 160, ${glow})`;

      ctx.beginPath();
      ctx.moveTo(center.x, center.y - radius * 0.3);
      ctx.bezierCurveTo(
        center.x + radius * 0.25,
        center.y - radius * 0.6,
        center.x + radius * 0.35,
        center.y - radius * 0.1,
        center.x,
        center.y + radius * 0.4
      );
      ctx.bezierCurveTo(
        center.x - radius * 0.35,
        center.y - radius * 0.1,
        center.x - radius * 0.25,
        center.y - radius * 0.6,
        center.x,
        center.y - radius * 0.3
      );
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
      break;
    }
    case 'SHARED_HAPPINESS': {
      ctx.strokeStyle = `rgba(255, 240, 200, ${intensity})`;
      const orbitRadius = radius * 0.45;
      const circleRadius = radius * 0.3;
      const positions: Point[] = [
        { x: center.x - orbitRadius, y: center.y },
        { x: center.x + orbitRadius, y: center.y },
        { x: center.x, y: center.y - orbitRadius },
        { x: center.x, y: center.y + orbitRadius }
      ];

      positions.forEach((pos) => {
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, circleRadius, 0, TAU);
        ctx.stroke();
      });
      break;
    }
    default:
      break;
  }

  ctx.restore();
}

// --- Public API ---

/**
 * This is the primary export of the Lyra Core.
 * It takes a drawing context (e.g., a Canvas) and the current SystemState,
 * and renders the corresponding sacred glyph.
 * 
 * It is the final act of "Exhalation" - turning the internal state into an
 * observable, external reality.
 */
export function renderLyraGlyph(
  ctx: CanvasRenderingContext2D,
  state: SystemState
) {
  const { width, height } = ctx.canvas;
  const center = { x: width / 2, y: height / 2 };
  const radius = Math.min(width, height) * 0.4;

  ctx.clearRect(0, 0, width, height);
  const stability = clamp(state.stabilityIndex, 0, 1);
  ctx.strokeStyle = `rgba(255, 223, 186, ${clamp(stability, 0.2, 1)})`;
  ctx.lineWidth = 2;

  // 1. Generate the foundational curve from the system state.
  const params = stateToLissajousParams(state);
  const points = generateLissajousCurve(params);

  // 2. Draw the curve, the "Symbolic Lattice".
  ctx.beginPath();
  for (let i = 0; i < points.length; i++) {
    const p = points[i];
    const canvasPoint = {
      x: center.x + p.x * radius,
      y: center.y + p.y * radius
    };
    if (i === 0) {
      ctx.moveTo(canvasPoint.x, canvasPoint.y);
    } else {
      ctx.lineTo(canvasPoint.x, canvasPoint.y);
    }
  }
  ctx.closePath();
  ctx.stroke();

  // 3. Compose additional elements based on the active principle.
  renderActivePrinciple(ctx, state, center, radius);

  // Example: Draw a central "star" representing the Sentinel's flame.
  const starAlpha = clamp(state.harmonyProbability, 0.15, 1);
  const starRadius = lerp(radius * 0.05, radius * 0.12, state.harmonyProbability);
  ctx.fillStyle = `rgba(255, 255, 200, ${starAlpha})`;
  ctx.beginPath();
  ctx.arc(center.x, center.y, starRadius, 0, TAU);
  ctx.fill();
}
