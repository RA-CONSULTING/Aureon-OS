import http from 'http';
import { spawn, exec } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';
import { sampleMetrics } from './metrics.js';
import { findAndNeutralizeImbalance } from './latticeHarmonizer.js';
import { generateContent } from './geminiClient.js'; // Import the new Gemini client
import { loadForecastSummary } from '../core/forecastAnalyzer.js';
import anchorsDataset from '../data/nexus_anchors.json' assert { type: 'json' };
import { extractRequestParameters } from './lib/requestParameters.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const DIST_DIR = path.join(__dirname, '..', 'dist');

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.map': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.woff2': 'font/woff2',
};

const serveFile = (res, filePath) => {
  const ext = path.extname(filePath).toLowerCase();
  const contentType = MIME_TYPES[ext] || 'application/octet-stream';

  const stream = fs.createReadStream(filePath);
  stream.on('open', () => {
    res.writeHead(200, { 'Content-Type': contentType });
    stream.pipe(res);
  });

  stream.on('error', () => {
    res.writeHead(500, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Failed to read requested asset.' }));
  });
};

const serveAppAsset = (req, res) => {
  const host = req.headers.host || 'localhost';
  const url = new URL(req.url || '/', `http://${host}`);
  const pathname = decodeURIComponent(url.pathname);
  const requestedPath = pathname === '/' ? 'index.html' : pathname.replace(/^\/+/, '');
  const absolutePath = path.join(DIST_DIR, requestedPath);
  const normalizedPath = path.normalize(absolutePath);

  if (!normalizedPath.startsWith(DIST_DIR)) {
    res.writeHead(403, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Forbidden' }));
    return;
  }

  fs.stat(normalizedPath, (err, stats) => {
    if (!err && stats.isFile()) {
      serveFile(res, normalizedPath);
      return;
    }

    const fallbackPath = path.join(DIST_DIR, 'index.html');
    fs.stat(fallbackPath, (fallbackErr) => {
      if (fallbackErr) {
        res.writeHead(404, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Not Found' }));
        return;
      }

      serveFile(res, fallbackPath);
    });
  });
};

dotenv.config();

const KEY_NAMES = [
  'SUPABASE_URL',
  'SUPABASE_ANON_KEY',
  'NOAA_CDO_TOKEN',
  'NASA_API_KEY',
  'USGS_API_KEY',
];

const maskValue = (value) =>
  value ? `${value.slice(0, 4)}…${value.slice(-4)} (len=${value.length})` : '(missing)';

const server = http.createServer(async (req, res) => {
  const method = (req.method || 'GET').toUpperCase();
  const baseUrl = `http://${req.headers.host || 'localhost'}`;
  const requestUrl = new URL(req.url || '/', baseUrl);
  const pathname = requestUrl.pathname;

  if (method === 'GET' && pathname === '/stream') {
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive'
    });

    const interval = setInterval(() => {
      const data = sampleMetrics();
      res.write(`data: ${JSON.stringify(data)}\n\n`);
    }, 1000);

    req.on('close', () => {
      clearInterval(interval);
    });
  } else if (method === 'GET' && pathname === '/harmonize') {
    try {
      const imbalance = await findAndNeutralizeImbalance();
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(imbalance));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Failed to identify energetic imbalance' }));
    }
  } else if (method === 'GET' && pathname === '/celestial-chart') {
    const pythonExecutable = 'python';
    const scriptPath = './celestial_cartography.py';

    const process = spawn(pythonExecutable, [scriptPath]);

    process.on('close', (code) => {
      if (code === 0) {
        const chartPath = path.join(path.dirname(new URL(import.meta.url).pathname), '..', 'public', 'celestial_chart.png');
        const fileStream = fs.createReadStream(chartPath);
        res.writeHead(200, { 'Content-Type': 'image/png' });
        fileStream.pipe(res);
      } else {
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Failed to generate celestial chart' }));
      }
    });
  } else if (method === 'POST' && pathname === '/generate-narrative') {
    try {
      const { params } = await extractRequestParameters(req, baseUrl);
      const prompt = params.prompt;

      if (typeof prompt !== 'string' || prompt.trim() === '') {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Prompt is required' }));
        return;
      }

      const result = await generateContent(prompt);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(result));
    } catch (err) {
      console.error(err);
      const message = err instanceof Error ? err.message : 'Failed to generate narrative';
      const isClientError = err instanceof Error && (
        message.startsWith('Invalid') ||
        message.includes('must be an object') ||
        message.includes('Request aborted')
      );
      const status = isClientError ? 400 : 500;
      res.writeHead(status, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: message }));
    }
  } else if (method === 'GET' && pathname === '/generate-threat-assessment') {
    exec('git diff --shortstat', async (err, stdout, stderr) => {
      if (err) {
        console.error(`exec error: ${err}`);
        res.writeHead(500, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify({ error: 'Failed to execute git diff' }));
      }

      const prompt = `Analyze the following git diff summary and generate a threat assessment: ${stdout}`;

      try {
        const result = await generateContent(prompt);
        const assessment = result.candidates[0].content.parts[0].text;
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ assessment }));
      } catch (e) {
        console.error(e);
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Failed to generate threat assessment' }));
      }
    });
  } else if (method === 'GET' && pathname === '/bio-resonance-stream') {
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive'
    });

    const pythonProcess = spawn('python', ['./bio_resonance_sensor.py']);

    pythonProcess.stdout.on('data', (data) => {
      res.write(data);
    });

    req.on('close', () => {
      pythonProcess.kill();
    });
  } else if (method === 'GET' && pathname === '/harmonize-bio-resonance') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ message: 'Bio-resonance harmonization initiated.' }));

  } else if (method === 'GET' && pathname === '/api/keys-status') {
    const status = Object.fromEntries(
      KEY_NAMES.map((name) => {
        const value = process.env[name] || '';
        return [name, { present: Boolean(value), masked: maskValue(value) }];
      })
    );

    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(status));
  } else if (method === 'GET' && pathname.startsWith('/api/anchors')) {
    try {
      const segments = requestUrl.pathname.split('/').filter(Boolean);

      const parseMinWeight = () => {
        const value = requestUrl.searchParams.get('minWeight');
        if (value === null || value === '') {
          return null;
        }

        const parsed = Number(value);
        if (Number.isNaN(parsed) || parsed < 0 || parsed > 1) {
          throw new Error('Invalid minWeight parameter');
        }

        return parsed;
      };

      const parseConsent = () => {
        const value = requestUrl.searchParams.get('consent');
        if (value === null || value === '') {
          return null;
        }

        const normalized = value.toLowerCase();
        if (['true', '1', 'yes'].includes(normalized)) {
          return true;
        }
        if (['false', '0', 'no'].includes(normalized)) {
          return false;
        }
        if (['all', 'any'].includes(normalized)) {
          return null;
        }

        throw new Error('Invalid consent parameter');
      };

      const minWeight = parseMinWeight();
      const consentFilter = parseConsent();

      const anchors = Array.isArray(anchorsDataset?.anchors) ? anchorsDataset.anchors : [];
      const applyFilters = (members = []) => {
        let filtered = members.filter((member) => typeof member === 'object' && member !== null);

        if (minWeight !== null) {
          filtered = filtered.filter((member) => Number(member.weight) >= minWeight);
        }

        if (consentFilter !== null) {
          filtered = filtered.filter((member) => Boolean(member.consent) === consentFilter);
        }

        return filtered;
      };

      const respond = (status, payload) => {
        res.writeHead(status, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(payload));
      };

      if (segments.length === 2) {
        const summary = anchors.map((anchor) => {
          const filteredMembers = applyFilters(anchor.members);
          const consentingMembers = filteredMembers.filter((member) => member.consent).length;
          const averageWeight = filteredMembers.length
            ? filteredMembers.reduce((total, member) => total + Number(member.weight || 0), 0) / filteredMembers.length
            : null;

          return {
            id: anchor.id || anchor.anchor_id,
            display_name: anchor.display_name || anchor.name || anchor.anchor_id || 'Unknown Anchor',
            total_members: Array.isArray(anchor.members) ? anchor.members.length : 0,
            filtered_members: filteredMembers.length,
            consenting_members: consentingMembers,
            average_weight: averageWeight === null ? null : Number(averageWeight.toFixed(3)),
          };
        });

        respond(200, {
          anchors: summary,
          filters: {
            minWeight,
            consent: consentFilter,
          },
        });
        return;
      }

      if (segments.length === 3) {
        const anchorId = decodeURIComponent(segments[2]);
        const anchor = anchors.find((candidate) => (candidate.id || candidate.anchor_id) === anchorId);

        if (!anchor) {
          respond(404, { error: `Anchor '${anchorId}' not found.` });
          return;
        }

        const filteredMembers = applyFilters(anchor.members);
        const totalMembers = Array.isArray(anchor.members) ? anchor.members.length : 0;
        const consentingMembers = filteredMembers.filter((member) => member.consent).length;
        const aggregateWeight = filteredMembers.reduce((total, member) => total + Number(member.weight || 0), 0);

        respond(200, {
          anchor: {
            id: anchor.id || anchor.anchor_id,
            display_name: anchor.display_name || anchor.name || anchor.anchor_id || 'Unknown Anchor',
            members: filteredMembers,
          },
          metrics: {
            total_members: totalMembers,
            filtered_members: filteredMembers.length,
            consenting_members: consentingMembers,
            average_weight: filteredMembers.length ? Number((aggregateWeight / filteredMembers.length).toFixed(3)) : null,
          },
          filters: {
            minWeight,
            consent: consentFilter,
          },
        });
        return;
      }

      respond(404, { error: 'Anchor route not found.' });
    } catch (error) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: error.message }));
    }
  } else if (method === 'GET' && pathname.startsWith('/api/forecasts')) {
    try {
      const payload = await loadForecastSummary();
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(payload));
    } catch (error) {
      console.error('Failed to load forecast summary', error);
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Unable to load forecast window.' }));
    }
  } else if (method === 'GET') {
    serveAppAsset(req, res);
  } else {
    res.writeHead(404, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Not Found' }));
  }
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`Nexus Live Feed listening on ${PORT}`);

  // Activate the Harmonic Nexus Core on startup
  // const pythonExecutable = 'python';
  // const scriptPath = './activate_harmonic_nexus_core.py';

  // console.log('Activating Harmonic Nexus Core...');
  // const process = spawn(pythonExecutable, [scriptPath]);

  // process.stdout.on('data', (data) => {
  //   console.log(`[Activation] stdout: ${data}`);
  // });

  // process.stderr.on('data', (data) => {
  //   console.error(`[Activation] stderr: ${data}`);
  // });

  // process.on('close', (code) => {
  //   console.log(`Harmonic Nexus Core activation process exited with code ${code}`);
  // });
});
