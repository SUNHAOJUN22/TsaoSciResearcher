import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Copy,
  Cpu,
  Download,
  FileSearch,
  Gauge,
  Loader2,
  Play,
  Square,
  Trash2,
  Upload,
} from 'lucide-react';
import {
  createKMeansProfileAuditDocument,
  validateKMeansProfileAuditImport,
  type KMeansProfileAuditDocument,
  type KMeansProfileAuditImportValidation,
} from '@/compute/kmeansProfileAudit';
import { createKMeansWorkerBenchmarkEnvironment } from '@/compute/kmeansWorkerEnvironment';
import { useLanguage } from '@/contexts/LanguageContext';
import { useKMeansBackendCalibration } from '@/hooks/workers/useKMeansBackendCalibration';

function formatTimestamp(value: string | null, language: string): string {
  if (!value) return '—';
  const timestamp = Date.parse(value);
  if (!Number.isFinite(timestamp)) return '—';
  return new Intl.DateTimeFormat(language === 'en' ? 'en-US' : 'zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(timestamp);
}

export interface KMeansBackendCalibrationPanelProps {
  sampleCount?: number;
  dimensions?: number;
}

export function KMeansBackendCalibrationPanel({
  sampleCount = 0,
  dimensions = 2,
}: KMeansBackendCalibrationPanelProps = {}) {
  const { language } = useLanguage();
  const [expanded, setExpanded] = useState(false);
  const [auditExpanded, setAuditExpanded] = useState(false);
  const [audit, setAudit] = useState<KMeansProfileAuditDocument | null>(null);
  const [auditError, setAuditError] = useState<string | null>(null);
  const [auditImportValidation, setAuditImportValidation] = useState<KMeansProfileAuditImportValidation | null>(null);
  const [isAuditLoading, setIsAuditLoading] = useState(false);
  const [copyStatus, setCopyStatus] = useState<string | null>(null);
  const auditFileInputRef = useRef<HTMLInputElement>(null);
  const {
    profileState,
    isLoadingProfile,
    isPersistingProfile,
    isCalibrating,
    benchmarkResult,
    benchmarkError,
    benchmarkProgress,
    storageError,
    runCalibration,
    cancelCalibration,
    clearProfile,
  } = useKMeansBackendCalibration();

  const english = language === 'en';
  const profile = profileState.profile;
  const progress = Math.round((benchmarkProgress?.ratio ?? 0) * 100);
  const maxClusters = useMemo(
    () => Math.max(1, Math.min(10, Math.floor(sampleCount / 2))),
    [sampleCount],
  );
  const statusLabel = profileState.status === 'valid'
    ? profile?.status === 'wasm-beneficial'
      ? (english ? 'Local WASM profile ready' : '本机 WASM 配置已就绪')
      : profile?.status === 'typescript-preferred'
        ? (english ? 'Local TypeScript preference' : '本机优先使用 TypeScript')
        : (english ? 'Local evidence is inconclusive' : '本机证据尚不充分')
    : profileState.status === 'missing'
      ? (english ? 'No local calibration profile' : '尚无本机校准配置')
      : (english ? 'Local profile unavailable' : '本机配置不可用');

  const generateAudit = useCallback(async () => {
    setIsAuditLoading(true);
    setAuditError(null);
    try {
      const document = await createKMeansProfileAuditDocument(profileState, {
        sampleCount,
        dimensions,
        maxClusters,
      });
      setAudit(document);
      return document;
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setAuditError(message);
      return null;
    } finally {
      setIsAuditLoading(false);
    }
  }, [dimensions, maxClusters, profileState, sampleCount]);

  useEffect(() => {
    setAudit(null);
    setCopyStatus(null);
    setAuditImportValidation(null);
    if (auditExpanded) void generateAudit();
  }, [auditExpanded, generateAudit]);

  const downloadAudit = useCallback(async () => {
    const document = audit ?? await generateAudit();
    if (!document) return;
    const blob = new Blob([`${JSON.stringify(document, null, 2)}\n`], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const anchor = window.document.createElement('a');
    anchor.href = url;
    anchor.download = `resindb-kmeans-profile-audit-${document.digest.slice(0, 12)}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }, [audit, generateAudit]);

  const copyAuditSummary = useCallback(async () => {
    const document = audit ?? await generateAudit();
    if (!document) return;
    const decision = document.autoDecision
      ? `${document.autoDecision.selectedBackend}:${document.autoDecision.reason}`
      : 'unavailable';
    const summary = [
      `schema=${document.schemaVersion}`,
      `digest=${document.digest}`,
      `environment=${document.environment?.fingerprint ?? 'unavailable'}`,
      `decision=${decision}`,
      `notice=${document.notice}`,
      `importPolicy=${document.importPolicy}`,
    ].join('\n');
    try {
      if (!navigator.clipboard?.writeText) {
        throw new Error('Clipboard API is unavailable');
      }
      await navigator.clipboard.writeText(summary);
      setCopyStatus(english ? 'Audit summary copied' : '审计摘要已复制');
    } catch (error) {
      setAuditError(error instanceof Error ? error.message : String(error));
    }
  }, [audit, english, generateAudit]);

  const importAudit = useCallback(async (file: File) => {
    setAuditError(null);
    setAuditImportValidation(null);
    try {
      const parsed = JSON.parse(await file.text()) as unknown;
      const validation = await validateKMeansProfileAuditImport(
        parsed,
        createKMeansWorkerBenchmarkEnvironment(),
      );
      setAuditImportValidation(validation);
      if (validation.valid && validation.document) setAudit(validation.document);
    } catch (error) {
      setAuditError(error instanceof Error ? error.message : String(error));
    }
  }, []);

  return (
    <div
      data-testid="kmeans-backend-calibration"
      className="absolute right-3 top-3 z-20 w-[min(24rem,calc(100%-1.5rem))] rounded-2xl border border-slate-200/90 bg-white/95 shadow-xl backdrop-blur dark:border-slate-700 dark:bg-slate-950/95"
    >
      <button
        type="button"
        data-testid="kmeans-calibration-toggle"
        onClick={() => setExpanded((value) => !value)}
        className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left"
      >
        <span className="flex min-w-0 items-center gap-2">
          <Gauge size={15} className="shrink-0 text-indigo-500" />
          <span className="truncate text-[11px] font-black uppercase tracking-wide text-slate-700 dark:text-slate-200">
            {english ? 'K-Means device calibration' : 'K-Means 本机性能校准'}
          </span>
        </span>
        <span className="text-[10px] font-bold text-slate-400">{expanded ? '−' : '+'}</span>
      </button>

      {expanded && (
        <div className="space-y-3 border-t border-slate-100 px-3 py-3 text-[11px] dark:border-slate-800">
          <div className="flex items-start gap-2">
            {profileState.status === 'valid' ? (
              <CheckCircle2 size={14} className="mt-0.5 shrink-0 text-emerald-500" />
            ) : (
              <Cpu size={14} className="mt-0.5 shrink-0 text-slate-400" />
            )}
            <div className="min-w-0">
              <div className="font-bold text-slate-700 dark:text-slate-200">
                {isLoadingProfile ? (english ? 'Loading local profile…' : '正在读取本机配置…') : statusLabel}
              </div>
              {profile && (
                <div className="mt-1 space-y-0.5 text-slate-500 dark:text-slate-400">
                  <div>{english ? 'Generated' : '生成时间'}: {formatTimestamp(profile.generatedAt, language)}</div>
                  <div>{english ? 'Expires' : '失效时间'}: {formatTimestamp(profile.expiresAt, language)}</div>
                  <div>
                    {english ? 'Crossover workload' : '交叉点工作量'}: {' '}
                    {profile.crossoverWorkloadOperations?.toLocaleString() ?? '—'}
                  </div>
                  <div className="truncate" title={profileState.environment?.fingerprint ?? ''}>
                    {english ? 'Environment' : '环境指纹'}: {profileState.environment?.fingerprint ?? '—'}
                  </div>
                </div>
              )}
              {profileState.migration && (
                <div
                  data-testid="kmeans-profile-migration-status"
                  className="mt-1 text-amber-600 dark:text-amber-300"
                >
                  {english ? 'Migration' : '迁移状态'}: {profileState.migration.reason}
                  {profileState.migration.requiresRecalibration
                    ? (english ? ' — recalibration required' : ' — 需要重新校准')
                    : (english ? ' — compatible re-key' : ' — 兼容重编码')}
                </div>
              )}
            </div>
          </div>

          <p
            data-testid="kmeans-calibration-privacy"
            className="rounded-xl bg-slate-50 px-2.5 py-2 leading-relaxed text-slate-500 dark:bg-slate-900 dark:text-slate-400"
          >
            {english
              ? 'Calibration runs in a browser Worker. The profile stays in IndexedDB on this device and is never uploaded.'
              : '校准在浏览器 Worker 中运行；配置仅保存在本机 IndexedDB，不会上传。'}
          </p>

          {isCalibrating && (
            <div className="space-y-1">
              <div className="flex items-center justify-between text-slate-500 dark:text-slate-400">
                <span>{benchmarkProgress?.phase ?? (english ? 'Benchmarking' : '正在校准')}</span>
                <span>{progress}%</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                <div className="h-full bg-indigo-500 transition-all" style={{ width: `${progress}%` }} />
              </div>
            </div>
          )}

          {(benchmarkError || storageError || auditError) && (
            <div className="flex items-start gap-2 rounded-xl bg-amber-50 px-2.5 py-2 text-amber-700 dark:bg-amber-950/30 dark:text-amber-300">
              <AlertTriangle size={13} className="mt-0.5 shrink-0" />
              <span>{benchmarkError ?? storageError ?? auditError}</span>
            </div>
          )}

          {benchmarkResult && !isPersistingProfile && !storageError && (
            <div className="rounded-xl bg-emerald-50 px-2.5 py-2 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300">
              {english ? 'Calibration completed and stored locally.' : '校准已完成并保存在本机。'}
            </div>
          )}

          <div className="grid grid-cols-2 gap-2">
            {isCalibrating ? (
              <button
                type="button"
                onClick={() => cancelCalibration('K-Means device calibration cancelled by the user')}
                className="flex items-center justify-center gap-1.5 rounded-xl bg-amber-100 px-2 py-2 font-bold text-amber-700 hover:bg-amber-200 dark:bg-amber-950/40 dark:text-amber-300"
              >
                <Square size={12} />
                {english ? 'Cancel' : '取消'}
              </button>
            ) : (
              <button
                type="button"
                data-testid="kmeans-calibration-run"
                onClick={() => runCalibration('full')}
                disabled={isPersistingProfile}
                className="flex items-center justify-center gap-1.5 rounded-xl bg-indigo-600 px-2 py-2 font-bold text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isPersistingProfile ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
                {english ? 'Calibrate' : '运行校准'}
              </button>
            )}
            <button
              type="button"
              data-testid="kmeans-calibration-clear"
              onClick={() => void clearProfile()}
              disabled={isCalibrating || isPersistingProfile || profileState.status === 'missing'}
              className="flex items-center justify-center gap-1.5 rounded-xl bg-slate-100 px-2 py-2 font-bold text-slate-600 hover:bg-slate-200 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
            >
              <Trash2 size={12} />
              {english ? 'Clear' : '清除配置'}
            </button>
          </div>

          <button
            type="button"
            data-testid="kmeans-audit-toggle"
            onClick={() => setAuditExpanded((value) => !value)}
            className="flex w-full items-center justify-center gap-1.5 rounded-xl border border-slate-200 px-2 py-2 font-bold text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-900"
          >
            <FileSearch size={12} />
            {auditExpanded
              ? (english ? 'Hide audit details' : '收起审计详情')
              : (english ? 'Profile audit details' : '配置审计详情')}
          </button>

          {auditExpanded && (
            <div
              data-testid="kmeans-audit-details"
              className="space-y-2 rounded-xl border border-slate-200 p-2.5 text-slate-500 dark:border-slate-700 dark:text-slate-400"
            >
              {isAuditLoading ? (
                <div className="flex items-center gap-2"><Loader2 size={12} className="animate-spin" />{english ? 'Generating audit…' : '正在生成审计…'}</div>
              ) : audit ? (
                <>
                  <div>{english ? 'Validation state' : '校验状态'}: <strong>{audit.profileLoad.status}</strong></div>
                  <div>{english ? 'Profile schema' : '配置 Schema'}: {audit.profile?.schemaVersion ?? '—'}</div>
                  <div>{english ? 'Kernel' : '内核'}: {audit.profile ? `${audit.profile.kernel}@${audit.profile.kernelVersion}` : '—'}</div>
                  <div>{english ? 'Protocol' : '协议'}: {audit.profile?.protocolVersion ?? '—'}</div>
                  <div>{english ? 'Generated' : '生成时间'}: {formatTimestamp(audit.profile?.generatedAt ?? null, language)}</div>
                  <div>{english ? 'Expires' : '失效时间'}: {formatTimestamp(audit.profile?.expiresAt ?? null, language)}</div>
                  <div className="break-all">{english ? 'Environment fingerprint' : '环境指纹'}: {audit.environment?.fingerprint ?? '—'}</div>
                  <div className="break-all">{english ? 'Benchmark digest' : 'Benchmark 摘要'}: {audit.profile?.benchmarkReportDigest ?? '—'}</div>
                  <div>{english ? 'Decision status' : '决策状态'}: {audit.profile?.status ?? '—'}</div>
                  <div>{english ? 'Crossover workload' : '交叉点工作量'}: {audit.profile?.crossoverWorkloadOperations?.toLocaleString() ?? '—'}</div>
                  <div>{english ? 'Decision history entries' : '决策历史条数'}: {audit.decisionHistory.length}</div>
                  <div>{english ? 'Auto decision' : '当前自动决策'}: <strong>{audit.autoDecision?.selectedBackend ?? '—'}</strong></div>
                  <div>{english ? 'Reason' : '决策原因'}: {audit.autoDecision?.reason ?? '—'}</div>
                  <div className="break-all">Audit SHA-256: {audit.digest}</div>
                  <p className="rounded-lg bg-amber-50 px-2 py-1.5 text-amber-700 dark:bg-amber-950/30 dark:text-amber-300">
                    {english
                      ? 'Device-local audit metadata only. Imported files are revalidated for read-only inspection and can never activate a runtime profile.'
                      : '仅为本机审计元数据。导入文件会重新校验，但只可查看，永远不能激活运行时配置。'}
                  </p>
                  {auditImportValidation && (
                    <div
                      data-testid="kmeans-audit-import-status"
                      className={auditImportValidation.valid
                        ? 'text-emerald-600 dark:text-emerald-300'
                        : 'text-amber-600 dark:text-amber-300'}
                    >
                      {auditImportValidation.valid
                        ? (english ? 'Imported audit verified: read-only only.' : '导入审计已验证：仅可只读查看。')
                        : auditImportValidation.reason}
                    </div>
                  )}
                  {copyStatus && <div className="text-emerald-600 dark:text-emerald-300">{copyStatus}</div>}
                  <input
                    ref={auditFileInputRef}
                    data-testid="kmeans-audit-import-input"
                    type="file"
                    accept="application/json,.json"
                    className="hidden"
                    onChange={(event) => {
                      const file = event.target.files?.[0];
                      event.target.value = '';
                      if (file) void importAudit(file);
                    }}
                  />
                  <div className="grid grid-cols-3 gap-2">
                    <button
                      type="button"
                      data-testid="kmeans-audit-copy"
                      onClick={() => void copyAuditSummary()}
                      className="flex items-center justify-center gap-1 rounded-lg bg-slate-100 px-1 py-1.5 font-bold text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300"
                    >
                      <Copy size={11} />
                      {english ? 'Copy' : '复制'}
                    </button>
                    <button
                      type="button"
                      data-testid="kmeans-audit-download"
                      onClick={() => void downloadAudit()}
                      className="flex items-center justify-center gap-1 rounded-lg bg-slate-100 px-1 py-1.5 font-bold text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300"
                    >
                      <Download size={11} />
                      {english ? 'Export' : '导出'}
                    </button>
                    <button
                      type="button"
                      data-testid="kmeans-audit-import"
                      onClick={() => auditFileInputRef.current?.click()}
                      className="flex items-center justify-center gap-1 rounded-lg bg-slate-100 px-1 py-1.5 font-bold text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300"
                    >
                      <Upload size={11} />
                      {english ? 'Import' : '导入'}
                    </button>
                  </div>
                </>
              ) : (
                <div>{english ? 'Audit metadata is unavailable.' : '审计元数据不可用。'}</div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
