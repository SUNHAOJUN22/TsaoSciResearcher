import React, { useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { AlertTriangle, CheckCircle2, Database, Loader2, RefreshCw, Server, Trash2, X } from 'lucide-react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useData } from '@/contexts/DataContext';
import { getValidPropertiesCount } from '@/utils/productUtils';

interface DatabaseSyncModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const DatabaseSyncModal: React.FC<DatabaseSyncModalProps> = ({ isOpen, onClose }) => {
  const { language } = useLanguage();
  const zh = language === 'zh';
  const { allProducts, refreshData, isRefreshing, syncEvents, handleDelete } = useData();
  const [isPruning, setIsPruning] = useState(false);
  const [confirmPrune, setConfirmPrune] = useState(false);

  const adapterType = import.meta.env.VITE_DATABASE_ADAPTER_TYPE === 'remote_api' ? 'remote_api' : 'indexeddb';
  const sparseProducts = useMemo(
    () => allProducts.filter((product) => getValidPropertiesCount(product.properties) < 2),
    [allProducts],
  );

  const pruneSparseRecords = async () => {
    if (!confirmPrune || sparseProducts.length === 0) return;
    setIsPruning(true);
    try {
      await handleDelete(sparseProducts.map((product) => product.id));
      setConfirmPrune(false);
    } finally {
      setIsPruning(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[150] flex items-center justify-center p-4">
          <motion.button
            type="button"
            aria-label="Close database status"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-slate-950/60 backdrop-blur-sm"
            onClick={onClose}
          />
          <motion.section
            role="dialog"
            aria-modal="true"
            initial={{ opacity: 0, scale: 0.97, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.97, y: 12 }}
            className="relative flex max-h-[86vh] w-full max-w-3xl flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-2xl dark:border-slate-800 dark:bg-slate-950"
          >
            <header className="flex items-center justify-between border-b border-slate-200 px-6 py-5 dark:border-slate-800">
              <div className="flex items-center gap-3">
                <div className="rounded-2xl bg-indigo-500/10 p-3 text-indigo-600 dark:text-indigo-400"><Database size={21} /></div>
                <div>
                  <h2 className="text-lg font-black text-slate-900 dark:text-white">{zh ? '数据库状态与维护' : 'Database Status & Maintenance'}</h2>
                  <p className="text-xs text-slate-500">{zh ? '仅显示真实适配器状态，不模拟第三方连接。' : 'Shows the actual adapter state; no simulated third-party connections.'}</p>
                </div>
              </div>
              <button type="button" onClick={onClose} className="rounded-xl p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-900"><X size={18} /></button>
            </header>

            <div className="grid gap-4 overflow-y-auto p-6 sm:grid-cols-3">
              <Metric icon={adapterType === 'remote_api' ? Server : Database} label={zh ? '当前适配器' : 'Active adapter'} value={adapterType === 'remote_api' ? 'Remote REST API' : 'IndexedDB'} />
              <Metric icon={CheckCircle2} label={zh ? '当前记录' : 'Current records'} value={String(allProducts.length)} />
              <Metric icon={AlertTriangle} label={zh ? '少于 2 个有效属性' : 'Fewer than 2 valid properties'} value={String(sparseProducts.length)} warning={sparseProducts.length > 0} />

              <div className="sm:col-span-3 rounded-2xl border border-slate-200 p-5 dark:border-slate-800">
                <h3 className="font-bold text-slate-900 dark:text-white">{zh ? '刷新数据' : 'Refresh data'}</h3>
                <p className="mt-1 text-sm leading-6 text-slate-500">
                  {adapterType === 'remote_api'
                    ? (zh ? '从已配置的远程 REST API 重新读取数据；失败时保留当前界面数据。' : 'Reload from the configured REST API. Current UI data is preserved if the request fails.')
                    : (zh ? '重新读取当前浏览器 IndexedDB。' : 'Reload the current browser IndexedDB store.')}
                </p>
                <button type="button" disabled={isRefreshing} onClick={() => void refreshData()} className="mt-4 inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-bold text-white disabled:opacity-50">
                  {isRefreshing ? <Loader2 className="animate-spin" size={16} /> : <RefreshCw size={16} />}
                  {zh ? '刷新' : 'Refresh'}
                </button>
              </div>

              <div className="sm:col-span-3 rounded-2xl border border-rose-200 bg-rose-50/60 p-5 dark:border-rose-900/50 dark:bg-rose-950/20">
                <h3 className="font-bold text-rose-800 dark:text-rose-200">{zh ? '删除稀疏记录' : 'Delete sparse records'}</h3>
                <p className="mt-1 text-sm leading-6 text-rose-700/80 dark:text-rose-300/80">
                  {zh ? '该操作永久删除有效属性少于 2 个的记录。请先导出备份；系统不会自动执行。' : 'Permanently deletes records with fewer than two valid properties. Export a backup first; this action is never automatic.'}
                </p>
                <label className="mt-4 flex items-center gap-2 text-sm text-rose-800 dark:text-rose-200">
                  <input type="checkbox" checked={confirmPrune} onChange={(event) => setConfirmPrune(event.target.checked)} />
                  {zh ? `确认删除 ${sparseProducts.length} 条记录` : `Confirm deletion of ${sparseProducts.length} records`}
                </label>
                <button type="button" disabled={!confirmPrune || sparseProducts.length === 0 || isPruning} onClick={() => void pruneSparseRecords()} className="mt-3 inline-flex items-center gap-2 rounded-xl bg-rose-600 px-4 py-2.5 text-sm font-bold text-white disabled:opacity-40">
                  {isPruning ? <Loader2 className="animate-spin" size={16} /> : <Trash2 size={16} />}
                  {zh ? '删除已确认记录' : 'Delete confirmed records'}
                </button>
              </div>

              <div className="sm:col-span-3 rounded-2xl border border-slate-200 p-5 dark:border-slate-800">
                <h3 className="font-bold text-slate-900 dark:text-white">{zh ? '最近同步事件' : 'Recent sync events'}</h3>
                <div className="mt-3 space-y-2">
                  {syncEvents.length === 0 ? (
                    <p className="text-sm text-slate-500">{zh ? '暂无同步事件。' : 'No sync events yet.'}</p>
                  ) : syncEvents.slice(0, 10).map((event) => (
                    <div key={event.id} className="flex items-start justify-between gap-4 rounded-xl bg-slate-50 px-3 py-2 text-xs dark:bg-slate-900">
                      <span className={event.status === 'success' ? 'text-emerald-600' : 'text-rose-600'}>{event.message}</span>
                      <time className="shrink-0 text-slate-400">{new Date(event.timestamp).toLocaleString()}</time>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </motion.section>
        </div>
      )}
    </AnimatePresence>
  );
};

function Metric({ icon: Icon, label, value, warning = false }: { icon: React.ComponentType<{ size?: number }>; label: string; value: string; warning?: boolean }) {
  return (
    <div className="rounded-2xl border border-slate-200 p-4 dark:border-slate-800">
      <Icon size={18} />
      <p className="mt-3 text-xs font-bold uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-1 text-xl font-black ${warning ? 'text-amber-600' : 'text-slate-900 dark:text-white'}`}>{value}</p>
    </div>
  );
}
