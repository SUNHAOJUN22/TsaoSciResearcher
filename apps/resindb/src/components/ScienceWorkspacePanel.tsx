import { useState } from 'react';
import { canonicalBytes } from '@/sharedCanonical';

interface WorkspaceStatus {
  product: string;
  edition: string;
  runtime_capabilities: number;
  external_execution: string;
  distribution_status: string;
}

const EXAMPLE = {
  schema_version: 'tsao.workflow/1', id: 'local-reference-plan', tasks: [{
    id: 'curve', capability: 'processing.first_order', depends_on: [],
    payload: { times: [0, 1, 2, 5, 10], time_unit: 's', rate_constant: { value: 0.1, unit: '1/s' } },
  }],
};

/** Planning and evidence inspection only. No browser-triggered solver execution. */
export function ScienceWorkspacePanel() {
  const [status, setStatus] = useState<WorkspaceStatus | null>(null);
  const [output, setOutput] = useState('尚未连接统一工作台。');
  const [busy, setBusy] = useState(false);

  async function inspect() {
    setBusy(true);
    try {
      const response = await fetch('/api/science/status', { cache: 'no-store' });
      if (!response.ok) throw new Error(`工作台返回 ${response.status}`);
      const value: unknown = await response.json();
      if (typeof value !== 'object' || value === null || !('product' in value) || value.product !== 'TsaoScience') {
        throw new Error('不是有效的统一工作台响应。');
      }
      setStatus(value as WorkspaceStatus);
      setOutput(JSON.stringify(value, null, 2));
    } catch (error) {
      setStatus(null);
      setOutput(`未连接。请在统一仓库运行 python -m tsao_science serve。${String(error)}`);
    } finally { setBusy(false); }
  }

  async function previewPlan() {
    setBusy(true);
    try {
      const requestBytes = canonicalBytes(EXAMPLE);
      const hash = await globalThis.crypto.subtle.digest('SHA-256', requestBytes);
      const expected = [...new Uint8Array(hash)].map((value) => value.toString(16).padStart(2, '0')).join('');
      const response = await fetch('/api/science/plan', {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Tsao-Client': 'workspace' },
        body: JSON.stringify(EXAMPLE), cache: 'no-store',
      });
      const value: unknown = await response.json();
      if (!response.ok) throw new Error(JSON.stringify(value));
      if (typeof value !== 'object' || value === null || !('workflow_digest' in value) || value.workflow_digest !== expected) {
        throw new Error('跨语言任务摘要不一致，拒绝接收计划。');
      }
      setOutput(JSON.stringify(value, null, 2));
    } catch (error) { setOutput(`计划检查失败：${String(error)}`); }
    finally { setBusy(false); }
  }

  return (
    <details className="border-b border-slate-200 bg-white px-4 py-2 text-sm dark:border-slate-800 dark:bg-slate-950 print:hidden" data-testid="science-workspace-panel">
      <summary className="cursor-pointer font-semibold">TsaoScience · 统一科研工作台 {status ? `· ${status.edition}` : '· 未连接'}</summary>
      <p className="my-2">研究、计算、DFT、过程模型与材料数据使用同一任务和证据合同。此面板只检查计划，不执行商业软件。</p>
      <div className="flex gap-3">
        <button type="button" disabled={busy} onClick={() => { void inspect(); }} className="rounded border px-3 py-1">检查连接</button>
        <button type="button" disabled={busy} onClick={() => { void previewPlan(); }} className="rounded border px-3 py-1">检查参考计算计划</button>
      </div>
      <pre className="mt-2 max-h-52 overflow-auto whitespace-pre-wrap text-xs" aria-live="polite">{output}</pre>
    </details>
  );
}
