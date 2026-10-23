// GET /api/jpl-horizons?command=399&start=2025-09-08&stop=2025-09-09&step=1%20d
export default async (req: Request) => {
  const q = new URL(req.url).searchParams;
  const params = new URLSearchParams({
    format: "json", COMMAND: `'${q.get("command") ?? "399"}'`, CENTER: "'0'",
    MAKE_EPHEM: "'YES'", TABLE_TYPE: "'VECTORS'", OUT_UNITS: "'KM-S'",
    START_TIME: `'${q.get("start") ?? "2025-09-08"}'`,
    STOP_TIME:  `'${q.get("stop")  ?? "2025-09-09"}'`,
    STEP_SIZE:  `'${q.get("step")  ?? "1 d"}'`
  });
  const r = await fetch(`https://ssd.jpl.nasa.gov/api/horizons.api?${params}`);
  if (!r.ok) return new Response(JSON.stringify({ error: await r.text() }), { status: r.status });
  return new Response(await r.text(), { headers: { "content-type": "application/json" }});
};
