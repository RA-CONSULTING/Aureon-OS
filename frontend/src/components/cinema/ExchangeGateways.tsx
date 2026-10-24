/**
 * ExchangeGateways - Portal nodes for each exchange
 * Torus geometry with rotating inner rings, positioned at 120-degree intervals
 */

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { Html } from '@react-three/drei';
import * as THREE from 'three';

interface ExchangeInfo {
  name: string;
  color: string;
  position: [number, number, number];
  connected: boolean;
  equity: number | null;
}

interface ExchangeGatewaysProps {
  krakenEquity: number | null;
  capitalEquity: number | null;
  binanceConnected: boolean;
  krakenConnected: boolean;
  capitalConnected: boolean;
}

function Gateway({ exchange }: { exchange: ExchangeInfo }) {
  const outerRef = useRef<THREE.Mesh>(null);
  const innerRef = useRef<THREE.Mesh>(null);
  const glowRef = useRef<THREE.Mesh>(null);
  const flickerRef = useRef(0);

  const color = useMemo(() => new THREE.Color(exchange.color), [exchange.color]);

  useFrame((state, delta) => {
    const t = state.clock.elapsedTime;

    if (outerRef.current) {
      outerRef.current.rotation.z = t * 0.3;
    }
    if (innerRef.current) {
      innerRef.current.rotation.z = -t * 0.5;
      innerRef.current.rotation.x = Math.sin(t * 0.2) * 0.3;
    }

    // Flicker when disconnected
    if (!exchange.connected && glowRef.current) {
      flickerRef.current += delta * 8;
      const flicker = Math.sin(flickerRef.current) > 0.3 ? 0.15 : 0.02;
      (glowRef.current.material as THREE.MeshBasicMaterial).opacity = flicker;
    }
  });

  const baseOpacity = exchange.connected ? 0.6 : 0.1;
  const emissiveIntensity = exchange.connected ? 1.5 : 0.2;

  return (
    <group position={exchange.position}>
      {/* Outer torus */}
      <mesh ref={outerRef}>
        <torusGeometry args={[1.2, 0.05, 16, 48]} />
        <meshStandardMaterial
          color={exchange.color}
          emissive={exchange.color}
          emissiveIntensity={emissiveIntensity}
          transparent
          opacity={baseOpacity}
        />
      </mesh>

      {/* Inner spinning ring */}
      <mesh ref={innerRef}>
        <torusGeometry args={[0.8, 0.03, 12, 32]} />
        <meshStandardMaterial
          color={exchange.color}
          emissive={exchange.color}
          emissiveIntensity={emissiveIntensity * 0.8}
          transparent
          opacity={baseOpacity * 0.7}
        />
      </mesh>

      {/* Central glow */}
      <mesh ref={glowRef}>
        <circleGeometry args={[0.7, 32]} />
        <meshBasicMaterial
          color={exchange.color}
          transparent
          opacity={exchange.connected ? 0.15 : 0.02}
          depthWrite={false}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Point light */}
      <pointLight
        color={exchange.color}
        intensity={exchange.connected ? 2 : 0.2}
        distance={8}
        decay={2}
      />

      {/* Label */}
      <Html
        position={[0, -2, 0]}
        center
        style={{
          pointerEvents: 'none',
          userSelect: 'none',
        }}
      >
        <div style={{
          color: exchange.color,
          fontSize: '11px',
          fontFamily: 'Source Code Pro, monospace',
          textAlign: 'center',
          textShadow: `0 0 10px ${exchange.color}`,
          opacity: exchange.connected ? 0.9 : 0.3,
          whiteSpace: 'nowrap',
        }}>
          <div style={{ fontWeight: 600, letterSpacing: '1px' }}>
            {exchange.name.toUpperCase()}
          </div>
          <div style={{ fontSize: '10px', opacity: 0.7, marginTop: '2px' }}>
            {exchange.equity == null
              ? 'unavailable'
              : `$${exchange.equity.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
          </div>
          <div style={{
            fontSize: '8px',
            marginTop: '2px',
            color: exchange.connected ? '#00ff88' : '#ff4444',
          }}>
            {exchange.connected ? 'LINKED' : 'OFFLINE'}
          </div>
        </div>
      </Html>
    </group>
  );
}

export function ExchangeGateways({
  krakenEquity = null,
  capitalEquity = null,
  binanceConnected = false,
  krakenConnected = true,
  capitalConnected = true,
}: ExchangeGatewaysProps) {
  const exchanges: ExchangeInfo[] = useMemo(() => [
    {
      name: 'Kraken',
      color: '#4488ff',
      position: [-10.4, 0, -6] as [number, number, number],
      connected: krakenConnected,
      equity: krakenEquity,
    },
    {
      name: 'Binance',
      color: '#f0b90b',
      position: [10.4, 0, -6] as [number, number, number],
      connected: binanceConnected,
      equity: null,
    },
    {
      name: 'Capital',
      color: '#00cc66',
      position: [0, 0, 12] as [number, number, number],
      connected: capitalConnected,
      equity: capitalEquity,
    },
  ], [krakenEquity, capitalEquity, binanceConnected, krakenConnected, capitalConnected]);

  return (
    <group>
      {exchanges.map(exchange => (
        <Gateway key={exchange.name} exchange={exchange} />
      ))}
    </group>
  );
}
