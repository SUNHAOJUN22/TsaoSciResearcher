import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { 
  CheckCircle, 
  AlertTriangle, 
  ShieldAlert, 
  Settings, 
  Play, 
  RefreshCw, 
  ArrowRight, 
  Beaker, 
  Sliders, 
  Sparkles,
  Info
} from 'lucide-react';
import { Product, FormulaConfig } from '@/types/index';
import { formulaEngine } from '@/lib/formulaParser';
import { useLanguage } from '@/contexts/LanguageContext';
import { useToasts } from '@/contexts/ToastContext';

interface BulkValidationProps {
  allProducts: Product[];
  formulas: FormulaConfig[];
  onViewProduct?: (p: Product) => void;
}

interface ValidationResult {
  product: Product;
  violations: {
    type: 'viscosity' | 'tensile' | 'mfr' | 'formula' | 'syntax' | 'chemical';
    severity: 'critical' | 'warning';
    messageZh: string;
    messageEn: string;
    metricLabelZh: string;
    metricLabelEn: string;
    expectedRange: string;
    actualValue: string | number;
  }[];
}

// Reuse chemical equation balance algorithm from editor
function validateEquationBalance(expression: string): { isValid: boolean; message: string } | null {
  const lines = expression.split('\n');
  let chemMatch = null;
  for (const line of lines) {
    if (line.includes('->') || line.includes('=')) {
      const eq = line.split(/->|=/);
      if (eq.length === 2 && eq[0].trim() && eq[1].trim()) {
        chemMatch = eq;
        break;
      }
    }
  }
  
  if (!chemMatch) return null;

  const parseSide = (side: string) => {
    const counts: Record<string, number> = {};
    const molecules = side.split('+').map(s => s.trim());
    for (const mol of molecules) {
      const mulMatch = mol.match(/^(\d+)/);
      const multiplier = mulMatch ? parseInt(mulMatch[1], 10) : 1;
      const formulaStr = mol.replace(/^\d+/, '').trim();
      
      const elRegex = /([A-Z][a-z]?)(\d*)/g;
      let match;
      let foundAny = false;
      while ((match = elRegex.exec(formulaStr)) !== null) {
        foundAny = true;
        const element = match[1];
        const count = match[2] ? parseInt(match[2], 10) : 1;
        counts[element] = (counts[element] || 0) + count * multiplier;
      }
      if (!foundAny && formulaStr.length > 0) return null;
    }
    return counts;
  };

  const leftCounts = parseSide(chemMatch[0]);
  const rightCounts = parseSide(chemMatch[1]);
  
  if (!leftCounts || !rightCounts) return null;

  const allElements = new Set([...Object.keys(leftCounts), ...Object.keys(rightCounts)]);
  if (allElements.size === 0) return null;

  for (const el of allElements) {
    const l = leftCounts[el] || 0;
    const r = rightCounts[el] || 0;
    if (l !== r) {
      return { isValid: false, message: `Unbalanced: ${el} (Left: ${l}, Right: ${r})` };
    }
  }

  return { isValid: true, message: "Balanced chemical equation format detected." };
}

export const BulkValidation: React.FC<BulkValidationProps> = ({
  allProducts,
  formulas,
  onViewProduct
}) => {
  const { language, t } = useLanguage();
  const { addToast } = useToasts();

  /** Local bilingual inline helper for strings not yet in i18n.ts */
  const tLocal = (zh: string, en: string) => (language === 'zh' ? zh : en);

  // States
  const [selectedFormulaIds, setSelectedFormulaIds] = useState<Set<string>>(() => {
    return new Set(formulas.map(f => f.id));
  });
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [showConfig, setShowConfig] = useState(false);
  const [filterType, setFilterType] = useState<'all' | 'critical' | 'warning' | 'clean'>('all');

  // Multi-threshold config states
  const [minMfr, setMinMfr] = useState(0.5);
  const [maxMfr, setMaxMfr] = useState(30.0);
  const [minTensile, setMinTensile] = useState(18.0);
  
  // Custom formula return limits
  const [enableFormulaBounds, setEnableFormulaBounds] = useState(true);
  const [formulaMinBoundary, setFormulaMinBoundary] = useState(10.0);
  const [formulaMaxBoundary, setFormulaMaxBoundary] = useState(300.0);

  // Handle checking / unchecking single formula
  const toggleFormulaSelection = (id: string) => {
    const next = new Set(selectedFormulaIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelectedFormulaIds(next);
  };

  // Check / Uncheck all
  const selectAllFormulas = () => {
    setSelectedFormulaIds(new Set(formulas.map(f => f.id)));
  };

  const deselectAllFormulas = () => {
    setSelectedFormulaIds(new Set());
  };

  // Run validation
  const runTrigger = () => {
    setIsEvaluating(true);
    setTimeout(() => {
      setIsEvaluating(false);
      addToast("success", t("bulkValidateComplete"));
    }, 850);
  };

  // Validate and flag product violations
  const validationResults = useMemo(() => {
    const results: ValidationResult[] = [];
    const activeFormulas = formulas.filter(f => selectedFormulaIds.has(f.id));

    // Compile active formulas logic
    let evaluator: ((product: Product) => Record<string, number>) | null = null;
    try {
      if (activeFormulas.length > 0) {
        evaluator = formulaEngine.compileGraph(activeFormulas);
      }
    } catch {
      // Ignore evaluation errors because we will flag syntax errors individually
    }

    // Evaluate each formulation product
    allProducts.forEach(p => {
      const violations: ValidationResult['violations'] = [];

      // Core Chemical Property helper
      const getVal = (k: string): number => {
        const raw = p.properties?.[k]?.value;
        const num = typeof raw === 'number' ? raw : parseFloat(String(raw));
        return isNaN(num) ? 0 : num;
      };

      // 1. MFR Bounds
      const mfrValue = getVal('mfr');
      if (mfrValue > 0) {
        if (mfrValue < minMfr) {
          violations.push({
            type: 'mfr',
            severity: 'warning',
            messageZh: `熔指 (MFR) 偏低 (${mfrValue} < ${minMfr})，熔体粘度过大，可能面临熔体进胶充填困难。`,
            messageEn: `MFR is below threshold (${mfrValue} < ${minMfr}), indicating extreme melt viscosity which may cause injection mold filling stress.`,
            metricLabelZh: '熔体流动速率 MFR',
            metricLabelEn: 'Melt Flow Rate MFR',
            expectedRange: `>= ${minMfr} g/10min`,
            actualValue: `${mfrValue} g/10min`
          });
        } else if (mfrValue > maxMfr) {
          violations.push({
            type: 'mfr',
            severity: 'warning',
            messageZh: `熔指 (MFR) 极高 (${mfrValue} > ${maxMfr})，易引发树脂溢料模飞边与毛刺隐患。`,
            messageEn: `MFR exceeds safety limit (${mfrValue} > ${maxMfr}), raising critical flash spill or burr risks during injection flow.`,
            metricLabelZh: '熔体流动速率 MFR',
            metricLabelEn: 'Melt Flow Rate MFR',
            expectedRange: `<= ${maxMfr} g/10min`,
            actualValue: `${mfrValue} g/10min`
          });
        }
      }

      // 2. Tensile Strength
      const tensileValue = getVal('tensileYield');
      if (tensileValue > 0 && tensileValue < minTensile) {
        violations.push({
          type: 'tensile',
          severity: 'critical',
          messageZh: `抗拉强度低 (${tensileValue} < ${minTensile} MPa)，承载形变抵抗力严重欠缺，恐易脆性撕裂折断。`,
          messageEn: `Tensile strength is low (${tensileValue} < ${minTensile} MPa). Absolute structural capability failure under tensile stress load.`,
          metricLabelZh: '拉伸屈服应力强度',
          metricLabelEn: 'Tensile Yield Strength',
          expectedRange: `>= ${minTensile} MPa`,
          actualValue: `${tensileValue} MPa`
        });
      }

      // 3. Formula Evaluations & Syntax/Equation flags
      activeFormulas.forEach(f => {
        // Run Syntax and Balance validate on the formula itself:
        const syntaxErr = formulaEngine.validate(f.expression, f.name, formulas);
        if (syntaxErr) {
          violations.push({
            type: 'syntax',
            severity: 'critical',
            messageZh: `公式 "${f.name}" 内存在阻断性语法/依赖闭合循环异常：${syntaxErr}`,
            messageEn: `Formula "${f.name}" contains compile blocking syntaxes or circular graph errors: ${syntaxErr}`,
            metricLabelZh: `公式语法: ${f.name}`,
            metricLabelEn: `Formula Compile: ${f.name}`,
            expectedRange: 'Valid syntax compilation',
            actualValue: 'Syntax Error'
          });
        }

        const equationsCheck = validateEquationBalance(f.expression);
        if (equationsCheck && !equationsCheck.isValid) {
          violations.push({
            type: 'chemical',
            severity: 'critical',
            messageZh: `公式 "${f.name}" 内置的反应方程式存在质量平衡亏损：${equationsCheck.message}`,
            messageEn: `Formula "${f.name}" reactive equation details are unbalanced: ${equationsCheck.message}`,
            metricLabelZh: `化学平衡: ${f.name}`,
            metricLabelEn: `Stoichiometric Balance: ${f.name}`,
            expectedRange: 'Balanced reaction equations',
            actualValue: 'Unbalanced Mass'
          });
        }

        // Run evaluative calculation on this product
        if (evaluator && !syntaxErr) {
          try {
            const outputs = evaluator(p);
            const computedVal = outputs[f.id];
            if (typeof computedVal === 'number' && enableFormulaBounds) {
              if (computedVal < formulaMinBoundary) {
                violations.push({
                  type: 'formula',
                  severity: 'warning',
                  messageZh: `公式 "${f.name}" 指数低于设定的功能容差下界 (${computedVal.toFixed(2)} < ${formulaMinBoundary})。`,
                  messageEn: `Formula indicator "${f.name}" fell below performance lower bound (${computedVal.toFixed(2)} < ${formulaMinBoundary}).`,
                  metricLabelZh: `公式指标 - ${f.name}`,
                  metricLabelEn: `Formula Index - ${f.name}`,
                  expectedRange: `>= ${formulaMinBoundary}`,
                  actualValue: computedVal.toFixed(3)
                });
              } else if (computedVal > formulaMaxBoundary) {
                violations.push({
                  type: 'formula',
                  severity: 'critical',
                  messageZh: `公式 "${f.name}" 指数高过安全极值容差上界 (${computedVal.toFixed(2)} > ${formulaMaxBoundary})，存在溶胀/过敏交联等隐性风险。`,
                  messageEn: `Formula indicator "${f.name}" exceeds safety upper limit (${computedVal.toFixed(2)} > ${formulaMaxBoundary}), risking composition swelling or excess crosslinking.`,
                  metricLabelZh: `公式指标 - ${f.name}`,
                  metricLabelEn: `Formula Index - ${f.name}`,
                  expectedRange: `<= ${formulaMaxBoundary}`,
                  actualValue: computedVal.toFixed(3)
                });
              }
            }
          } catch {
            // Evaluator crash fallback
          }
        }
      });

      // Push to results if there is anything checked, always structure info
      results.push({
        product: p,
        violations
      });
    });

    return results;
  }, [allProducts, formulas, selectedFormulaIds, minMfr, maxMfr, minTensile, enableFormulaBounds, formulaMinBoundary, formulaMaxBoundary]);

  // Statistics calculation
  const stats = useMemo(() => {
    let criticalCount = 0;
    let warningCount = 0;
    let totalViolations = 0;
    let cleanProductsCount = 0;

    validationResults.forEach(r => {
      if (r.violations.length === 0) {
        cleanProductsCount++;
      } else {
        totalViolations += r.violations.length;
        r.violations.forEach(v => {
          if (v.severity === 'critical') criticalCount++;
          if (v.severity === 'warning') warningCount++;
        });
      }
    });

    const totalPrds = allProducts.length || 1;
    const healthPercent = Math.round((cleanProductsCount / totalPrds) * 100);

    return {
      criticalCount,
      warningCount,
      totalViolations,
      cleanProductsCount,
      healthPercent
    };
  }, [validationResults, allProducts]);

  // Filters results items
  const filteredResults = useMemo(() => {
    return validationResults.filter(r => {
      if (filterType === 'all') return true;
      if (filterType === 'clean') return r.violations.length === 0;
      if (filterType === 'critical') return r.violations.some(v => v.severity === 'critical');
      if (filterType === 'warning') return r.violations.some(v => v.severity === 'warning');
      return true;
    });
  }, [validationResults, filterType]);

  return (
    <div className="w-full bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800/80 rounded-2xl shadow-sm p-5 md:p-6 flex flex-col space-y-6">
      
      {/* 1. Header with metadata properties */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <div className="p-2 bg-indigo-50 dark:bg-indigo-950/40 rounded-xl border border-indigo-100 text-indigo-500 shadow-sm">
              <ShieldAlert size={16} />
            </div>
            <h3 className="text-sm font-black text-slate-800 dark:text-white uppercase tracking-tight flex items-center gap-1.5">
              {t("bulkValidateTitle")}
              <span className="text-[10px] bg-emerald-500/10 text-emerald-650 dark:text-emerald-400 px-1.5 py-0.5 rounded font-black tracking-widest uppercase">
                {t("bulkValidateProLabel")}
              </span>
            </h3>
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-450 font-medium">
            {t("bulkValidateDescription")}
          </p>
        </div>

        {/* Action Controllers */}
        <div className="flex flex-wrap items-center gap-2.5">
          <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
            onClick={() => setShowConfig(!showConfig)}
            className={`px-3.5 py-2 border rounded-xl text-xs font-black flex items-center gap-1.5 transition-all outline-none ${
              showConfig 
                ? 'bg-slate-100 dark:bg-slate-800 border-slate-300 dark:border-slate-700 text-slate-850 dark:text-white' 
                : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-850 text-slate-700 dark:text-slate-300 shadow-sm'
            }`}
          >
            <Settings size={13} className={showConfig ? "animate-spin text-primary-500" : ""} />
            {t("bulkValidateThresholdConfig")}
          </motion.button>
          
          <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
            onClick={runTrigger}
            disabled={isEvaluating}
            className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-xl text-xs font-black shadow-sm flex items-center gap-1.5 active:scale-95 transition-all disabled:opacity-55"
          >
            {isEvaluating ? (
              <>
                <RefreshCw size={13} className="animate-spin" />
                {t("bulkValidateRunning")}
              </>
            ) : (
              <>
                <Play size={12} className="fill-current text-white" />
                {t("bulkValidateRunScan")}
              </>
            )}
          </motion.button>
        </div>
      </div>

      {/* 2. Collapsible Custom Threshold Configuration Area */}
      <AnimatePresence>
        {showConfig && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="p-4 md:p-5 bg-slate-50/70 dark:bg-slate-950/40 border border-slate-200 dark:border-slate-800 rounded-2xl grid grid-cols-1 md:grid-cols-3 gap-5">
              
              {/* Box 1: Rheology Rheostatic Bounds MFR */}
              <div className="space-y-3 p-3 bg-white dark:bg-slate-900 border border-slate-150 dark:border-slate-850 rounded-xl shadow-sm">
                <span className="text-[9px] font-black text-slate-400 uppercase tracking-wider flex items-center gap-1">
                  <Sliders size={11} className="text-amber-500" />
                  {tLocal("熔体流动速率因子 (MFR)", "Rheology Melt Flow (MFR) Limits")}
                </span>
                
                <div className="space-y-3 pt-1">
                  <div className="space-y-1">
                    <div className="flex justify-between text-[11px] font-bold text-slate-650 dark:text-slate-400">
                      <span>{tLocal("熔体溢流上界 (Max MFR)", "Upper Flash Risk (Max MFR)")}</span>
                      <span className="font-mono text-slate-900 dark:text-white font-black">{maxMfr} g/10min</span>
                    </div>
                    <input 
                      type="range" 
                      min="5" 
                      max="60" 
                      step="1"
                      value={maxMfr} 
                      onChange={(e) => setMaxMfr(parseFloat(e.target.value))}
                      className="w-full accent-primary-500 h-1 bg-slate-150 dark:bg-slate-800 rounded"
                    />
                  </div>

                  <div className="space-y-1">
                    <div className="flex justify-between text-[11px] font-bold text-slate-650 dark:text-slate-400">
                      <span>{tLocal("熔体难充填下界 (Min MFR)", "Lower Viscous flow (Min MFR)")}</span>
                      <span className="font-mono text-slate-900 dark:text-white font-black">{minMfr} g/10min</span>
                    </div>
                    <input 
                      type="range" 
                      min="0.1" 
                      max="4.9" 
                      step="0.1"
                      value={minMfr} 
                      onChange={(e) => setMinMfr(parseFloat(e.target.value))}
                      className="w-full accent-primary-500 h-1 bg-slate-150 dark:bg-slate-800 rounded"
                    />
                  </div>
                </div>
              </div>

              {/* Box 2: Mechanical Tensile yield stress limits */}
              <div className="space-y-3 p-3 bg-white dark:bg-slate-900 border border-slate-150 dark:border-slate-850 rounded-xl shadow-sm">
                <span className="text-[9px] font-black text-slate-400 uppercase tracking-wider flex items-center gap-1">
                  <Beaker size={11} className="text-rose-500" />
                  {tLocal("承应力刚度安全线 (Tensile)", "Structural Tensile Thresholds")}
                </span>
                
                <div className="space-y-4 pt-1">
                  <div className="space-y-1">
                    <div className="flex justify-between text-[11px] font-bold text-slate-650 dark:text-slate-400">
                      <span>{tLocal("抗拉屈服最低安全线", "Min Safety Tensile Strength")}</span>
                      <span className="font-mono text-rose-600 dark:text-rose-450 font-black">{minTensile} MPa</span>
                    </div>
                    <input 
                      type="range" 
                      min="5" 
                      max="45" 
                      step="1"
                      value={minTensile} 
                      onChange={(e) => setMinTensile(parseFloat(e.target.value))}
                      className="w-full accent-primary-500 h-1 bg-slate-150 dark:bg-slate-800 rounded"
                    />
                  </div>
                  <p className="text-[9.5px] text-slate-400 italic">
                    {tLocal("* 拉伸屈服强度低于此标准的树脂将被列为结构断裂风险等红线极高缺陷级。", "* Products with strength below this is flagged as critical fracture load risks.")}
                  </p>
                </div>
              </div>

              {/* Box 3: Custom formula calculated outputs */}
              <div className="space-y-3 p-3 bg-white dark:bg-slate-900 border border-slate-150 dark:border-slate-850 rounded-xl shadow-sm">
                <span className="text-[9px] font-black text-slate-400 uppercase tracking-wider flex items-center gap-1">
                  <Sparkles size={11} className="text-indigo-500" />
                  {tLocal("公式计算表现容差 (Computed Index)", "Computed Formula Boundaries")}
                </span>
                
                <div className="space-y-2.5 pt-1">
                  <div className="flex items-center justify-between pb-1">
                    <label className="text-[10px] font-bold text-slate-500">{tLocal("启用公式结果验证", "Validate output bounds")}</label>
                    <input 
                      type="checkbox" 
                      checked={enableFormulaBounds}
                      onChange={(e) => setEnableFormulaBounds(e.target.checked)}
                      className="rounded accent-primary-500"
                    />
                  </div>

                  <div className="space-y-1">
                    <div className="flex justify-between text-[10px] font-bold text-slate-650">
                      <span>{tLocal("计算容许上限 (Max Cap)", "Max Allowable Limit")}</span>
                      <span className="font-mono font-bold text-slate-850 dark:text-white">{formulaMaxBoundary}</span>
                    </div>
                    <input 
                      disabled={!enableFormulaBounds}
                      type="range" 
                      min="50" 
                      max="1000" 
                      step="10"
                      value={formulaMaxBoundary} 
                      onChange={(e) => setFormulaMaxBoundary(parseInt(e.target.value))}
                      className="w-full accent-primary-500 h-1 bg-slate-155 dark:bg-slate-800 rounded disabled:opacity-30"
                    />
                  </div>

                  <div className="space-y-1">
                    <div className="flex justify-between text-[10px] font-bold text-slate-650">
                      <span>{tLocal("计算容许下限 (Min Cap)", "Min Allowable Limit")}</span>
                      <span className="font-mono font-bold text-slate-850 dark:text-white">{formulaMinBoundary}</span>
                    </div>
                    <input 
                      disabled={!enableFormulaBounds}
                      type="range" 
                      min="0" 
                      max="49" 
                      step="1"
                      value={formulaMinBoundary} 
                      onChange={(e) => setFormulaMinBoundary(parseInt(e.target.value))}
                      className="w-full accent-primary-500 h-1 bg-slate-155 dark:bg-slate-800 rounded disabled:opacity-30"
                    />
                  </div>
                </div>
              </div>

            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 3. Formulas list select pills */}
      <div className="space-y-2.5 pt-1 border-t border-slate-100 dark:border-slate-800">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest block">
            {tLocal("已选定的分析公式系列 (勾选以验证)", "Select Formulas to evaluate in batch")}
          </span>
          <div className="flex items-center gap-3">
            <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
              onClick={selectAllFormulas}
              className="text-[9px] font-black text-indigo-500 hover:text-indigo-600 uppercase"
            >
              {tLocal("全部选择", "Select All")}
            </motion.button>
            <span className="text-slate-350">|</span>
            <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
              onClick={deselectAllFormulas}
              className="text-[9px] font-black text-slate-450 hover:text-slate-600 uppercase"
            >
              {tLocal("全部取消", "Clear Selection")}
            </motion.button>
          </div>
        </div>

        {formulas.length === 0 ? (
          <div className="p-4 rounded-xl border border-dashed border-slate-200 text-center text-xs text-slate-400">
            {tLocal("暂无任何公式可以使用，请先在下方库中创建自定义计算公式。", "No custom formulas available. Try adding one in the Editor.")}
          </div>
        ) : (
          <div className="flex flex-wrap gap-2.5">
            {formulas.map(f => {
              const isSelected = selectedFormulaIds.has(f.id);
              return (
                <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                  key={f.id}
                  onClick={() => toggleFormulaSelection(f.id)}
                  className={`px-3 py-1.5 rounded-full border text-xs font-bold transition-all flex items-center gap-1.5 active:scale-95 ${
                    isSelected
                      ? 'bg-primary-50 dark:bg-primary-950/30 border-primary-300 text-primary-650 dark:text-primary-400 shadow-sm'
                      : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-850'
                  }`}
                >
                  <div className={`w-1.5 h-1.5 rounded-full ${isSelected ? "bg-primary-550" : "bg-slate-300 dark:bg-slate-600"}`} />
                  <span className="truncate max-w-[150px]">{f.name}</span>
                  <span className="text-[9px] font-mono opacity-60 bg-slate-100 dark:bg-slate-850 px-1 rounded">
                    {f.unit || 'Index'}
                  </span>
                </motion.button>
              );
            })}
          </div>
        )}
      </div>

      {/* 4. Overall Analytics Summary Dashboard Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        
        {/* Core resin health index */}
        <div className="p-4 bg-indigo-50/45 dark:bg-indigo-950/15 border border-indigo-100/70 dark:border-indigo-900/30 rounded-2xl flex flex-col justify-between">
          <span className="text-[9px] font-black text-indigo-500 uppercase tracking-wider block">{tLocal("合规率指标", "Formulation Health")}</span>
          <div className="flex items-baseline gap-1 mt-3">
            <span className="text-3xl font-black font-sans leading-none text-indigo-650 dark:text-indigo-400">{stats.healthPercent}%</span>
          </div>
          <span className="text-[10px] text-slate-400/90 font-bold block mt-2">{tLocal("全树脂无阀值偏离率", "Of products safe & compliant")}</span>
        </div>

        {/* Checked Formulas */}
        <div className="p-4 bg-slate-50 dark:bg-slate-950/20 border border-slate-150 dark:border-slate-850 rounded-2xl flex flex-col justify-between">
          <span className="text-[9px] font-black text-slate-550 dark:text-slate-400 uppercase tracking-wider block">{tLocal("选检公式组件", "Formulas Activated")}</span>
          <div className="flex items-baseline gap-1 mt-3">
            <span className="text-3xl font-black font-sans leading-none">{selectedFormulaIds.size}</span>
            <span className="text-xs text-slate-400">/ {formulas.length}</span>
          </div>
          <span className="text-[10px] text-slate-400/90 font-bold block mt-2">{tLocal("进入流程的多因子数量", "Formulation variables checked")}</span>
        </div>

        {/* Flagged Products total */}
        <div className="p-4 bg-slate-50 dark:bg-slate-950/20 border border-slate-150 dark:border-slate-850 rounded-2xl flex flex-col justify-between">
          <span className="text-[9px] font-black text-slate-550 dark:text-slate-400 uppercase tracking-wider block">{tLocal("触发拦截产品", "Total Flagged")}</span>
          <div className="flex items-baseline gap-1 mt-3">
            <span className="text-3xl font-black font-sans leading-none text-slate-800 dark:text-white">
              {allProducts.length - stats.cleanProductsCount}
            </span>
            <span className="text-xs text-slate-400">/ {allProducts.length}</span>
          </div>
          <span className="text-[10px] text-slate-400/90 font-bold block mt-2">{tLocal("偏离设定限度的树脂", "Materials with violations")}</span>
        </div>

        {/* Warning Violations */}
        <div className="p-4 bg-amber-50/20 dark:bg-amber-950/10 border border-amber-100/50 dark:border-amber-900/10 rounded-2xl flex flex-col justify-between">
          <span className="text-[9px] font-black text-amber-500 uppercase tracking-wider block">{tLocal("一般预警偏离 (Warn)", "Warnings Flagged")}</span>
          <div className="flex items-baseline gap-1 mt-3">
            <span className="text-3xl font-black font-sans leading-none text-amber-600 dark:text-amber-450">{stats.warningCount}</span>
          </div>
          <span className="text-[10px] text-slate-400/90 font-bold block mt-2">{tLocal("处于亚健康阈值带", "Moderate range deviations")}</span>
        </div>

        {/* Critical Violations */}
        <div className="p-4 bg-rose-50/20 dark:bg-rose-950/10 border border-rose-100/40 dark:border-rose-900/20 rounded-2xl col-span-2 lg:col-span-1 flex flex-col justify-between">
          <span className="text-[9px] font-black text-rose-500 uppercase tracking-wider block">{tLocal("严重风险偏置 (Crit)", "Critical Hazards")}</span>
          <div className="flex items-baseline gap-1 mt-3">
            <span className="text-3xl font-black font-sans leading-none text-rose-600 dark:text-rose-450">{stats.criticalCount}</span>
          </div>
          <span className="text-[10px] text-slate-400/90 font-bold block mt-2">{tLocal("强度缺失/反应不匹配", "Severe structure/syntax risks")}</span>
        </div>

      </div>

      {/* 5. Validation Tab Controllers & Display Grid */}
      <div className="space-y-4">
        {/* Tab Filters and labels */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-2.5 gap-3">
          <div className="flex items-center gap-1.5 bg-slate-100/70 dark:bg-slate-900/60 p-1 rounded-xl">
            <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
              onClick={() => setFilterType('all')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                filterType === 'all' 
                  ? 'bg-white dark:bg-slate-800 text-slate-850 dark:text-white shadow-sm' 
                  : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
              }`}
            >
              {tLocal("全部数据", "All Results")} ({validationResults.length})
            </motion.button>
            <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
              onClick={() => setFilterType('critical')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                filterType === 'critical' 
                  ? 'bg-rose-50 dark:bg-rose-950/30 text-rose-650 dark:text-rose-400 shadow-sm' 
                  : 'text-slate-500 hover:text-rose-600 dark:text-slate-400 dark:hover:text-rose-450'
              }`}
            >
              {tLocal("红色缺陷", "Critical Alerts")} ({stats.criticalCount})
            </motion.button>
            <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
              onClick={() => setFilterType('warning')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                filterType === 'warning' 
                  ? 'bg-amber-50 dark:bg-amber-950/20 text-amber-650 dark:text-amber-450 shadow-sm' 
                  : 'text-slate-500 hover:text-amber-650 dark:text-slate-400'
              }`}
            >
              {tLocal("黄色预警", "Warnings")} ({stats.warningCount})
            </motion.button>
            <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
              onClick={() => setFilterType('clean')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                filterType === 'clean' 
                  ? 'bg-indigo-50 dark:bg-indigo-950/30 text-indigo-650 dark:text-indigo-400 shadow-sm' 
                  : 'text-slate-500 hover:text-slate-700 dark:text-slate-400'
              }`}
            >
              {tLocal("完美配方", "Compliant")} ({stats.cleanProductsCount})
            </motion.button>
          </div>

          <div className="text-[10px] text-slate-400 font-bold flex items-center gap-1">
            <Info size={12} className="text-primary-500" />
            <span>{tLocal("点击任一产品名可调出其配方编辑或基本性能信息", "Click product's grade name to view detailed molecular properties")}</span>
          </div>
        </div>

        {/* Results Render Cards Grid */}
        <div className="max-h-[380px] overflow-y-auto custom-scrollbar space-y-3 pr-1">
          <AnimatePresence mode="popLayout">
            {filteredResults.length === 0 ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="py-12 border border-dashed border-slate-205 dark:border-slate-800 rounded-2xl text-center text-xs text-slate-400"
              >
                {tLocal("在此过滤器下未检测到符合条件的配方产品。", "No matching items detected in this category.")}
              </motion.div>
            ) : (
              filteredResults.map((r, pIdx) => {
                const hasViolations = r.violations.length > 0;
                return (
                  <motion.div
                    key={r.product.id || pIdx}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    className={`p-4 rounded-2xl border transition-all ${
                      hasViolations
                        ? r.violations.some(v => v.severity === 'critical')
                          ? 'border-rose-100 bg-rose-50/10 dark:border-rose-950/30 dark:bg-rose-950/5'
                          : 'border-amber-100 bg-amber-50/10 dark:border-amber-950/10 dark:bg-amber-950/5'
                        : 'border-slate-150 bg-white dark:border-slate-850 dark:bg-slate-950/10'
                    } flex flex-col md:flex-row md:items-start justify-between gap-4`}
                  >
                    
                    {/* Left details - product identifier */}
                    <div className="space-y-2 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        {onViewProduct ? (
                          <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                            onClick={() => onViewProduct(r.product)}
                            className="text-xs font-black text-slate-850 dark:text-white hover:text-primary-500 text-left outline-none hover:underline"
                          >
                            {r.product.gradeName}
                          </motion.button>
                        ) : (
                          <span className="text-xs font-black text-slate-850 dark:text-white leading-none">
                            {r.product.gradeName}
                          </span>
                        )}
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 font-bold text-slate-500">
                          {r.product.manufacturer}
                        </span>

                        {/* Status tag */}
                        {hasViolations ? (
                          r.violations.some(v => v.severity === 'critical') ? (
                            <span className="text-[9px] bg-rose-500/10 text-rose-600 dark:text-rose-400 px-1.5 py-0.5 rounded font-black uppercase tracking-wider flex items-center gap-0.5">
                              <ShieldAlert size={10} />
                              {tLocal("严重危险缺陷", "CRITICAL")}
                            </span>
                          ) : (
                            <span className="text-[9px] bg-amber-500/10 text-amber-600 dark:text-amber-450 px-1.5 py-0.5 rounded font-black uppercase tracking-wider flex items-center gap-0.5">
                              <AlertTriangle size={10} />
                              {tLocal("一般限制预警", "WARNING")}
                            </span>
                          )
                        ) : (
                          <span className="text-[9px] bg-indigo-500/10 text-indigo-650 dark:text-indigo-400 px-1.5 py-0.5 rounded font-black uppercase tracking-wider flex items-center gap-0.5">
                            <CheckCircle size={10} />
                            {tLocal("极致健康达边", "COMPLIANT")}
                          </span>
                        )}
                      </div>

                      {/* Diagnostic list */}
                      <div className="space-y-1.5 pt-0.5">
                        {hasViolations ? (
                          r.violations.map((v, vIdx) => (
                            <div key={vIdx} className="flex items-start gap-1.5 text-[11px] leading-relaxed font-semibold">
                              <span className={`w-1.5 h-1.5 rounded-full shrink-0 mt-1.5 ${v.severity === 'critical' ? 'bg-rose-500' : 'bg-amber-500'}`} />
                              <span className="text-slate-650 dark:text-slate-350">
                                {tLocal(v.messageZh, v.messageEn)}
                              </span>
                            </div>
                          ))
                        ) : (
                          <div className="text-[11px] text-slate-450 italic font-semibold">
                            {tLocal("✓ 合规通过：公式解析均吻合化学计量且配方物性参数完整在预设安全范围内。", "✓ All systems clear: stoichiometry matches and formulation metrics operate fully within healthy ranges.")}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Right details - physical thresholds matrix */}
                    {hasViolations && (
                      <div className="flex flex-wrap gap-2.5 md:self-center shrink-0">
                        {r.violations.map((v, vIdx) => (
                          <div key={vIdx} className="p-2.5 bg-slate-50 dark:bg-slate-900/60 rounded-xl border border-slate-150/45 dark:border-slate-850 text-right min-w-[120px]">
                            <span className="text-[8px] font-black text-slate-400 uppercase tracking-wider block">
                              {tLocal(v.metricLabelZh, v.metricLabelEn)}
                            </span>
                            <span className="text-[10px] font-bold text-slate-400 block mt-0.5">
                              {tLocal("限值", "Limit")}: {v.expectedRange}
                            </span>
                            <span className={`text-xs font-black font-mono mt-1 block flex items-center justify-end gap-1 ${
                              v.severity === 'critical' ? 'text-rose-600 dark:text-rose-450' : 'text-amber-600 dark:text-amber-450'
                            }`}>
                              {v.actualValue}
                              <ArrowRight size={10} />
                            </span>
                          </div>
                        ))}
                      </div>
                    )}

                  </motion.div>
                );
              })
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};
