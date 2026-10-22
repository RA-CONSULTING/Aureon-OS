// netlify/functions/rss-proxy.ts
import type { Handler } from '@netlify/functions';

export const handler: Handler = async (event) => {
  const url = event.queryStringParameters?.url;
  if (!url) return { statusCode: 400, body: JSON.stringify({ error: 'Missing url' }) };

  try {
    const r = await fetch(url, { 
      headers: { 'user-agent': 'NewsProxy/1.0' },
      signal: AbortSignal.timeout(10000)
    });
    if (!r.ok) return { statusCode: r.status, body: JSON.stringify({ error: 'Upstream error' }) };

    const xml = await r.text();
    const items = [...xml.matchAll(/<item>([\s\S]*?)<\/item>/g)].slice(0, 25).map(m => {
      const b = m[1];
      const pick = (tag: string) => (b.match(new RegExp(`<${tag}>([\\s\\S]*?)<\\/${tag}>`, 'i')) || [])[1]?.trim();
      return { title: pick('title'), link: pick('link'), pubDate: pick('pubDate') };
    });

    return { 
      statusCode: 200, 
      headers: { 
        'cache-control': 'max-age=60',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET',
        'Access-Control-Allow-Headers': 'Content-Type'
      }, 
      body: JSON.stringify({ items }) 
    };
  } catch (error) {
    return { statusCode: 500, body: JSON.stringify({ error: 'Fetch failed' }) };
  }
};