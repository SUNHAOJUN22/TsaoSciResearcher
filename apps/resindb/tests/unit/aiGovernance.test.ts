import { describe, expect, it, vi } from 'vitest';
import {
  GOVERNED_AI_PROXY_PATH,
  MAX_AI_AUTHORIZATION_MS,
  buildAiAuditRecord,
  buildGovernedAiEnvelope,
  governedAiFetch,
  issueAiAuthorization,
  validateAiAuthorization,
} from '@/services/aiGovernance';

describe('governed AI egress contract', () => {
  it('issues a bounded UUIDv4 authorization and rejects invalid windows', () => {
    const now = new Date('2026-08-27T00:00:00.000Z');
    const auth = issueAiAuthorization('connectivity', now);
    expect(auth.requestId).toMatch(/^[0-9a-f-]{36}$/i);
    expect(() => validateAiAuthorization(auth, new Date(now.getTime() + 1))).not.toThrow();
    expect(() => issueAiAuthorization('connectivity', now, MAX_AI_AUTHORIZATION_MS + 1)).toThrow(/five minutes/);
    expect(() => validateAiAuthorization({ ...auth, authorizedAt: new Date(now.getTime() + 1_000).toISOString() }, now)).toThrow(/future-dated/);
    expect(() => validateAiAuthorization({ ...auth, expiresAt: now.toISOString() }, now)).toThrow(/expired/);
  });

  it('denies identity, secret and free-form provider fields recursively', () => {
    const base = { model: 'approved-model', purpose: 'material-summary' as const };
    for (const payload of [
      { data: { manufacturer: 'Maker' } },
      { data: { gradeName: 'PP-X' } },
      { data: { apiKey: 'secret' } },
      { messages: [] },
      { prompt: 'raw' },
    ]) {
      expect(() => buildGovernedAiEnvelope({ ...base, payload })).toThrow(/denied by default/);
    }
  });

  it('caps serialized requests before network transmission', () => {
    expect(() => buildGovernedAiEnvelope({
      model: 'approved-model', purpose: 'material-summary', payload: { data: 'x'.repeat(70_000) },
    })).toThrow(/governed limit/);
  });

  it('uses only the same-origin proxy without browser credentials', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(new Response('{}'));
    await governedAiFetch({ model: 'approved-model', purpose: 'connectivity', payload: { task: 'connectivity' }, fetchImpl });
    expect(fetchImpl).toHaveBeenCalledOnce();
    const [target, options] = fetchImpl.mock.calls[0];
    expect(target).toBe(GOVERNED_AI_PROXY_PATH);
    expect(options.headers).not.toHaveProperty('Authorization');
    expect(options.credentials).toBe('same-origin');
  });

  it('emits digest-only audit metadata', async () => {
    const envelope = buildGovernedAiEnvelope({ model: 'approved-model', purpose: 'connectivity', payload: { task: 'connectivity' } });
    const audit = await buildAiAuditRecord(envelope);
    expect(audit.payloadSha256).toMatch(/^[0-9a-f]{64}$/);
    expect(audit).not.toHaveProperty('payload');
    expect(JSON.stringify(audit)).not.toContain('approved-model');
  });
});


describe('unified immutable egress', () => {
  it('detaches the governed envelope from caller mutation', () => {
    const payload: Record<string, unknown> = { density: 0.9 };
    const envelope = buildGovernedAiEnvelope({ model: 'approved-model', purpose: 'material-summary', payload });
    payload.manufacturer = 'SYNTHETIC-TEST';
    expect(envelope.payload).toEqual({ density: 0.9 });
  });

  it('does not transmit fields added after validation', async () => {
    const payload: Record<string, unknown> = { density: 0.9 };
    const fetchImpl = vi.fn().mockResolvedValue(new Response('{}'));
    const pending = governedAiFetch({ model: 'approved-model', purpose: 'material-summary', payload, fetchImpl });
    payload.manufacturer = 'SYNTHETIC-TEST';
    payload.large = 'x'.repeat(70_000);
    await pending;
    const body = JSON.parse(String(fetchImpl.mock.calls[0][1].body));
    expect(body.payload).toEqual({ density: 0.9 });
  });
});
