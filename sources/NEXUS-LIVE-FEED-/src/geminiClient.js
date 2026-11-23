import { promptAureonOwn } from './aureonOwnClient.js';

export async function generateContent(prompt) {
  if (typeof prompt !== 'string' || !prompt.trim()) {
    throw new Error('aureon_own_model_prompt_required');
  }

  const result = await promptAureonOwn([{ role: 'user', content: prompt }]);
  return {
    candidates: [
      {
        content: {
          parts: [{ text: result.text }],
        },
      },
    ],
    model: result.model,
    provider: 'aureon_own_model',
    status: 'complete',
  };
}
