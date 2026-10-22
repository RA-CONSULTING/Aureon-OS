import fetch from 'node-fetch';
import dotenv from 'dotenv';
dotenv.config();

const API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent';
const apiKey = process.env.GEMINI_API_KEY;
const isConfigured = Boolean(apiKey);

const summarizePrompt = (value) => {
  if (!value) return '<<no prompt provided>>';
  const text = String(value).replace(/\s+/g, ' ').trim();
  if (text.length <= 160) return text;
  return `${text.slice(0, 157)}…`;
};

const offlineResponse = (prompt) => ({
  candidates: [
    {
      content: {
        parts: [
          {
            text: `Gemini API offline. Provide manual narrative for prompt: "${summarizePrompt(prompt)}"`,
          },
        ],
      },
    },
  ],
  status: 'offline',
});

if (!isConfigured) {
  console.warn('[Gemini] GEMINI_API_KEY missing. Using offline stub responses.');
}

export async function generateContent(prompt) {
  if (!isConfigured) {
    return offlineResponse(prompt);
  }

  const payload = {
    contents: [
      {
        parts: [{ text: prompt }]
      }
    ]
  };

  const res = await fetch(API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-goog-api-key': apiKey
    },
    body: JSON.stringify(payload)
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Gemini API request failed: ${res.status} ${errText}`);
  }

  return res.json();
}
