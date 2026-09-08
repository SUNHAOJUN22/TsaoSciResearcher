import { useState } from 'react';
import {
  getWorkspaceStatus, getWorkspaceExamples, previewWorkflow, verifyWorkspaceRecord,
  type WorkspaceStatus, type WorkspaceExample,
} from '@/services/scienceWorkspace';

/** One source registry, one planner and one result verifier; no browser solver execution. */
export function ScienceWorkspacePanel() {
  const [status, setStatus] = useState<WorkspaceStatus | null>(null);
  const [examples, setExamples] = useState<WorkspaceExample[]>([]);
  const [selected, setSelected] = useState('');
  const [output, setOutput] = useState('运行 python -m tsao_science serve 后连接统一工作台。');
  const [busy, setBusy] = useState(false);
  async function inspect() {
    setBusy(true);
    try {
      const [value, workflows] = await Promise.all([getWorkspaceStatus(), getWorkspaceExamples()]);
      setStatus(value); setExamples(workflows); setSelected(workflows[0]?.id ?? '');
      setOutput(JSON.stringify(value, null, 2));
    } catch (error) {
      setStatus(null); setExamples([]); setOutput(`连接检查失败：${String(error)}`);
    } finally { setBusy(false); }
  }
  async function preview() {
    const item = examples.find((entry) => entry.id === selected);
    if (!item) return;
    setBusy(true);
    try { setOutput(JSON.stringify(await previewWorkflow(item.workflow), null, 2)); }
    catch (error) { setOutput(`计划检查失败：${String(error)}`); }
    finally { setBusy(false); }
  }
  async function importResult(file: File | undefined) {
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) { setOutput('记录超过 2 MiB 限制。'); return; }
    setBusy(true);
    try { setOutput(JSON.stringify(await verifyWorkspaceRecord(await file.text()), null, 2)); }
    catch (error) { setOutput(`记录核验失败：${String(error)}`); }
    finally { setBusy(false); }
  }
  return (
    <details className="border-b border-slate-200 bg-white px-4 py-2 text-sm dark:border-slate-800 dark:bg-slate-950 print:hidden" data-testid="science-workspace-panel">
      <summary className="cursor-pointer font-semibold">TsaoScience · 统一科研工作台 {status ? `· ${status.edition}` : '· 未连接'}</summary>
      <p className="my-2">从同一仓库读取工作流，预检任务，核验本地 result.json。参考计算、仿真、实测与假设保留各自标识。</p>
      <div className="flex flex-wrap items-center gap-3">
        <button type="button" disabled={busy} onClick={() => { void inspect(); }} className="rounded border px-3 py-1">连接与检查</button>
        <select aria-label="选择统一工作流" value={selected} disabled={busy || examples.length === 0} onChange={(event) => setSelected(event.target.value)} className="rounded border px-3 py-1 dark:bg-slate-900">
          {examples.length === 0 && <option value="">先连接工作台</option>}
          {examples.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
        </select>
        <button type="button" disabled={busy || !selected} onClick={() => { void preview(); }} className="rounded border px-3 py-1">检查所选计划</button>
        <label className="rounded border px-3 py-1">核验计算记录
          <input aria-label="导入计算记录" type="file" accept=".json,application/json" disabled={busy} onChange={(event) => { void importResult(event.target.files?.[0]); event.target.value = ''; }} className="ml-2 max-w-52" />
        </label>
      </div>
      <p className="mt-2 text-xs">记录只提交同源科研网关，不转发至 AI。完整性通过不代表实测真实性或科学批准；此界面不执行求解器，也不自动修改材料数据库。</p>
      <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap text-xs" aria-live="polite">{output}</pre>
    </details>
  );
}
