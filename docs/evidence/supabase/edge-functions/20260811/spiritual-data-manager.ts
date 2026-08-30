export const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type'
};

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
const supabase = createClient(supabaseUrl, supabaseKey);

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    const { action, data } = await req.json();
    switch (action) {
      case 'createUser': return await createSpiritualUser(data);
      case 'getUserProfile': return await getUserProfile(data.userId);
      case 'updateUserProfile': return await updateUserProfile(data.userId, data.updates);
      case 'createAuraScan': return await createAuraScan(data);
      case 'getUserScans': return await getUserScans(data.userId, data.limit);
      case 'createSignature': return await createSpiritualSignature(data);
      case 'validateSignature': return await validateSignature(data.signatureHash);
      case 'recordBiometric': return await recordBiometricData(data);
      case 'getAnalytics': return await getSpiritualAnalytics(data.userId);
      default: throw new Error('Invalid action');
    }
  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }),
      { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
  }
});

async function createSpiritualUser(userData: any) {
  const { data, error } = await supabase.from('spiritual_users').insert([{
    email: userData.email, name: userData.name, birth_date: userData.birthDate,
    birth_time: userData.birthTime, birth_location: userData.birthLocation,
    preferred_frequencies: userData.preferredFrequencies || [432, 528, 741]
  }]).select().single();
  if (error) throw error;
  return new Response(JSON.stringify({ success: true, user: data }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
}

async function getUserProfile(userId: string) {
  const { data, error } = await supabase.from('spiritual_users')
    .select('*, spiritual_signatures(count), aura_scans(count)')
    .eq('id', userId).single();
  if (error) throw error;
  return new Response(JSON.stringify({ success: true, profile: data }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
}

async function updateUserProfile(userId: string, updates: any) {
  const { data, error } = await supabase.from('spiritual_users')
    .update({ ...updates, updated_at: new Date().toISOString() })
    .eq('id', userId).select().single();
  if (error) throw error;
  return new Response(JSON.stringify({ success: true, user: data }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
}

async function createAuraScan(scanData: any) {
  const { data, error } = await supabase.from('aura_scans').insert([{
    user_id: scanData.userId, scan_type: scanData.scanType || 'full_spectrum',
    coherence_score: scanData.coherenceScore, purity_reading: scanData.purityReading,
    energy_level: scanData.energyLevel, chakra_readings: scanData.chakraReadings,
    frequency_analysis: scanData.frequencyAnalysis, realignment_tone_used: scanData.realignmentTone,
    scan_location: scanData.location, device_info: scanData.deviceInfo
  }]).select().single();
  if (error) throw error;
  return new Response(JSON.stringify({ success: true, scan: data }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
}

async function getUserScans(userId: string, limit = 50) {
  const { data, error } = await supabase.from('aura_scans')
    .select('*, spiritual_signatures(signature_hash)')
    .eq('user_id', userId).order('created_at', { ascending: false }).limit(limit);
  if (error) throw error;
  return new Response(JSON.stringify({ success: true, scans: data }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
}

async function createSpiritualSignature(sigData: any) {
  const { data, error } = await supabase.from('spiritual_signatures').insert([{
    user_id: sigData.userId, signature_hash: sigData.signatureHash,
    energy_pattern: sigData.energyPattern, frequency_signature: sigData.frequencySignature,
    sacred_geometry_code: sigData.sacredGeometryCode, dimensional_resonance: sigData.dimensionalResonance,
    is_primary: sigData.isPrimary || false
  }]).select().single();
  if (error) throw error;
  return new Response(JSON.stringify({ success: true, signature: data }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
}

async function validateSignature(signatureHash: string) {
  const { data, error } = await supabase.from('spiritual_signatures')
    .update({ validation_count: supabase.raw('validation_count + 1'), last_validated_at: new Date().toISOString() })
    .eq('signature_hash', signatureHash).select().single();
  if (error) throw error;
  return new Response(JSON.stringify({ success: true, validated: true, signature: data }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
}

async function recordBiometricData(bioData: any) {
  const { data, error } = await supabase.from('biometric_data').insert([{
    user_id: bioData.userId, scan_id: bioData.scanId, measurement_type: bioData.measurementType,
    value: bioData.value, unit: bioData.unit, frequency_hz: bioData.frequencyHz,
    amplitude: bioData.amplitude, phase_angle: bioData.phaseAngle,
    harmonic_content: bioData.harmonicContent, sensor_id: bioData.sensorId
  }]).select().single();
  if (error) throw error;
  return new Response(JSON.stringify({ success: true, biometric: data }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
}

async function getSpiritualAnalytics(userId: string) {
  const [userStats, recentScans, signatures] = await Promise.all([
    supabase.from('spiritual_users').select('*').eq('id', userId).single(),
    supabase.from('aura_scans').select('*').eq('user_id', userId).order('created_at', { ascending: false }).limit(10),
    supabase.from('spiritual_signatures').select('*').eq('user_id', userId)
  ]);
  
  return new Response(JSON.stringify({
    success: true, analytics: {
      user: userStats.data, recentScans: recentScans.data, signatures: signatures.data
    }
  }), { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
}
