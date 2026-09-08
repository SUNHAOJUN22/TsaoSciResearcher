import { afterEach, describe, expect, it, vi } from 'vitest';
import { getWorkspaceStatus, getWorkspaceExamples, previewWorkflow, verifyWorkspaceRecord } from '@/services/scienceWorkspace';
import { canonicalBytes } from '@/sharedCanonical';

function reply(value: unknown, ok = true) {
  const fetch = vi.fn().mockResolvedValue({ ok, status: ok ? 200 : 400, json: async () => value });
  vi.stubGlobal('fetch', fetch); return fetch;
}
afterEach(() => vi.unstubAllGlobals());
describe('one scientific workspace', () => {
  it('accepts explicit source status', async () => {
    reply({ product: 'TsaoScience', edition: 'astra-pro-2', runtime_capabilities: 10, external_execution: 'NOT_EVALUATED', distribution_status: 'BLOCKED' });
    expect((await getWorkspaceStatus()).product).toBe('TsaoScience');
  });
  it.each([true, '10', NaN, -1, 1.5])('rejects invalid capability count %s', async (count) => {
    reply({ product: 'TsaoScience', edition: 'a2', runtime_capabilities: count, external_execution: 'NOT_EVALUATED', distribution_status: 'BLOCKED' });
    await expect(getWorkspaceStatus()).rejects.toThrow();
  });
  it('gets examples from the backend rather than a UI duplicate', async () => {
    const fetch = reply({ examples: [{ id: 'poe', label: '参考', workflow: { tasks: [] } }] });
    expect((await getWorkspaceExamples())[0].id).toBe('poe');
    expect(fetch.mock.calls[0][0]).toBe('/api/science/examples');
  });
  it('rejects duplicated example identities', async () => {
    const item = { id: 'x', label: 'x', workflow: {} }; reply({ examples: [item, item] });
    await expect(getWorkspaceExamples()).rejects.toThrow();
  });
  it('sends the same snapshot that was hashed', async () => {
    const workflow: Record<string, unknown> = { tasks: [], id: 'before' };
    const bytes = canonicalBytes(workflow);
    const digest = await crypto.subtle.digest('SHA-256', bytes);
    const expected = Array.from(new Uint8Array(digest), x => x.toString(16).padStart(2, '0')).join('');
    const fetch = reply({ workflow_digest: expected, execution: 'NOT_EXECUTED', external_solver_executed: false });
    const pending = previewWorkflow(workflow); workflow.id = 'after';
    await pending;
    expect(JSON.parse(fetch.mock.calls[0][1].body).id).toBe('before');
  });
  it('rejects digest mismatch', async () => {
    reply({ workflow_digest: 'wrong', execution: 'NOT_EXECUTED', external_solver_executed: false });
    await expect(previewWorkflow({ x: 1 })).rejects.toThrow();
  });
  it('retains imported result provenance limits', async () => {
    const fetch = reply({ integrity: 'PASS', external_solver_executed: false, scientific_approval: 'NOT_EVALUATED', source_authenticity: 'NOT_AUTHENTICATED', observations: [] });
    await verifyWorkspaceRecord('{"schema_version":"tsao.run/2"}');
    expect(fetch.mock.calls[0][0]).toBe('/api/science/verify');
  });
  it('rejects forged scientific approval in a verification reply', async () => {
    reply({ integrity: 'PASS', external_solver_executed: false, scientific_approval: 'APPROVED', observations: [] });
    await expect(verifyWorkspaceRecord('{"schema_version":"tsao.run/2"}')).rejects.toThrow();
  });
  it('rejects oversized records before fetch', async () => {
    const fetch = reply({});
    await expect(verifyWorkspaceRecord(' '.repeat(2 * 1024 * 1024 + 1))).rejects.toThrow();
    expect(fetch).not.toHaveBeenCalled();
  });
});
