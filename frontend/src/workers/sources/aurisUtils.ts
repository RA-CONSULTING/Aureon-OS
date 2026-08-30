import type { AurisClassification } from './aurisSandbox';
import { supabase } from '@/integrations/supabase/client';

const DEFAULT: AurisClassification = {
  valence: 0.5,
  arousal: 0.5,
  emotion: "neutral",
  tags: [],
};

/**
 * Mode B: authenticated server-side external-LLM fallback.
 * Provider credentials stay in Edge Function secrets and never enter Vite.
 */
export async function classifyViaOpenAI(texts: string[], opts?: Partial<RequestInit>): Promise<AurisClassification[]> {
  void opts;
  const { data, error } = await supabase.functions.invoke('auris-classify', {
    body: { texts },
  });
  if (error) throw error;
  return normalizeArray(Array.isArray(data?.items) ? data.items : [], texts.length);
}

export function normalizeArray(items: unknown[], expected: number): AurisClassification[] {
  const out: AurisClassification[] = [];
  for (let i = 0; i < expected; i++) {
    const raw = items?.[i] as any;
    const v = clamp01(toNumber(raw?.valence, 0.5));
    const a = clamp01(toNumber(raw?.arousal, 0.5));
    const emotion = (raw?.emotion ?? "neutral").toString();
    const tags = Array.isArray(raw?.tags) ? raw.tags.map((t: any) => String(t)).slice(0, 4) : [];
    out.push({ valence: v, arousal: a, emotion, tags, raw });
  }
  return out;
}

function toNumber(x: unknown, fb = 0): number {
  const n = typeof x === "number" ? x : typeof x === "string" ? Number(x) : NaN;
  return Number.isFinite(n) ? n : fb;
}

function clamp01(n: number): number { 
  return Math.max(0, Math.min(1, n)); 
}
