'use strict';

const { fetch } = globalThis;

if (typeof fetch !== 'function') {
  throw new Error('Global fetch API is required to use the Nexus agent wrapper.');
}

const API_ROOT = 'https://generativelanguage.googleapis.com/v1beta';

function assertApiKey(apiKey) {
  if (!apiKey) {
    throw new Error('A valid GEMINI_API_KEY is required to initialize the Nexus agent.');
  }
}

function buildHeaders(apiKey) {
  return {
    'Content-Type': 'application/json',
    'X-Goog-Api-Key': apiKey,
  };
}

async function parseJsonResponse(response) {
  const rawText = await response.text();
  if (!rawText) {
    return {};
  }

  try {
    return JSON.parse(rawText);
  } catch (error) {
    const parseError = new Error('Unable to parse response from the Gemini service as JSON.');
    parseError.cause = error;
    parseError.raw = rawText;
    throw parseError;
  }
}

function raiseForErrorResponse(response, data) {
  const errorPayload = data?.error;
  if (response.ok && !errorPayload) {
    return;
  }

  const status = errorPayload?.status || response.status;
  const message = errorPayload?.message || `Gemini request failed with status ${response.status}.`;
  const error = new Error(message);
  error.status = status;
  if (errorPayload) {
    error.code = errorPayload.status;
    error.details = errorPayload.details;
  } else {
    error.details = data;
  }
  throw error;
}

class NexusGenerativeModel {
  constructor(apiKey, model) {
    assertApiKey(apiKey);
    if (!model) {
      throw new Error('A model name must be provided when creating a Nexus generative model.');
    }

    this.apiKey = apiKey;
    this.model = model;
  }

  async generateContent(requestPayload) {
    const url = `${API_ROOT}/models/${encodeURIComponent(this.model)}:generateContent`;
    const response = await fetch(url, {
      method: 'POST',
      headers: buildHeaders(this.apiKey),
      body: JSON.stringify(requestPayload ?? {}),
    });

    const data = await parseJsonResponse(response);
    raiseForErrorResponse(response, data);

    // Mirror the structure returned by the original Nexus agent implementation.
    return { response: data };
  }
}

export class GoogleAIStudio {
  constructor(apiKey) {
    assertApiKey(apiKey);
    this.apiKey = apiKey;
    this.modelCache = new Map();
  }

  getGenerativeModel(options = {}) {
    const { model } = options;
    if (!model) {
      throw new Error('Model option is required when requesting a generative model from the Nexus agent.');
    }

    if (!this.modelCache.has(model)) {
      this.modelCache.set(model, new NexusGenerativeModel(this.apiKey, model));
    }

    return this.modelCache.get(model);
  }
}

export class GoogleAIFileManager {
  constructor(apiKey) {
    assertApiKey(apiKey);
    this.apiKey = apiKey;
  }

  // Placeholder methods can be expanded as the Nexus system evolves.
  async uploadBuffer() {
    throw new Error('File upload is not implemented within the Nexus agent wrapper.');
  }
}

export default {
  GoogleAIFileManager,
  GoogleAIStudio,
};
