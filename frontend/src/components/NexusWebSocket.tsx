// WebSocket hook and main dashboard component
import React, { useEffect, useRef, useState } from "react";
import { AurisMetrics, AuraMetrics } from "./NexusLiveDashboardComplete";

// ---------- WebSocket hook ----------
export function useAurisWS(url = "ws://localhost:8787"){
  const [connected, setConnected] = useState(false);
  const [auris, setAuris] = useState<AurisMetrics>({});
  const [aura,  setAura]  = useState<AuraMetrics>({});
  const wsRef = useRef<WebSocket|null>(null);
  
  useEffect(()=>{
    let alive = true;
    function connect(){
      const ws = new WebSocket(url);
      wsRef.current = ws;
      ws.onopen = () => setConnected(true);
      ws.onclose = () => { setConnected(false); if(alive) setTimeout(connect, 1200); };
      ws.onerror = () => { try{ws.close();}catch{} };
      ws.onmessage = (ev) => {
        try{
          const msg = JSON.parse(ev.data);
          if(msg?.type === 'auris_metrics') setAuris(msg.data||{});
          if(msg?.type === 'aura_features') setAura(msg.data||{});
        }catch{}
      };
    }
    connect();
    return ()=>{ alive=false; wsRef.current?.close(); };
  }, [url]);
  
  return {connected, auris, aura, wsCtl: wsRef};
}

// ---------- Controls Component ----------
export function HarmonicControls({onUpdate}: {onUpdate: (params: any) => void}) {
  const [gain, setGain] = useState(0.5);
  const [fundamental, setFundamental] = useState(7.83);
  const [intent, setIntent] = useState("validation love grounding");

  useEffect(() => {
    onUpdate({ gain, fundamental, intent });
  }, [gain, fundamental, intent, onUpdate]);

  return (
    <div className="bg-zinc-800/50 rounded-xl p-4 space-y-4">
      <h3 className="text-zinc-200 font-medium">Field Tuning</h3>
      
      <div className="space-y-2">
        <label className="text-sm text-zinc-300">Gain: {gain.toFixed(2)}</label>
        <input 
          type="range" 
          min="0" max="1" step="0.01" 
          value={gain}
          onChange={(e) => setGain(Number(e.target.value))}
          className="w-full"
        />
      </div>

      <div className="space-y-2">
        <label className="text-sm text-zinc-300">Fundamental: {fundamental} Hz</label>
        <input 
          type="range" 
          min="6" max="12" step="0.01" 
          value={fundamental}
          onChange={(e) => setFundamental(Number(e.target.value))}
          className="w-full"
        />
      </div>

      <div className="space-y-2">
        <label className="text-sm text-zinc-300">Intent</label>
        <input 
          type="text" 
          value={intent}
          onChange={(e) => setIntent(e.target.value)}
          className="w-full bg-zinc-700 text-zinc-200 px-3 py-2 rounded-lg"
          placeholder="validation love grounding"
        />
      </div>
      
      <button
        onClick={()=>{
          const payload = {
            type: "snapshot",
            at: new Date().toISOString(),
            controls: { gain, fundamental, intent },
          };
          // This would be handled by parent component with WebSocket reference
          console.log("Snapshot requested:", payload);
        }}
        className="mt-3 w-full px-3 py-2 rounded-xl bg-success hover:bg-success text-white transition-colors">
        Snapshot ⌘S
      </button>
    </div>
  );
}