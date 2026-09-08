
import { useState, useEffect, useCallback, useMemo } from 'react';
import { FormulaConfig } from '@/types/index';
import { safeStorage } from '@/lib/utils';

export function useFormulas() {
  const [formulas, setFormulas] = useState<FormulaConfig[]>(() => {
    const saved = safeStorage.local.getItem('resindb-formulas');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (parsed && parsed.length > 0) return parsed;
      } catch {
        // Ignored
      }
    }
    
    // Default professional polymer science formulas
    return [
      {
        id: "f_default_spec_strength",
        name: "Specific Strength (比强度)",
        expression: "(props['拉伸屈服应力'] || props['Tensile Strength'] || 0) / (props['密度'] || props['Density'] || 1)",
        unit: "MPa·cm³/g",
        description: "Materials strength to weight ratio (Tensile / Density). Higher is better for lightweight structural parts."
      },
      {
        id: "f_default_spec_modulus",
        name: "Specific Modulus (比模量)",
        expression: "(props['弯曲模量'] || props['Flexural Modulus'] || 0) / (props['密度'] || props['Density'] || 1)",
        unit: "MPa·cm³/g",
        description: "Stiffness to weight ratio (Flexural Modulus / Density). Critical for metal replacement."
      },
      {
        id: "f_default_toughness_index",
        name: "Toughness Balance Index (刚韧平衡指数)",
        expression: "((props['简支梁缺口冲击强度'] || props['Izod Impact'] || 0) * (props['弯曲模量'] || props['Flexural Modulus'] || 0)) / 10000",
        unit: "Index",
        description: "Empirical index evaluating the balance between impact resistance and structural stiffness."
      }
    ];
  });

  useEffect(() => {
    safeStorage.local.setItem('resindb-formulas', JSON.stringify(formulas));
  }, [formulas]);

  const addFormula = useCallback((formula: Omit<FormulaConfig, 'id'>) => {
    const newFormula: FormulaConfig = {
      ...formula,
      id: `f_${Date.now()}`
    };
    setFormulas(prev => [...prev, newFormula]);
    return newFormula;
  }, []);

  const updateFormula = useCallback((id: string, updates: Partial<FormulaConfig>) => {
    setFormulas(prev => prev.map(f => f.id === id ? { ...f, ...updates } : f));
  }, []);

  const removeFormula = useCallback((id: string) => {
    setFormulas(prev => prev.filter(f => f.id !== id));
  }, []);

  return useMemo(() => ({
    formulas,
    addFormula,
    updateFormula,
    removeFormula
  }), [formulas, addFormula, updateFormula, removeFormula]);
}
