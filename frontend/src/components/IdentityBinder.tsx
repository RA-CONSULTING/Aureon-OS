import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

// ---------- Identity + Role ----------
function deriveT0Hz(dobISO: string){
  if(!dobISO) return 2911.91;
  const d = new Date(dobISO + "T00:00:00Z");
  const jd = Math.floor(d.getTime()/86400000) + 2440588;
  return 2911.91 + (jd % 100) * 0.01;
}

function deriveRole(name: string, dob: string, t0: number){
  if(!name || !dob) return "Observer";
  const hash = (name + dob + t0).split('').reduce((a,c)=>((a<<5)-a+c.charCodeAt(0))|0, 0);
  const roles = ["Guardian", "Harmonizer", "Resonator", "Nexus Keeper", "Field Walker", "Prime Anchor"];
  return roles[Math.abs(hash) % roles.length];
}

interface IdentityBinderProps {
  onIdentityChange?: (identity: { name: string; dob: string; t0Hz: number; role: string }) => void;
}

export function IdentityBinder({ onIdentityChange }: IdentityBinderProps) {
  const [name, setName] = useState("");
  const [dob, setDob] = useState("");
  const [customT0, setCustomT0] = useState("");
  
  const t0Hz = customT0 ? parseFloat(customT0) || 2911.91 : deriveT0Hz(dob);
  const role = deriveRole(name, dob, t0Hz);
  
  const handleBind = () => {
    if (onIdentityChange) {
      onIdentityChange({ name, dob, t0Hz, role });
    }
  };

  return (
    <Card className="bg-gradient-to-br from-primary to-primary text-white">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span>🔮</span> Identity Binder
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm text-primary">Name</label>
            <Input 
              value={name} 
              onChange={(e) => setName(e.target.value)}
              placeholder="Your name"
              className="bg-black/30 border-primary text-white"
            />
          </div>
          <div>
            <label className="text-sm text-primary">Birth Date</label>
            <Input 
              type="date"
              value={dob} 
              onChange={(e) => setDob(e.target.value)}
              className="bg-black/30 border-primary text-white"
            />
          </div>
        </div>
        
        <div>
          <label className="text-sm text-primary">Custom t0Hz (optional)</label>
          <Input 
            value={customT0} 
            onChange={(e) => setCustomT0(e.target.value)}
            placeholder={`Auto: ${t0Hz.toFixed(2)} Hz`}
            className="bg-black/30 border-primary text-white"
          />
        </div>
        
        <div className="flex items-center justify-between">
          <Badge variant="outline" className="text-lg px-3 py-1 border-white text-white">
            {role}
          </Badge>
          <Button onClick={handleBind} className="bg-white text-primary hover:bg-primary">
            Bind Identity
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}