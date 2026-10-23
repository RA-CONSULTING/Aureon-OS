export default function KeyStatus() {
  // Only boolean flags from server via build env → VITE_* (optional)
  const hasSupabase = !!import.meta.env.VITE_SUPABASE_URL && !!import.meta.env.VITE_SUPABASE_ANON_KEY;
  const flags = [
    { name: "Supabase", ok: hasSupabase },
    { name: "NOAA CDO", ok: !!import.meta.env.VITE_NOAA_CDO_TOKEN },
    { name: "NASA",     ok: !!import.meta.env.VITE_NASA_API_KEY },
    { name: "Clarity",  ok: true, value: 0.93 }, // Placeholder
  ];
  return (
    <div className="text-[11px] opacity-70">
      {flags.map(f => (
        <span key={f.name} className={`mr-3 ${f.ok ? "text-emerald-400" : "text-rose-400"}`}>
          {f.name}:{f.ok ? (f.value ? `${f.value}` : "OK") : "missing"}
        </span>
      ))}
    </div>
  );
}
