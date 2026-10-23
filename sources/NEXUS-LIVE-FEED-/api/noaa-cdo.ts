// GET /api/noaa-cdo?dataset=GHCND&location=FIPS:US&start=2025-01-01&end=2025-01-31
export default async (req: Request) => {
  const token = process.env.NOAA_CDO_TOKEN!;
  if (!token) return new Response(JSON.stringify({ error: "NOAA_CDO_TOKEN missing" }), { status: 500 });

  const q = new URL(req.url).searchParams;
  const params = new URLSearchParams({
    datasetid: q.get("dataset") ?? "GHCND",
    locationid: q.get("location") ?? "FIPS:US",
    startdate: q.get("start") ?? "2025-01-01",
    enddate: q.get("end") ?? "2025-01-31",
    limit: q.get("limit") ?? "1000",
  });

  const r = await fetch(`https://www.ncdc.noaa.gov/cdo-web/api/v2/data?${params}`, {
    headers: { token, accept: "application/json" }
  });
  if (!r.ok) return new Response(JSON.stringify({ error: await r.text() }), { status: r.status });
  return new Response(await r.text(), { headers: { "content-type": "application/json" }});
};
