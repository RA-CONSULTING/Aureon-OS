import React from "react";
import {
  AAI, scanAAI, resample,
  startPingPong, setAM, setCarrier, stopPingPong,
  type Stream
} from "@/lib/akashic/aureon-akashic";

export const AkashicMappingStudio: React.FC = () => {
  const [pp, setPP] = React.useState<ReturnType<typeof startPingPong> | null>(null);
  const [carrier, setCarrierHz] = React.useState(432);
  const [am, setAmHz] = React.useState(0.10); // start near 0.1 Hz (6 breaths/min)
  const [status, setStatus] = React.useState<"IDLE"|"LIVE">("IDLE");

  // Demo streams if you don't have sensors wired yet
  const t0 = React.useMemo(()=>Date.now()/1000,[]);
  const demoBreath: Stream = React.useMemo(()=>{
    // synthetic slow breath ~0.11 Hz with slight noise
    const out: Stream = [];
    const dur = 180, dt=0.25;
    for (let k=0;k<dur/dt;k++){
      const t = t0 + k*dt;
      const v = Math.sin(2*Math.PI*0.11*(t-t0)) + 0.1*Math.random();
      out.push({ t, v });
    }
    return out;
  },[t0]);
  const demoHRV: Stream = React.useMemo(()=>{
    const out: Stream = [];
    const dur = 180, dt=0.25;
    for (let k=0;k<dur/dt;k++){
      const t = t0 + k*dt;
      const v = Math.sin(2*Math.PI*0.11*(t-t0)+0.2) * 0.8 + 0.1*Math.random();
      out.push({ t, v });
    }
    return out;
  },[t0]);

  const [bestF, setBestF] = React.useState<number|null>(null);
  const [bestAAI, setBestAAI] = React.useState<number|null>(null);
  const [lastAAI, setLastAAI] = React.useState<number>(0);

  const enable = async () => {
    const ctx = startPingPong(carrier, am, 0.12);
    await ctx.ctx.resume();
    setPP(ctx); setStatus("LIVE");
  };
  const disable = () => { if (pp) stopPingPong(pp); setPP(null); setStatus("IDLE"); };

  const onCarrier = (hz:number) => { setCarrierHz(hz); if (pp) setCarrier(pp, hz); };
  const onAM = (hz:number) => { setAmHz(hz); if (pp) setAM(pp, hz); };

  // Live AAI readout using demo streams (replace with real sensors as arrays of {t,v})
  React.useEffect(()=>{
    const id = setInterval(()=>{
      const breath = resample(demoBreath, 0.25);
      const hrv    = resample(demoHRV, 0.25);
      const { score } = AAI({ f: am, breath, hrv });
      setLastAAI(score);
    }, 1000);
    return ()=>clearInterval(id);
  },[am, demoBreath, demoHRV]);

  const runScan = () => {
    const breath = resample(demoBreath, 0.25);
    const hrv    = resample(demoHRV, 0.25);
    const { bestF: f, bestAAI: a } = scanAAI({ breath, hrv }, 0.05, 12, 72);
    setBestF(f); setBestAAI(a);
    if (pp) setAM(pp, f);
    setAmHz(f);
  };

  return (
    <div className="grid lg:grid-cols-2 gap-6">
      <div className="rounded-2xl border border-white/10 bg-slate-950/70 p-4">
        <div className="text-sm font-semibold mb-2">Akashic Mapping — Mirror Ping-Pong Driver</div>
        <div className="flex gap-2 mb-3">
          {status==="IDLE" ? (
            <button onClick={enable} className="px-3 py-1.5 rounded-lg border border-cyan-500/50 text-cyan-200 hover:bg-cyan-500/10">
              Enable Audio
            </button>
          ) : (
            <button onClick={disable} className="px-3 py-1.5 rounded-lg border border-rose-500/50 text-rose-200 hover:bg-rose-500/10">
              Stop
            </button>
          )}
          <button onClick={runScan} className="px-3 py-1.5 rounded-lg border border-emerald-500/50 text-emerald-200 hover:bg-emerald-500/10">
            Scan & Map
          </button>
        </div>

        <label className="text-xs opacity-70">Carrier (Hz)</label>
        <input type="range" min={64} max={1024} step={1} value={carrier}
          onChange={e=>onCarrier(Number(e.target.value))} className="w-full" />
        <div className="text-xs mb-2">Carrier: <b>{carrier.toFixed(0)} Hz</b></div>

        <label className="text-xs opacity-70">Ping-Pong Modulation (Hz)</label>
        <input type="range" min={0.05} max={12} step={0.01} value={am}
          onChange={e=>onAM(Number(e.target.value))} className="w-full" />
        <div className="text-xs">AM: <b>{am.toFixed(2)} Hz</b> | Live AAI: <b>{lastAAI.toFixed(3)}</b></div>
      </div>

      <div className="rounded-2xl border border-white/10 bg-slate-950/70 p-4">
        <div className="text-sm font-semibold mb-2">Akashic Map</div>
        <div className="text-xs opacity-70 mb-2">
          Best frequency f* = where AAI is maximal during focused intent.
        </div>
        <div className="text-sm">
          {bestF
            ? <>Mapped <b>f* = {bestF.toFixed(3)} Hz</b> with AAI = <b>{(bestAAI ?? 0).toFixed(3)}</b>. Saved to session.</>
            : <>Run <i>Scan & Map</i> while holding your intent.</>}
        </div>
        <ul className="mt-3 text-xs list-disc list-inside opacity-80">
          <li>Breathe gently (≈0.1 Hz). Keep attention on your intention (the “record”).</li>
          <li>Let the L/R ping-pong guide hemispheric balance; notice stillness when it “locks.”</li>
          <li>Repeat scans on different days; stable peaks form your Akashic signature band.</li>
        </ul>
      </div>
    </div>
  );
};

export default AkashicMappingStudio;
