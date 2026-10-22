// GET /api/nasa-neo?start=2025-09-01&end=2025-09-08
export default async (req: Request) => {
  const key = process.env.NASA_API_KEY || "DEMO_KEY";
  const q = new URL(req.url).searchParams;
  const start = q.get("start") ?? "2025-09-01";
  const end   = q.get("end")   ?? "2025-09-08";
  const r = await fetch(`https://api.nasa.gov/neo/rest/v1/feed?start_date=${start}&end_date=${end}&api_key=${key}`);
  if (!r.ok) return new Response(JSON.stringify({ error: await r.text() }), { status: r.status });
  return new Response(await r.text(), { headers: { "content-type": "application/json" }});
};
