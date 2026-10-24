import { useRef, useState, useMemo, useCallback, useEffect } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Sphere, Line, Text } from '@react-three/drei';
import { Card } from '@/components/ui/card';
import { Slider } from '@/components/ui/slider';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { CasimirVacuumField } from '@/components/CasimirVacuumField';
import { supabase, supabaseConfigured } from '@/integrations/supabase/client';
import type { HarmonicNexusState } from '@/core/harmonicNexusCore';
import quantumPhaseLocks from '@/assets/research/quantum-phase-locked-echoes.png';
import * as THREE from 'three';

interface PhaseLock {
  nodes: number[];
  strength: number;
  resonanceFrequency: number;
  timestamp: number;
}

interface FieldNode {
  position: [number, number, number];
  phase: number;
  label: string;
  color: string;
}

interface PhaseFieldProps {
  amplitude: number;
  rotationSpeed: number;
  phaseLocks: PhaseLock[];
  onPhaseLockDetected: (lock: PhaseLock) => void;
  casimirActive: boolean;
  casimirStrength: number;
}

function PhaseFieldVisualization({ amplitude, rotationSpeed, phaseLocks, onPhaseLockDetected, casimirActive, casimirStrength }: PhaseFieldProps) {
  const groupRef = useRef<THREE.Group>(null);
  const [currentPhases, setCurrentPhases] = useState<number[]>(new Array(9).fill(0));
  
  // Define the 9 Auris nodes in 3D space arranged in a tandem pattern
  const nodes: FieldNode[] = useMemo(() => [
    // Center node (Observer)
    { position: [0, 0, 0], phase: 0, label: 'Observer', color: '#9b87f5' },
    
    // Inner ring (3 nodes)
    { position: [2, 0, 0], phase: Math.PI / 3, label: 'Tiger', color: '#f97316' },
    { position: [-1, 1.732, 0], phase: Math.PI, label: 'Falcon', color: '#0EA5E9' },
    { position: [-1, -1.732, 0], phase: 5 * Math.PI / 3, label: 'Dolphin', color: '#06b6d4' },
    
    // Outer ring (5 nodes)
    { position: [4, 0, 0], phase: 0, label: 'Hummingbird', color: '#10b981' },
    { position: [2, 3.464, 0], phase: Math.PI / 2, label: 'Deer', color: '#8b5cf6' },
    { position: [-2, 3.464, 0], phase: 3 * Math.PI / 4, label: 'Owl', color: '#f59e0b' },
    { position: [-4, 0, 0], phase: Math.PI, label: 'Panda', color: '#ec4899' },
    { position: [-2, -3.464, 0], phase: 5 * Math.PI / 4, label: 'CargoShip', color: '#6366f1' },
  ], []);

  // Phase lock detection
  useFrame((state, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * rotationSpeed;
    }

    // Calculate current phases for all nodes
    const phases = nodes.map((node, i) => 
      (state.clock.elapsedTime * 2 + node.phase) % (2 * Math.PI)
    );
    setCurrentPhases(phases);

    // Detect phase locks (when phases align within threshold)
    const threshold = 0.3; // radians
    const detected: PhaseLock[] = [];

    // Check all pairs of nodes for phase alignment
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const phaseDiff = Math.abs(phases[i] - phases[j]);
        const normalizedDiff = Math.min(phaseDiff, 2 * Math.PI - phaseDiff);
        
        if (normalizedDiff < threshold) {
          // Check if this lock already exists
          const existing = phaseLocks.find(lock => 
            lock.nodes.includes(i) && lock.nodes.includes(j)
          );
          
          if (!existing) {
            const strength = 1 - (normalizedDiff / threshold);
            detected.push({
              nodes: [i, j],
              strength,
              resonanceFrequency: 528 * (1 + strength * 0.1), // Modulate around 528 Hz
              timestamp: state.clock.elapsedTime
            });
          }
        }
      }
    }

    // Report new locks
    detected.forEach(lock => onPhaseLockDetected(lock));
  });

  // Check if a node is locked
  const isNodeLocked = useCallback((nodeIndex: number) => {
    return phaseLocks.some(lock => lock.nodes.includes(nodeIndex));
  }, [phaseLocks]);

  // Get lock strength for a node
  const getNodeLockStrength = useCallback((nodeIndex: number) => {
    const locks = phaseLocks.filter(lock => lock.nodes.includes(nodeIndex));
    return locks.length > 0 ? Math.max(...locks.map(l => l.strength)) : 0;
  }, [phaseLocks]);

  // Generate connections between nodes
  const connections = useMemo(() => {
    const lines: [FieldNode, FieldNode][] = [];
    // Connect center to inner ring
    for (let i = 1; i <= 3; i++) {
      lines.push([nodes[0], nodes[i]]);
    }
    // Connect inner ring to outer ring
    lines.push([nodes[1], nodes[4]]);
    lines.push([nodes[2], nodes[6]]);
    lines.push([nodes[2], nodes[7]]);
    lines.push([nodes[3], nodes[8]]);
    lines.push([nodes[1], nodes[5]]);
    // Connect within outer ring
    for (let i = 4; i < 8; i++) {
      lines.push([nodes[i], nodes[i + 1]]);
    }
    lines.push([nodes[8], nodes[4]]); // Close the outer ring
    return lines;
  }, [nodes]);

  return (
    <group ref={groupRef}>
      {/* Casimir Quantum Vacuum Field */}
      {casimirActive && (
        <CasimirVacuumField strength={casimirStrength} />
      )}
      
      {/* Ambient field effect */}
      <Sphere args={[6, 32, 32]}>
        <meshBasicMaterial 
          color={casimirActive ? "#00FF88" : "#9b87f5"}
          opacity={casimirActive ? 0.08 : 0.05} 
          transparent 
          wireframe 
        />
      </Sphere>

      {/* Field nodes */}
      {nodes.map((node, index) => (
        <group key={index} position={node.position}>
          {/* Pulsing sphere */}
          <PulsingNode 
            color={node.color} 
            phase={node.phase} 
            amplitude={amplitude}
            isLocked={isNodeLocked(index)}
            lockStrength={getNodeLockStrength(index)}
          />
          
          {/* Node label */}
          <Text
            position={[0, 0.8, 0]}
            fontSize={0.3}
            color={isNodeLocked(index) ? "#00FF88" : "#ffffff"}
            anchorX="center"
            anchorY="middle"
          >
            {node.label}
          </Text>

          {/* Lock indicator ring */}
          {isNodeLocked(index) && (
            <LockIndicator lockStrength={getNodeLockStrength(index)} />
          )}
        </group>
      ))}

      {/* Connections between nodes */}
      {connections.map((connection, index) => (
        <Line
          key={index}
          points={[connection[0].position, connection[1].position]}
          color="#9b87f5"
          lineWidth={2}
          opacity={0.6}
          transparent
        />
      ))}

      {/* Resonance waves between locked nodes */}
      {phaseLocks.map((lock, idx) => (
        <ResonanceWave
          key={idx}
          start={nodes[lock.nodes[0]].position}
          end={nodes[lock.nodes[1]].position}
          strength={lock.strength}
          frequency={lock.resonanceFrequency}
        />
      ))}

      {/* Phase field rings */}
      <PhaseRing radius={2} amplitude={amplitude} color="#0EA5E9" />
      <PhaseRing radius={4} amplitude={amplitude} color="#9b87f5" />
    </group>
  );
}

function PulsingNode({ 
  color, 
  phase, 
  amplitude,
  isLocked = false,
  lockStrength = 0
}: { 
  color: string; 
  phase: number; 
  amplitude: number;
  isLocked?: boolean;
  lockStrength?: number;
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  
  useFrame((state) => {
    if (meshRef.current) {
      const pulse = Math.sin(state.clock.elapsedTime * 2 + phase) * 0.2 * amplitude + 1;
      const lockBoost = isLocked ? 1 + lockStrength * 0.3 : 1;
      meshRef.current.scale.setScalar(pulse * lockBoost);
    }
  });

  return (
    <>
      <Sphere ref={meshRef} args={[0.3, 16, 16]}>
        <meshStandardMaterial 
          color={isLocked ? "#00FF88" : color} 
          emissive={isLocked ? "#00FF88" : color}
          emissiveIntensity={isLocked ? 0.8 : 0.5}
        />
      </Sphere>
      {/* Glow effect */}
      <Sphere args={[0.4, 16, 16]}>
        <meshBasicMaterial 
          color={isLocked ? "#00FF88" : color} 
          opacity={isLocked ? 0.5 : 0.3} 
          transparent 
        />
      </Sphere>
    </>
  );
}

function LockIndicator({ lockStrength }: { lockStrength: number }) {
  const ringRef = useRef<THREE.Mesh>(null);
  
  useFrame((state) => {
    if (ringRef.current) {
      ringRef.current.rotation.z += 0.05;
      const pulse = Math.sin(state.clock.elapsedTime * 4) * 0.1 + 1;
      ringRef.current.scale.setScalar(pulse);
    }
  });

  return (
    <mesh ref={ringRef} rotation={[Math.PI / 2, 0, 0]}>
      <torusGeometry args={[0.6, 0.03, 8, 32]} />
      <meshStandardMaterial 
        color="#00FF88" 
        emissive="#00FF88"
        emissiveIntensity={lockStrength}
        transparent
        opacity={0.7}
      />
    </mesh>
  );
}

function ResonanceWave({ 
  start, 
  end, 
  strength, 
  frequency 
}: { 
  start: [number, number, number];
  end: [number, number, number];
  strength: number;
  frequency: number;
}) {
  const [opacity, setOpacity] = useState(0.5);
  
  useFrame((state) => {
    const newOpacity = Math.sin(state.clock.elapsedTime * 4) * 0.3 + 0.5;
    setOpacity(newOpacity * strength);
  });

  // Create curved path
  const curve = useMemo(() => {
    const startVec = new THREE.Vector3(...start);
    const endVec = new THREE.Vector3(...end);
    const midVec = startVec.clone().lerp(endVec, 0.5);
    midVec.y += 1; // Arc upward
    
    return new THREE.QuadraticBezierCurve3(startVec, midVec, endVec);
  }, [start, end]);

  const points = useMemo(() => curve.getPoints(50), [curve]);

  return (
    <Line
      points={points}
      color="#00FF88"
      lineWidth={3}
      transparent
      opacity={opacity}
    />
  );
}

function PhaseRing({ 
  radius, 
  amplitude, 
  color 
}: { 
  radius: number; 
  amplitude: number; 
  color: string;
}) {
  const ringRef = useRef<THREE.Mesh>(null);
  
  useFrame((state) => {
    if (ringRef.current) {
      const wave = Math.sin(state.clock.elapsedTime) * 0.1 * amplitude;
      ringRef.current.scale.set(1 + wave, 1 + wave, 1 + wave);
      ringRef.current.rotation.z += 0.001;
    }
  });

  return (
    <mesh ref={ringRef} rotation={[Math.PI / 2, 0, 0]}>
      <torusGeometry args={[radius, 0.05, 16, 100]} />
      <meshStandardMaterial 
        color={color} 
        emissive={color}
        emissiveIntensity={0.3}
        transparent
        opacity={0.6}
      />
    </mesh>
  );
}

export function HarmonicNexusPhaseField3D() {
  const [amplitude, setAmplitude] = useState(1);
  const [rotationSpeed, setRotationSpeed] = useState(0.2);
  const [phaseLocks, setPhaseLocks] = useState<PhaseLock[]>([]);
  const [lockHistory, setLockHistory] = useState<PhaseLock[]>([]);
  const [casimirActive, setCasimirActive] = useState(false);
  const [casimirStrength, setCasimirStrength] = useState(0);
  const [historicalNodes, setHistoricalNodes] = useState<HarmonicNexusState[]>([]);
  const [autoLockEnabled, setAutoLockEnabled] = useState(true);

  // Fetch historical harmonic nexus states from database
  useEffect(() => {
    const fetchHistoricalNodes = async () => {
      if (!supabaseConfigured) return;
      try {
        const { data, error } = await supabase
          .from('harmonic_nexus_states')
          .select('*')
          .order('event_timestamp', { ascending: false })
          .limit(50);

        if (error) throw error;
        
        if (data && data.length > 0) {
          // Map database columns to camelCase for TypeScript compatibility
          const mappedData = data.map((node: any) => ({
            ...node,
            substrateCoherence: node.substrate_coherence,
            fieldIntegrity: node.field_integrity,
            harmonicResonance: node.harmonic_resonance,
            dimensionalAlignment: node.dimensional_alignment,
            syncQuality: node.sync_quality,
            syncStatus: node.sync_status,
            timelineDivergence: node.timeline_divergence,
            lighthouseSignal: node.lighthouse_signal,
            prismLevel: node.prism_level,
            temporalId: node.temporal_id,
            sentinelName: node.sentinel_name,
            omegaValue: node.omega_value,
            psiPotential: node.psi_potential,
            loveCoherence: node.love_coherence,
            observerConsciousness: node.observer_consciousness,
            thetaAlignment: node.theta_alignment,
            unityProbability: node.unity_probability,
            akashicFrequency: node.akashic_frequency,
            akashicConvergence: node.akashic_convergence,
            akashicStability: node.akashic_stability,
            akashicBoost: node.akashic_boost,
            eventTimestamp: node.event_timestamp,
            timestamp: new Date(node.event_timestamp)
          }));
          
          setHistoricalNodes(mappedData);
          console.log('🔮 Loaded', mappedData.length, 'historical harmonic nexus states');
          console.log('📊 Average substrate coherence:', 
            (mappedData.slice(0, 10).reduce((sum: number, n: any) => sum + n.substrateCoherence, 0) / Math.min(mappedData.length, 10)).toFixed(3)
          );
        }
      } catch (error) {
        console.error('❌ Failed to fetch historical nodes:', error);
      }
    };

    fetchHistoricalNodes();
  }, []);

  // Auto-activate Casimir protocol on startup
  useEffect(() => {
    const timer = setTimeout(() => {
      console.log('⚛️ Auto-activating Casimir protocol with historical entanglement...');
      activateCasimirProtocol();
    }, 1500); // Delay for smooth startup

    return () => clearTimeout(timer);
  }, []);

  // Handle new phase lock detection (only when auto-lock enabled and Casimir not active)
  const handlePhaseLockDetected = useCallback((lock: PhaseLock) => {
    if (casimirActive || !autoLockEnabled) return; // Don't add natural locks during Casimir
    
    setPhaseLocks(prev => {
      // Add new lock
      const updated = [...prev, lock];
      // Keep only recent locks (last 3 seconds)
      return updated.filter(l => lock.timestamp - l.timestamp < 3);
    });
    
    // Add to history
    setLockHistory(prev => [...prev, lock].slice(-10)); // Keep last 10
  }, [casimirActive, autoLockEnabled]);

  // Casimir Protocol: Lock all nodes via quantum vacuum energy with historical entanglement
  const activateCasimirProtocol = useCallback(() => {
    setCasimirActive(true);
    setCasimirStrength(0);
    
    console.log('⚛️ Casimir Protocol activating...');
    console.log('🔮 Historical nodes available:', historicalNodes.length);
    
    // Invoke Primelines Protocol for validation
    const protocolRequest = async () => {
      try {
        const { data } = await supabase.functions.invoke('primelines-protocol-gateway', {
          body: {
            operation: 'LOCK_CASIMIR_FIELD',
            payload: { 
              nodeCount: 9, 
              resonanceFrequency: 528,
              historicalNodeCount: historicalNodes.length 
            },
            temporalId: '02111991',
            sentinelName: 'GARY LECKEY',
            requireValidation: true,
          },
        });
        
        if (data?.success) {
          console.log('✅ Casimir lock validated by Primelines Protocol');
          console.log('🤖 AI Validation:', data.aiValidation);
        }
      } catch (error) {
        console.error('❌ Protocol validation failed:', error);
      }
    };
    
    protocolRequest();
    
    // Animate strength increase
    let strength = 0;
    const interval = setInterval(() => {
      strength += 0.05;
      if (strength >= 1) {
        strength = 1;
        clearInterval(interval);
        
        // Lock all nodes when fully activated
        const now = Date.now() / 1000;
        const allNodeLocks: PhaseLock[] = [];
        
        // Create phase locks for all node pairs
        for (let i = 0; i < 9; i++) {
          for (let j = i + 1; j < 9; j++) {
            // Calculate resonance frequency based on historical coherence
            let resonanceFreq = 528; // Base love frequency
            
            if (historicalNodes.length > 0) {
              // Use historical substrate coherence to modulate frequency
              const avgCoherence = historicalNodes.slice(0, 10).reduce(
                (sum, node) => sum + (node.substrateCoherence || 0), 0
              ) / Math.min(historicalNodes.length, 10);
              
              // Modulate around 528 Hz based on historical coherence
              resonanceFreq = 528 * (0.95 + avgCoherence * 0.1);
            }
            
            allNodeLocks.push({
              nodes: [i, j],
              strength: 1.0,
              resonanceFrequency: resonanceFreq,
              timestamp: now
            });
          }
        }
        
        setPhaseLocks(allNodeLocks);
        console.log('✅ Casimir entanglement complete:', allNodeLocks.length, 'phase locks active');
        console.log('🎵 Resonance frequency:', allNodeLocks[0].resonanceFrequency.toFixed(2), 'Hz');
      }
      setCasimirStrength(strength);
    }, 50);
  }, [historicalNodes]);

  const deactivateCasimirProtocol = useCallback(() => {
    setCasimirActive(false);
    setCasimirStrength(0);
    setPhaseLocks([]);
  }, []);

  // Clean up old locks (when Casimir is not active)
  useEffect(() => {
    if (casimirActive) return; // Don't clean up during Casimir
    
    const interval = setInterval(() => {
      setPhaseLocks(prev => {
        const now = Date.now() / 1000;
        return prev.filter(lock => now - lock.timestamp < 3);
      });
    }, 100);
    return () => clearInterval(interval);
  }, [casimirActive]);

  const nodeNames = ['Observer', 'Tiger', 'Falcon', 'Dolphin', 'Hummingbird', 'Deer', 'Owl', 'Panda', 'CargoShip'];

  return (
    <Card className="p-6 bg-card border-border">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xl font-semibold text-foreground mb-2">
              🌀 Harmonic Nexus Phase Field (Tandem View)
            </h3>
            <p className="text-sm text-muted-foreground">
              {supabaseConfigured
                ? `Interactive 3D visualization with Casimir entanglement • ${historicalNodes.length} historical nodes loaded`
                : 'backend not configured'}
            </p>
          </div>
          {phaseLocks.length > 0 && (
            <Badge className="text-sm px-3 py-1" style={{ backgroundColor: '#00FF88' }}>
              🔒 {phaseLocks.length} Active Lock{phaseLocks.length !== 1 ? 's' : ''}
            </Badge>
          )}
        </div>

        {/* 3D Canvas */}
        <div className="h-[500px] bg-black/20 rounded-lg border border-border overflow-hidden">
          <Canvas camera={{ position: [8, 8, 12], fov: 50 }}>
            <ambientLight intensity={0.4} />
            <pointLight position={[10, 10, 10]} intensity={1.5} />
            <pointLight position={[-10, -10, -10]} intensity={0.8} />
            <pointLight position={[0, 10, 0]} intensity={1.0} color="#00FF88" />
            
            <PhaseFieldVisualization 
              amplitude={amplitude} 
              rotationSpeed={rotationSpeed}
              phaseLocks={phaseLocks}
              onPhaseLockDetected={handlePhaseLockDetected}
              casimirActive={casimirActive}
              casimirStrength={casimirStrength}
            />
            
            <OrbitControls 
              enablePan={true}
              enableZoom={true}
              enableRotate={true}
              minDistance={5}
              maxDistance={25}
            />
          </Canvas>
        </div>

        {/* Casimir Protocol Control */}
        <div className="p-4 bg-primary/10 rounded-lg border border-primary/30">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h4 className="text-sm font-semibold text-foreground flex items-center gap-2">
                ⚛️ Casimir Protocol
                {casimirActive && <Badge className="text-xs" style={{ backgroundColor: '#00FF88' }}>ACTIVE</Badge>}
              </h4>
              <p className="text-xs text-muted-foreground mt-1">
                Quantum vacuum energy field • Auto-activated with {historicalNodes.length} historical node entanglements
              </p>
            </div>
            <button
              onClick={casimirActive ? deactivateCasimirProtocol : activateCasimirProtocol}
              className={`px-4 py-2 rounded-lg font-semibold transition-all ${
                casimirActive 
                  ? 'bg-destructive hover:bg-destructive/80 text-white' 
                  : 'bg-primary hover:bg-primary/80 text-white'
              }`}
            >
              {casimirActive ? 'DEACTIVATE' : 'ACTIVATE'}
            </button>
          </div>
          {casimirActive && (
            <div className="mt-3">
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="text-muted-foreground">Field Strength</span>
                <span className="text-foreground font-mono">{(casimirStrength * 100).toFixed(1)}%</span>
              </div>
              <div className="h-2 bg-background/50 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-primary via-chart-2 to-chart-1 transition-all duration-300"
                  style={{ width: `${casimirStrength * 100}%` }}
                />
              </div>
            </div>
          )}
        </div>

        {/* Active Phase Locks Display */}
        {phaseLocks.length > 0 && (
          <div className="border border-border rounded-lg p-4 bg-black/10">
            <h4 className="text-sm font-semibold text-foreground mb-2">
              🔒 Active Phase Locks
            </h4>
            <div className="space-y-2">
              {phaseLocks.map((lock, idx) => (
                <div key={idx} className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">
                    {nodeNames[lock.nodes[0]]} ↔ {nodeNames[lock.nodes[1]]}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="text-primary font-mono">
                      {lock.resonanceFrequency.toFixed(2)} Hz
                    </span>
                    <div className="w-16 h-1.5 bg-secondary rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-primary transition-all"
                        style={{ width: `${lock.strength * 100}%` }}
                      />
                    </div>
                    <span className="text-muted-foreground font-mono">
                      {(lock.strength * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Controls */}
        <div className="space-y-4 border-t border-border pt-4">
          {/* Quantum Phase Lock Research */}
          <div className="mb-4">
            <h4 className="text-sm font-semibold mb-2 text-muted-foreground">Research: Quantum Phase-Locked Echoes</h4>
            <img 
              src={quantumPhaseLocks}
              alt="Quantum phase-locked echo states research"
              className="w-full rounded-lg border border-border/50"
            />
          </div>
          
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <Label htmlFor="amplitude" className="text-sm text-foreground">
                Field Amplitude
              </Label>
              <span className="text-sm text-muted-foreground">
                {amplitude.toFixed(2)}x
              </span>
            </div>
            <Slider
              id="amplitude"
              min={0}
              max={2}
              step={0.1}
              value={[amplitude]}
              onValueChange={(value) => setAmplitude(value[0])}
              className="w-full"
            />
          </div>

          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <Label htmlFor="rotation" className="text-sm text-foreground">
                Rotation Speed
              </Label>
              <span className="text-sm text-muted-foreground">
                {rotationSpeed.toFixed(2)}x
              </span>
            </div>
            <Slider
              id="rotation"
              min={0}
              max={1}
              step={0.05}
              value={[rotationSpeed]}
              onValueChange={(value) => setRotationSpeed(value[0])}
              className="w-full"
            />
          </div>
        </div>

        {/* Legend */}
        <div className="grid grid-cols-3 gap-2 border-t border-border pt-4">
          <div className="text-xs">
            <span className="inline-block w-3 h-3 rounded-full bg-[#9b87f5] mr-1" />
            <span className="text-muted-foreground">Observer Core</span>
          </div>
          <div className="text-xs">
            <span className="inline-block w-3 h-3 rounded-full bg-[#0EA5E9] mr-1" />
            <span className="text-muted-foreground">Inner Ring</span>
          </div>
          <div className="text-xs">
            <span className="inline-block w-3 h-3 rounded-full bg-[#10b981] mr-1" />
            <span className="text-muted-foreground">Outer Ring</span>
          </div>
        </div>
      </div>
    </Card>
  );
}
