import React, { useState, useMemo, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { X, Download, FileJson, FileText, FileCode, Printer, CheckSquare, Square } from 'lucide-react';
import { useLanguage } from '@/contexts/LanguageContext';
import { Product } from '@/types/index';

interface SmartExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  filteredData: Product[];
  handleExport: (format: 'csv' | 'json' | 'xml', selectedColumns?: string[]) => void;
  handleExportPdf: () => void;
}

export const SmartExportModal: React.FC<SmartExportModalProps> = ({
  isOpen,
  onClose,
  filteredData,
  handleExport,
  handleExportPdf
}) => {
  const { t } = useLanguage();
  
  // Extract all unique attribute properties from the filtered data
  const availableColumns = useMemo(() => {
    const cols = new Set<string>();
    filteredData.forEach(p => {
      Object.keys(p.properties).forEach(k => cols.add(k));
    });
    return Array.from(cols).sort();
  }, [filteredData]);

  const [selectedColumns, setSelectedColumns] = useState<string[]>([]);
  const [exportFormat, setExportFormat] = useState<'csv' | 'json' | 'xml' | 'pdf'>('csv');

  useEffect(() => {
    if (isOpen) {
      setSelectedColumns(availableColumns);
    }
  }, [isOpen, availableColumns]);

  const handleToggleColumn = (col: string) => {
    setSelectedColumns(prev => 
      prev.includes(col) ? prev.filter(c => c !== col) : [...prev, col]
    );
  };

  const handleToggleAll = () => {
    if (selectedColumns.length === availableColumns.length) {
      setSelectedColumns([]);
    } else {
      setSelectedColumns(availableColumns);
    }
  };

  const onExportSubmit = () => {
    if (exportFormat === 'pdf') {
      handleExportPdf();
    } else {
      handleExport(exportFormat, selectedColumns);
    }
    onClose();
  };

  if (!isOpen) return null;

  const isAllSelected = selectedColumns.length === availableColumns.length;
  const isSomeSelected = selectedColumns.length > 0 && selectedColumns.length < availableColumns.length;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[150] flex items-center justify-center p-4">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm"
          onClick={onClose}
        />
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 10 }}
          className="relative bg-white dark:bg-slate-900 rounded-xl shadow-2xl w-full max-w-2xl border border-slate-200 dark:border-slate-800 flex flex-col max-h-[85vh]"
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-indigo-100 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-400 rounded-lg">
                <Download size={20} />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-slate-800 dark:text-slate-100">
                  {t('smartExport')}
                </h2>
                <p className="text-xs text-slate-500 mt-1">
                  {t('itemsFilteredForExport').replace('{count}', filteredData.length.toString())}
                </p>
              </div>
            </div>
            <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
              onClick={onClose}
              className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
            >
              <X size={20} />
            </motion.button>
          </div>

          <div className="p-6 overflow-y-auto space-y-6 flex-1">
            
            {/* Format Selection */}
            <div>
              <h3 className="text-sm font-semibold mb-3 text-slate-700 dark:text-slate-300">
                {t('selectExportFormat')}
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <FormatCard 
                  title="CSV" 
                  icon={<FileText size={20} className={exportFormat === 'csv' ? 'text-blue-500' : 'text-slate-400'} />} 
                  selected={exportFormat === 'csv'} 
                  onClick={() => setExportFormat('csv')} 
                />
                <FormatCard 
                  title="JSON" 
                  icon={<FileJson size={20} className={exportFormat === 'json' ? 'text-amber-500' : 'text-slate-400'} />} 
                  selected={exportFormat === 'json'} 
                  onClick={() => setExportFormat('json')} 
                />
                <FormatCard 
                  title="XML" 
                  icon={<FileCode size={20} className={exportFormat === 'xml' ? 'text-emerald-500' : 'text-slate-400'} />} 
                  selected={exportFormat === 'xml'} 
                  onClick={() => setExportFormat('xml')} 
                />
                <FormatCard 
                  title="PDF" 
                  icon={<Printer size={20} className={exportFormat === 'pdf' ? 'text-pink-500' : 'text-slate-400'} />} 
                  selected={exportFormat === 'pdf'} 
                  onClick={() => setExportFormat('pdf')} 
                />
              </div>
            </div>

            {/* Column Selection (Disabled if PDF) */}
            <div className={`transition-opacity ${exportFormat === 'pdf' ? 'opacity-50 pointer-events-none' : 'opacity-100'}`}>
              <div className="flex items-center justify-between mb-3 border-b border-slate-200 dark:border-slate-800 pb-2">
                <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                  {t('selectExportColumns')}
                </h3>
                <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} 
                  onClick={handleToggleAll}
                  className="text-xs flex items-center gap-1.5 text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300 transition-colors"
                >
                  {isAllSelected ? (
                    <CheckSquare size={14} />
                  ) : isSomeSelected ? (
                    <div className="w-3.5 h-3.5 rounded-sm bg-indigo-600 dark:bg-indigo-400 flex items-center justify-center">
                       <div className="w-2 h-0.5 bg-white rounded-full"></div>
                    </div>
                  ) : (
                    <Square size={14} />
                  )}
                  {t('selectAllNone')}
                </motion.button>
              </div>

              <div className="bg-slate-50 dark:bg-slate-900/50 p-4 rounded-lg border border-slate-200 dark:border-slate-800 max-h-[250px] overflow-y-auto">
                {availableColumns.length === 0 ? (
                   <p className="text-sm text-slate-500 text-center py-4">
                      {t('noAttributesAvailable')}
                   </p>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
                    {availableColumns.map(col => {
                      const isSelected = selectedColumns.includes(col);
                      return (
                        <label 
                          key={col} 
                          onClick={(e) => {
                             e.preventDefault();
                             handleToggleColumn(col);
                          }}
                          className={`flex items-start gap-2 p-2 rounded cursor-pointer transition-colors border ${
                            isSelected 
                              ? 'bg-white dark:bg-slate-800 border-indigo-200 dark:border-indigo-800/50 shadow-sm' 
                              : 'bg-transparent border-transparent hover:bg-slate-100 dark:hover:bg-slate-800'
                          }`}
                        >
                          <div className="mt-0.5 text-indigo-600 dark:text-indigo-400 flex-shrink-0">
                            {isSelected ? <CheckSquare size={16} /> : <Square size={16} className="text-slate-400" />}
                          </div>
                          <span className={`text-sm select-none break-words ${isSelected ? 'text-slate-800 dark:text-slate-200 font-medium' : 'text-slate-600 dark:text-slate-400'}`}>
                            {col}
                          </span>
                        </label>
                      );
                    })}
                  </div>
                )}
              </div>
              {exportFormat !== 'pdf' && (
                <p className="text-xs text-slate-500 mt-2">
                  <span className="font-semibold text-slate-600 dark:text-slate-400">Note:</span> 
                  {t('baseFieldsExportNotice')}
                </p>
              )}
            </div>

          </div>

          <div className="p-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 flex justify-end gap-3 flex-shrink-0">
            <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 transition-colors"
            >
              {t('cancel')}
            </motion.button>
            <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
              onClick={onExportSubmit}
              disabled={selectedColumns.length === 0 && exportFormat !== 'pdf'}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Download size={16} />
              {t('startExport')}
            </motion.button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

const FormatCard = ({ 
  title, 
  icon, 
  selected, 
  onClick 
}: { 
  title: string, 
  icon: React.ReactNode, 
  selected: boolean, 
  onClick: () => void 
}) => {
  return (
    <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
      onClick={onClick}
      className={`flex flex-col items-center justify-center p-4 rounded-xl border-2 transition-all ${
        selected 
          ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300' 
          : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-600'
      }`}
    >
      <div className="mb-2">
        {icon}
      </div>
      <span className="text-sm font-medium">{title}</span>
    </motion.button>
  );
};
