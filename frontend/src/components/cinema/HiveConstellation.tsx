/**
 * HiveConstellation - Orbiting hive agents as a living planetary system
 * Each hive is a cluster of spheres orbiting the Queen at different radii
 */

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

interface HiveConstellationProps {
  hiveCount: number;       // myceliumHives
  agentCount: number;      // myceliumAgents
  generation: number;      // myceliumGeneration
  queenPnl: number;        // queen's P&L
  coherence: number;       // drives orbit brightness
}

const MAX_AGENTS = 200;
const dummy = new THREE.Object3D();
const tempColor = new THREE.Color();

export function HiveConstellation({
  hiveCount,
  agentCount,
  generation,
  queenPnl,
  coherence,
}: HiveConstellationProps) {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const glowRef = useRef<THREE.InstancedMesh>(null);

  // Generate agent orbital data
  const agents = useMemo(() => {
    const data = [];
    const effectiveCount = Math.min(Math.max(agentCount, 0), MAX_AGENTS);
    const effectiveHives = Math.max(hiveCount, 1);

    for (let i = 0; i < effectiveCount; i++) {
      const hiveIndex = i % effectiveHives;
      const baseRadius = 5 + hiveIndex * 2.5 + (generation * 0.3);
      const radiusJitter = Math.sin((i + 1) * 1.618) * 0.75;
      const radius = baseRadius + radiusJitter;

      // Orbital parameters
      const angle = (i / effectiveCount) * Math.PI * 2 + hiveIndex * 1.2;
      const speed = (0.15 + ((i % 7) / 7) * 0.15) / (1 + hiveIndex * 0.3);
      const yOffset = Math.sin((i + 1) * 2.414) * 1.0;
      const yWobble = (i % 5) * 0.1;
      const size = 0.08 + (i % 6) * 0.02;

      // Profit status determines color
      let color: THREE.Color;
      if (queenPnl === 0) {
        color = new THREE.Color(0.9, 0.7, 0.2); // amber
      } else if (queenPnl > 0) {
        color = new THREE.Color(0.1, 0.9, 0.4); // green
      } else {
        color = new THREE.Color(0.9, 0.2, 0.2); // red
      }

      data.push({ radius, angle, speed, yOffset, yWobble, size, color, hiveIndex });
    }
    return data;
  }, [hiveCount, agentCount, generation, queenPnl]);

  useFrame((state) => {
    if (!meshRef.current || !glowRef.current) return;
    const t = state.clock.elapsedTime;

    for (let i = 0; i < agents.length; i++) {
      const a = agents[i];
      const currentAngle = a.angle + t * a.speed;

      const x = Math.cos(currentAngle) * a.radius;
      const z = Math.sin(currentAngle) * a.radius;
      const y = a.yOffset + Math.sin(t * 0.5 + a.angle) * a.yWobble;

      // Agent sphere
      dummy.position.set(x, y, z);
      dummy.scale.setScalar(a.size);
      dummy.updateMatrix();
      meshRef.current.setMatrixAt(i, dummy.matrix);
      meshRef.current.setColorAt(i, a.color);

      // Glow sphere (slightly larger, more transparent)
      dummy.scale.setScalar(a.size * 2.5);
      dummy.updateMatrix();
      glowRef.current.setMatrixAt(i, dummy.matrix);
      tempColor.copy(a.color);
      glowRef.current.setColorAt(i, tempColor);
    }

    meshRef.current.instanceMatrix.needsUpdate = true;
    if (meshRef.current.instanceColor) meshRef.current.instanceColor.needsUpdate = true;
    glowRef.current.instanceMatrix.needsUpdate = true;
    if (glowRef.current.instanceColor) glowRef.current.instanceColor.needsUpdate = true;
  });

  const count = Math.min(Math.max(agentCount, 0), MAX_AGENTS);

  return (
    <group>
      {/* Solid agent cores */}
      <instancedMesh ref={meshRef} args={[undefined, undefined, count]}>
        <sphereGeometry args={[1, 8, 8]} />
        <meshStandardMaterial
          emissive="white"
          emissiveIntensity={0.5 + coherence * 0.5}
          roughness={0.3}
          metalness={0.7}
        />
      </instancedMesh>

      {/* Glow halos */}
      <instancedMesh ref={glowRef} args={[undefined, undefined, count]}>
        <sphereGeometry args={[1, 6, 6]} />
        <meshBasicMaterial
          transparent
          opacity={0.1 + coherence * 0.15}
          depthWrite={false}
        />
      </instancedMesh>

      {/* Orbital path rings (visual guides) */}
      {Array.from({ length: Math.min(hiveCount, 5) }, (_, i) => (
        <mesh key={i} rotation={[Math.PI / 2, 0, 0]}>
          <ringGeometry args={[
            4.8 + i * 2.5 + generation * 0.3,
            5.0 + i * 2.5 + generation * 0.3,
            64
          ]} />
          <meshBasicMaterial
            color="#224488"
            transparent
            opacity={0.06}
            side={THREE.DoubleSide}
            depthWrite={false}
          />
        </mesh>
      ))}
    </group>
  );
}
