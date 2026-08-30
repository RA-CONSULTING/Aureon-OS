import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface PrimeRatio {
  numerator: number;
  denominator: number;
  frequency: number;
}

interface HelixStrand {
  x: number;
  y: number;
  z: number;
  frequency: number;
}

// Prime generator function
function* primeGenerator(): Generator<number, never, unknown> {
  yield 2;
  const primes: number[] = [2];
  let candidate = 3;
  
  while (true) {
    let isPrime = true;
    const sqrtCandidate = Math.sqrt(candidate);
    
    for (const prime of primes) {
      if (prime > sqrtCandidate) break;
      if (candidate % prime === 0) {
        isPrime = false;
        break;
      }
    }
    
    if (isPrime) {
      primes.push(candidate);
      yield candidate;
    }
    candidate += 2;
  }
}

const PrimeDNAHelix: React.FC = () => {
  const [isActive, setIsActive] = useState(false);
  const [primeRatios, setPrimeRatios] = useState<PrimeRatio[]>([]);
  const [leftStrand, setLeftStrand] = useState<HelixStrand[]>([]);
  const [rightStrand, setRightStrand] = useState<HelixStrand[]>([]);
  const [rotationPhase, setRotationPhase] = useState(0);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Generate prime ratios
  useEffect(() => {
    const generator = primeGenerator();
    const primes: number[] = [];
    
    for (let i = 0; i < 19; i++) {
      primes.push(generator.next().value);
    }
    
    const ratios: PrimeRatio[] = [];
    for (let i = 0; i < primes.length - 1; i++) {
      const numerator = primes[i];
      const denominator = primes[i + 1];
      ratios.push({
        numerator,
        denominator,
        frequency: numerator / denominator
      });
    }
    
    setPrimeRatios(ratios);
    
    // Build DNA helix strands
    const left: HelixStrand[] = [];
    const right: HelixStrand[] = [];
    
    ratios.forEach((ratio, i) => {
      const phase = i * Math.PI / 3; // twist spacing
      const freq = ratio.frequency;
      
      left.push({
        x: Math.cos(phase),
        y: Math.sin(phase),
        z: i,
        frequency: freq
      });
      
      right.push({
        x: -Math.cos(phase),
        y: -Math.sin(phase),
        z: i,
        frequency: freq
      });
    });
    
    setLeftStrand(left);
    setRightStrand(right);
  }, []);

  // Animation loop
  useEffect(() => {
    if (!isActive) return;
    
    const interval = setInterval(() => {
      setRotationPhase(prev => prev + 0.02);
    }, 16);
    
    return () => clearInterval(interval);
  }, [isActive]);

  // Canvas rendering
  useEffect(() => {
    if (!canvasRef.current || leftStrand.length === 0) return;
    
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const scale = 80;
    const zScale = 15;
    
    // Draw connections between strands
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
    ctx.lineWidth = 1;
    
    for (let i = 0; i < Math.min(leftStrand.length, rightStrand.length); i++) {
      const left = leftStrand[i];
      const right = rightStrand[i];
      
      const leftX = centerX + (left.x * Math.cos(rotationPhase) - left.y * Math.sin(rotationPhase)) * scale;
      const leftY = centerY + left.z * zScale - 150;
      const rightX = centerX + (right.x * Math.cos(rotationPhase) - right.y * Math.sin(rotationPhase)) * scale;
      const rightY = centerY + right.z * zScale - 150;
      
      ctx.beginPath();
      ctx.moveTo(leftX, leftY);
      ctx.lineTo(rightX, rightY);
      ctx.stroke();
    }
    
    // Draw left strand (gold)
    ctx.strokeStyle = '#FFD700';
    ctx.lineWidth = 3;
    ctx.beginPath();
    
    leftStrand.forEach((point, i) => {
      const x = centerX + (point.x * Math.cos(rotationPhase) - point.y * Math.sin(rotationPhase)) * scale;
      const y = centerY + point.z * zScale - 150;
      
      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
      
      // Draw frequency nodes
      ctx.fillStyle = `hsl(${point.frequency * 360}, 70%, 60%)`;
      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fill();
    });
    ctx.stroke();
    
    // Draw right strand (blue)
    ctx.strokeStyle = '#4A90E2';
    ctx.lineWidth = 3;
    ctx.beginPath();
    
    rightStrand.forEach((point, i) => {
      const x = centerX + (point.x * Math.cos(rotationPhase) - point.y * Math.sin(rotationPhase)) * scale;
      const y = centerY + point.z * zScale - 150;
      
      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
      
      // Draw frequency nodes
      ctx.fillStyle = `hsl(${240 + point.frequency * 60}, 70%, 60%)`;
      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fill();
    });
    ctx.stroke();
    
  }, [leftStrand, rightStrand, rotationPhase]);

  return (
    <Card className="bg-black/50 border-warning">
      <CardHeader>
        <CardTitle className="text-warning text-center text-2xl">
          PRIME DNA HELIX
        </CardTitle>
        <div className="text-center text-warning text-sm">
          String Vibration Model • Prime Ratio Frequencies
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex justify-center mb-4">
          <Button
            onClick={() => setIsActive(!isActive)}
            className={`${isActive ? 'bg-destructive hover:bg-destructive' : 'bg-warning hover:bg-warning'} text-white`}
          >
            {isActive ? 'STOP ROTATION' : 'START ROTATION'}
          </Button>
        </div>
        
        <canvas
          ref={canvasRef}
          width={600}
          height={400}
          className="w-full border border-warning rounded mb-4"
        />
        
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="text-center">
            <Badge className="bg-warning text-black mb-2">Left Strand (Gold)</Badge>
            <div className="text-sm text-warning">Prime Numerators</div>
          </div>
          <div className="text-center">
            <Badge className="bg-primary text-white mb-2">Right Strand (Blue)</Badge>
            <div className="text-sm text-primary">Prime Denominators</div>
          </div>
        </div>
        
        <div className="text-center text-warning text-sm">
          Active Prime Ratios: {primeRatios.length} • Phase: {rotationPhase.toFixed(3)} rad
        </div>
      </CardContent>
    </Card>
  );
};

export { PrimeDNAHelix };
export default PrimeDNAHelix;