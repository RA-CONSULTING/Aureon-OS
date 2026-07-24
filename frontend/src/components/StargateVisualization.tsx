import { useEffect, useRef, useState, Suspense } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Sphere, Line } from '@react-three/drei';
import * as THREE from 'three';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { stargateLayer, type StargateNode, type StargateActivation } from '@/core/stargateLattice';
import { useSentinelConfig } from '@/hooks/useSentinelConfig';
import { useStargateNetwork } from '@/hooks/useStargateNetwork';

// Convert lat/lng to 3D sphere coordinates
const latLngToVector3 = (lat: number, lng: number, radius: number = 5) => {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lng + 180) * (Math.PI / 180);
  
  return new THREE.Vector3(
    -radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta)
  );
};

interface MarkerProps {
  node: StargateNode;
  isSelected: boolean;
  onClick: () => void;
  activation?: StargateActivation;
}

function StargateMarker({ node, isSelected, onClick, activation }: MarkerProps) {
  const meshRef = useRef<THREE.Mesh>(null);
  const position = latLngToVector3(node.coordinates.lat, node.coordinates.lng, 5.1);
  
  useFrame((state) => {
    if (meshRef.current) {
      const time = state.clock.getElapsedTime();
      const pulse = Math.sin(time * 2) * 0.2 + 1;
      const activationBoost = activation ? activation.coherence : 0.7;
      meshRef.current.scale.setScalar(pulse * (isSelected ? 1.5 : 1) * activationBoost);
    }
  });

  return (
    <group>
      <mesh ref={meshRef} position={position} onClick={onClick}>
        <sphereGeometry args={[0.15, 16, 16]} />
        <meshStandardMaterial 
          color={activation?.status === 'ACTIVE' ? "#00ff88" : (isSelected ? "#00ff88" : "#00ffff")} 
          emissive={activation?.status === 'ACTIVE' ? "#00ff88" : (isSelected ? "#00ff88" : "#00ffff")}
          emissiveIntensity={activation ? (activation.coherence * 3) : (isSelected ? 2 : 1)}
          transparent
          opacity={0.8}
        />
      </mesh>
      
      {/* Frequency ring for active nodes */}
      {activation && (
        <mesh position={position} rotation={[Math.PI / 2, 0, 0]}>
          <torusGeometry args={[0.3, 0.02, 8, 32]} />
          <meshStandardMaterial 
            color="#00ff88" 
            emissive="#00ff88"
            emissiveIntensity={activation.coherence * 2}
            transparent
            opacity={0.6}
          />
        </mesh>
      )}
    </group>
  );
}

// Ley lines connecting nodes
function LeyLines({ nodes }: { nodes: StargateNode[] }) {
  const connections: [THREE.Vector3, THREE.Vector3][] = [];
  
  // Connect primary trinity
  const stonehenge = nodes.find(n => n.name === 'Stonehenge');
  const giza = nodes.find(n => n.name === 'Giza Pyramids');
  const uluru = nodes.find(n => n.name === 'Uluru');
  
  if (stonehenge && giza && uluru) {
    const pos1 = latLngToVector3(stonehenge.coordinates.lat, stonehenge.coordinates.lng);
    const pos2 = latLngToVector3(giza.coordinates.lat, giza.coordinates.lng);
    const pos3 = latLngToVector3(uluru.coordinates.lat, uluru.coordinates.lng);
    connections.push([pos1, pos2], [pos2, pos3], [pos3, pos1]);
  }

  return (
    <>
      {connections.map((points, i) => (
        <Line
          key={i}
          points={points}
          color="#00ffff"
          lineWidth={2}
          transparent
          opacity={0.3}
        />
      ))}
    </>
  );
}

// Earth sphere
function Earth() {
  const meshRef = useRef<THREE.Mesh>(null);
  
  useFrame(() => {
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.001;
    }
  });

  return (
    <Sphere ref={meshRef} args={[5, 64, 64]}>
      <meshStandardMaterial
        color="#1a1a2e"
        emissive="#0a0a1e"
        roughness={0.8}
        metalness={0.2}
        wireframe
      />
    </Sphere>
  );
}

// Energy field
function EnergyField() {
  const meshRef = useRef<THREE.Mesh>(null);
  
  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.0005;
      const scale = 1 + Math.sin(state.clock.getElapsedTime() * 0.5) * 0.05;
      meshRef.current.scale.setScalar(scale);
    }
  });

  return (
    <Sphere ref={meshRef} args={[5.3, 32, 32]}>
      <meshStandardMaterial
        color="#00ffff"
        emissive="#00ffff"
        emissiveIntensity={0.2}
        transparent
        opacity={0.1}
        wireframe
      />
    </Sphere>
  );
}

interface SceneProps {
  nodes: StargateNode[];
  activations: StargateActivation[];
  selectedNode: string | null;
  onNodeClick: (name: string) => void;
}

function Scene({ nodes, activations, selectedNode, onNodeClick }: SceneProps) {
  return (
    <>
      <ambientLight intensity={0.3} />
      <pointLight position={[10, 10, 10]} intensity={1} />
      <pointLight position={[-10, -10, -10]} intensity={0.5} />
      
      <Suspense fallback={null}>
        <Earth />
        <EnergyField />
        <LeyLines nodes={nodes} />
        {nodes.map((node) => {
          const activation = activations.find(a => a.nodeName.toLowerCase().includes(node.name.toLowerCase()));
          return (
            <StargateMarker 
              key={node.name}
              node={node} 
              isSelected={selectedNode === node.name}
              onClick={() => onNodeClick(node.name)}
              activation={activation}
            />
          );
        })}
      </Suspense>
      
      <OrbitControls 
        enableZoom 
        enablePan={false}
        minDistance={8}
        maxDistance={15}
      />
    </>
  );
}

export function StargateVisualization() {
  const { config } = useSentinelConfig();
  const { activations, metrics, isActive } = useStargateNetwork();
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const nodes = stargateLayer.getAllNodes();
  const gridEnergy = stargateLayer.calculateGridEnergy();

  return (
    <Card className="bg-card shadow-card">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <span className="text-2xl">🌍</span>
              Stargate Lattice Network
            </CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              12-node planetary sacred geometry grid
            </p>
            {config && (
              <div className="mt-2 px-3 py-2 rounded-lg bg-primary/10 border border-primary/30">
                <p className="text-xs font-semibold text-primary flex items-center gap-2">
                  <span>⚡</span>
                  {config.sentinel_title}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Stargate Locked: {config.stargate_location}
                </p>
              </div>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-[500px] rounded-lg overflow-hidden border border-border bg-background/50 mb-6">
          <Canvas camera={{ position: [0, 0, 12], fov: 50 }}>
            <Scene 
              nodes={nodes} 
              activations={activations}
              selectedNode={selectedNode}
              onNodeClick={setSelectedNode}
            />
          </Canvas>
        </div>
        
        <div className="space-y-6">
          {/* Network Status */}
          <div className="flex items-center gap-2 text-sm">
            <div className={`w-2 h-2 rounded-full ${isActive ? 'bg-success animate-pulse' : 'bg-gray-500'}`} />
            <span className="text-muted-foreground">
              {isActive ? 'Live Network Pinging' : 'Network Offline'}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs text-muted-foreground">Active Nodes</div>
              <div className="text-2xl font-bold text-primary">
                {metrics?.activeNodes || 0}/{metrics?.totalNodes || 12}
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Grid Energy</div>
              <div className="text-2xl font-bold text-primary">{(gridEnergy * 100).toFixed(1)}%</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Avg Coherence</div>
              <div className="text-2xl font-bold text-primary">
                {metrics ? (metrics.avgCoherence * 100).toFixed(1) : '0'}%
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Network Strength</div>
              <div className="text-2xl font-bold text-primary">
                {metrics ? (metrics.networkStrength * 100).toFixed(1) : '0'}%
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Avg Latency</div>
              <div className="text-2xl font-bold text-primary">
                {metrics?.avgLatency.toFixed(0) || '0'}ms
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Energy Flow</div>
              <div className="text-2xl font-bold text-primary">
                {metrics ? (metrics.avgEnergyFlow * 100).toFixed(1) : '0'}%
              </div>
            </div>
          </div>

          <div className="text-xs text-muted-foreground space-y-2">
            <p>• 12-Node Planetary Grid</p>
            <p>• Continuous Live Pinging (2s interval)</p>
            <p>• Primelines Protocol Integration</p>
            <p>• Real-Time Coherence Monitoring</p>
            <p>• Multi-Frequency Resonance Lock</p>
          </div>

          {/* Live Node Status */}
          {activations.length > 0 && (
            <div className="space-y-2">
              <div className="text-sm font-medium">Live Node Status</div>
              <div className="grid grid-cols-2 gap-2 max-h-40 overflow-y-auto">
                {activations.slice(0, 6).map((activation) => (
                  <div key={activation.nodeName} className="text-xs p-2 bg-background/50 rounded">
                    <div className="font-medium">{activation.nodeName}</div>
                    <div className="text-muted-foreground">
                      {(activation.coherence * 100).toFixed(0)}% • {activation.pingLatency.toFixed(0)}ms
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};
