import { canonicalBytes } from '@/sharedCanonical';

export interface WorkspaceExample { id: string; label: string; workflow: Record<string, unknown> }
export interface WorkspaceStatus {
  product: 'TsaoScience'; edition: string; runtime_capabilities: number;
  external_execution: string; distribution_status: string;
}
function object(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
async function request(path: string, body?: string): Promise<unknown> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 20_000);
  try {
    const response = await fetch(`/api/science/${path}`, {
      method: body === undefined ? 'GET' : 'POST', cache: 'no-store', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-Tsao-Client': 'workspace' },
      body, signal: controller.signal,
    });
    const value: unknown = await response.json();
    if (!response.ok) throw new Error(`工作台请求被拒绝 (${response.status})`);
    return value;
  } finally { clearTimeout(timer); }
}
export async function getWorkspaceStatus(): Promise<WorkspaceStatus> {
  const data = await request('status');
  if (!object(data) || data.product !== 'TsaoScience' || typeof data.edition !== 'string'
    || typeof data.runtime_capabilities !== 'number' || !Number.isInteger(data.runtime_capabilities)
    || data.runtime_capabilities < 0 || typeof data.external_execution !== 'string'
    || typeof data.distribution_status !== 'string') throw new Error('无效的工作台状态。');
  return data as unknown as WorkspaceStatus;
}
export async function getWorkspaceExamples(): Promise<WorkspaceExample[]> {
  const data = await request('examples');
  if (!object(data) || !Array.isArray(data.examples) || data.examples.length > 20) throw new Error('无效的工作流目录。');
  const seen = new Set<string>();
  return data.examples.map((row: unknown) => {
    if (!object(row) || typeof row.id !== 'string' || !row.id || seen.has(row.id)
      || typeof row.label !== 'string' || !object(row.workflow)) throw new Error('无效的工作流条目。');
    seen.add(row.id);
    return { id: row.id, label: row.label, workflow: row.workflow };
  });
}
export async function previewWorkflow(workflow: Record<string, unknown>): Promise<unknown> {
  // Snapshot BEFORE awaiting. Hash and send the same graph, not a mutable UI object.
  canonicalBytes(workflow);
  const body = JSON.stringify(workflow);
  if (new TextEncoder().encode(body).length > 64 * 1024) throw new Error('计划超过大小限制。');
  const hash = await crypto.subtle.digest('SHA-256', canonicalBytes(JSON.parse(body)));
  const expected = Array.from(new Uint8Array(hash), (v) => v.toString(16).padStart(2, '0')).join('');
  const data = await request('plan', body);
  if (!object(data) || data.workflow_digest !== expected || data.execution !== 'NOT_EXECUTED'
    || data.external_solver_executed !== false) throw new Error('任务摘要或执行边界不一致。');
  return data;
}
export async function verifyWorkspaceRecord(text: string): Promise<Record<string, unknown>> {
  if (new TextEncoder().encode(text).length > 2 * 1024 * 1024) throw new Error('记录超过 2 MiB 限制。');
  const value: unknown = JSON.parse(text);
  if (!object(value) || !['tsao.run/1', 'tsao.run/2'].includes(String(value.schema_version))) throw new Error('不是支持的计算记录。');
  const response = await request('verify', text);
  if (!object(response) || response.integrity !== 'PASS' || response.external_solver_executed !== false
    || response.scientific_approval !== 'NOT_EVALUATED' || !Array.isArray(response.observations)
    || response.source_authenticity !== 'NOT_AUTHENTICATED') throw new Error('无效的记录核验响应。');
  return response;
}
