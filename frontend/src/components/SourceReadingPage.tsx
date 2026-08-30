'use client';
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Badge } from './ui/badge';
import { Separator } from './ui/separator';
import { supabase } from '@/integrations/supabase/client';

type Category = 'yes_no' | 'timing' | 'angel_message';
type ApiCard = { name: string; category: Category; oracle_summary: string; yes_no_value?: string; time_window?: string; border_color?: string; };
type TarotCard = { name: string; arcana: 'Major' | 'Minor'; upright: string; reversed: string; keywords: string[]; };
type ApiSpreadItem = { slot: string; card: ApiCard };
type TarotSpreadItem = { pos: string; card: TarotCard; reversed: boolean };
type AuraSpec = { primary: string; secondary?: string; traits: string[]; message: string; };
type ApiResponse = {
  ok: boolean; title: string; mode: 'distant'; question?: string; seed: number; count: number;
  angel: { spread: ApiSpreadItem[]; merged_nexus?: { field: string; value: string; support: number; examples: string[] }[]; };
  tarot: { spread: TarotSpreadItem[]; };
  aura: AuraSpec; synthesis: string; plan?: { day1: string[]; day2: string[]; day3: string[]; }; generated_at: string; timezone: string; error?: string;
};

const AURA_COLORS = [
  { value: 'gold', label: 'Gold', bg: 'bg-warning' },
  { value: 'white', label: 'White', bg: 'bg-gray-100' },
  { value: 'blue', label: 'Blue', bg: 'bg-primary' },
  { value: 'green', label: 'Green', bg: 'bg-success' },
  { value: 'purple', label: 'Purple', bg: 'bg-primary' },
  { value: 'red', label: 'Red', bg: 'bg-destructive' }
];

export default function SourceReadingPage() {
  const [question, setQuestion] = useState('');
  const [name, setName] = useState('');
  const [dob, setDob] = useState('');
  const [count, setCount] = useState(9);
  const [tarotSpread, setTarotSpread] = useState('three');
  const [auraColors, setAuraColors] = useState<string[]>([]);
  const [seed, setSeed] = useState<number | ''>('');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<ApiResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleColorToggle = (color: string) => {
    setAuraColors(prev => prev.includes(color) ? prev.filter(c => c !== color) : [...prev, color].slice(0, 2));
  };

  const runReading = async () => {
    setLoading(true); setError(null); setData(null);
    try {
      const { data: result, error: err } = await supabase.functions.invoke('source-reading', {
        body: { question: question || undefined, profile: { name, dob }, count, tarotSpread, auraColors: auraColors.length > 0 ? auraColors : undefined, seed: seed === '' ? undefined : Number(seed) }
      });
      if (err) throw err;
      if (!result.ok) throw new Error(result.error || 'Reading failed');
      setData(result);
    } catch (e: any) {
      setError(e?.message || 'Request failed');
    } finally {
      setLoading(false);
    }
  };

  const getBorderColor = (color?: string) => {
    switch (color) {
      case 'blue': return 'border-primary';
      case 'gold': return 'border-warning';
      case 'purple': return 'border-primary';
      default: return 'border-gray-300';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-warning to-white">
      <header className="sticky top-0 backdrop-blur bg-white/70 border-b border-black/5 z-10">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <h1 className="text-3xl font-bold tracking-tight">🔥 Reading from Source</h1>
          <p className="text-sm text-black/60 mt-1">Angel Answers × Harmonic Nexus × Aura Reading × Tarot × 72h Action Plan</p>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6 space-y-6">
        <Card>
          <CardHeader><CardTitle>Configure Your Reading</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div><Label htmlFor="question">Your Question (optional)</Label><Input id="question" value={question} onChange={e => setQuestion(e.target.value)} placeholder="What guidance do you seek?" /></div>
              <div><Label htmlFor="name">Your Name</Label><Input id="name" value={name} onChange={e => setName(e.target.value)} placeholder="For aura reading" /></div>
              <div><Label htmlFor="dob">Date of Birth</Label><Input id="dob" type="date" value={dob} onChange={e => setDob(e.target.value)} /></div>
              <div><Label htmlFor="seed">Seed (optional)</Label><Input id="seed" type="number" value={seed} onChange={e => setSeed(e.target.value === '' ? '' : Number(e.target.value))} placeholder="For reproducible readings" /></div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div><Label>Angel Cards Count</Label><Select value={count.toString()} onValueChange={v => setCount(Number(v))}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="9">9 Cards</SelectItem><SelectItem value="12">12 Cards</SelectItem></SelectContent></Select></div>
              <div><Label>Tarot Spread</Label><Select value={tarotSpread} onValueChange={setTarotSpread}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="three">3-Card Spread</SelectItem><SelectItem value="five">5-Card Spread</SelectItem><SelectItem value="ten">10-Card Celtic Cross</SelectItem></SelectContent></Select></div>
            </div>

            <div>
              <Label>Aura Colors (optional - select up to 2)</Label>
              <div className="flex flex-wrap gap-2 mt-2">
                {AURA_COLORS.map(color => (
                  <button key={color.value} onClick={() => handleColorToggle(color.value)} className={`px-3 py-2 rounded-lg border-2 transition-all ${auraColors.includes(color.value) ? 'border-black bg-black text-white' : 'border-gray-300 hover:border-gray-400'}`}>
                    <div className={`w-4 h-4 rounded-full ${color.bg} inline-block mr-2`} />{color.label}
                  </button>
                ))}
              </div>
            </div>

            <Button onClick={runReading} disabled={loading || !name || !dob} className="w-full">{loading ? 'Channeling...' : 'Begin Reading from Source'}</Button>
            {error && <div className="text-destructive text-sm p-3 bg-destructive rounded-lg">{error}</div>}
          </CardContent>
        </Card>

        {data && (
          <div className="space-y-6">
            {/* Aura Chips */}
            <Card>
              <CardHeader><CardTitle className="flex items-center gap-2"><div className={`w-6 h-6 rounded-full bg-${data.aura.primary}-400`} />Your Aura Reading</CardTitle></CardHeader>
              <CardContent>
                <div className="flex gap-2 mb-3">{data.aura.traits.map(trait => <Badge key={trait} variant="secondary">{trait}</Badge>)}</div>
                <p className="text-sm text-gray-600">{data.aura.message}</p>
              </CardContent>
            </Card>

            {/* Angel Cards with Badges */}
            <Card>
              <CardHeader><CardTitle>Angel Answers ({(data.angel?.spread || []).length} cards)</CardTitle></CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {(data.angel?.spread || []).map(item => (
                    <div key={item.slot} className={`p-4 rounded-lg border-2 ${getBorderColor(item.card.border_color)} bg-white`}>
                      <h4 className="font-semibold text-sm mb-2">{item.card.name}</h4>
                      <p className="text-xs text-gray-600 mb-2">{item.card.oracle_summary}</p>
                      {item.card.yes_no_value && <Badge className="text-xs">{item.card.yes_no_value}</Badge>}
                      {item.card.time_window && <Badge variant="outline" className="text-xs ml-1">{item.card.time_window}</Badge>}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Tarot Cards with Badges */}
            <Card>
              <CardHeader><CardTitle>Tarot ({(data.tarot?.spread || []).length} cards)</CardTitle></CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {(data.tarot?.spread || []).map((t, idx) => (
                    <div key={idx} className="rounded-xl border border-black/10 p-3">
                      <div className="text-xs uppercase tracking-wide text-black/50">{t.pos}</div>
                      <div className="mt-1 font-medium">{t.card.name}{t.reversed?" (reversed)":""}</div>
                      <div className="mt-1 text-xs text-black/60">Keywords: {t.card.keywords?.join(', ')}</div>
                      <div className="mt-1 text-sm text-black/70">{t.reversed? t.card.reversed : t.card.upright}</div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Merged Harmonic Nexus */}
            <Card>
              <CardHeader><CardTitle>Harmonic Nexus — Merged Map</CardTitle></CardHeader>
              <CardContent>
                {(() => {
                  const nexus = data.angel?.merged_nexus ?? (data as any)?.merged_nexus ?? [];
                  return Array.isArray(nexus) && nexus.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
                      {nexus.slice(0,12).map((n: any, i: number) => (
                        <div key={i} className="rounded-lg border border-black/10 p-2 flex items-center justify-between">
                          <div>
                            <div className="text-black/70">
                              <b>{String(n.field ?? 'field')}</b>: <span className="text-black/80">{String(n.value ?? '')}</span>
                            </div>
                            {n?.examples?.length ? (
                              <div className="text-xs text-black/50">ex: {n.examples.join(', ')}</div>
                            ) : null}
                          </div>
                          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-success border border-success">
                            support {Number(n.support ?? 0)}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-black/60">No nexus fields available.</p>
                  );
                })()}
              </CardContent>
            </Card>

            {/* 72-Hour Action Plan */}
            {data.plan && (
              <Card>
                <CardHeader><CardTitle>72-Hour Action Plan</CardTitle></CardHeader>
                <CardContent className="space-y-4">
                  <div className="rounded-xl border border-success bg-success p-3">
                    <div className="text-sm font-medium text-success mb-2">Day 1 (Today)</div>
                    <ul className="text-sm text-success space-y-1">
                      {data.plan.day1?.map((action: string, i: number) => <li key={i}>• {action}</li>)}
                    </ul>
                  </div>
                  <div className="rounded-xl border border-primary bg-primary p-3">
                    <div className="text-sm font-medium text-primary mb-2">Day 2 (Tomorrow)</div>
                    <ul className="text-sm text-primary space-y-1">
                      {data.plan.day2?.map((action: string, i: number) => <li key={i}>• {action}</li>)}
                    </ul>
                  </div>
                  <div className="rounded-xl border border-primary bg-primary p-3">
                    <div className="text-sm font-medium text-primary mb-2">Day 3 (72h Mark)</div>
                    <ul className="text-sm text-primary space-y-1">
                      {data.plan.day3?.map((action: string, i: number) => <li key={i}>• {action}</li>)}
                    </ul>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Enhanced Synthesis */}
            <Card>
              <CardHeader><CardTitle>Integrated Reading</CardTitle></CardHeader>
              <CardContent>
                <div className="bg-gray-50 p-4 rounded-lg border">
                  <pre className="text-sm leading-relaxed whitespace-pre-wrap">{data.synthesis}</pre>
                </div>
                <Separator className="my-4" />
                <div className="text-xs text-gray-500">
                  <p>Generated: {new Date(data.generated_at).toLocaleString()}</p>
                  <p>Timezone: {data.timezone} • Mode: {data.mode}</p>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </main>
    </div>
  );
}