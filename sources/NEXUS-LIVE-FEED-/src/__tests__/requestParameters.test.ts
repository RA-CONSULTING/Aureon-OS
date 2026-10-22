import { describe, expect, it } from 'vitest';
import { Readable } from 'node:stream';
import type { IncomingHttpHeaders } from 'http';
import { extractRequestParameters } from '../lib/requestParameters.js';

class MockRequest extends Readable {
  method: string;
  url: string;
  headers: IncomingHttpHeaders;
  private readonly body: string | Buffer | null;
  private sent = false;

  constructor({ method = 'GET', url = '/', headers = {}, body = null }: {
    method?: string;
    url?: string;
    headers?: IncomingHttpHeaders;
    body?: string | Buffer | null;
  }) {
    super();
    this.method = method;
    this.url = url;
    this.headers = headers;
    this.body = body;
  }

  _read() {
    if (this.sent) {
      this.push(null);
      return;
    }
    this.sent = true;
    if (this.body && this.body.length > 0) {
      this.push(this.body);
    }
    this.push(null);
  }
}

describe('extractRequestParameters', () => {
  it('returns only query parameters for GET requests', async () => {
    const req = new MockRequest({
      method: 'GET',
      url: '/status?mode=test&flag=on',
    });

    const result = await extractRequestParameters(req as any, 'http://example.com');

    expect(result.method).toBe('GET');
    expect(result.query).toEqual({ mode: 'test', flag: 'on' });
    expect(result.body).toEqual({});
    expect(result.params).toEqual({ mode: 'test', flag: 'on' });
    expect(result.rawBody).toBe('');
  });

  it('parses JSON request bodies', async () => {
    const body = JSON.stringify({ prompt: 'hello', tone: 'calm' });
    const req = new MockRequest({
      method: 'POST',
      url: '/generate-narrative',
      headers: { 'content-type': 'application/json' },
      body,
    });

    const result = await extractRequestParameters(req as any, 'http://localhost');

    expect(result.method).toBe('POST');
    expect(result.body).toEqual({ prompt: 'hello', tone: 'calm' });
    expect(result.params).toEqual({ prompt: 'hello', tone: 'calm' });
    expect(result.query).toEqual({});
  });

  it('parses x-www-form-urlencoded bodies', async () => {
    const req = new MockRequest({
      method: 'POST',
      url: '/generate-narrative',
      headers: { 'content-type': 'application/x-www-form-urlencoded' },
      body: 'prompt=sync&lang=en',
    });

    const result = await extractRequestParameters(req as any, 'http://localhost');

    expect(result.body).toEqual({ prompt: 'sync', lang: 'en' });
    expect(result.params).toEqual({ prompt: 'sync', lang: 'en' });
  });

  it('lets query string values override body parameters', async () => {
    const req = new MockRequest({
      method: 'POST',
      url: '/generate-narrative?prompt=query',
      headers: { 'content-type': 'application/x-www-form-urlencoded' },
      body: 'prompt=body&tone=warm',
    });

    const result = await extractRequestParameters(req as any, 'http://localhost');

    expect(result.body).toEqual({ prompt: 'body', tone: 'warm' });
    expect(result.query).toEqual({ prompt: 'query' });
    expect(result.params).toEqual({ prompt: 'query', tone: 'warm' });
  });
});

