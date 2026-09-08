import React, { useMemo } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { X, ShieldAlert, AlertTriangle, Info, CheckCircle2 } from 'lucide-react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useData } from '@/contexts/DataContext';

interface DataQualityAuditModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const DataQualityAuditModal: React.FC<DataQualityAuditModalProps> = ({
  isOpen,
  onClose,
}) => {
  const { t } = useLanguage();
  const { allProducts } = useData();

  const auditResults = useMemo(() => {
    let missingFields = 0;
    let missingRefs = 0;
    let itemsWithMissingData = 0;
    const itemsWithoutCategory: string[] = [];
    const missingManufacturer: string[] = [];

    const grades = new Set<string>();
    const duplicates = new Set<string>();

    let totalProps = 0;
    const unitsMap: Record<string, Set<string>> = {};

    allProducts.forEach(product => {
      let isItemMissingData = false;
      if (!product.categoryIds || product.categoryIds.length === 0) {
        itemsWithoutCategory.push(product.gradeName);
      }
      if (!product.manufacturer || product.manufacturer.trim() === '') {
        missingManufacturer.push(product.gradeName);
      }

      if (grades.has(product.gradeName)) {
        duplicates.add(product.gradeName);
      } else {
        grades.add(product.gradeName);
      }

      Object.entries(product.properties || {}).forEach(([key, propValue]) => {
        totalProps++;
        if (propValue.value === undefined || propValue.value === null || propValue.value === '') {
          missingFields++;
          isItemMissingData = true;
        }
        if (!propValue.referenceId && !propValue.sourceUrl) {
          missingRefs++;
        }
        if (propValue.unit) {
          if (!unitsMap[key]) unitsMap[key] = new Set();
          unitsMap[key].add(propValue.unit);
        }
      });
      if (isItemMissingData) {
        itemsWithMissingData++;
      }
    });

    const inconsistentUnits = Object.entries(unitsMap).filter(([_, units]) => units.size > 1).map(([key, units]) => ({
      property: key,
      units: Array.from(units)
    }));

    return {
      missingFields,
      missingRefs,
      itemsWithMissingData,
      itemsWithoutCategory,
      missingManufacturer,
      duplicates: Array.from(duplicates),
      totalProps,
      inconsistentUnits
    };
  }, [allProducts]);

  if (!isOpen) return null;

  const score = Math.max(0, 100 - (auditResults.missingFields * 0.1) - (auditResults.duplicates.length * 2) - (auditResults.inconsistentUnits.length * 5) - (auditResults.itemsWithoutCategory.length * 1));

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
          className="relative bg-white dark:bg-slate-900 rounded-xl shadow-2xl w-full max-w-4xl border border-slate-200 dark:border-slate-800 overflow-hidden flex flex-col max-h-[90vh]"
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 rounded-lg">
                <ShieldAlert size={20} />
              </div>
              <h2 className="text-xl font-semibold text-slate-800 dark:text-slate-100">
                {t('dataQualityAudit')}
              </h2>
            </div>
            <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
              onClick={onClose}
              className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
            >
              <X size={20} />
            </motion.button>
          </div>

          <div className="p-6 overflow-y-auto space-y-6 flex-1">
            
            {/* Overview */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm flex flex-col justify-center items-center">
                 <div className="text-3xl font-bold text-slate-800 dark:text-slate-100 mb-1">{score.toFixed(1)}</div>
                 <div className="text-xs text-slate-500 uppercase tracking-wider font-mono">质量评分 / Score</div>
              </div>
              <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm flex flex-col justify-center items-center">
                 <div className="flex items-center gap-2">
                     <AlertTriangle size={18} className="text-amber-500" />
                     <div className="text-3xl font-bold text-amber-500 mb-1">{auditResults.missingFields}</div>
                 </div>
                 <div className="text-xs text-slate-500 uppercase tracking-wider font-mono">缺失字段 / Missing Fields</div>
              </div>
              <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm flex flex-col justify-center items-center">
                 <div className="flex items-center gap-2">
                     <ShieldAlert size={18} className="text-red-500" />
                     <div className="text-3xl font-bold text-red-500 mb-1">{auditResults.duplicates.length}</div>
                 </div>
                 <div className="text-xs text-slate-500 uppercase tracking-wider font-mono">重复项 / Duplicates</div>
              </div>
              <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm flex flex-col justify-center items-center">
                 <div className="flex items-center gap-2">
                     <Info size={18} className="text-blue-500" />
                     <div className="text-3xl font-bold text-blue-500 mb-1">{auditResults.inconsistentUnits.length}</div>
                 </div>
                 <div className="text-xs text-slate-500 uppercase tracking-wider font-mono">单位不一致 / Inconsistent Units</div>
              </div>
            </div>

            {/* Layout for details */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              
              {/* Duplicates */}
              <div className="space-y-3">
                 <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-2 border-b border-slate-200 dark:border-slate-800 pb-2">
                    <span className="w-2 h-2 rounded-full bg-red-500" />
                    {t('duplicateGrades')}
                 </h3>
                 <div className="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-3 max-h-[250px] overflow-y-auto border border-slate-100 dark:border-slate-800">
                    {auditResults.duplicates.length === 0 ? (
                       <div className="text-sm text-slate-500 flex items-center gap-2">
                         <CheckCircle2 size={16} className="text-emerald-500" />
                         {t('noDuplicateGrades')}
                       </div>
                    ) : (
                       <ul className="space-y-1">
                          {auditResults.duplicates.map(d => (
                            <li key={d} className="text-sm text-slate-700 dark:text-slate-300 py-1 px-2 bg-white dark:bg-slate-800 rounded border border-slate-200 dark:border-slate-700 font-mono">
                               {d}
                            </li>
                          ))}
                       </ul>
                    )}
                 </div>
              </div>

              {/* Inconsistent Units */}
              <div className="space-y-3">
                 <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-2 border-b border-slate-200 dark:border-slate-800 pb-2">
                    <span className="w-2 h-2 rounded-full bg-amber-500" />
                    {t('inconsistentUnits')}
                 </h3>
                 <div className="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-3 max-h-[250px] overflow-y-auto border border-slate-100 dark:border-slate-800">
                    {auditResults.inconsistentUnits.length === 0 ? (
                       <div className="text-sm text-slate-500 flex items-center gap-2">
                         <CheckCircle2 size={16} className="text-emerald-500" />
                         {t('consistentUnits')}
                       </div>
                    ) : (
                       <ul className="space-y-2">
                          {auditResults.inconsistentUnits.map(inc => (
                            <li key={inc.property} className="text-sm flex flex-col gap-1 p-2 bg-white dark:bg-slate-800 rounded border border-slate-200 dark:border-slate-700">
                               <span className="font-semibold text-slate-700 dark:text-slate-200">{inc.property}</span>
                               <span className="text-xs text-slate-500 font-mono">{inc.units.join(' / ')}</span>
                            </li>
                          ))}
                       </ul>
                    )}
                 </div>
              </div>

              {/* Missing Categories */}
              <div className="space-y-3">
                 <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-2 border-b border-slate-200 dark:border-slate-800 pb-2">
                    <span className="w-2 h-2 rounded-full bg-blue-500" />
                    {t('uncategorizedProducts')}
                 </h3>
                 <div className="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-3 max-h-[250px] overflow-y-auto border border-slate-100 dark:border-slate-800">
                    {auditResults.itemsWithoutCategory.length === 0 ? (
                       <div className="text-sm text-slate-500 flex items-center gap-2">
                         <CheckCircle2 size={16} className="text-emerald-500" />
                         {t('allProductsCategorized')}
                       </div>
                    ) : (
                       <ul className="space-y-1">
                          {auditResults.itemsWithoutCategory.map(d => (
                            <li key={d} className="text-sm text-slate-700 dark:text-slate-300 py-1 px-2 bg-white dark:bg-slate-800 rounded border border-slate-200 dark:border-slate-700 font-mono">
                               {d}
                            </li>
                          ))}
                       </ul>
                    )}
                 </div>
              </div>

              {/* Missing Manufacturers */}
              <div className="space-y-3">
                 <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-2 border-b border-slate-200 dark:border-slate-800 pb-2">
                    <span className="w-2 h-2 rounded-full bg-purple-500" />
                    {t('missingManufacturers')}
                 </h3>
                 <div className="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-3 max-h-[250px] overflow-y-auto border border-slate-100 dark:border-slate-800">
                    {auditResults.missingManufacturer.length === 0 ? (
                       <div className="text-sm text-slate-500 flex items-center gap-2">
                         <CheckCircle2 size={16} className="text-emerald-500" />
                         {t('allProductsHaveManufacturer')}
                       </div>
                    ) : (
                       <ul className="space-y-1">
                          {auditResults.missingManufacturer.map(d => (
                            <li key={d} className="text-sm text-slate-700 dark:text-slate-300 py-1 px-2 bg-white dark:bg-slate-800 rounded border border-slate-200 dark:border-slate-700 font-mono">
                               {d}
                            </li>
                          ))}
                       </ul>
                    )}
                 </div>
              </div>

            </div>
          </div>
          <div className="p-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 flex justify-end">
             <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                onClick={onClose}
                className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-800 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-100 rounded-lg text-sm transition-colors"
             >
                {t('close')}
             </motion.button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
