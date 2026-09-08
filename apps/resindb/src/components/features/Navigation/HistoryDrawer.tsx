import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { X, Clock, Undo2, RotateCcw } from 'lucide-react';
import { useData } from '@/contexts/DataContext';

interface HistoryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export const HistoryDrawer: React.FC<HistoryDrawerProps> = ({ isOpen, onClose }) => {
  const { history, restoreSnapshot } = useData();

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-slate-900/20 backdrop-blur-sm z-40"
          />
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed inset-y-0 right-0 w-full sm:w-96 bg-white dark:bg-slate-900 shadow-2xl z-50 flex flex-col border-l border-slate-200 dark:border-slate-800"
          >
            <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/50">
              <div className="flex items-center gap-2">
                <Clock className="text-primary-500" size={18} />
                <h2 className="text-sm font-bold text-slate-800 dark:text-slate-100">
                  Version History
                </h2>
              </div>
              <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                onClick={onClose}
                className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              >
                <X size={16} />
              </motion.button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
              {history.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-slate-400 space-y-3">
                  <RotateCcw size={32} className="opacity-20" />
                  <p className="text-sm">No history recorded yet.</p>
                  <p className="text-xs opacity-70 text-center max-w-[200px]">
                    Changes to products will appear here.
                  </p>
                </div>
              ) : (
                <div className="space-y-4 relative before:absolute before:inset-0 before:ml-4 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-slate-200 before:via-slate-200 before:to-transparent dark:before:from-slate-800 dark:before:via-slate-800">
                  {history.map((record, idx) => (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.05 }}
                      key={record.id}
                      className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group"
                    >
                      <div className="flex items-center justify-center w-8 h-8 rounded-full bg-white dark:bg-slate-900 border-2 border-slate-200 dark:border-slate-700 shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10 transition-colors group-hover:border-primary-400">
                         {idx === 0 ? <Clock size={12} className="text-primary-500" /> : <div className="w-2 h-2 rounded-full bg-slate-300 dark:bg-slate-600" />}
                      </div>
                      
                      <div className="w-[calc(100%-3rem)] md:w-[calc(50%-2rem)] p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 shadow-sm transition-shadow hover:shadow-md">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-[10px] font-mono text-slate-400">
                             {new Date(record.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                          </span>
                        </div>
                        <p className="text-xs font-medium text-slate-700 dark:text-slate-300 mb-3 break-words">
                          {record.description}
                        </p>
                        <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                          onClick={() => restoreSnapshot(record.id)}
                          className="flex items-center gap-1.5 px-2 py-1 text-[10px] font-bold text-primary-600 bg-primary-50 hover:bg-primary-100 dark:text-primary-400 dark:bg-primary-900/30 dark:hover:bg-primary-900/50 rounded transition-colors w-full justify-center"
                        >
                          <Undo2 size={12} />
                          Restore this version
                        </motion.button>
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};
