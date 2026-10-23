import crypto from "node:crypto";

const WANT = [
  "SUPABASE_URL","SUPABASE_ANON_KEY",
  "NOAA_CDO_TOKEN","NASA_API_KEY","USGS_API_KEY",
  "VITE_SUPABASE_URL","VITE_SUPABASE_ANON_KEY",
  "VITE_NOAA_CDO_TOKEN","VITE_NASA_API_KEY"
];

function mask(v){ return v ? `${v.slice(0,4)}…${v.slice(-4)} (len=${v.length})` : "(missing)"; }
function sha(v){ return v ? crypto.createHash("sha256").update(v).digest("hex") : null; }

const report = Object.fromEntries(WANT.map(k=>{
  const v = process.env[k] || "";
  return [k, { present: !!v, masked: mask(v), sha256: sha(v) }];
}));

console.log(JSON.stringify(report, null, 2));
