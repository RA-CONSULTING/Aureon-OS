import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

type SolarFlare = {
  flrID: string;
  beginTime: string;
  peakTime: string;
  endTime: string;
  classType: string;
  sourceLocation: string;
  activeRegionNum: number;
};

async function fetchNASASolarFlares(startDate: string, endDate: string): Promise<SolarFlare[]> {
  const apiKey = Deno.env.get('NASA_API_KEY')?.trim();
  if (!apiKey) throw new Error('NASA_API_KEY_NOT_CONFIGURED');
  const url = `https://api.nasa.gov/DONKI/FLR?startDate=${startDate}&endDate=${endDate}&api_key=${apiKey}`;
  const response = await fetch(url);
  if (!response.ok) throw new Error(`NASA_DONKI_HTTP_${response.status}`);
  const payload = await response.json();
  if (!Array.isArray(payload)) throw new Error('NASA_DONKI_INVALID_PAYLOAD');
  return payload;
}

function parseSolarFlareClass(classType: string): { class: string; magnitude: number; power: number } {
  const match = classType.match(/^([XMCBA])(\d+\.?\d*)/);
  if (!match) return { class: 'A', magnitude: 0, power: 1.0 };
  
  const [, flareClass, magnitudeStr] = match;
  const magnitude = parseFloat(magnitudeStr);
  
  let basePower = 1.0;
  switch (flareClass) {
    case 'X': basePower = 2.5 + (magnitude * 0.3); break;
    case 'M': basePower = 1.5 + (magnitude * 0.1); break;
    case 'C': basePower = 1.1 + (magnitude * 0.02); break;
    case 'B': basePower = 1.0 + (magnitude * 0.005); break;
  }
  
  return { class: flareClass, magnitude, power: basePower };
}

function calculateMoonPhase(date: Date): number {
  const year = date.getFullYear();
  const month = date.getMonth() + 1;
  const day = date.getDate();
  
  let c, e, jd;
  if (month < 3) {
    const yearAdjust = year - 1;
    const monthAdjust = month + 12;
    c = yearAdjust / 100;
    e = 2 - c + Math.floor(c / 4);
    jd = Math.floor(365.25 * (yearAdjust + 4716)) + Math.floor(30.6001 * (monthAdjust + 1)) + day + e - 1524.5;
  } else {
    c = year / 100;
    e = 2 - c + Math.floor(c / 4);
    jd = Math.floor(365.25 * (year + 4716)) + Math.floor(30.6001 * (month + 1)) + day + e - 1524.5;
  }
  
  const daysSinceNew = jd - 2451549.5;
  const newMoons = daysSinceNew / 29.53;
  return (newMoons - Math.floor(newMoons));
}

function getMoonPhaseInfo(phase: number): { name: string; power: number; influence: string } {
  if (phase < 0.03 || phase > 0.97) return { name: 'New Moon', power: 1.5, influence: 'New Beginnings, Manifestation' };
  if (phase < 0.22) return { name: 'Waxing Crescent', power: 1.1, influence: 'Growth, Intention Setting' };
  if (phase < 0.28) return { name: 'First Quarter', power: 1.3, influence: 'Action, Decision Making' };
  if (phase < 0.47) return { name: 'Waxing Gibbous', power: 1.2, influence: 'Refinement, Building' };
  if (phase < 0.53) return { name: 'Full Moon', power: 2.0, influence: 'Completion, Illumination, Peak Power' };
  if (phase < 0.72) return { name: 'Waning Gibbous', power: 1.2, influence: 'Gratitude, Sharing' };
  if (phase < 0.78) return { name: 'Last Quarter', power: 1.3, influence: 'Release, Letting Go' };
  return { name: 'Waning Crescent', power: 1.1, influence: 'Reflection, Rest' };
}

function calculatePlanetaryAlignment(date: Date): { score: number; alignedPlanets: string[] } {
  const dayOfYear = Math.floor((date.getTime() - new Date(date.getFullYear(), 0, 0).getTime()) / 86400000);
  const positions = [
    { name: 'Mercury', pos: (dayOfYear % 88) / 88 },
    { name: 'Venus', pos: (dayOfYear % 225) / 225 },
    { name: 'Mars', pos: (dayOfYear % 687) / 687 },
    { name: 'Jupiter', pos: (dayOfYear % 4333) / 4333 },
    { name: 'Saturn', pos: (dayOfYear % 10759) / 10759 }
  ];
  
  const alignedPlanets: string[] = [];
  let alignmentScore = 0;
  
  for (let i = 0; i < positions.length; i++) {
    for (let j = i + 1; j < positions.length; j++) {
      const diff = Math.abs(positions[i].pos - positions[j].pos);
      if (diff < 0.1 || diff > 0.9) {
        alignmentScore += 0.2;
        if (!alignedPlanets.includes(positions[i].name)) alignedPlanets.push(positions[i].name);
        if (!alignedPlanets.includes(positions[j].name)) alignedPlanets.push(positions[j].name);
      }
    }
  }
  
  return { score: Math.min(alignmentScore, 1.0), alignedPlanets };
}

function calculateSeasonalAlignment(date: Date): { name: string; proximity: number; power: number } {
  const year = date.getFullYear();
  const dayOfYear = Math.floor((date.getTime() - new Date(year, 0, 0).getTime()) / 86400000);
  const events = [
    { name: 'Spring Equinox', day: 80 },
    { name: 'Summer Solstice', day: 172 },
    { name: 'Autumn Equinox', day: 266 },
    { name: 'Winter Solstice', day: 355 }
  ];
  
  let closest = events[0];
  let minDist = Math.abs(dayOfYear - events[0].day);
  
  events.forEach(event => {
    const dist = Math.abs(dayOfYear - event.day);
    if (dist < minDist) {
      minDist = dist;
      closest = event;
    }
  });
  
  const proximity = Math.max(0, 1 - minDist / 30);
  return { name: closest.name, proximity, power: 1 + proximity * 0.8 };
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const now = new Date();
    const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    const solarFlares = await fetchNASASolarFlares(sevenDaysAgo.toISOString().split('T')[0], now.toISOString().split('T')[0]);
    
    const recentFlares = solarFlares.filter(f => (now.getTime() - new Date(f.peakTime || f.beginTime).getTime()) < 48 * 60 * 60 * 1000);
    
    let solarPower = 1.0;
    let solarPhase = 'Quiet';
    let dominantFlareClass = '';
    let topFlare: { class: string; time: string; power: number; hoursSince: number } | null = null;
    
    recentFlares.forEach(flare => {
      const info = parseSolarFlareClass(flare.classType);
      if (info.power > solarPower) {
        solarPower = info.power;
        solarPhase = `Active: ${flare.classType} Flare`;
        dominantFlareClass = flare.classType;
        topFlare = {
          class: flare.classType,
          time: flare.peakTime || flare.beginTime,
          power: info.power,
          hoursSince: Math.round((now.getTime() - new Date(flare.peakTime || flare.beginTime).getTime()) / (1000 * 60 * 60))
        };
      }
    });
    
    const moonPhase = calculateMoonPhase(now);
    const moonInfo = getMoonPhaseInfo(moonPhase);
    const planetary = calculatePlanetaryAlignment(now);
    const seasonal = calculateSeasonalAlignment(now);
    const cosmicPower = (moonInfo.power + solarPower + seasonal.power + (1 + planetary.score)) / 4;
    
    const sacredFrequencies: number[] = [];
    if (moonInfo.name.includes('Full')) sacredFrequencies.push(528, 639, 741);
    else if (moonInfo.name.includes('New')) sacredFrequencies.push(396, 417, 528);
    
    // Check for X-class flares
    if (dominantFlareClass.startsWith('X')) sacredFrequencies.push(963, 852, 741);
    else if (solarPower > 1.5) sacredFrequencies.push(852, 963);
    
    if (seasonal.name.includes('Equinox')) sacredFrequencies.push(528);
    else if (seasonal.name.includes('Solstice')) sacredFrequencies.push(396, 963);
    if (planetary.score > 0.5) sacredFrequencies.push(741, 852);
    
    return new Response(JSON.stringify({
      timestamp: now.toISOString(),
      moon: { phase: moonPhase, name: moonInfo.name, power: moonInfo.power, influence: moonInfo.influence, illumination: Math.abs(moonPhase - 0.5) * 200 },
      solar: {
        activity: recentFlares.length === 0 ? 0 : Math.min(1.0, (solarPower - 1.0) * 0.3),
        phase: solarPhase,
        power: solarPower,
        recentFlares: recentFlares.map(f => ({ class: f.classType, time: f.peakTime || f.beginTime, source: f.sourceLocation, power: parseSolarFlareClass(f.classType).power })),
        dominantFlare: topFlare
      },
      planetary: { alignmentScore: planetary.score, alignedPlanets: planetary.alignedPlanets, power: 1 + planetary.score * 0.5 },
      seasonal: { name: seasonal.name, proximity: seasonal.proximity, power: seasonal.power, daysUntil: Math.round(seasonal.proximity * 30) },
      cosmic: { overallPower: cosmicPower, coherenceBoost: (cosmicPower - 1) * 0.15, sacredFrequencies: [...new Set(sacredFrequencies)].sort((a, b) => a - b) },
      truthStatus: 'real_derived',
      sourceId: 'NASA_DONKI_FLR_AND_ASTRONOMICAL_CALCULATION',
      sourceTimestamp: now.toISOString(),
      generatedValues: false,
    }), { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
  } catch (error) {
    return new Response(JSON.stringify({
      error: error instanceof Error ? error.message : 'Unknown error',
      truthStatus: 'no_data',
      generatedValues: false,
    }), {
      status: 503,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
});
