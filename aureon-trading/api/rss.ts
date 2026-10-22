// api/rss.ts - Vercel-style API route
export default async function handler(req: Request): Promise<Response> {
  const { searchParams } = new URL(req.url);
  const url = searchParams.get('url');
  if (!url) return new Response(JSON.stringify({ error: 'Missing url' }), { status: 400 });

  try {
    const upstream = await fetch(url, { 
      headers: { 'user-agent': 'NewsProxy/1.0' },
      signal: AbortSignal.timeout(10000) // 10s timeout
    });
    if (!upstream.ok) return new Response(JSON.stringify({ error: 'Upstream error' }), { status: upstream.status });

    const xml = await upstream.text();
    const items = [...xml.matchAll(/<item>([\s\S]*?)<\/item>/g)].slice(0, 25).map(m => {
      const b = m[1];
      const pick = (tag: string) => (b.match(new RegExp(`<${tag}>([\\s\\S]*?)<\\/${tag}>`, 'i')) || [])[1]?.trim();
      return { title: pick('title'), link: pick('link'), pubDate: pick('pubDate') };
    });

    return Response.json({ items }, { 
      headers: { 
        'Cache-Control': 'max-age=60',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET',
        'Access-Control-Allow-Headers': 'Content-Type'
      } 
    });
  } catch (error) {
    return new Response(JSON.stringify({ error: 'Fetch failed' }), { status: 500 });
  }
}