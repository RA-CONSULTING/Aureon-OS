/**
 * MetricRings - Saturn-like orbital rings showing key metrics
 * Equity progress, coherence intensity, and trade count
 */

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { Html } from '@react-three/drei';
import * as THREE from 'three';
import { finiteOrNull, metricRingCaption } from '@/lib/reading';

interface MetricRingsProps {
  totalEquity: number | null;
  coherence: number | null;         // 0-1
  totalTrades: number | null;
  winRate: number | null;            // 0-100
  totalPnl: number | null;
}

const ringVertexShader = `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const progressRingFragmentShader = `
  uniform float uProgress;
  uniform vec3 uColor;
  uniform vec3 uBgColor;
  uniform float uTime;

  varying vec2 vUv;

  void main() {
    // Convert UV to angle (0-1 maps to full circle)
    float angle = atan(vUv.y - 0.5, vUv.x - 0.5) / (2.0 * 3.14159) + 0.5;

    // Fill based on progress
    float fill = step(angle, uProgress);
    vec3 color = mix(uBgColor, uColor, fill);

    // Animated leading edge glow
    float edge = 1.0 - smoothstep(0.0, 0.03, abs(angle - uProgress));
    color += uColor * edge * 2.0;

    // Subtle shimmer
    float shimmer = sin(angle * 30.0 + uTime * 2.0) * 0.05 + 0.95;
    color *= shimmer;

    float alpha = 0.15 + fill * 0.35 + edge * 0.3;
    gl_FragColor = vec4(color, alpha);
  }
`;

// Equity ring - fills based on equity growth
function EquityRing({ equity, pnl }: { equity: number; pnl: number }) {
  const meshRef = useRef<THREE.Mesh>(null);
  const materialRef = useRef<THREE.ShaderMaterial>(null);

  const color = useMemo(() =>
    pnl >= 0 ? new THREE.Color(0.1, 0.9, 0.5) : new THREE.Color(0.9, 0.2, 0.3),
    [pnl]
  );

  // Normalize equity to 0-1 range (assume 0-10000 scale, clamped)
  const progress = Math.min(Math.max(equity / 10000, 0), 1);

  const uniforms = useMemo(() => ({
    uProgress: { value: progress },
    uColor: { value: color },
    uBgColor: { value: new THREE.Color(0.05, 0.05, 0.1) },
    uTime: { value: 0 },
  }), []);

  useFrame((state) => {
    if (materialRef.current) {
      materialRef.current.uniforms.uTime.value = state.clock.elapsedTime;
      materialRef.current.uniforms.uProgress.value = THREE.MathUtils.lerp(
        materialRef.current.uniforms.uProgress.value, progress, 0.02
      );
      materialRef.current.uniforms.uColor.value.lerp(color, 0.05);
    }
    if (meshRef.current) {
      meshRef.current.rotation.z = state.clock.elapsedTime * 0.05;
    }
  });

  return (
    <mesh ref={meshRef} rotation={[Math.PI / 2, 0, 0]}>
      <ringGeometry args={[3.3, 3.6, 64]} />
      <shaderMaterial
        ref={materialRef}
        vertexShader={ringVertexShader}
        fragmentShader={progressRingFragmentShader}
        uniforms={uniforms}
        transparent
        depthWrite={false}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}

// Coherence ring - brightness maps to Gamma
function CoherenceRing({ coherence }: { coherence: number }) {
  const meshRef = useRef<THREE.Mesh>(null);

  const color = useMemo(() => {
    if (coherence > 0.7) return '#00ffaa';
    if (coherence > 0.4) return '#44aaff';
    return '#8844ff';
  }, [coherence]);

  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.z = -state.clock.elapsedTime * 0.08;
    }
  });

  return (
    <mesh ref={meshRef} rotation={[Math.PI / 2 + 0.5, 0, 0]}>
      <ringGeometry args={[3.8, 4.0, 64]} />
      <meshBasicMaterial
        color={color}
        transparent
        opacity={0.1 + coherence * 0.4}
        side={THREE.DoubleSide}
        depthWrite={false}
      />
    </mesh>
  );
}

// Trade count ring - dotted segments, each dot = a batch of trades
function TradeCountRing({ totalTrades, winRate }: { totalTrades: number; winRate: number }) {
  const groupRef = useRef<THREE.Group>(null);

  // Create dots around the ring
  const dots = useMemo(() => {
    const dotCount = Math.min(Math.ceil(totalTrades / 5), 60); // 1 dot per 5 trades, max 60
    const result = [];
    for (let i = 0; i < dotCount; i++) {
      const angle = (i / 60) * Math.PI * 2;
      const radius = 4.3;
      const x = Math.cos(angle) * radius;
      const z = Math.sin(angle) * radius;
      const isWin = (i / dotCount) < (winRate / 100);
      result.push({ x, z, isWin });
    }
    return result;
  }, [totalTrades, winRate]);

  useFrame((state) => {
    if (groupRef.current) {
      groupRef.current.rotation.y = state.clock.elapsedTime * 0.03;
    }
  });

  return (
    <group ref={groupRef} rotation={[Math.PI / 2 + 1.0, 0, 0]}>
      {dots.map((dot, i) => (
        <mesh key={i} position={[dot.x, 0, dot.z]}>
          <sphereGeometry args={[0.06, 6, 6]} />
          <meshBasicMaterial
            color={dot.isWin ? '#00ff66' : '#ff4466'}
            transparent
            opacity={0.7}
          />
        </mesh>
      ))}
    </group>
  );
}

export function MetricRings({
  totalEquity = null,
  coherence = null,
  totalTrades = null,
  winRate = null,
  totalPnl = null,
}: MetricRingsProps) {
  const equity = finiteOrNull(totalEquity);
  const gamma = finiteOrNull(coherence);
  const trades = finiteOrNull(totalTrades);
  const rate = finiteOrNull(winRate);
  const pnl = finiteOrNull(totalPnl);
  const caption = metricRingCaption([
    { name: 'equity', value: equity },
    { name: 'coherence', value: gamma },
    { name: 'trades', value: trades },
    { name: 'win rate', value: rate },
    { name: 'pnl', value: pnl },
  ]);

  return (
    <group>
      {equity != null && pnl != null && <EquityRing equity={equity} pnl={pnl} />}
      {gamma != null && <CoherenceRing coherence={gamma} />}
      {trades != null && rate != null && <TradeCountRing totalTrades={trades} winRate={rate} />}
      {caption && (
        <Html position={[0, 2.4, 0]} center>
          <span className="text-[10px] uppercase tracking-wider text-white/50 whitespace-nowrap">
            {caption}
          </span>
        </Html>
      )}
    </group>
  );
}
