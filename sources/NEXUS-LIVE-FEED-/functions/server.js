import dotenv from 'dotenv';
import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();

app.use(express.json());
app.use(cors());

// Serve static files from the React build directory
app.use(express.static(path.join(__dirname, '../dist')));

app.get('/api/keys-status', (req, res) => {
  const KEYS = ["SUPABASE_URL","SUPABASE_ANON_KEY","NOAA_CDO_TOKEN","NASA_API_KEY","USGS_API_KEY"];
  const mask = (v) => v ? `${v.slice(0,4)}…${v.slice(-4)} (len=${v.length})` : "(missing)";
  const body = Object.fromEntries(
    KEYS.map(k => [k, { present: !!process.env[k], masked: mask(process.env[k]||"") }])
  );
  res.json(body);
});

// The "catchall" handler: for any request that doesn't match one above,
// send back React's index.html file.
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, '../dist', 'index.html'));
});

export default app;
