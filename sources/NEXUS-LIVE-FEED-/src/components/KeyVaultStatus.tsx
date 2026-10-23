import { useEffect, useState } from "react";

type Status = Record<string, { present: boolean; masked: string }>;

export default function KeyVaultStatus() {
  const [data, setData] = useState<Status| null>(null);
  const [err, setErr]   = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/keys-status")
      .then(r => r.json())
      .then(setData)
      .catch(e => setErr(String(e)));
  }, []);

  if (err) return <div className="text-rose-400 text-xs">Key status error: {err}</div>;
  if (!data) return <div className="text-xs opacity-70">Checking keys…</div>;

  return (
    <div className="p-3 rounded-xl bg-black/40 border border-white/10 text-xs space-y-1">
      {Object.entries(data).map(([k, v]) => (
        <div key={k} className="flex items-center justify-between">
          <span className="opacity-80">{k}</span>
          <span className={v.present ? "text-emerald-400" : "text-rose-400"}>
            {v.masked}
          </span>
        </div>
      ))}
      <div className="mt-2 text-[10px] opacity-60">
        Values are masked. Rotate keys if compromised.
      </div>
    </div>
  );
}
