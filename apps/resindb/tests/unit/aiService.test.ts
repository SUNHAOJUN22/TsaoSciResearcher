import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Product } from '@/types/index';
import {
  clearAiConfig,
  getAiConfig,
  getAiInsights,
  getChemicalReplacementSuggestions,
  getSmartRecommendations,
  saveAiConfig,
  testAiConnection,
} from '@/services/aiService';

function product(id: string): Product {
  return {
    id, gradeName: `PP-${id}`, manufacturerId: 'm-1', manufacturer: 'Maker',
    categoryIds: ['cat_pp'], properties: { Density: { value: 0.9, unit: 'g/cm³' } },
    createdAt: '2026-07-28', updatedAt: '2026-07-28',
  };
}

function aiResponse(content: string, headers?: HeadersInit): Response {
  return new Response(JSON.stringify({ text: content }), { status: 200, headers: { 'Content-Type': 'application/json', ...headers } });
}

describe('AI service governed proxy boundary', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    saveAiConfig({ endpoint: '/api/ai/proxy', apiKey: '', model: 'approved-model' });
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    localStorage.clear();
    sessionStorage.clear();
  });

  it('persists only the model preference and removes legacy session secrets', () => {
    sessionStorage.setItem('resindb-ai-api-session-key', 'legacy');
    saveAiConfig({ endpoint: '/api/ai/proxy', apiKey: '', model: 'approved-model' });
    expect(JSON.parse(localStorage.getItem('resindb-ai-api-config') || '{}')).toEqual({ model: 'approved-model' });
    expect(sessionStorage.getItem('resindb-ai-api-session-key')).toBeNull();
    expect(getAiConfig()).toEqual({ endpoint: '/api/ai/proxy', apiKey: '', model: 'approved-model' });
    clearAiConfig();
    expect(getAiConfig().model).toBe('');
  });

  it('rejects browser API keys and arbitrary endpoints before fetch', async () => {
    expect(() => saveAiConfig({ endpoint: '/api/ai/proxy', apiKey: 'secret', model: 'm' })).toThrow(/prohibited/);
    expect(() => saveAiConfig({ endpoint: 'https://provider.example/v1', apiKey: '', model: 'm' })).toThrow(/same-origin/);
    expect(fetch).not.toHaveBeenCalled();
  });

  it('disables browser image egress', async () => {
    await expect(getAiInsights([], { imagePart: { inlineData: { mimeType: 'image/png', data: 'AAAA' } } })).rejects.toThrow(/image egress is disabled/);
    expect(fetch).not.toHaveBeenCalled();
  });

  it('rejects an announced oversized response', async () => {
    vi.mocked(fetch).mockResolvedValue(aiResponse('OK', { 'Content-Length': '100001' }));
    await expect(testAiConnection()).rejects.toThrow(/response is too large/);
  });

  it('sends de-identified records to the fixed same-origin proxy', async () => {
    vi.mocked(fetch).mockResolvedValue(aiResponse('summary'));
    await expect(getAiInsights([product('p-1')], 'Compare density.')).resolves.toBe('summary');
    const [target, options] = vi.mocked(fetch).mock.calls[0];
    expect(target).toBe('/api/ai/proxy');
    const body = String(options?.body);
    expect(body).not.toContain('p-1');
    expect(body).not.toContain('PP-p-1');
    expect(body).not.toContain('Maker');
    expect(body).not.toContain('Authorization');
  });

  it('maps transient candidate aliases back to local IDs', async () => {
    vi.mocked(fetch).mockResolvedValue(aiResponse(JSON.stringify({ recommendations: [
      { id: 'candidate-1', reason: 'same category' },
      { id: 'p-2', reason: 'leaked local id' },
    ] })));
    await expect(getSmartRecommendations(product('p-1'), [product('p-1'), product('p-2'), product('p-3')]))
      .resolves.toEqual({ recommendations: [{ id: 'p-2', reason: 'same category' }] });
  });

  it('normalizes governed formulation hypotheses', async () => {
    vi.mocked(fetch).mockResolvedValue(aiResponse(JSON.stringify({ overview: 'Hypotheses only', suggestions: [
      { chemicalName: 'A', replacement: 'B', impact: 'test', confidenceScore: 120, rationale: 'screening' },
      { chemicalName: 'bad' },
    ] })));
    await expect(getChemicalReplacementSuggestions(
      { name: 'secret-formula', expression: 'x+y', description: '', unit: 'phr' }, [product('p-1')],
    )).resolves.toEqual({
      overview: 'Hypotheses only',
      suggestions: [{ chemicalName: 'A', replacement: 'B', impact: 'test', confidenceScore: 100, rationale: 'screening' }],
    });
    expect(String(vi.mocked(fetch).mock.calls[0][1]?.body)).not.toContain('secret-formula');
    expect(String(vi.mocked(fetch).mock.calls[0][1]?.body)).not.toContain('x+y');
  });
});
