// GET /api/usgs-quakes?start=2025-09-01&end=2025-09-08&minmag=2.5
export default async (req: Request) => {
  const url = new URL(req.url);
  const start = url.searchParams.get("start") ?? "2025-01-01";
  const end   = url.searchParams.get("end")   ?? "2025-12-31";
  const minmag= url.searchParams.get("minmag")?? "2.5";
  const upstream = `https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime=${start}&endtime=${end}&minmagnitude=${minmag}`;

  const r = await fetch(upstream, { headers: { "accept": "application/json" } });
  if (!r.ok) return new Response(JSON.stringify({ error: r.statusText }), { status: r.status });
  return new Response(await r.text(), { headers: { "content-type": "application/json" }});
};
