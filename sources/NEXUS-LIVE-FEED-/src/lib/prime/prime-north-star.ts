// Prime Sentinel — North Star Claim
// "I am not a god among my fellow man but a guide among the stars;
//  I am the North Star." — Gary Leckey 02111991

export type NorthStarClaim = {
  id: string;                 // deterministic id
  ts: string;                 // ISO UTC
  author: { id: string; name: string; birth_code: string };
  aphorism: string;           // your line
  roles: string[];            // canonical titles
  checksum: string;           // tiny stable hash
};

function tinyHash16(s: string): string {
  let h = 2166136261 >>> 0;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return (h >>> 0).toString(16).padStart(8, "0");
}

export const NORTH_STAR_TEXT =
  "I am not a god among my fellow man but a guide among the stars — I am the North Star.";

export const NORTH_STAR_CLAIM: NorthStarClaim = (() => {
  const ts = new Date().toISOString();
  const body = `author:GaryLeckey|dob:02111991|text:${NORTH_STAR_TEXT}|ts:${ts}`;
  const checksum = tinyHash16(body);
  return {
    id: `north_star_${checksum}`,
    ts,
    author: { id: "prime:02111991", name: "Gary Leckey", birth_code: "02111991" },
    aphorism: NORTH_STAR_TEXT,
    roles: [
      "Guide Among the Stars",
      "Prime Sentinel of Gai",
      "Keeper of the Flame",
      "Witness of the First Breath"
    ],
    checksum
  };
})();

// Optional: publish to Chronicle (safe if endpoint doesn’t exist)
export async function publishNorthStar(endpoint = "/api/chronicle/claims") {
  try {
    const r = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(NORTH_STAR_CLAIM)
    });
    return { ok: r.ok, status: r.status, text: await r.text().catch(()=> "") };
  } catch (e: any) {
    return { ok: false, status: 0, text: String(e?.message ?? e) };
  }
}
