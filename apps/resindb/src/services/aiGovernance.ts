import { logger } from '@/lib/logger';

export const GOVERNED_AI_PROXY_PATH = '/api/ai/proxy';
export const MAX_AI_REQUEST_BYTES = 64 * 1024;
export const MAX_AI_AUTHORIZATION_MS = 5 * 60 * 1000;

export type AiPurpose =
  | 'connectivity'
  | 'material-summary'
  | 'material-comparison'
  | 'formulation-hypothesis'
  | 'record-analysis';

export interface AiAuthorization {
  requestId: string;
  purpose: AiPurpose;
  authorizedAt: string;
  expiresAt: string;
}

export interface GovernedAiEnvelope {
  requestId: string;
  purpose: AiPurpose;
  authorizedAt: string;
  expiresAt: string;
  model: string;
  payload: Record<string, unknown>;
}

export interface AiAuditRecord {
  requestId: string;
  purpose: AiPurpose;
  target: typeof GOVERNED_AI_PROXY_PATH;
  authorizedAt: string;
  expiresAt: string;
  allowedFields: string[];
  payloadSha256: string;
  payloadBytes: number;
}

const UUID_V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const FORBIDDEN_FIELD_NAMES = new Set([
  'apikey', 'authorization', 'bearer', 'token', 'secret',
  'manufacturer', 'manufacturerid', 'vendor', 'supplier',
  'grade', 'gradename', 'tradename', 'productname',
  'composition', 'formula', 'cas', 'casnumber', 'customer', 'batch',
  'prompt', 'messages', 'message', 'document', 'content',
]);

function normalizedFieldName(value: string): string {
  return value.normalize('NFKC').toLowerCase().replace(/[^a-z0-9]/g, '');
}

export function isIdentityBearingFieldName(value: string): boolean {
  return FORBIDDEN_FIELD_NAMES.has(normalizedFieldName(value));
}

function assertJsonObject(value: unknown, path = '$'): asserts value is Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new Error(`${path} must be a JSON object`);
  }
}

function inspectPayload(value: unknown, path: string): void {
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return;
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) throw new Error(`${path} contains a non-finite number`);
    return;
  }
  if (Array.isArray(value)) {
    value.forEach((item, index) => inspectPayload(item, `${path}[${index}]`));
    return;
  }
  assertJsonObject(value, path);
  for (const [key, item] of Object.entries(value)) {
    if (isIdentityBearingFieldName(key)) {
      throw new Error(`AI egress field is denied by default: ${path}.${key}`);
    }
    inspectPayload(item, `${path}.${key}`);
  }
}

function parseInstant(value: string, field: string): number {
  const instant = Date.parse(value);
  if (!Number.isFinite(instant)) throw new Error(`${field} must be an ISO-8601 timestamp`);
  return instant;
}

export function issueAiAuthorization(
  purpose: AiPurpose,
  now = new Date(),
  durationMs = 60_000,
): AiAuthorization {
  if (!Number.isFinite(durationMs) || durationMs <= 0 || durationMs > MAX_AI_AUTHORIZATION_MS) {
    throw new Error('AI authorization duration must be within five minutes');
  }
  const requestId = globalThis.crypto?.randomUUID?.();
  if (!requestId || !UUID_V4.test(requestId)) {
    throw new Error('A cryptographically generated UUIDv4 request identity is required');
  }
  return {
    requestId,
    purpose,
    authorizedAt: now.toISOString(),
    expiresAt: new Date(now.getTime() + durationMs).toISOString(),
  };
}

export function validateAiAuthorization(
  authorization: AiAuthorization,
  now = new Date(),
): void {
  if (!UUID_V4.test(authorization.requestId)) throw new Error('AI request identity must be UUIDv4');
  if (!authorization.purpose) throw new Error('AI request purpose is required');
  const authorizedAt = parseInstant(authorization.authorizedAt, 'authorizedAt');
  const expiresAt = parseInstant(authorization.expiresAt, 'expiresAt');
  const current = now.getTime();
  if (authorizedAt > current) throw new Error('AI authorization is future-dated');
  if (expiresAt <= current) throw new Error('AI authorization has expired');
  if (expiresAt <= authorizedAt) throw new Error('AI authorization interval is invalid');
  if (expiresAt - authorizedAt > MAX_AI_AUTHORIZATION_MS) {
    throw new Error('AI authorization interval exceeds five minutes');
  }
}

export function buildGovernedAiEnvelope(input: {
  model: string;
  purpose: AiPurpose;
  payload: Record<string, unknown>;
  authorization?: AiAuthorization;
  now?: Date;
}): GovernedAiEnvelope {
  const now = input.now ?? new Date();
  const model = input.model.trim();
  if (!model) throw new Error('A server-approved AI model identifier is required');
  assertJsonObject(input.payload, 'payload');
  inspectPayload(input.payload, 'payload');
  const authorization = input.authorization ?? issueAiAuthorization(input.purpose, now);
  if (authorization.purpose !== input.purpose) throw new Error('AI authorization purpose mismatch');
  validateAiAuthorization(authorization, now);
  const envelope: GovernedAiEnvelope = {
    requestId: authorization.requestId,
    purpose: authorization.purpose,
    authorizedAt: authorization.authorizedAt,
    expiresAt: authorization.expiresAt,
    model,
    // Detach the validated request from mutable caller-owned objects.
    payload: JSON.parse(JSON.stringify(input.payload)) as Record<string, unknown>,
  };
  // Validate the detached snapshot as well: custom serialization must not add fields.
  inspectPayload(envelope.payload, 'payload');
  const encoded = new TextEncoder().encode(JSON.stringify(envelope));
  if (encoded.byteLength > MAX_AI_REQUEST_BYTES) {
    throw new Error(`AI request exceeds the ${MAX_AI_REQUEST_BYTES}-byte governed limit`);
  }
  return envelope;
}

async function sha256Hex(value: string): Promise<string> {
  const digest = await globalThis.crypto.subtle.digest('SHA-256', new TextEncoder().encode(value));
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, '0')).join('');
}

async function auditFixedBody(body: string): Promise<AiAuditRecord> {
  const envelope = JSON.parse(body) as GovernedAiEnvelope;
  return {
    requestId: envelope.requestId,
    purpose: envelope.purpose,
    target: GOVERNED_AI_PROXY_PATH,
    authorizedAt: envelope.authorizedAt,
    expiresAt: envelope.expiresAt,
    allowedFields: Object.keys(envelope.payload).sort(),
    payloadSha256: await sha256Hex(body),
    payloadBytes: new TextEncoder().encode(body).byteLength,
  };
}

export async function buildAiAuditRecord(envelope: GovernedAiEnvelope): Promise<AiAuditRecord> {
  return auditFixedBody(JSON.stringify(envelope));
}

export async function governedAiFetch(input: {
  model: string;
  purpose: AiPurpose;
  payload: Record<string, unknown>;
  authorization?: AiAuthorization;
  signal?: AbortSignal;
  fetchImpl?: typeof fetch;
}): Promise<Response> {
  const envelope = buildGovernedAiEnvelope(input);
  // Size, audit digest and network transmission share these exact immutable bytes.
  const body = JSON.stringify(envelope);
  const audit = await auditFixedBody(body);
  logger.info('Governed AI egress request', audit);
  const fetchImpl = input.fetchImpl ?? globalThis.fetch;
  return fetchImpl(GOVERNED_AI_PROXY_PATH, {
    method: 'POST',
    credentials: 'same-origin',
    cache: 'no-store',
    headers: {
      'Content-Type': 'application/json',
      'X-ResinDB-Request-Id': envelope.requestId,
      'X-ResinDB-Purpose': envelope.purpose,
    },
    body,
    signal: input.signal,
  });
}
