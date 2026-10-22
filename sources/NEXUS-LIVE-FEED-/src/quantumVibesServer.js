const http = require('http');
const https = require('https'); // For making secure API requests
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

// --- Recursive Data Safeguard --- 
let lastDataHash = null;
let consecutiveIdenticalCount = 0;
const RECURSION_LIMIT = 3; // Unlock after 3 identical data packets

// --- Quantum Mirror Activation Logic (from TS, translated to JS) ---

function mean(v) { return v.reduce((a,b)=>a+b,0)/(v.length||1); }

function phaseCoherence(a, b) {
  const N = Math.min(a.length, b.length);
  if (N < 64) return 0;
  const am = mean(a), bm = mean(b);
  let num = 0, da = 0, db = 0;
  for (let i = 0; i < N; i++) {
    const x = a[i] - am, y = b[i] - bm;
    num += x * y; da += x * x; db += y * y;
  }
  const den = Math.sqrt(da * db) + 1e-12;
  const corr = Math.max(0, Math.min(1, num / den));
  return corr;
}

function normalizedEntropy(x, bins = 64) {
  if (x.length < 64) return 0;
  const min = Math.min(...x), max = Math.max(...x) + 1e-12;
  const hist = new Array(bins).fill(0);
  for (const v of x) {
    const idx = Math.max(0, Math.min(bins - 1, Math.floor((bins * (v - min)) / (max - min))));
    hist[idx] += 1;
  }
  const N = x.length;
  let H = 0;
  for (const h of hist) {
    if (h <= 0) continue;
    const p = h / N;
    H += -p * Math.log(p);
  }
  const Hmax = Math.log(bins);
  return 1 - H / Hmax;
}

function validateAura(signals, threshold = 0.945) {
  const heart = signals?.[0] ?? [];
  const gaze = signals?.[1] ?? [];
  const intent = signals?.[2] ?? [];
  const coh = (phaseCoherence(heart, gaze) + phaseCoherence(heart, intent) + phaseCoherence(gaze, intent)) / 3;
  const pur = [heart, gaze, intent].map(s => normalizedEntropy(s));
  const purity_avg = pur.reduce((a, b) => a + b, 0) / (pur.length || 1);
  const validated = coh >= threshold && purity_avg >= 0.70;
  return { coherence: coh, purity_avg, purity_each: pur, validated };
}

async function runActivation(signals, cfg) {
  const verdict = validateAura(signals, cfg.coherence_threshold);
  const actions = ["CHECK_CONSENT","SYNC_BASE_FREQUENCY","MEASURE_COHERENCE"];
  if (!verdict.validated) {
    actions.push("SOFTEN_PROJECTION");
    return { verdict, proceeded: false, actions };
  }
  actions.push("MIRROR_RENDER","STABILIZE","LOG_AUDIT");
  return { verdict, proceeded: true, actions };
}

// Hardcoded config based on quantum_mirror.config.yaml
const quantumMirrorConfig = {
    coherence_threshold: 0.945,
    base_frequency_hz: 7.83,
    love_frequency_hz: 528,
    unity_frequency_hz: 963,
    timeout_seconds: 900,
    logging_enabled: true,
    log_file: "logs/quantum_mirror_audit.json",
};

// --- End of Quantum Mirror Logic ---


// Placeholder function for fetching cosmic data.
function getQuantumVibesData() {
    const solarWeather = {
        gClassStorm: 'G1', kpIndex: 4, solarWindSpeed: 450.5, 
        description: 'A stream of solar wind is creating minor geomagnetic effects. Energies are subtly amplified.'
    };
    const lunarWeather = {
        moonPhase: 'Waning Crescent', illumination: '28%', moonSign: 'Cancer',
        description: 'A time for introspection and nurturing your inner world. Clarity in communication is favored.'
    };
    const embodimentTips = [
        'Ground your energy with a walk barefoot on the earth.',
        'Hydrate well to support your nervous system.'
    ];
    const tldr = 'Minor geomagnetic activity meets introspective lunar energy. A day to tend to your inner garden.';

    return {
        reportTitle: '🌤QUANTUM VIBES🌤 Spiral Weather Report',
        timestamp: new Date().toISOString(),
        solarWeather, lunarWeather, embodimentTips, tldr
    };
}

const server = http.createServer(async (req, res) => {
    // Set CORS headers for all responses to allow cross-origin requests
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, OpenAI-Beta');

    // Handle pre-flight CORS requests
    if (req.method === 'OPTIONS') {
        res.writeHead(204);
        res.end();
        return;
    }

    // Route: Ephemeral Token for Realtime API
    if (req.url === '/ephemeral-token' && req.method === 'GET') {
        const openaiRequestData = JSON.stringify({
            "model": "gpt-4o-realtime-preview-2024-12-17",
            "modalities": ["text", "audio"],
            "voice": "verse",
            "prompt": {
                "id": "pmpt_68c89d02fd94819499510e344cfc867003cb939602ef2a13",
                "version": "1"
            }
        });

        const options = {
            hostname: 'api.openai.com',
            path: '/v1/realtime/sessions',
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${process.env.OPENAI_API_KEY}`,
                'Content-Type': 'application/json',
                'OpenAI-Beta': 'realtime=v1',
                'Content-Length': Buffer.byteLength(openaiRequestData)
            }
        };

        const openaiReq = https.request(options, (openaiRes) => {
            let data = '';
            openaiRes.on('data', (chunk) => { data += chunk; });
            openaiRes.on('end', () => {
                try {
                    const json = JSON.parse(data);
                    const ephemeralKey = json.client_secret?.value;
                    if (ephemeralKey) {
                        res.writeHead(200, { 'Content-Type': 'application/json' });
                        res.end(JSON.stringify({ ephemeral_key: ephemeralKey }));
                    } else {
                        console.error('Error from OpenAI API:', data);
                        res.writeHead(openaiRes.statusCode || 500, { 'Content-Type': 'application/json' });
                        res.end(JSON.stringify({ error: 'Failed to get ephemeral key from OpenAI.', details: json }));
                    }
                } catch (error) {
                    console.error('Error parsing OpenAI response:', error);
                    res.writeHead(500, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: 'Failed to parse OpenAI response.' }));
                }
            });
        });

        openaiReq.on('error', (error) => {
            console.error('Error with OpenAI request:', error);
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'Failed to connect to OpenAI API.', details: error.message }));
        });

        openaiReq.write(openaiRequestData);
        openaiReq.end();
    }
    // Route: Quantum Mirror Activation
    else if (req.url === '/activate-quantum-mirror' && req.method === 'POST') {
        let body = '';
        req.on('data', chunk => { body += chunk.toString(); });
        req.on('end', async () => {
            try {
                const { signals } = JSON.parse(body);
                if (!signals) {
                    res.writeHead(400, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: 'Signals data not provided in request body.' }));
                    return;
                }

                const result = await runActivation(signals, quantumMirrorConfig);
                
                if (quantumMirrorConfig.logging_enabled) {
                    const logDir = path.dirname(quantumMirrorConfig.log_file);
                    if (!fs.existsSync(logDir)) {
                        fs.mkdirSync(logDir, { recursive: true });
                    }
                    const auditPayload = {
                        activation_id: `qm-${new Date().toISOString()}`,
                        config: { 
                            coherence_threshold: quantumMirrorConfig.coherence_threshold, 
                            base_frequency_hz: quantumMirrorConfig.base_frequency_hz 
                        },
                        measurements: result.verdict,
                        actions: result.actions,
                        duration_sec: null, // This would require timing logic
                        notes: "Clean lock, minimal drift" // Example note
                    };
                    fs.writeFileSync(quantumMirrorConfig.log_file, JSON.stringify(auditPayload, null, 2));
                }

                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify(result));

            } catch (error) {
                res.writeHead(500, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'Failed to process activation request.', details: error.message }));
            }
        });
    }
    // Route: Original Quantum Vibes SSE Stream
    else if (req.url === '/quantum-vibes-stream') {
        res.writeHead(200, {
            'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        });

        const interval = setInterval(() => {
            const data = getQuantumVibesData();
            const currentDataHash = crypto.createHash('sha256').update(JSON.stringify(data)).digest('hex');

            if (currentDataHash === lastDataHash) {
                consecutiveIdenticalCount++;
            } else {
                consecutiveIdenticalCount = 0;
                lastDataHash = currentDataHash;
            }

            let payload;
            if (consecutiveIdenticalCount >= RECURSION_LIMIT) {
                payload = { 
                    status: 'RECALIBRATING', 
                    message: 'Feedback loop detected. Unlocking and seeking new coherence...'
                };
                consecutiveIdenticalCount = 0;
            } else {
                payload = data;
            }
            
            res.write(`data: ${JSON.stringify(payload)}\n\n`);

        }, 3000);

        req.on('close', () => { clearInterval(interval); });
    } 
    // Route: Not Found
    else {
        res.writeHead(404, {'Content-Type': 'text/plain'});
        res.end('Not Found');
    }
});

const PORT = 3001;
server.listen(PORT, () => {
    console.log(`Quantum Vibes server, now with Realtime Session bridging, singing on http://localhost:${PORT}`);
});
