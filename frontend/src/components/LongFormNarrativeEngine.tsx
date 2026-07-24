import React, { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Badge } from '@/components/ui/badge';

interface NarrativeControls {
  voice: 'mythic' | 'plain' | 'dual';
  lengthTarget: number;
  sectionWeights: {
    origins: number;
    present: number;
    futures: number;
    unity: number;
  };
}

interface AuraData {
  name: string;
  archetype: { primary: string; secondary: string };
  karmic: { motifs: string[] };
  strengths: string[];
  challenges: string[];
  colors: Record<string, number>;
  chakra: Record<string, number>;
  crossroad: { theme: string };
  confidence: number;
  timelines: {
    aligned: { likelihood: number; outcomes: string[]; drivers: string[] };
    middle: { likelihood: number; outcomes: string[]; drivers: string[] };
    resistant: { likelihood: number; outcomes: string[]; drivers: string[] };
  };
  practices: Record<string, number>;
  cosmic?: { note: string };
  earth?: { note: string };
}

interface LongFormNarrativeEngineProps {
  auraData: AuraData;
  qaid: string;
}

export function LongFormNarrativeEngine({ auraData, qaid }: LongFormNarrativeEngineProps) {
  const [controls, setControls] = useState<NarrativeControls>({
    voice: 'mythic',
    lengthTarget: 1200,
    sectionWeights: { origins: 0.25, present: 0.25, futures: 0.35, unity: 0.15 }
  });

  const [isGenerating, setIsGenerating] = useState(false);
  const [lastGenerated, setLastGenerated] = useState<{ timestamp: number; wordCount: number } | null>(null);

  // Deterministic paragraph size based on QAID
  const getParagraphSize = (sectionIndex: number, paragraphIndex: number): number => {
    const seed = qaid + sectionIndex + paragraphIndex;
    const hash = Array.from(seed).reduce((a, b) => ((a << 5) - a + b.charCodeAt(0)) | 0, 0);
    return 80 + (Math.abs(hash) % 51); // 80-130 words
  };

  const formatPercentage = (value: number): string => `${Math.round(value * 100)}%`;

  const humanizeCrossroad = (theme: string): string => {
    const map: Record<string, string> = {
      'comfort_vs_growth': 'comfort vs. growth',
      'control_vs_trust': 'control vs. trust',
      'silence_vs_voice': 'staying quiet vs. speaking up',
      'guarding_vs_opening': 'guarding the heart vs. opening to love'
    };
    return map[theme] || theme;
  };

  const getTopColors = (): { color: string; value: number; desc: string }[] => {
    const colorDescs: Record<string, string> = {
      red: 'drive and raw power',
      orange: 'creativity and connection',
      yellow: 'clarity and confidence',
      green: 'healing and compassion',
      blue: 'truth and peace',
      indigo: 'intuition and insight',
      violet: 'unity and faith'
    };

    return Object.entries(auraData.colors)
      .map(([color, value]) => ({ color, value, desc: colorDescs[color] || color }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 2);
  };
  const downloadNarrative = (narrative: string, filename: string) => {
    const blob = new Blob([narrative], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const generateAndDownloadNarrative = async () => {
    setIsGenerating(true);
    
    const topColors = getTopColors();
    const { voice } = controls;
    
    let fullNarrative = '';

    // Add metadata header
    const timestamp = new Date().toISOString();
    fullNarrative += `# Aura Narrative Report\n`;
    fullNarrative += `Generated: ${timestamp}\n`;
    fullNarrative += `Subject: ${auraData.name}\n`;
    fullNarrative += `QAID: ${qaid}\n`;
    fullNarrative += `Voice Mode: ${voice}\n`;
    fullNarrative += `Target Length: ${controls.lengthTarget} words\n\n`;
    fullNarrative += `---\n\n`;

    // ACT I - All That Was (Origins)
    if (voice === 'mythic' || voice === 'dual') {
      fullNarrative += `**ACT I — All That Was (Origins)**\n\n`;
      fullNarrative += `Before this lifetime wore a name, ${auraData.name} moved through seasons of learning as the ${auraData.archetype.primary}, carrying threads of ${auraData.karmic.motifs.join(', ')}. What endured across these passages were the gifts of ${auraData.strengths.join(', ')}—lights that never went out—even as the lessons of ${auraData.challenges.join(', ')} returned, asking not for punishment, but for completion. This is the ground beneath today's footsteps: a soul trained in the ways of the ${auraData.archetype.primary}, ready to make old wisdom useful in new light.\n\n`;
      
      if (topColors.length >= 2) {
        fullNarrative += `Around you, the field shows ${topColors[0].color} and ${topColors[1].color}—tones of ${topColors[0].desc} and ${topColors[1].desc}—suggesting that even your beginnings carry both strength and wisdom.\n\n`;
      }
    }

    if (voice === 'plain' || voice === 'dual') {
      if (voice === 'dual') fullNarrative += `**Plain Voice:**\n\n`;
      fullNarrative += `Your story began long before now. At your core you're a ${auraData.archetype.primary} (with ${auraData.archetype.secondary} qualities). You consistently bring ${auraData.strengths.join(', ')} to the table, and you've been working on ${auraData.challenges.join(', ')} for a while—these aren't flaws, they're repeating lessons that want resolution. That background explains why certain choices feel familiar: they're invitations to finish what you started.\n\n`;
    }

    // ACT II - All That Is (Present Crossroads)
    if (voice === 'mythic' || voice === 'dual') {
      fullNarrative += `**ACT II — All That Is (Present Crossroads)**\n\n`;
      fullNarrative += `Today, the road divides at ${humanizeCrossroad(auraData.crossroad.theme)}. Your energy centers hum with a measured togetherness—coherence ${formatPercentage(auraData.chakra.coherence)}—and the heart speaks the loudest (${formatPercentage(auraData.chakra.heart)}). In your aura, ${formatPercentage(auraData.colors.green)} green and ${formatPercentage(auraData.colors.blue)} blue lift like gentle banners—healing and truth, compassion and voice. The message is simple, if not always easy: open the door you guard, say the words you mean, and let your choices match your inner music.\n\n`;
    }

    if (voice === 'plain' || voice === 'dual') {
      if (voice === 'dual') fullNarrative += `**Plain Voice:**\n\n`;
      fullNarrative += `Right now you're at a choice point: ${humanizeCrossroad(auraData.crossroad.theme)}. Your energy is fairly balanced (coherence ${formatPercentage(auraData.chakra.coherence)}), with a strong heart (${formatPercentage(auraData.chakra.heart)}). Your aura highlights—green (healing/connection) and blue (calm/expression)—suggest this is a moment to lead with care and to be clear in what you say. In short: choose growth, but keep it kind.\n\n`;
    }

    // Supportive conditions
    const badges = [];
    if (auraData.cosmic?.note) badges.push(auraData.cosmic.note);
    if (auraData.earth?.note) badges.push(auraData.earth.note);
    badges.push(`Confidence ${formatPercentage(auraData.confidence)}`);
    fullNarrative += `*Supportive conditions: ${badges.join(' · ')}*\n\n`;

    // ACT III - All That Shall Be (Branching Futures)
    fullNarrative += `**ACT III — All That Shall Be (Branching Futures)**\n\n`;

    // Aligned Path
    fullNarrative += `**A) Aligned Path — Awakening (${formatPercentage(auraData.timelines.aligned.likelihood)})**\n\n`;
    fullNarrative += `If you lean into what you already know is true, the road widens. People arrive who speak your language; work begins to feel like service, not struggle. Conversations turn into invitations, and small steady tasks grow roots.\n\n`;
    fullNarrative += `This path is marked by ${auraData.timelines.aligned.outcomes.join(', ')}. The drivers are already alive in you: ${auraData.timelines.aligned.drivers.join(', ')}. Together they form a current you don't have to force.\n\n`;
    fullNarrative += `Here, the lesson is trust-in-action: let your heart lead while your voice stays clear. Practices that help now: meditation ${formatPercentage(auraData.practices.meditation)}, grounding ${formatPercentage(auraData.practices.grounding)}, service ${formatPercentage(auraData.practices.service)}. Think 'consistent, kind, and true.'\n\n`;

    // Middle Path
    fullNarrative += `**B) Middle Path — Gradual Growth (${formatPercentage(auraData.timelines.middle.likelihood)})**\n\n`;
    fullNarrative += `If you choose caution with curiosity, the journey becomes tidal—step, settle, learn; step, settle, learn. You keep what works and add what's needed.\n\n`;
    fullNarrative += `Expect ${auraData.timelines.middle.outcomes.join(', ')}. This mode relies on ${auraData.timelines.middle.drivers.join(', ')}—solid enough to move forward, gentle enough to avoid shocks.\n\n`;
    fullNarrative += `Tools that suit a steady pace: ritual ${formatPercentage(auraData.practices.ritual)}, timing ${formatPercentage(auraData.practices.timing)}, dreamwork ${formatPercentage(auraData.practices.dreamwork)}—small lights that add up.\n\n`;

    // Resistant Path
    fullNarrative += `**C) Resistant Path — Repetition (${formatPercentage(auraData.timelines.resistant.likelihood)})**\n\n`;
    fullNarrative += `If you turn away from what calls you, life repeats the chapter. The names change; the pattern doesn't.\n\n`;
    fullNarrative += `Here we see ${auraData.timelines.resistant.outcomes.join(', ')}. The drivers show what tightens the loop: ${auraData.timelines.resistant.drivers.join(', ')}. None of this is punishment; it's a reminder that some doors only open from the inside.\n\n`;

    // ACT IV - All That Moves in Unity
    fullNarrative += `**ACT IV — All That Moves in Unity**\n\n`;
    fullNarrative += `Beyond the three paths lies a fourth understanding: all choices lead home, but some roads are kinder. Your ${auraData.archetype.primary} nature knows this. With confidence at ${formatPercentage(auraData.confidence)}, you have enough trust to begin. The invitation is not to be perfect, but to be present—to let your gifts serve the moment and your lessons deepen your compassion.\n\n`;
    fullNarrative += `In unity, there is no wrong choice, only the choice to choose consciously. Move with love, speak with truth, and trust that what is yours will find you.\n\n`;

    // Calculate word count and update tracking
    const wordCount = fullNarrative.split(/\s+/).filter(word => word.length > 0).length;
    setLastGenerated({ timestamp: Date.now(), wordCount });

    // Generate filename with timestamp
    const dateStr = new Date().toISOString().split('T')[0];
    const timeStr = new Date().toTimeString().split(' ')[0].replace(/:/g, '-');
    const filename = `aura-narrative-${auraData.name.replace(/\s+/g, '-').toLowerCase()}-${dateStr}-${timeStr}.txt`;

    // Download the file
    downloadNarrative(fullNarrative, filename);
    
    setIsGenerating(false);
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            🧭 Long-Form Narrative Engine (Story Mode)
            {lastGenerated && (
              <Badge variant="outline">
                Last: {lastGenerated.wordCount} words
              </Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="text-sm font-medium">Voice Mode</label>
              <Select value={controls.voice} onValueChange={(value: any) => setControls({...controls, voice: value})}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="mythic">Mythic (Prophecy)</SelectItem>
                  <SelectItem value="plain">Plain (Practical)</SelectItem>
                  <SelectItem value="dual">Dual (Both)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <label className="text-sm font-medium">Target Length: {controls.lengthTarget} words</label>
              <Slider
                value={[controls.lengthTarget]}
                onValueChange={([value]) => setControls({...controls, lengthTarget: value})}
                min={1000}
                max={2500}
                step={100}
                className="mt-2"
              />
            </div>
            
            <div className="flex items-end">
              <Button 
                onClick={generateAndDownloadNarrative}
                disabled={isGenerating}
                className="w-full"
              >
                {isGenerating ? 'Generating...' : '📥 Generate & Download'}
              </Button>
            </div>
          </div>

          <div className="grid grid-cols-4 gap-2 text-xs">
            <div>Origins: {Math.round(controls.sectionWeights.origins * 100)}%</div>
            <div>Present: {Math.round(controls.sectionWeights.present * 100)}%</div>
            <div>Futures: {Math.round(controls.sectionWeights.futures * 100)}%</div>
            <div>Unity: {Math.round(controls.sectionWeights.unity * 100)}%</div>
          </div>

          {lastGenerated && (
            <div className="p-4 bg-success border border-success rounded-lg">
              <div className="flex items-center gap-2 text-success">
                <span className="text-lg">✅</span>
                <div>
                  <div className="font-medium">Narrative Generated Successfully</div>
                  <div className="text-sm text-success">
                    {lastGenerated.wordCount} words • Downloaded at {new Date(lastGenerated.timestamp).toLocaleTimeString()}
                  </div>
                  <div className="text-xs text-success mt-1">
                    File saved as: aura-narrative-{auraData.name.replace(/\s+/g, '-').toLowerCase()}-[timestamp].txt
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="p-4 bg-primary border border-primary rounded-lg">
            <div className="flex items-start gap-2">
              <span className="text-lg">ℹ️</span>
              <div className="text-sm text-primary">
                <div className="font-medium mb-2">Download Mode Active</div>
                <div className="space-y-1">
                  <div>• Stories are generated as downloadable text files to prevent system overload</div>
                  <div>• Files include metadata header with generation details</div>
                  <div>• Supports all voice modes: Mythic, Plain, and Dual</div>
                  <div>• Automatic filename with timestamp for organization</div>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}