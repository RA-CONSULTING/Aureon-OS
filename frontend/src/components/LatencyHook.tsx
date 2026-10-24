// Heartbeat + Latency Hook for Nexus Live Dashboard
import { useEffect, useState, useRef } from "react";

import { bridgeWsUrl } from "@/config/serviceEndpoints";

export function useLatency(wsUrl = bridgeWsUrl){
  const [latencyMs, setLatency] = useState<number | null>(null);
  const wsRef = useRef<WebSocket|null>(null);

  useEffect(()=>{
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;
    let timer: any;

    ws.onopen = ()=>{
      timer = setInterval(()=>{
        const t0 = performance.now();
        ws.send(JSON.stringify({type:"ping", t0}));
      }, 1000);
    };
    
    ws.onmessage = (ev)=>{
      try{
        const msg = JSON.parse(ev.data);
        if (msg?.type === "pong" && typeof msg.t0 === "number"){
          const dt = performance.now() - msg.t0;
          setLatency(Math.round(dt));
        }
      }catch{}
    };
    
    ws.onerror = () => setLatency(null);
    ws.onclose = () => setLatency(null);
    
    return ()=>{ 
      try{clearInterval(timer)}catch{}; 
      try{ws.close()}catch{} 
    };
  }, [wsUrl]);

  return latencyMs;
}