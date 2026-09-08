import React, { useState, useMemo, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "motion/react";
import * as echarts from "@/lib/echarts";
import {
  X,
  Calculator,
  Plus,
  Trash2,
  Info,
  Check,
  Play,
  Settings,
  Layers,
  Activity,
  ChevronDown,
  ChevronUp,
  Loader2,
  GitCompare,
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
  Beaker,
  Share2,
  Copy,
  Download,
  BookOpen,
  Save,
} from "lucide-react";
import { FormulaConfig, Product, FormulaHistory, FormulaTemplate } from '@/types/index';
import { formulaEngine } from "@/lib/formulaParser";
import { useLanguage } from "@/contexts/LanguageContext";
import { useMonteCarlo } from '@/hooks/math/useMonteCarlo';
import { diffWords } from 'diff';
import { DependencyHeatmap } from "@/components/features/Product/DependencyHeatmap";
import { 
  getChemicalReplacementSuggestions, 
  AiSuggestionEngineResponse 
} from "@/services/aiService";
import { safeStorage } from "@/lib/utils";


interface FormulaEditorModalProps {
  isOpen: boolean;
  onClose: () => void;
  formulas: FormulaConfig[];
  onAdd: (f: Omit<FormulaConfig, "id">) => void;
  onUpdate: (id: string, f: Partial<FormulaConfig>) => void;
  onRemove: (id: string) => void;
  allProducts: Product[];
}

const DiffViewer = ({ oldText, newText, className = "" }: { oldText: string, newText: string, className?: string }) => {
  const diffs = useMemo(() => diffWords(oldText || '', newText || ''), [oldText, newText]);
  return (
    <div className={`whitespace-pre-wrap break-words ${className}`}>
      {diffs.map((part, index) => {
        if (!part.added && !part.removed && part.value.trim() === '') {
          return <span key={index}>{part.value}</span>;
        }
        const color = part.added 
            ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-800 dark:text-emerald-300' 
            : part.removed 
                ? 'bg-rose-100 dark:bg-rose-900/40 text-rose-800 dark:text-rose-300 line-through opacity-75' 
                : 'text-slate-700 dark:text-slate-300';
        return <span key={index} className={`rounded-[2px] ${color}`}>{part.value}</span>;
      })}
    </div>
  );
};

function validateChemicalBalance(expression: string): { isValid: boolean; message: string } | null {
  const lines = expression.split('\n');
  let chemMatch = null;
  for(const line of lines) {
    if (line.includes('->') || line.includes('=')) {
       const eq = line.split(/->|=/);
       if(eq.length === 2 && eq[0].trim() && eq[1].trim()) {
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

const BUILT_IN_TEMPLATES: FormulaTemplate[] = [
  {
    id: "t_epoxy_amine",
    name: "Epoxy-Amine Stoichiometric Ratio (环氧-胺固化剂配比)",
    description: "Calculates the stoichiometric amine hardener amount required for 100 parts of epoxy resin based on Amine Hydrogen Equivalent Weight (AHEW) and Epoxy Equivalent Weight (EEW). Useful for stoichiometric blend designs.",
    unit: "phr (parts per hundred resin)",
    baseExpression: "((props['环氧当量'] || props['Epoxy Equivalent Weight'] || 190) > 0 ? ({{AHEW}} * 100 / (props['环氧当量'] || props['Epoxy Equivalent Weight'] || 190)) : 0)",
    category: "Stoichiometry & Mixing",
    parameters: [
      {
        key: "AHEW",
        label: "Amine Hydrogen Equivalent Weight (AHEW)",
        type: "number",
        defaultValue: 43,
        placeholder: "e.g. 43 for DETA",
        unit: "g/eq",
        description: "Molecular weight of the amine hardener divided by the number of active amine hydrogens."
      }
    ]
  },
  {
    id: "t_arrhenius_gel",
    name: "Arrhenius Gelation Time (阿伦尼乌斯凝胶时间预测)",
    description: "Predicts polymer gelation or curing time as a function of processing temperature using Arrhenius kinetic relation: t = A * exp(Ea / (R * T)). Helps optimize thermosetting compound profiles.",
    unit: "min",
    baseExpression: "{{A}} * Math.exp({{Ea}} / (8.314 * ((props['固化温度'] || props['Curing Temperature'] || 120) + 273.15)))",
    category: "Kinetic Modeling",
    parameters: [
      {
        key: "A",
        label: "Pre-exponential Frequency Factor (A)",
        type: "number",
        defaultValue: 0.005,
        placeholder: "e.g. 0.005",
        unit: "min",
        description: "The kinetic collision/frequency factor representing molecular interactions."
      },
      {
        key: "Ea",
        label: "Arrhenius Activation Energy (Ea)",
        type: "number",
        defaultValue: 52000,
        placeholder: "e.g. 52000",
        unit: "J/mol",
        description: "Energy activation barrier necessary to initiate crosslink/polymerization reaction."
      }
    ]
  },
  {
    id: "t_fox_tg",
    name: "Copolymer Tg Estimator (Fox Equation / 共聚物Tg预测)",
    description: "Estimates the Glass Transition Temperature (Tg) of custom acrylic, epoxy, or urethane co-polymeric systems using the mass fraction of Monomer 1 and homopolymer Tg values.",
    unit: "°C",
    baseExpression: "1 / ({{w1}} / {{tg1}} + (1 - {{w1}}) / {{tg2}}) - 273.15",
    category: "Thermal Properties",
    parameters: [
      {
        key: "w1",
        label: "Mass Fraction of Monomer 1 (w1)",
        type: "number",
        defaultValue: 0.6,
        placeholder: "Value between 0 and 1, e.g. 0.6",
        unit: "fraction",
        description: "The weight fraction of the first homopolymer constituent in the copolymer network."
      },
      {
        key: "tg1",
        label: "Tg of Monomer 1 Homopolymer (Tg1)",
        type: "number",
        defaultValue: 378,
        placeholder: "In Kelvin, e.g. 378 for PMMA (105°C)",
        unit: "K",
        description: "Homopolymer reference glass transition temperature of component 1 inside Kelvin scale."
      },
      {
        key: "tg2",
        label: "Tg of Monomer 2 Homopolymer (Tg2)",
        type: "number",
        defaultValue: 219,
        placeholder: "In Kelvin, e.g. 219 for n-BA (-54°C)",
        unit: "K",
        description: "Homopolymer reference glass transition temperature of component 2 inside Kelvin scale."
      }
    ]
  },
  {
    id: "t_crosslink_density",
    name: "Thermoset Crosslink Density (热固性交联密度估算)",
    description: "Estimates physical crosslink density from resin density and molecular weight average between crosslinks (Mc) according to the relation: [X] = Density / Mc.",
    unit: "mol/cm³",
    baseExpression: "(props['密度'] || props['Density'] || 1.1) / {{Mc}}",
    category: "Physical Chemistry",
    parameters: [
      {
        key: "Mc",
        label: "MW Between Crosslinks (Mc)",
        type: "number",
        defaultValue: 350,
        placeholder: "e.g. 350",
        unit: "g/mol",
        description: "Average molecular mass of polymer chain segments separating adjacent nodes."
      }
    ]
  }
];

export const FormulaEditorModal: React.FC<FormulaEditorModalProps> = React.memo(({
  isOpen,
  onClose,
  formulas,
  onAdd,
  onUpdate,
  onRemove,
  allProducts,
}) => {
  const { t: _t } = useLanguage();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [expression, setExpression] = useState("");
  const [description, setDescription] = useState("");
  const [unit, setUnit] = useState("");
  const [testResult, setTestResult] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [realtimeError, setRealtimeError] = useState<string | null>(null);
  const [realtimeChemBalance, setRealtimeChemBalance] = useState<{isValid: boolean; message: string} | null>(null);
  
  const [activeTab, setActiveTab] = useState<'editor' | 'history' | 'templates' | 'heatmap' | 'suggestions'>('editor');
  const [isGeneratingSuggestions, setIsGeneratingSuggestions] = useState(false);
  const [suggestionsResponse, setSuggestionsResponse] = useState<AiSuggestionEngineResponse | null>(null);
  const [suggestionError, setSuggestionError] = useState<string | null>(null);
  const [targetProperty, setTargetProperty] = useState<string>("Durability");
  const [customConstraints, setCustomConstraints] = useState<string>("");
  const [comparingHistory, setComparingHistory] = useState<FormulaHistory | null>(null);
  const [copiedType, setCopiedType] = useState<'json' | 'share' | null>(null);
  
  const [customTemplates, setCustomTemplates] = useState<FormulaTemplate[]>(() => {
    const saved = safeStorage.local.getItem('resindb-custom-templates');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        return [];
      }
    }
    return [];
  });

  useEffect(() => {
    safeStorage.local.setItem('resindb-custom-templates', JSON.stringify(customTemplates));
  }, [customTemplates]);

  const [selectedTemplate, setSelectedTemplate] = useState<FormulaTemplate | null>(null);
  const [templateParamValues, setTemplateParamValues] = useState<Record<string, string>>({});
  const [customTemplateName, setCustomTemplateName] = useState("");
  const [customTemplateDesc, setCustomTemplateDesc] = useState("");
  
  const [showMonteCarlo, setShowMonteCarlo] = useState(false);
  const [variances, setVariances] = useState<Record<string, number>>({});
  const { simulationStats, isSimulating, error: mcError, runSimulation, resetSimulation } = useMonteCarlo();
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (!expression.trim()) {
        setRealtimeError(null);
        setRealtimeChemBalance(null);
        return;
      }
      
      const validationError = formulaEngine.validate(expression, name, formulas);
      setRealtimeError(validationError);
      
      setRealtimeChemBalance(validateChemicalBalance(expression));
    }, 400);
    return () => clearTimeout(timer);
  }, [expression, name, formulas]);

  // Extract variables used in the formula
  const usedVariables = useMemo(() => {
     const matches: string[] = expression.match(/props\['([^']+)'\]/g) || [];
     const vars = new Set<string>();
     matches.forEach(m => vars.add(m.replace(/^props\['/, '').replace(/'\]$/, '')));
     return Array.from(vars);
  }, [expression]);

  // Sync variance state when used variables change
  useEffect(() => {
     setVariances(prev => {
         const next = { ...prev };
         for (const v of usedVariables) {
             if (!(v in next)) next[v] = 5; // Default 5% variance
         }
         return next;
     });
     resetSimulation();
  }, [usedVariables, resetSimulation]);
  
  // Render KDE chart when stats update
  useEffect(() => {
     if (showMonteCarlo && simulationStats && chartRef.current) {
         if (!chartInstance.current) {
             chartInstance.current = echarts.getInstanceByDom(chartRef.current) || echarts.init(chartRef.current);
         }
         
         const data = simulationStats.kde.map((point) => [point.x, point.y]);
         
         chartInstance.current.setOption({
            backgroundColor: 'transparent',
            tooltip: {
                trigger: 'axis',
                
                 
                formatter: (params: unknown) => {
                    const first = Array.isArray(params) ? params[0] : null;
                    const rawValue = first && typeof first === 'object' && 'value' in first
                      ? (first as { value?: unknown }).value
                      : null;
                    const x = Array.isArray(rawValue) && typeof rawValue[0] === 'number'
                      ? rawValue[0].toFixed(2)
                      : '—';
                    return `Value: ${x}`;
                }
            },
            grid: { top: 20, right: 20, bottom: 20, left: 20 },
            xAxis: { 
                type: 'value', 
                scale: true,
                axisLabel: { fontSize: 10, color: '#94a3b8' },
                splitLine: { show: false }
            },
            yAxis: { 
                type: 'value', 
                show: false 
            },
            series: [{
                name: 'KDE',
                type: 'line',
                data: data,
                smooth: true,
                symbol: 'none',
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(99, 102, 241, 0.4)' },
                        { offset: 1, color: 'rgba(99, 102, 241, 0.05)' }
                    ])
                },
                lineStyle: { color: '#6366f1', width: 2 },
                markLine: {
                    symbol: 'none',
                    data: [
                        { xAxis: simulationStats.p5, lineStyle: { color: '#f43f5e', type: 'dashed' }, label: { formatter: 'P5', position: 'insideStartTop' } },
                        { xAxis: simulationStats.p95, lineStyle: { color: '#f43f5e', type: 'dashed' }, label: { formatter: 'P95', position: 'insideEndTop' } }
                    ]
                }
            }]
         });
     }
  }, [simulationStats, showMonteCarlo]);

  // Handle Resize
  useEffect(() => {
      const ro = new ResizeObserver(() => { if (chartInstance.current) chartInstance.current.resize(); });
    if (chartRef.current) ro.observe(chartRef.current);
    return () => ro.disconnect();
  }, []);

  // Available properties for variables
  const availableProps = useMemo(() => {
    const keys = new Set<string>();
    allProducts.slice(0, 100).forEach((p) => {
      Object.keys(p.properties).forEach((k) => keys.add(k));
    });
    return Array.from(keys).sort();
  }, [allProducts]);

  const currentFormula = formulas.find((f) => f.id === editingId);

  useEffect(() => {
    if (currentFormula) {
      setName(currentFormula.name);
      setExpression(currentFormula.expression);
      setDescription(currentFormula.description || "");
      setUnit(currentFormula.unit || "");
    } else {
      setName("");
      setExpression("");
      setDescription("");
      setUnit("");
      setActiveTab('editor'); // Reset to editor tab on new formula
    }
    setError(null);
    setTestResult(null);
  }, [currentFormula, editingId]);

  const handleTest = () => {
    if (!expression.trim()) return;
    try {
      const tempConfig: FormulaConfig = { id: "temp_test_id", name: name || "TestFormula", expression, unit: "" };
      const tempFormulas = [...formulas.filter(f => f.name !== tempConfig.name), tempConfig];
      const evaluator = formulaEngine.compileGraph(tempFormulas);
      
      const firstProduct = allProducts[0];
      if (firstProduct) {
        const result = evaluator(firstProduct)[tempConfig.id];
        setTestResult(result);
        setError(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid formula or cyclic dependency detected");
    }
  };

  const handleSave = () => {
    if (!name || !expression) return;
    const validationError = formulaEngine.validate(expression, name, formulas);
    if (validationError) {
      setError(validationError);
      return;
    }
    if (editingId) {
      if (currentFormula) {
        if (
          currentFormula.expression !== expression ||
          currentFormula.name !== name ||
          currentFormula.unit !== unit ||
          currentFormula.description !== description
        ) {
          const newHistoryItem: FormulaHistory = {
            date: new Date().toISOString(),
            expression: currentFormula.expression,
            name: currentFormula.name,
            unit: currentFormula.unit,
            description: currentFormula.description
          };
          const updatedHistory = [...(currentFormula.history || []), newHistoryItem];
          onUpdate(editingId, { name, expression, description, unit, history: updatedHistory });
        } else {
          onUpdate(editingId, { name, expression, description, unit });
        }
      }
    } else {
      onAdd({ name, expression, description, unit, history: [] });
    }
    setEditingId(null);
  };

  const getFormulaExportData = () => {
    return {
      name: name || "Untitled Formula",
      expression: expression || "",
      unit: unit || undefined,
      description: description || undefined,
      history: currentFormula?.history || [],
      validation: {
        status: realtimeError ? "invalid" : (expression ? "valid" : "empty"),
        error: realtimeError || undefined,
        chemicalBalance: realtimeChemBalance || undefined
      },
      exportedAt: new Date().toISOString()
    };
  };

  const handleCopyJson = () => {
    const dataStr = JSON.stringify(getFormulaExportData(), null, 2);
    navigator.clipboard.writeText(dataStr).then(() => {
      setCopiedType('json');
      setTimeout(() => setCopiedType(null), 2000);
    });
  };

  const handleCopyShareText = () => {
    const validationText = realtimeError 
      ? `⚠️ Invalid Formula: ${realtimeError}` 
      : (realtimeChemBalance ? `✅ Valid Formula (Chem: ${realtimeChemBalance.message})` : (expression ? "✅ Formula is valid and compiles" : "Empty Formula"));

    const text = `🧪 *ResinDB Formula Configuration: ${name || "Untitled Formula"}*
*   **Expression**: \`${expression || "None"}\`
*   **Unit**: ${unit || 'N/A'}
*   **Description**: ${description || 'N/A'}
*   **Validation**: ${validationText}
*   **History length**: ${(currentFormula?.history || []).length} previous iteration(s)`;
    
    navigator.clipboard.writeText(text).then(() => {
      setCopiedType('share');
      setTimeout(() => setCopiedType(null), 2000);
    });
  };

  const handleDownloadJson = () => {
    const dataStr = JSON.stringify(getFormulaExportData(), null, 2);
    const blob = new Blob([dataStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${(name || "untitled").toLowerCase().replace(/\s+/g, "_")}_formula_export.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleSelectTemplate = (template: FormulaTemplate) => {
    setSelectedTemplate(template);
    const initialVals: Record<string, string> = {};
    template.parameters.forEach(p => {
      initialVals[p.key] = String(p.defaultValue);
    });
    setTemplateParamValues(initialVals);
  };

  const getComputedTemplateExpression = (template: FormulaTemplate, values: Record<string, string>) => {
    let expr = template.baseExpression;
    template.parameters.forEach(p => {
      const val = values[p.key] !== undefined && values[p.key] !== "" ? values[p.key] : String(p.defaultValue);
      expr = expr.replaceAll(`{{${p.key}}}`, val);
    });
    return expr;
  };

  const handleApplyTemplate = () => {
    if (!selectedTemplate) return;
    const finalExpr = getComputedTemplateExpression(selectedTemplate, templateParamValues);
    setName(selectedTemplate.name.split(" (")[0]);
    setExpression(finalExpr);
    setUnit(selectedTemplate.unit);
    setDescription(selectedTemplate.description);
    setActiveTab('editor');
    setSelectedTemplate(null);
  };

  const handleSaveAsTemplate = () => {
    if (!name || !expression) return;
    const newTemplate: FormulaTemplate = {
      id: `t_custom_${Date.now()}`,
      name: customTemplateName || `${name} Template`,
      description: customTemplateDesc || description || "Custom defined formula template",
      unit: unit || "",
      baseExpression: expression,
      parameters: [],
      category: "My Custom Templates",
      isCustom: true,
      createdAt: new Date().toISOString()
    };
    setCustomTemplates(prev => [...prev, newTemplate]);
    setCustomTemplateName("");
    setCustomTemplateDesc("");
  };

  const handleGenerateSuggestions = async () => {
    setIsGeneratingSuggestions(true);
    setSuggestionError(null);
    try {
      const res = await getChemicalReplacementSuggestions(
        { name: name || "Current Formulation", expression, description, unit },
        allProducts,
        targetProperty,
        customConstraints
      );
      setSuggestionsResponse(res);
    } catch (err) {
      setSuggestionError(err instanceof Error ? err.message : "Error querying Chemical Suggestion Engine.");
    } finally {
      setIsGeneratingSuggestions(false);
    }
  };


  const handleRemoveCustomTemplate = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setCustomTemplates(prev => prev.filter(t => t.id !== id));
    if (selectedTemplate?.id === id) {
      setSelectedTemplate(null);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm"
      />
      <motion.div
        initial={{ scale: 0.9, opacity: 0, y: 20 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        exit={{ scale: 0.9, opacity: 0, y: 20 }}
        className="relative w-full max-w-4xl max-h-[80vh] bg-white dark:bg-slate-950 rounded-3xl shadow-2xl overflow-hidden flex flex-col border border-slate-200 dark:border-slate-800"
      >
        {/* Header */}
        <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-900/50">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-primary-100 dark:bg-primary-900/30 rounded-2xl text-primary-600">
              <Calculator size={24} />
            </div>
            <div>
              <h2 className="text-xl font-black text-slate-800 dark:text-white tracking-tight">
                Performance Index Engine
              </h2>
              <p className="text-xs text-slate-500 font-medium tracking-wide flex items-center gap-1.5 uppercase">
                <Settings size={12} /> Custom Material Computation Formulas
              </p>
            </div>
          </div>
          <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
            onClick={onClose}
            className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-colors"
          >
            <X size={20} className="text-slate-400" />
          </motion.button>
        </div>

        <div className="flex-1 overflow-hidden flex">
          {/* Sidebar: Formula List */}
          <div className="w-64 border-r border-slate-100 dark:border-slate-800 flex flex-col bg-slate-50/30 dark:bg-slate-950/20">
            <div className="p-4 space-y-3 flex-1 overflow-y-auto">
              <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                onClick={() => setEditingId(null)}
                className={`w-full flex items-center gap-2 p-3 rounded-2xl text-sm font-bold transition-all border ${editingId === null ? "bg-primary-600 text-white border-transparent" : "bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-800"}`}
              >
                <Plus size={16} /> New Formula
              </motion.button>

              <div className="space-y-1">
                {formulas.map((f) => (
                  <div key={f.id} className="group relative">
                    <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                      onClick={() => setEditingId(f.id)}
                      className={`w-full text-left px-4 py-3 rounded-xl text-xs font-bold transition-all ${editingId === f.id ? "bg-primary-50 dark:bg-primary-900/20 text-primary-600" : "hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500"}`}
                    >
                      {f.name}
                    </motion.button>
                    <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                      onClick={(e) => {
                        e.stopPropagation();
                        onRemove(f.id);
                      }}
                      className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 opacity-0 group-hover:opacity-100 hover:text-rose-500 transition-all"
                    >
                      <Trash2 size={12} />
                    </motion.button>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Editor Area */}
          <div className="flex-1 overflow-y-auto p-4 md:p-6 flex flex-col space-y-4 custom-scrollbar">
            {/* Tabs & Share/Export Controls */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-200 dark:border-slate-800 shrink-0 pb-1 sm:pb-0 gap-2">
              <div className="flex">
                <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} 
                  onClick={() => setActiveTab('editor')} 
                  className={`px-4 py-2 text-sm font-bold border-b-2 transition-colors ${activeTab === 'editor' ? 'border-primary-500 text-primary-600 dark:text-primary-400' : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'}`}
                >
                  Editor
                </motion.button>
                <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} 
                  onClick={() => setActiveTab('templates')} 
                  className={`px-4 py-2 text-sm font-bold border-b-2 transition-colors ${activeTab === 'templates' ? 'border-primary-500 text-primary-600 dark:text-primary-450' : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'}`}
                >
                  Templates
                </motion.button>
                <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} 
                  onClick={() => setActiveTab('heatmap')} 
                  className={`px-4 py-2 text-sm font-bold border-b-2 transition-colors ${activeTab === 'heatmap' ? 'border-primary-500 text-primary-600 dark:text-primary-400' : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'}`}
                >
                  Dependencies Heatmap
                </motion.button>
                <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} 
                  onClick={() => setActiveTab('suggestions')} 
                  className={`px-4 py-2 text-sm font-bold border-b-2 transition-colors ${activeTab === 'suggestions' ? 'border-primary-500 text-primary-600 dark:text-primary-400' : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'} flex items-center gap-1.5`}
                >
                  <Beaker size={14} className="text-primary-500" /> AI Suggestions
                </motion.button>
                {editingId && (
                  <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} 
                    onClick={() => setActiveTab('history')} 
                    className={`px-4 py-2 text-sm font-bold border-b-2 transition-colors ${activeTab === 'history' ? 'border-primary-500 text-primary-600 dark:text-primary-400' : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'}`}
                  >
                    Change History
                  </motion.button>
                )}
              </div>

              {/* Share & Export controls */}
              <div className="flex items-center gap-1.5 px-2 pb-1 sm:pb-0">
                <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                  onClick={handleCopyShareText}
                  title="Copy formatted template to share with teammates"
                  className="px-2.5 py-1.5 bg-slate-50 hover:bg-slate-100 dark:bg-slate-900 dark:hover:bg-slate-850 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-800 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 active:scale-95 shadow-sm"
                >
                  {copiedType === 'share' ? (
                    <>
                      <Check size={12} className="text-emerald-500" />
                      <span className="text-emerald-600 dark:text-emerald-400 font-bold">Copied Share!</span>
                    </>
                  ) : (
                    <>
                      <Share2 size={12} />
                      <span>Copy Share</span>
                    </>
                  )}
                </motion.button>

                <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                  onClick={handleCopyJson}
                  title="Copy full config JSON with history to clipboard"
                  className="px-2.5 py-1.5 bg-slate-50 hover:bg-slate-100 dark:bg-slate-900 dark:hover:bg-slate-850 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-800 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 active:scale-95 shadow-sm"
                >
                  {copiedType === 'json' ? (
                    <>
                      <Check size={12} className="text-emerald-500" />
                      <span className="text-emerald-600 dark:text-emerald-400 font-bold">Copied JSON!</span>
                    </>
                  ) : (
                    <>
                      <Copy size={12} />
                      <span>Copy JSON</span>
                    </>
                  )}
                </motion.button>

                <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                  onClick={handleDownloadJson}
                  title="Download configuration JSON file"
                  className="px-2.5 py-1.5 bg-slate-50 hover:bg-slate-100 dark:bg-slate-900 dark:hover:bg-slate-850 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-800 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 active:scale-95 shadow-sm"
                >
                  <Download size={12} />
                  <span>Download</span>
                </motion.button>
              </div>
            </div>

            {activeTab === 'editor' ? (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 flex-1">
                <div className="space-y-4">
                  <div className="space-y-1.5">
                  <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest px-1">
                    Index Name
                  </label>
                  <input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Stiffness-to-Weight"
                    className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl text-sm focus:ring-2 focus:ring-primary-500/20 outline-none transition-all"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest px-1">
                    Unit
                  </label>
                  <input
                    value={unit}
                    onChange={(e) => setUnit(e.target.value)}
                    placeholder="e.g. MPa, g/cm³"
                    className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl text-sm focus:ring-2 focus:ring-primary-500/20 outline-none transition-all"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest px-1">
                    Formula (JS Syntax)
                  </label>
                  <div className="relative">
                    <textarea
                      value={expression}
                      onChange={(e) => setExpression(e.target.value)}
                      placeholder="props['Density'] * 0.1"
                      rows={4}
                      className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl text-sm font-mono focus:ring-2 focus:ring-primary-500/20 outline-none transition-all resize-none"
                    />
                    <div className="absolute right-3 bottom-3 flex gap-2">
                      <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                        onClick={handleTest}
                        className="p-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700/50 rounded-xl text-primary-500 hover:bg-primary-50 dark:hover:bg-primary-900/10 transition-all shadow-sm flex items-center gap-1.5 text-[10px] font-black"
                      >
                        <Play size={10} /> TEST
                      </motion.button>
                    </div>
                  </div>
                  {error && !realtimeError && (
                    <p className="text-[10px] text-rose-500 font-bold px-1">
                      {error}
                    </p>
                  )}
                  {(realtimeError || realtimeChemBalance || (!realtimeError && expression.trim())) && (
                    <div className="space-y-2 mt-2 px-1">
                       {expression.trim() && !realtimeError && (
                          <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 text-[11px] font-bold">
                            <CheckCircle2 size={12} />
                            <span>Syntax valid</span>
                          </div>
                       )}
                       {realtimeError && (
                          <div className="flex items-center gap-2 text-rose-600 dark:text-rose-400 text-[11px] font-bold">
                            <AlertCircle size={12} />
                            <span>{realtimeError}</span>
                          </div>
                       )}
                       {realtimeChemBalance && (
                          <div className={`flex items-center gap-2 text-[11px] font-bold ${
                             realtimeChemBalance.isValid 
                                ? 'text-indigo-600 dark:text-indigo-400'
                                : 'text-amber-600 dark:text-amber-400'
                          }`}>
                            <Beaker size={12} />
                            <span>{realtimeChemBalance.message}</span>
                          </div>
                       )}
                    </div>
                  )}
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest px-1">
                    Description
                  </label>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Detailed explanation of this computation..."
                    className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl text-sm focus:ring-2 focus:ring-primary-500/20 outline-none transition-all resize-none"
                  />
                </div>
              </div>

              <div className="space-y-4">
                <div className="p-4 bg-indigo-50/50 dark:bg-indigo-900/10 border border-indigo-100 dark:border-indigo-800/40 rounded-2xl space-y-3">
                  <h3 className="text-xs font-black text-indigo-600 dark:text-indigo-400 flex items-center gap-2 uppercase tracking-tight">
                    <Layers size={14} /> Available Properties
                  </h3>
                  <div className="flex flex-wrap gap-1.5 h-40 lg:h-48 overflow-y-auto custom-scrollbar p-1">
                    {availableProps.map((prop) => (
                      <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                        key={prop}
                        onClick={() =>
                          setExpression((prev) => prev.endsWith("props['") ? prev + `${prop}']` : prev + `props['${prop}']`)
                        }
                        className="px-2 py-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-[10px] font-mono text-slate-500 hover:border-primary-500 hover:text-primary-600 rounded-lg transition-all"
                      >
                        {prop}
                      </motion.button>
                    ))}
                  </div>
                  <div className="pt-2 border-t border-indigo-100 dark:border-indigo-900/30 flex items-center gap-3 text-[10px] text-indigo-500/60 font-bold italic">
                    <Info size={12} /> Click to insert into formula
                  </div>
                </div>

                {testResult !== null && (
                  <motion.div
                    initial={{ scale: 0.95, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className="p-4 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-100 dark:border-emerald-800 rounded-2xl flex flex-col gap-3"
                  >
                    <div className="flex items-center justify-between">
                        <div>
                          <p className="text-[10px] font-black text-emerald-600 uppercase tracking-widest">
                            Test Output
                          </p>
                          <p className="text-2xl font-mono font-black text-emerald-700 dark:text-emerald-400">
                            {testResult.toFixed(4)}
                          </p>
                        </div>
                        <div className="p-3 bg-emerald-500 rounded-2xl text-white">
                          <Check size={20} />
                        </div>
                    </div>
                    
                    {/* Monte Carlo Simulator Toggle */}
                    <div className="border-t border-emerald-200/50 dark:border-emerald-800/50 pt-3">
                       <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} 
                         onClick={() => setShowMonteCarlo(!showMonteCarlo)}
                         className="flex items-center justify-between w-full text-xs font-bold text-emerald-700 dark:text-emerald-500 hover:bg-emerald-100/50 dark:hover:bg-emerald-900/30 p-2 rounded-lg transition-colors"
                       >
                           <span className="flex items-center gap-1.5"><Activity size={14}/> Monte Carlo Uncertainty Simulator</span>
                           {showMonteCarlo ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                       </motion.button>
                    </div>
                    
                    <AnimatePresence>
                        {showMonteCarlo && (
                           <motion.div
                              initial={{ height: 0, opacity: 0 }}
                              animate={{ height: "auto", opacity: 1 }}
                              exit={{ height: 0, opacity: 0 }}
                              className="overflow-hidden"
                           >
                              <div className="pt-2 pb-2 space-y-3">
                                  <div>
                                     <p className="text-[10px] font-bold text-slate-500 mb-2 uppercase tracking-wide">Input Variability (+/- %)</p>
                                     <div className="space-y-2 max-h-32 overflow-y-auto custom-scrollbar pr-2">
                                        {usedVariables.length === 0 ? (
                                           <div className="text-xs text-slate-400 italic">No variables detected yet. Add a property to the formula to simulate uncertainty.</div>
                                        ) : usedVariables.map(v => (
                                            <div key={v} className="flex items-center justify-between">
                                                <span className="text-[10px] font-mono text-slate-600 truncate max-w-[120px]" title={v}>{v}</span>
                                                <div className="flex items-center gap-2">
                                                   <span className="text-[10px] text-slate-400 font-bold">{variances[v]}%</span>
                                                   <input 
                                                      type="range" min="0" max="25" step="1" 
                                                      value={variances[v] || 0}
                                                      onChange={e => setVariances(prev => ({...prev, [v]: parseInt(e.target.value)}))}
                                                      className="w-20 accent-emerald-500"
                                                   />
                                                </div>
                                            </div>
                                        ))}
                                     </div>
                                  </div>
                                  
                                  <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                                     onClick={() => {
                                        if (allProducts[0] && expression) {
                                            const tempConfig = { id: name || "temp", name, expression, unit };
                                            const testFormulas = [...formulas.filter(f => f.id !== tempConfig.id), tempConfig];
                                            runSimulation(tempConfig.id, testFormulas, allProducts[0], variances, 5000);
                                        }
                                     }}
                                     disabled={usedVariables.length === 0 || isSimulating || !expression}
                                     className="w-full py-2 bg-slate-800 text-white rounded-xl text-xs font-bold hover:bg-slate-700 disabled:opacity-50 flex items-center justify-center gap-2 transition-all"
                                  >
                                      {isSimulating ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />} 
                                      {isSimulating ? "Simulating..." : "Run 5000 Permutations"}
                                  </motion.button>
                                  
                                  {mcError && <p className="text-[10px] text-rose-500 font-bold">{mcError}</p>}
                                  
                                  {/* Result Chart */}
                                  {simulationStats && (
                                     <div className="bg-white dark:bg-slate-900 rounded-xl p-3 border border-slate-100 dark:border-slate-800">
                                         <div className="flex justify-between items-center mb-1">
                                             <span className="text-[10px] font-black text-slate-400 uppercase tracking-wide">Distribution (KDE)</span>
                                             <span className="text-[10px] font-mono text-emerald-600 font-bold border border-emerald-200 bg-emerald-50 px-1.5 py-0.5 rounded">
                                                μ = {simulationStats.mean.toFixed(2)}, σ = {simulationStats.stdDev.toFixed(2)}
                                             </span>
                                         </div>
                                         <div ref={chartRef} className="w-full h-32" />
                                         <div className="flex justify-between items-center mt-1 text-[9px] font-bold text-slate-400">
                                             <span>P5: {simulationStats.p5.toFixed(2)}</span>
                                             <span>90% CI</span>
                                             <span>P95: {simulationStats.p95.toFixed(2)}</span>
                                         </div>
                                     </div>
                                  )}
                              </div>
                           </motion.div>
                        )}
                    </AnimatePresence>
                  </motion.div>
                )}
              </div>
            </div>
            ) : activeTab === 'templates' ? (
              <div className="flex-1 overflow-hidden flex flex-col space-y-4 min-h-0">
                {/* Save Current Formula as Template banner if filled in */}
                {expression && name && (
                  <div className="p-4 bg-primary-50/50 dark:bg-primary-950/20 border border-slate-200 dark:border-slate-800 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4 shrink-0 transition-all">
                    <div className="space-y-1">
                      <h4 className="text-xs font-black text-primary-600 dark:text-primary-400 flex items-center gap-1.5 uppercase tracking-tight">
                        <Save size={13} /> Reusable Template Generator
                      </h4>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">
                        Save the currently configured formula <strong>"{name}"</strong> as a custom blueprint template to load and parameterize later.
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <input
                        value={customTemplateName}
                        onChange={(e) => setCustomTemplateName(e.target.value)}
                        placeholder="Template Name (e.g. My Formula)"
                        className="px-3 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-xs font-bold outline-none focus:ring-2 focus:ring-primary-500/20 w-48"
                      />
                      <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                        onClick={handleSaveAsTemplate}
                        className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-xl text-xs font-black shadow-md shadow-primary-500/10 transition-all flex items-center gap-1 active:scale-95"
                      >
                        <Plus size={12} /> Save Template
                      </motion.button>
                    </div>
                  </div>
                )}

                <div className="flex-1 grid grid-cols-1 lg:grid-cols-5 gap-6 overflow-hidden min-h-0">
                  {/* Left Column: Templates Library list */}
                  <div className="lg:col-span-3 flex flex-col space-y-4 overflow-y-auto custom-scrollbar pr-1 pb-4">
                    <div>
                      <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2 px-1">
                        Curated Synthetic Resin Blueprints
                      </h3>
                      <div className="space-y-3">
                        {BUILT_IN_TEMPLATES.map((tpl) => (
                          <div
                            key={tpl.id}
                            onClick={() => handleSelectTemplate(tpl)}
                            className={`p-4 rounded-2xl border text-left cursor-pointer transition-all ${
                              selectedTemplate?.id === tpl.id
                                ? "bg-primary-50/40 dark:bg-primary-950/20 border-primary-500 dark:border-primary-800 shadow-sm"
                                : "bg-white dark:bg-slate-950/40 border-slate-100 dark:border-slate-850 hover:bg-slate-50 dark:hover:bg-slate-900/60"
                            }`}
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div>
                                <span className="inline-block px-2 py-0.5 bg-slate-100 dark:bg-slate-850 rounded-md text-[9px] font-black text-slate-500 uppercase tracking-wide mb-1">
                                  {tpl.category}
                                </span>
                                <h4 className="text-sm font-bold text-slate-850 dark:text-white">
                                  {tpl.name}
                                </h4>
                              </div>
                              <span className="shrink-0 px-2.5 py-1 bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-100 dark:border-indigo-900/40 rounded-xl text-[10px] font-mono text-indigo-600 dark:text-indigo-400 font-bold">
                                {tpl.unit}
                              </span>
                            </div>
                            <p className="text-xs text-slate-500 dark:text-slate-400 mt-2 leading-relaxed">
                              {tpl.description}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>

                    {customTemplates.length > 0 && (
                      <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-800">
                        <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2 px-1">
                          My Custom Blueprint Templates
                        </h3>
                        <div className="space-y-3">
                          {customTemplates.map((tpl) => (
                            <div
                              key={tpl.id}
                              onClick={() => handleSelectTemplate(tpl)}
                              className={`p-4 rounded-2xl border text-left cursor-pointer relative group transition-all ${
                                selectedTemplate?.id === tpl.id
                                  ? "bg-primary-50/40 dark:bg-primary-950/20 border-primary-500 dark:border-primary-800 shadow-sm"
                                  : "bg-white dark:bg-slate-950/40 border-slate-100 dark:border-slate-850 hover:bg-slate-50 dark:hover:bg-slate-900/60"
                              }`}
                            >
                              <div className="flex items-start justify-between gap-4">
                                <div>
                                  <span className="inline-block px-2 py-0.5 bg-primary-50 dark:bg-primary-950/30 rounded-md text-[9px] font-black text-primary-600 dark:text-primary-400 uppercase tracking-wide mb-1">
                                    {tpl.category}
                                  </span>
                                  <h4 className="text-sm font-bold text-slate-850 dark:text-white pr-6">
                                    {tpl.name}
                                  </h4>
                                </div>
                                <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                                  onClick={(e) => handleRemoveCustomTemplate(tpl.id, e)}
                                  className="absolute right-3 top-3 p-1.5 text-slate-400 hover:text-rose-500 rounded-xl hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-all"
                                  title="Delete custom template"
                                >
                                  <Trash2 size={13} />
                                </motion.button>
                              </div>
                              <p className="text-xs text-slate-500 dark:text-slate-400 mt-2 leading-relaxed">
                                {tpl.description}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Right Column: Interactive parameter setup & formula compiler */}
                  <div className="lg:col-span-2 flex flex-col bg-slate-50/50 dark:bg-slate-900/10 border border-slate-100 dark:border-slate-850 rounded-3xl p-5 overflow-y-auto custom-scrollbar">
                    {selectedTemplate ? (
                      <div className="space-y-5 h-full flex flex-col justify-between">
                        <div className="space-y-2 shrink-0">
                          <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-widest">
                            Parameters Configuration
                          </h3>
                          <h4 className="text-sm font-black text-slate-800 dark:text-white leading-snug">
                            {selectedTemplate.name}
                          </h4>
                          <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                            {selectedTemplate.description}
                          </p>
                        </div>

                        {selectedTemplate.parameters.length > 0 ? (
                          <div className="space-y-4 my-4 overflow-y-auto pr-1 py-1 flex-1">
                            {selectedTemplate.parameters.map((p) => (
                              <div key={p.key} className="space-y-1.5 p-3.5 bg-white dark:bg-slate-950 rounded-2xl border border-slate-100 dark:border-slate-850 shadow-sm">
                                <div className="flex items-center justify-between">
                                  <label className="text-xs font-bold text-slate-700 dark:text-slate-300">
                                    {p.label}
                                  </label>
                                  {p.unit && (
                                    <span className="text-[10px] font-extrabold text-slate-400 uppercase bg-slate-100 dark:bg-slate-900 px-1.5 py-0.5 rounded">
                                      {p.unit}
                                    </span>
                                  )}
                                </div>
                                <p className="text-[10px] text-slate-400 leading-relaxed font-semibold">
                                  {p.description}
                                </p>
                                <input
                                  type={p.type}
                                  value={templateParamValues[p.key] !== undefined ? templateParamValues[p.key] : p.defaultValue}
                                  onChange={(e) =>
                                    setTemplateParamValues((prev) => ({
                                      ...prev,
                                      [p.key]: e.target.value
                                    }))
                                  }
                                  placeholder={p.placeholder}
                                  className="w-full mt-1.5 px-3 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-xs font-bold outline-none focus:ring-2 focus:ring-primary-500/20"
                                />
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="my-6 p-6 bg-slate-50 dark:bg-slate-900/50 rounded-2xl border border-dashed border-slate-200 dark:border-slate-850 text-center text-xs text-slate-400 font-bold italic flex-1 flex items-center justify-center">
                            This static template has no configurable arguments.
                          </div>
                        )}

                        <div className="space-y-3 pt-4 border-t border-slate-200 dark:border-slate-800 shrink-0">
                          <div>
                            <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest block mb-1">
                              Mathematical JavaScript Compilation
                            </span>
                            <div className="p-3.5 bg-slate-950 text-emerald-400 rounded-2xl font-mono text-xs overflow-x-auto border border-slate-850 shadow-inner max-h-32 select-all leading-relaxed whitespace-pre-wrap">
                              {getComputedTemplateExpression(selectedTemplate, templateParamValues)}
                            </div>
                          </div>

                          <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                            onClick={handleApplyTemplate}
                            className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-2xl text-xs font-black shadow-lg shadow-indigo-600/10 transition-all flex items-center justify-center gap-1.5 active:scale-95"
                          >
                            <Check size={14} /> Apply Template Parameters
                          </motion.button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex-1 flex flex-col items-center justify-center text-center p-6 space-y-3">
                        <div className="p-4 bg-slate-100 dark:bg-slate-900 rounded-3xl text-slate-400">
                          <BookOpen size={30} />
                        </div>
                        <div className="max-w-[200px]">
                          <h4 className="text-sm font-bold text-slate-800 dark:text-white">
                            No Blueprint Selected
                          </h4>
                          <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                            Select a polymer science formula from the left to configure parameters & compile code.
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ) : activeTab === 'heatmap' ? (
              <DependencyHeatmap
                expression={expression}
                name={name || "Custom Formula"}
                formulas={formulas}
                allProducts={allProducts}
              />
            ) : activeTab === 'suggestions' ? (
              <div className="flex-1 overflow-y-auto pr-1 flex flex-col space-y-6 custom-scrollbar pb-6">
                <div className="p-5 bg-indigo-50/50 dark:bg-indigo-900/10 border border-indigo-100 dark:border-indigo-800/40 rounded-3xl space-y-3">
                  <div className="flex items-center gap-2">
                    <Beaker className="text-indigo-600 dark:text-indigo-400" size={20} />
                    <h3 className="text-sm font-black text-indigo-950 dark:text-white uppercase tracking-tight">
                      Chemical Suggestion Engine (AI-Powered)
                    </h3>
                  </div>
                  <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed font-semibold">
                    ResinAI Principal Scientist runs microstructural simulations on molecular chain kinetics and crosslinks, cross-referencing indices from the live dataset to propose high-impact physical chemical modifiers and formulation replacements in order to maximize durability.
                  </p>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  {/* Left Column: Settings */}
                  <div className="space-y-4 lg:col-span-1">
                    <div className="space-y-2">
                      <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest px-1">
                        Durability target Dimension
                      </label>
                      <select
                        id="targetPropertySelect"
                        value={targetProperty}
                        onChange={(e) => setTargetProperty(e.target.value)}
                        className="w-full px-3 py-2.5 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-xs font-bold focus:ring-2 focus:ring-indigo-500/20 outline-none cursor-pointer"
                      >
                        <option value="Durability">General Material Durability & Wear Longevity</option>
                        <option value="Impact Strength">Izod Impact Strength & Fracture Energy Resistance (韧性提升)</option>
                        <option value="Environmental Stress cracking resistance">Environmental Stress Cracking Resistance (ESCR)</option>
                        <option value="Weatherability and Curing Stability">UV Aging Protection & Photo-Oxidative Stability</option>
                        <option value="Thermal Longevity and Glass Transition">High Temperature Curing & Tg Arrhenius Stability</option>
                      </select>
                    </div>

                    <div className="space-y-2">
                      <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest px-1">
                        Add Formulation Constraints
                      </label>
                      <textarea
                        id="customConstraintsText"
                        value={customConstraints}
                        onChange={(e) => setCustomConstraints(e.target.value)}
                        placeholder="e.g., Must keep raw material costs low, use non-halogenated filler, or restrict glass fiber density..."
                        rows={5}
                        className="w-full px-3 py-2.5 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-xs font-semibold focus:ring-2 focus:ring-indigo-500/20 outline-none resize-none"
                      />
                    </div>

                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      id="generateSuggestionsBtn"
                      onClick={handleGenerateSuggestions}
                      disabled={isGeneratingSuggestions || !expression}
                      className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-2xl text-xs font-black shadow-lg shadow-indigo-600/10 transition-all flex items-center justify-center gap-2 active:scale-95 cursor-pointer"
                    >
                      {isGeneratingSuggestions ? (
                        <>
                          <Loader2 size={14} className="animate-spin" />
                          <span>Executing AI Chemistry Model...</span>
                        </>
                      ) : (
                        <>
                          <Beaker size={14} />
                          <span>Generate Durability suggestions</span>
                        </>
                      )}
                    </motion.button>
                    {!expression && (
                      <p className="text-[10px] text-amber-600 dark:text-amber-400 font-semibold px-2 text-center leading-relaxed">
                        ⚠️ Please write or apply a formula in the Editor tab to load variables.
                      </p>
                    )}
                  </div>

                  {/* Right Column: Suggestions Result Output */}
                  <div className="lg:col-span-2 space-y-4">
                    {isGeneratingSuggestions ? (
                      <div className="bg-slate-50/50 dark:bg-slate-900/10 border border-slate-100 dark:border-slate-800 rounded-3xl p-8 flex flex-col items-center justify-center space-y-6 min-h-[320px] text-center border-dashed">
                        <div className="relative">
                          <div className="w-16 h-16 rounded-full border-4 border-indigo-100 dark:border-indigo-900/40 animate-pulse flex items-center justify-center">
                            <Beaker size={28} className="text-indigo-600 animate-bounce" />
                          </div>
                          <div className="absolute inset-0 w-16 h-16 rounded-full border-4 border-transparent border-t-indigo-600 animate-spin" />
                        </div>
                        <div className="max-w-sm space-y-2">
                          <h4 className="text-sm font-bold text-slate-800 dark:text-white animate-pulse">
                            ResinAI Scholar Engine Analyzing...
                          </h4>
                          <p className="text-xs text-slate-500 dark:text-slate-400 italic">
                            Constructing property-structure-performance correlation maps, cross-referencing polymeric ratios in ResinDB, and generating detailed stoichiometric recommendations...
                          </p>
                        </div>
                      </div>
                    ) : suggestionError ? (
                      <div className="p-5 bg-rose-50 dark:bg-rose-950/20 border border-rose-150 dark:border-rose-900/30 rounded-2xl flex items-start gap-3">
                        <AlertCircle className="text-rose-500 mt-0.5 shrink-0" size={16} />
                        <div>
                          <h4 className="text-xs font-black text-rose-700 dark:text-rose-400 uppercase tracking-tight">AI Service Error</h4>
                          <p className="text-xs text-rose-600 dark:text-rose-400 mt-1">{suggestionError}</p>
                        </div>
                      </div>
                    ) : suggestionsResponse ? (
                      <div className="space-y-5">
                        {/* Summary Overview */}
                        <div className="p-5 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm space-y-2">
                          <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-1.5 leading-none">
                            <Info size={12} className="text-indigo-500" /> Resin Durability Bottlenecks & Trends
                          </h4>
                          <p className="text-xs text-slate-600 dark:text-slate-350 leading-relaxed font-medium">
                            {suggestionsResponse.overview}
                          </p>
                        </div>

                        {/* Recommendation cards */}
                        <div className="space-y-4">
                          <h3 className="text-[10px] font-black text-indigo-500 uppercase tracking-widest px-1">
                            Actionable Replacement & formulation Suggestions
                          </h3>
                          {suggestionsResponse.suggestions?.map((item, idx) => (
                            <div
                              key={idx}
                              className="p-5 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-850 hover:border-slate-300 dark:hover:border-slate-755 rounded-2xl shadow-sm transition-all space-y-4 relative"
                            >
                              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                                <div className="space-y-1">
                                  <div className="flex flex-wrap items-center gap-2">
                                    <span className="text-[11px] font-mono font-black text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/30 border border-rose-100 dark:border-rose-900/30 px-2 py-0.5 rounded-md line-through">
                                      {item.chemicalName}
                                    </span>
                                    <span className="text-xs text-slate-400 font-bold">➔</span>
                                    <span className="text-[11px] font-mono font-black text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-100 dark:border-emerald-900/30 px-2 py-0.5 rounded-md">
                                      {item.replacement}
                                    </span>
                                  </div>
                                </div>
                                <div className="flex flex-col items-end shrink-0">
                                  <span className="text-[9px] font-black text-indigo-600 dark:text-indigo-400 uppercase bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-150 dark:border-indigo-900/40 px-2 py-0.5 rounded-md font-mono">
                                    Confidence: {item.confidenceScore}%
                                  </span>
                                  <div className="w-16 bg-slate-200 dark:bg-slate-850 h-1 rounded-full overflow-hidden mt-1">
                                    <div
                                      className="bg-indigo-500 h-full rounded-full"
                                      style={{ width: `${item.confidenceScore}%` }}
                                    />
                                  </div>
                                </div>
                              </div>

                              <div className="space-y-2">
                                <p className="text-xs font-black text-slate-850 dark:text-white flex items-center gap-1.5">
                                  <Activity size={12} className="text-indigo-500" />
                                  Mechanistic Durability Impact: <span className="font-normal text-slate-600 dark:text-slate-300">{item.impact}</span>
                                </p>
                                <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed pl-3.5 border-l-2 border-slate-200 dark:border-slate-800">
                                  {item.rationale}
                                </p>
                              </div>

                              {item.formulaUpdate && (
                                <div className="pt-3.5 border-t border-slate-100 dark:border-slate-850 space-y-2">
                                  <div className="flex items-center justify-between">
                                    <span className="text-[10px] font-black text-slate-450 uppercase tracking-wider block">
                                      Formula Representation Adjustments
                                    </span>
                                    <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                                      onClick={() => {
                                        setExpression(item.formulaUpdate!);
                                        setActiveTab('editor');
                                        setError(null);
                                      }}
                                      className="px-2.5 py-1.5 bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-950/20 dark:hover:bg-emerald-900/30 text-[10px] font-black text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-900/40 rounded-xl transition-all flex items-center gap-1 active:scale-95 shadow-sm cursor-pointer"
                                    >
                                      <Check size={11} />
                                      <span>Apply Update</span>
                                    </motion.button>
                                  </div>
                                  <pre className="p-3 bg-slate-950 text-emerald-450 rounded-xl font-mono text-[10px] overflow-x-auto border border-slate-850 leading-relaxed select-all">
                                    {item.formulaUpdate}
                                  </pre>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <div className="bg-slate-50/50 dark:bg-slate-900/10 border border-slate-150 dark:border-slate-850 rounded-3xl p-8 flex flex-col items-center justify-center space-y-3 min-h-[320px] text-center border-dashed">
                        <div className="p-4 bg-slate-100 dark:bg-slate-900 rounded-3xl text-indigo-500">
                          <Beaker size={28} />
                        </div>
                        <div className="max-w-xs space-y-1">
                          <h4 className="text-sm font-bold text-slate-800 dark:text-white">
                            Awaiting Trigger Parameters
                          </h4>
                          <p className="text-xs text-slate-400 leading-relaxed font-semibold">
                            Select a target physical property from the left panel and click "Generate Durability suggestions" to launch the AI-powered scientific suggestion engine.
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex-1 space-y-4 min-h-0 flex flex-col">
                {comparingHistory ? (
                  <div className="flex flex-col h-full space-y-4 overflow-hidden">
                    <div className="flex items-center gap-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-2 rounded-xl shrink-0">
                      <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} 
                        onClick={() => setComparingHistory(null)}
                        className="p-1.5 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-lg text-slate-500 transition-colors"
                      >
                        <ArrowLeft size={16} />
                      </motion.button>
                      <h3 className="text-sm font-bold text-slate-700 dark:text-slate-300 flex items-center gap-2">
                        <GitCompare size={16} className="text-primary-500" />
                        Comparing Versions
                      </h3>
                      <div className="ml-auto flex items-center gap-2">
                        <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                            onClick={() => {
                               setName(comparingHistory.name);
                               setExpression(comparingHistory.expression);
                               setUnit(comparingHistory.unit || "");
                               setDescription(comparingHistory.description || "");
                               setActiveTab('editor');
                               setComparingHistory(null);
                            }}
                            className="px-3 py-1.5 bg-primary-50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400 border border-primary-200 dark:border-primary-800 rounded-lg text-xs font-bold hover:bg-primary-100 dark:hover:bg-primary-900/40 transition-colors"
                        >
                          Revert to this version
                        </motion.button>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4 flex-1 overflow-y-auto custom-scrollbar pb-4">
                       {/* Left side: Historical */}
                       <div className="space-y-4 pr-1">
                          <h4 className="text-xs font-black text-rose-500 uppercase tracking-widest sticky top-0 bg-white dark:bg-slate-950 py-1 z-10 border-b border-rose-100 dark:border-slate-800">
                             Historical ({new Date(comparingHistory.date).toLocaleString()})
                          </h4>
                          
                          <div className="space-y-3">
                             <div>
                                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Name</label>
                                <div className="p-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-sm font-medium text-slate-700 dark:text-slate-300">
                                   {comparingHistory.name}
                                </div>
                             </div>
                             <div>
                                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Formula</label>
                                <div className="p-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-xs font-mono text-slate-700 dark:text-slate-300">
                                   {comparingHistory.expression}
                                </div>
                             </div>
                             <div>
                                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Unit</label>
                                <div className="p-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-sm font-medium text-slate-700 dark:text-slate-300 break-words">
                                   {comparingHistory.unit || <span className="italic text-slate-400">None</span>}
                                </div>
                             </div>
                             <div>
                                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Description</label>
                                <div className="p-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-sm font-medium text-slate-700 dark:text-slate-300 break-words">
                                   {comparingHistory.description || <span className="italic text-slate-400">None</span>}
                                </div>
                             </div>
                          </div>
                       </div>
                       
                       {/* Right side: Current with diff highlights */}
                       <div className="space-y-4 pl-1">
                          <h4 className="text-xs font-black text-emerald-500 uppercase tracking-widest sticky top-0 bg-white dark:bg-slate-950 py-1 z-10 border-b border-emerald-100 dark:border-slate-800">
                             Current Status
                          </h4>
                          
                          <div className="space-y-3">
                             <div>
                                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Name</label>
                                <div className="p-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-sm font-medium">
                                   <DiffViewer oldText={comparingHistory.name} newText={name} />
                                </div>
                             </div>
                             <div>
                                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Formula</label>
                                <div className="p-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-xs font-mono">
                                   <DiffViewer oldText={comparingHistory.expression} newText={expression} />
                                </div>
                             </div>
                             <div>
                                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Unit</label>
                                <div className="p-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-sm font-medium break-words">
                                   <DiffViewer oldText={comparingHistory.unit || ""} newText={unit || ""} />
                                   {!unit && !comparingHistory.unit && <span className="italic text-slate-400">None</span>}
                                </div>
                             </div>
                             <div>
                                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Description</label>
                                <div className="p-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-sm font-medium break-words">
                                   <DiffViewer oldText={comparingHistory.description || ""} newText={description || ""} />
                                   {!description && !comparingHistory.description && <span className="italic text-slate-400">None</span>}
                                </div>
                             </div>
                          </div>
                       </div>
                    </div>
                  </div>
                ) : !currentFormula?.history || currentFormula.history.length === 0 ? (
                  <div className="flex items-center justify-center h-full text-sm font-bold text-slate-400 italic">
                    No history found for this formula.
                  </div>
                ) : (
                  <div className="space-y-3 overflow-y-auto custom-scrollbar flex-1 pb-4">
                    {[...currentFormula.history].reverse().map((h, i) => (
                      <div key={i} className="p-4 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl space-y-2 group transition-all">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-slate-500">{new Date(h.date).toLocaleString()}</span>
                          <div className="flex items-center gap-2">
                              <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                                onClick={() => setComparingHistory(h)}
                                className="px-3 py-1.5 bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded-lg text-xs font-bold text-indigo-600 dark:text-indigo-400 hover:bg-indigo-100 dark:hover:bg-indigo-900/40 transition-colors flex items-center gap-1 opacity-0 group-hover:opacity-100"
                              >
                                <GitCompare size={12} /> Compare
                              </motion.button>
                              <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                                onClick={() => {
                                   setName(h.name);
                                   setExpression(h.expression);
                                   setUnit(h.unit || "");
                                   setDescription(h.description || "");
                                   setActiveTab('editor');
                                }}
                                className="px-3 py-1.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-xs font-bold text-primary-600 dark:text-primary-400 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                              >
                                Revert
                              </motion.button>
                          </div>
                        </div>
                        <div className="space-y-1">
                           <div className="text-sm font-bold text-slate-800 dark:text-slate-200">{h.name}</div>
                           <div className="p-3 bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl text-xs font-mono text-slate-600 dark:text-slate-400">
                             {h.expression}
                           </div>
                           {(h.description || h.unit) && (
                              <div className="text-[10px] text-slate-500 flex gap-4 mt-2">
                                {h.unit && <span><strong className="text-slate-600 dark:text-slate-300">Unit:</strong> {h.unit}</span>}
                                {h.description && <span><strong className="text-slate-600 dark:text-slate-300">Desc:</strong> {h.description}</span>}
                              </div>
                           )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 px-6 border-t border-slate-100 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between bg-slate-50/50 dark:bg-slate-900/50 gap-4">
          <p className="text-[10px] text-slate-400 font-bold italic flex items-center gap-1.5 text-center sm:text-left">
            <Info size={12} className="shrink-0" /> Computed columns are
            automatically added to the Data Grid and Analytics charts.
          </p>
          <div className="flex gap-3 w-full sm:w-auto">
            <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
              onClick={onClose}
              className="flex-1 sm:flex-none px-6 py-2.5 text-sm font-bold text-slate-500 hover:text-slate-800 transition-colors"
            >
              Cancel
            </motion.button>
            <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
              onClick={handleSave}
              disabled={!name || !expression}
              className="flex-1 sm:flex-none px-8 py-2.5 bg-primary-600 hover:bg-primary-700 disabled:opacity-50 text-white rounded-2xl text-sm font-black shadow-lg shadow-primary-500/20 transition-all active:scale-95"
            >
              Save Formula
            </motion.button>
          </div>
        </div>
      </motion.div>
    </div>
  );
});
