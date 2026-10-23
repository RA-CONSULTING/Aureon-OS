export async function api<T>(path: string, params?: Record<string,string>): Promise<T> {
  const qs = params ? "?" + new URLSearchParams(params) : "";
  const r = await fetch(`/api/${path}${qs}`);
  if (!r.ok) throw new Error(`${path} ${r.status} ${await r.text()}`);
  return r.json() as Promise<T>;
}
