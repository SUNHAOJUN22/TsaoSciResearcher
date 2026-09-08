import type { Product, PropertyValue } from '@/types/index';
import { logger } from '@/lib/logger';
import {
  GOVERNED_AI_PROXY_PATH,
  governedAiFetch,
  isIdentityBearingFieldName,
  type AiPurpose,
} from '@/services/aiGovernance';

const PERSISTENT_STORAGE_KEY = 'resindb-ai-api-config';
const LEGACY_SESSION_KEY_STORAGE_KEY = 'resindb-ai-api-session-key';
const REQUEST_TIMEOUT_MS = 60_000;
const MAX_CONTEXT_PRODUCTS = 20;
const MAX_RESPONSE_CHARS = 100_000;
const MAX_QUERY_CHARS = 4_000;

export interface AiApiConfig {
  /** Fixed to the same-origin governed proxy. */
  endpoint: string;
  /** Browser API keys are prohibited; retained only for source compatibility. */
  apiKey: string;
  model: string;
}

export interface AiInsightOptions {
  query?: string;
  isDeepThinking?: boolean;
  imagePart?: { inlineData: { data: string; mimeType: string } };
}

export interface ChemicalSuggestion {
  chemicalName: string;
  replacement: string;
  impact: string;
  confidenceScore: number;
  rationale: string;
  formulaUpdate?: string;
}

export interface AiSuggestionEngineResponse {
  overview: string;
  suggestions: ChemicalSuggestion[];
}

interface RecommendationResponse {
  recommendations: Array<{ id: string; reason: string }>;
}

interface ProxyRequestOptions {
  purpose: AiPurpose;
  instructions: string;
  query: string;
  data?: Record<string, unknown>;
  temperature?: number;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function readStoredModel(): string {
  if (typeof window === 'undefined') return '';
  try {
    const value = window.localStorage.getItem(PERSISTENT_STORAGE_KEY);
    if (!value) return '';
    const parsed: unknown = JSON.parse(value);
    return isRecord(parsed) && typeof parsed.model === 'string' ? parsed.model.trim() : '';
  } catch (error) {
    logger.warn('Unable to read governed AI model configuration', error);
    return '';
  }
}

export function getAiConfig(): AiApiConfig {
  return {
    endpoint: GOVERNED_AI_PROXY_PATH,
    apiKey: '',
    model: readStoredModel() || import.meta.env.VITE_AI_MODEL?.trim() || '',
  };
}

function endpointIsGoverned(endpoint: string): boolean {
  const value = endpoint.trim();
  if (!value || value === GOVERNED_AI_PROXY_PATH) return true;
  if (typeof window === 'undefined') return false;
  try {
    const resolved = new URL(value, window.location.origin);
    return resolved.origin === window.location.origin && resolved.pathname === GOVERNED_AI_PROXY_PATH;
  } catch {
    return false;
  }
}

export function saveAiConfig(config: AiApiConfig): void {
  if (config.apiKey.trim()) throw new Error('Browser API keys are prohibited; configure secrets on the server proxy.');
  if (!endpointIsGoverned(config.endpoint)) {
    throw new Error(`AI requests are restricted to the same-origin ${GOVERNED_AI_PROXY_PATH} proxy.`);
  }
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(PERSISTENT_STORAGE_KEY, JSON.stringify({ model: config.model.trim() }));
    window.sessionStorage.removeItem(LEGACY_SESSION_KEY_STORAGE_KEY);
  } catch (error) {
    logger.error('Unable to save governed AI model configuration', error);
    throw new Error('This browser blocked AI model settings storage.', { cause: error });
  }
}

export function clearAiConfig(): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.removeItem(PERSISTENT_STORAGE_KEY);
    window.sessionStorage.removeItem(LEGACY_SESSION_KEY_STORAGE_KEY);
  } catch (error) {
    logger.error('Unable to clear governed AI settings', error);
    throw new Error('This browser blocked clearing AI settings.', { cause: error });
  }
}

export function isAiConfigured(): boolean {
  return Boolean(getAiConfig().model);
}

function requireModel(): string {
  const model = getAiConfig().model;
  if (!model) throw new Error('AI model is not configured. Select a server-approved model identifier.');
  return model;
}

function safeProperties(product: Product): Array<Record<string, unknown>> {
  return Object.entries(product.properties)
    .filter(([name]) => !isIdentityBearingFieldName(name))
    .flatMap(([name, property]) => {
      const value = property?.value;
      if (typeof value !== 'string' && !(typeof value === 'number' && Number.isFinite(value))) return [];
      return [{
        property: name.slice(0, 120),
        value,
        ...(property?.unit ? { unit: property.unit.slice(0, 40) } : {}),
        ...(property?.standard ? { method: property.standard.slice(0, 120) } : {}),
        ...(property?.temperature !== undefined ? { condition: String(property.temperature).slice(0, 80) } : {}),
      }];
    });
}

function summarizeProducts(products: Product[], limit = MAX_CONTEXT_PRODUCTS): Array<Record<string, unknown>> {
  return products.slice(0, limit).map((product, index) => ({
    recordAlias: `record-${index + 1}`,
    properties: safeProperties(product),
  }));
}

function normalizeFreeText(value: string, label: string): string {
  const normalized = value.normalize('NFKC').replace(new RegExp(`[${String.fromCharCode(0)}-${String.fromCharCode(31)}${String.fromCharCode(127)}]`, 'g'), ' ').replace(/\s+/g, ' ').trim();
  if (normalized.length > MAX_QUERY_CHARS) throw new Error(`${label} exceeds the governed text limit`);
  return normalized;
}

function stripMarkdownFence(text: string): string {
  const trimmed = text.trim();
  const fenced = trimmed.match(/^```(?:json)?\s*([\s\S]*?)\s*```$/i);
  return fenced ? fenced[1].trim() : trimmed;
}

function parseJson<T>(text: string, fallback: T, context: string): T {
  try {
    return JSON.parse(stripMarkdownFence(text)) as T;
  } catch (error) {
    logger.warn(`Unable to parse ${context} JSON response`, error);
    return fallback;
  }
}

function isRecommendationItem(value: unknown): value is { id: string; reason: string } {
  return isRecord(value) && typeof value.id === 'string' && typeof value.reason === 'string';
}

function normalizeRecommendations(value: unknown): RecommendationResponse {
  if (!isRecord(value) || !Array.isArray(value.recommendations)) return { recommendations: [] };
  return { recommendations: value.recommendations.filter(isRecommendationItem) };
}

function isChemicalSuggestion(value: unknown): value is ChemicalSuggestion {
  return (
    isRecord(value) &&
    typeof value.chemicalName === 'string' &&
    typeof value.replacement === 'string' &&
    typeof value.impact === 'string' &&
    typeof value.rationale === 'string' &&
    (typeof value.confidenceScore === 'number' || typeof value.confidenceScore === 'string') &&
    (value.formulaUpdate === undefined || typeof value.formulaUpdate === 'string')
  );
}

function normalizeChemicalSuggestions(value: unknown): AiSuggestionEngineResponse {
  if (!isRecord(value)) return { overview: '', suggestions: [] };
  const overview = typeof value.overview === 'string' ? value.overview : '';
  const suggestions = Array.isArray(value.suggestions)
    ? value.suggestions.filter(isChemicalSuggestion).slice(0, 3).map((suggestion) => ({
        ...suggestion,
        confidenceScore: Math.max(0, Math.min(100, Number(suggestion.confidenceScore) || 0)),
      }))
    : [];
  return { overview, suggestions };
}

function extractResponseText(payload: unknown): string {
  if (!isRecord(payload)) return '';
  if (typeof payload.text === 'string') return payload.text;
  if (typeof payload.outputText === 'string') return payload.outputText;
  const choices = payload.choices;
  if (!Array.isArray(choices) || choices.length === 0 || !isRecord(choices[0])) return '';
  const message = choices[0].message;
  return isRecord(message) && typeof message.content === 'string' ? message.content : '';
}

async function requestProxy(options: ProxyRequestOptions): Promise<string> {
  const controller = new AbortController();
  const timer = globalThis.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await governedAiFetch({
      model: requireModel(),
      purpose: options.purpose,
      payload: {
        task: options.purpose,
        instructions: normalizeFreeText(options.instructions, 'AI instructions'),
        query: normalizeFreeText(options.query, 'AI query'),
        temperature: options.temperature ?? 0.3,
        ...(options.data ? { data: options.data } : {}),
      },
      signal: controller.signal,
    });
    const announced = Number(response.headers.get('content-length'));
    if (Number.isFinite(announced) && announced > MAX_RESPONSE_CHARS) {
      throw new Error('AI proxy response is too large to process safely.');
    }
    const raw = await response.text();
    if (raw.length > MAX_RESPONSE_CHARS) throw new Error('AI proxy response is too large to process safely.');
    if (!response.ok) throw new Error(`AI proxy request failed (${response.status}).`);
    let payload: unknown;
    try {
      payload = JSON.parse(raw);
    } catch {
      return raw;
    }
    const text = extractResponseText(payload);
    if (!text) throw new Error('AI proxy returned no readable text content.');
    return text;
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error(`AI proxy request timed out after ${REQUEST_TIMEOUT_MS / 1000} seconds.`, { cause: error });
    }
    throw error;
  } finally {
    globalThis.clearTimeout(timer);
  }
}

const MATERIALS_INSTRUCTIONS = `Analyze only the supplied de-identified material-property data. Separate observations, calculations, and hypotheses. Never claim certification, external-tool execution, manufacturer facts, or official specifications. State missing evidence explicitly.`;

export async function testAiConnection(): Promise<string> {
  return requestProxy({ purpose: 'connectivity', instructions: 'Return exactly OK.', query: 'Connectivity check.', temperature: 0 });
}

export async function getAiInsights(products: Product[], options: AiInsightOptions | string): Promise<string> {
  const input = typeof options === 'string' ? { query: options } : options;
  if (input.imagePart) throw new Error('Browser image egress is disabled; use a governed server-side upload workflow.');
  return requestProxy({
    purpose: 'material-summary',
    instructions: MATERIALS_INSTRUCTIONS,
    query: input.query || 'Summarize the supplied de-identified property records.',
    temperature: input.isDeepThinking ? 0.25 : 0.35,
    data: { records: summarizeProducts(products, 10) },
  });
}

export async function getSmartRecommendations(currentProduct: Product, allProducts: Product[]): Promise<RecommendationResponse> {
  const candidates = allProducts.filter((product) => product.id !== currentProduct.id).slice(0, MAX_CONTEXT_PRODUCTS);
  if (candidates.length === 0) return { recommendations: [] };
  const aliases = new Map(candidates.map((product, index) => [`candidate-${index + 1}`, product.id]));
  try {
    const text = await requestProxy({
      purpose: 'material-comparison',
      instructions: `${MATERIALS_INSTRUCTIONS} Return JSON with recommendations using only candidate aliases.`,
      query: 'Select at most three technically relevant alternatives.',
      temperature: 0.2,
      data: {
        target: summarizeProducts([currentProduct], 1)[0],
        candidates: candidates.map((product, index) => ({
          candidateAlias: `candidate-${index + 1}`,
          properties: safeProperties(product),
        })),
      },
    });
    const parsed = normalizeRecommendations(parseJson<unknown>(text, {}, 'recommendations'));
    return {
      recommendations: parsed.recommendations.flatMap((item) => {
        const id = aliases.get(item.id);
        return id && item.reason.trim() ? [{ id, reason: item.reason }] : [];
      }).slice(0, 3),
    };
  } catch (error) {
    logger.error('Governed AI recommendation request failed', error);
    return { recommendations: [] };
  }
}

export async function getChemicalReplacementSuggestions(
  currentFormula: { name: string; expression: string; description: string; unit: string },
  allProducts: Product[],
  targetProperty = 'Durability',
  customNotes?: string,
): Promise<AiSuggestionEngineResponse> {
  const text = await requestProxy({
    purpose: 'formulation-hypothesis',
    instructions: `${MATERIALS_INSTRUCTIONS} Return JSON with overview and up to three testable suggestions.`,
    query: `Develop hypotheses for ${normalizeFreeText(targetProperty, 'Target property')}.`,
    temperature: 0.3,
    data: {
      selectedExpressionUnit: currentFormula.unit.slice(0, 40),
      constraints: normalizeFreeText(customNotes || 'No additional constraints supplied.', 'Constraints'),
      referenceRecords: summarizeProducts(allProducts),
    },
  });
  return normalizeChemicalSuggestions(parseJson<unknown>(text, {}, 'chemical suggestions'));
}

function _normalizeGeneratedProperties(value: unknown): Record<string, PropertyValue> {
  if (!isRecord(value)) return {};
  const result: Record<string, PropertyValue> = {};
  for (const [key, property] of Object.entries(value)) {
    if (!key.trim() || !isRecord(property) || isIdentityBearingFieldName(key)) continue;
    if (typeof property.value !== 'string' && !(typeof property.value === 'number' && Number.isFinite(property.value))) continue;
    result[key] = {
      value: property.value,
      ...(typeof property.unit === 'string' ? { unit: property.unit } : {}),
      ...(typeof property.standard === 'string' ? { standard: property.standard } : {}),
      ...(typeof property.temperature === 'string' ? { temperature: property.temperature } : {}),
    };
  }
  return result;
}

export const aiService = {
  generateProductProperties: async (): Promise<Record<string, PropertyValue>> => {
    throw new Error('Identity-bearing grade/manufacturer property generation is disabled in browser egress.');
  },

  analyzeProduct: async (product: Product): Promise<string> => requestProxy({
    purpose: 'record-analysis',
    instructions: MATERIALS_INSTRUCTIONS,
    query: 'Analyze this de-identified resin property record and identify missing validation data.',
    data: { record: summarizeProducts([product], 1)[0] },
  }),
};
