import { Buffer } from 'buffer';

const METHODS_WITH_BODY = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

const normalizeContentType = (header = '') => header.split(';')[0].trim().toLowerCase();

const parseJsonBody = (raw) => {
  if (!raw) return {};
  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch (error) {
    throw new Error('Invalid JSON body');
  }

  if (parsed === null || Array.isArray(parsed) || typeof parsed !== 'object') {
    throw new Error('Request JSON body must be an object');
  }

  return parsed;
};

const parseFormBody = (raw) => {
  if (!raw) return {};
  const params = new URLSearchParams(raw);
  const result = {};
  for (const [key, value] of params.entries()) {
    result[key] = value;
  }
  return result;
};

const parseBodyByType = (raw, contentType) => {
  const type = normalizeContentType(contentType);
  if (!raw) {
    return {};
  }

  if (type === 'application/json' || type.endsWith('+json') || type === 'text/json') {
    return parseJsonBody(raw);
  }

  if (type === 'application/x-www-form-urlencoded') {
    return parseFormBody(raw);
  }

  if (!type) {
    try {
      return parseJsonBody(raw);
    } catch (error) {
      return parseFormBody(raw);
    }
  }

  return {};
};

const readRequestBody = (req) => new Promise((resolve, reject) => {
  const chunks = [];

  req.on('data', (chunk) => {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  });

  req.on('end', () => {
    resolve(Buffer.concat(chunks).toString('utf8'));
  });

  req.on('error', reject);
  req.on('aborted', () => reject(new Error('Request aborted')));
});

export const extractRequestParameters = async (req, baseUrl = 'http://localhost') => {
  const method = (req.method || 'GET').toUpperCase();
  const url = new URL(req.url || '/', baseUrl);
  const query = Object.fromEntries(url.searchParams.entries());

  if (!METHODS_WITH_BODY.has(method)) {
    return {
      method,
      url,
      query,
      body: {},
      params: { ...query },
      rawBody: '',
    };
  }

  const rawBody = await readRequestBody(req);
  const body = parseBodyByType(rawBody, req.headers?.['content-type'] || '');

  return {
    method,
    url,
    query,
    body,
    params: { ...body, ...query },
    rawBody,
  };
};

