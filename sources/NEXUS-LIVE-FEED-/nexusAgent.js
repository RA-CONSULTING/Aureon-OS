'use strict';

import {
  AUREON_OWN_DEFAULT_MODEL,
  promptAureonOwn,
} from './src/aureonOwnClient.js';

function messageText(parts) {
  if (!Array.isArray(parts)) return '';
  return parts.map((part) => String(part?.text || '')).join('');
}

class NexusGenerativeModel {
  constructor(model) {
    if (model !== AUREON_OWN_DEFAULT_MODEL) {
      throw new Error('aureon_own_model_required');
    }
    this.model = model;
  }

  async generateContent(requestPayload) {
    const contents = Array.isArray(requestPayload?.contents)
      ? requestPayload.contents
      : [];
    const messages = contents.map((content) => ({
      role: content?.role === 'model' ? 'assistant' : 'user',
      content: messageText(content?.parts),
    }));
    const system = messageText(requestPayload?.systemInstruction?.parts);
    if (system) messages.unshift({ role: 'system', content: system });

    const result = await promptAureonOwn(messages, {
      maxTokens: requestPayload?.generationConfig?.maxOutputTokens ?? 512,
      temperature: requestPayload?.generationConfig?.temperature ?? 0,
    });
    return {
      response: {
        candidates: [
          {
            content: {
              role: 'model',
              parts: [{ text: result.text }],
            },
          },
        ],
        model: result.model,
        provider: 'aureon_own_model',
      },
    };
  }
}

export class GoogleAIStudio {
  constructor() {
    this.modelCache = new Map();
  }

  getGenerativeModel(options = {}) {
    const { model } = options;
    if (!model) {
      throw new Error('A model name must be provided when requesting the Aureon model.');
    }

    if (!this.modelCache.has(model)) {
      this.modelCache.set(model, new NexusGenerativeModel(model));
    }

    return this.modelCache.get(model);
  }
}

export class GoogleAIFileManager {
  async uploadBuffer() {
    throw new Error('File upload is not implemented within the Nexus agent wrapper.');
  }
}

export default {
  GoogleAIFileManager,
  GoogleAIStudio,
};
