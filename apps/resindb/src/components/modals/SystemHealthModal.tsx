import { logger } from '@/lib/logger';
import React, { useMemo, useRef } from 'react';
import { Activity, Database, Download, RefreshCw, Server, Upload, X } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import { useData } from '@/contexts/DataContext';
import { useLanguage } from '@/contexts/LanguageContext';
import { safeStorage } from '@/lib/utils';

interface SystemHealthModalProps {
  isOpen: boolean;
  onClose: () => void;
  status: string;
  addToast: (type: 'success' | 'error' | 'info', message: string) => void;
}

const CONFIG_KEYS = [
  'resindb-saved-views',
  'resindb-theme',
  'resindb-language',
  'resindb-compact',
  'resindb-users',
  'resindb-formulas',
  'resindb-tour-completed',
] as const;

export const SystemHealthModal: React.FC<SystemHealthModalProps> = ({
  isOpen,
  onClose,
  status,
  addToast,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { refreshData, isRefreshing, syncEvents } = useData();
  const { t } = useLanguage();

  const lastEvent = syncEvents[0];
  const runtimeCards = useMemo(() => [
    { label: 'Runtime', value: 'Current browser', icon: Server },
    { label: 'Storage', value: 'Configured product adapter', icon: Database },
    { label: 'Status', value: isRefreshing ? 'Refreshing' : status.toUpperCase(), icon: RefreshCw },
    {
      label: 'Last event',
      value: lastEvent ? new Date(lastEvent.timestamp).toLocaleString() : 'No recorded event',
      icon: Activity,
    },
  ], [isRefreshing, lastEvent, status]);

  const handleExportConfig = () => {
    const configData = Object.fromEntries(CONFIG_KEYS.map((key) => [key, safeStorage.local.getItem(key)]));
    const blob = new Blob([JSON.stringify(configData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `resindb-config-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  };

  const handleImportConfig = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (file.type && file.type !== 'application/json') {
      addToast('error', 'Please select a JSON configuration file.');
      return;
    }
    if (file.size > 512 * 1024) {
      addToast('error', 'Configuration files must be smaller than 512 KB.');
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      try {
        const parsed: unknown = JSON.parse(String(reader.result || ''));
        if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
          throw new Error('Configuration root must be an object');
        }

        let imported = 0;
        for (const key of CONFIG_KEYS) {
          const value = (parsed as Record<string, unknown>)[key];
          if (typeof value === 'string') {
            safeStorage.local.setItem(key, value);
            imported += 1;
          }
        }
        if (imported === 0) throw new Error('No supported configuration values found');
        addToast('success', t('sysHealthImportSuccess'));
        window.setTimeout(() => window.location.reload(), 500);
      } catch (error) {
        logger.error('Config import error:', error);
        addToast('error', t('sysHealthImportError'));
      } finally {
        if (fileInputRef.current) fileInputRef.current.value = '';
      }
    };
    reader.onerror = () => addToast('error', t('sysHealthImportError'));
    reader.readAsText(file);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div className="fixed inset-0 z-[200] flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-slate-950/40 backdrop-blur-sm"
            onClick={onClose}
          />
          <motion.div
            initial={{ scale: 0.96, opacity: 0, y: 16 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.96, opacity: 0, y: 16 }}
            className="relative flex max-h-[85vh] w-full max-w-lg flex-col overflow-hidden rounded-[2rem] border border-slate-300 bg-white shadow-2xl dark:border-slate-700 dark:bg-slate-950"
          >
            <header className="flex items-center justify-between border-b border-slate-200 bg-slate-100/70 px-6 py-4 dark:border-slate-800 dark:bg-slate-900/70">
              <div className="flex items-center gap-3">
                <span className="rounded-xl border border-emerald-700 bg-emerald-600 p-2 text-white"><Activity size={18} /></span>
                <div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">{t('sysHealthTitle')}</h3>
                  <p className="mt-0.5 text-[10px] font-mono uppercase tracking-widest text-slate-500">Observed browser state</p>
                </div>
              </div>
              <button onClick={onClose} className="rounded-xl p-2 text-slate-500 hover:bg-rose-600 hover:text-white" aria-label="Close"><X size={16} /></button>
            </header>

            <div className="space-y-5 overflow-y-auto p-6 custom-scrollbar">
              <p className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-[11px] leading-5 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/20 dark:text-amber-300">
                This view reports only state observable in the browser. It does not claim a cloud region, server uptime, database capacity, or external API availability.
              </p>

              <div className="grid grid-cols-2 gap-3">
                {runtimeCards.map(({ label, value, icon: Icon }) => (
                  <div key={label} className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900">
                    <div className="mb-3 flex items-center gap-2 text-slate-400"><Icon size={14} /><span className="text-[9px] font-mono uppercase tracking-widest">{label}</span></div>
                    <p className="break-words text-xs font-bold text-slate-800 dark:text-slate-100">{value}</p>
                  </div>
                ))}
              </div>

              <button
                onClick={() => void refreshData()}
                disabled={isRefreshing}
                className="flex w-full items-center justify-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-xs font-bold text-emerald-700 disabled:cursor-not-allowed disabled:opacity-60 dark:border-emerald-900 dark:bg-emerald-950/20 dark:text-emerald-300"
              >
                <RefreshCw size={14} className={isRefreshing ? 'animate-spin' : ''} />
                {isRefreshing ? t('syncing') : t('syncNow')}
              </button>

              <section className="space-y-2">
                <div className="flex items-center justify-between"><h4 className="text-[10px] font-bold uppercase tracking-widest text-slate-500">{t('sysHealthSyncLog')}</h4><span className="text-[9px] font-mono text-slate-400">{syncEvents.length}</span></div>
                <div className="max-h-48 space-y-2 overflow-y-auto pr-1 custom-scrollbar">
                  {syncEvents.length === 0 ? (
                    <p className="rounded-xl border border-dashed border-slate-200 p-4 text-center text-[10px] text-slate-400 dark:border-slate-800">{t('sysHealthNoEvents')}</p>
                  ) : syncEvents.map((entry) => (
                    <div key={entry.id} className="rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-900">
                      <div className="flex items-start gap-2"><span className={`mt-1.5 h-1.5 w-1.5 rounded-full ${entry.status === 'success' ? 'bg-emerald-500' : 'bg-rose-500'}`} /><div className="min-w-0"><p className="text-[11px] text-slate-700 dark:text-slate-300">{entry.message}</p><p className="mt-1 text-[9px] font-mono text-slate-400">{new Date(entry.timestamp).toLocaleString()}</p></div></div>
                    </div>
                  ))}
                </div>
              </section>

              <div className="grid grid-cols-2 gap-3 border-t border-slate-200 pt-4 dark:border-slate-800">
                <button onClick={handleExportConfig} className="flex items-center justify-center gap-2 rounded-xl border border-slate-200 px-3 py-2.5 text-[10px] font-bold uppercase tracking-wider dark:border-slate-800"><Download size={13} /> Export settings</button>
                <button onClick={() => fileInputRef.current?.click()} className="flex items-center justify-center gap-2 rounded-xl border border-slate-200 px-3 py-2.5 text-[10px] font-bold uppercase tracking-wider dark:border-slate-800"><Upload size={13} /> Import settings</button>
                <input ref={fileInputRef} type="file" accept="application/json,.json" className="hidden" onChange={handleImportConfig} />
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
