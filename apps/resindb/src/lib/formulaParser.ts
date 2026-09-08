import type { FormulaConfig, Product } from '@/types/index';
import {
  compileFormulaExpression,
  type Evaluator,
  type PropertyDictionary,
} from '@/lib/formula/expressionParser';

export type FormulaResult =
  | { status: 'OK'; value: number; unit: string; dependencies: string[] }
  | { status: 'UNKNOWN' | 'INVALID'; value: null; reason: string; dependencies: string[] };

export type FormulaResultMap = Record<string, FormulaResult>;
export type PropertyGraphExecutor = (
  properties: PropertyDictionary,
  results?: Record<string, number>,
) => Record<string, number>;
export type PropertyResultGraphExecutor = (
  properties: PropertyDictionary,
  results?: FormulaResultMap,
) => FormulaResultMap;

interface CompiledStep {
  id: string;
  name: string;
  unit: string;
  dependencies: string[];
  evaluator?: Evaluator;
  compileError?: string;
}

interface CompiledFormulaPlan {
  formulasRef: FormulaConfig[];
  productExecutor: (product: Product) => Record<string, number>;
  propertyExecutor: PropertyGraphExecutor;
  productResultExecutor: (product: Product) => FormulaResultMap;
  propertyResultExecutor: PropertyResultGraphExecutor;
}

function finiteNumeric(value: unknown): number | null {
  if (typeof value === 'boolean' || value === null || value === undefined) return null;
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  if (typeof value !== 'string' || value.trim() === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

export class FormulaEngine {
  private static readonly MATH_FUNCTIONS = [
    'abs', 'sqrt', 'pow', 'log', 'log10', 'exp', 'sin', 'cos', 'tan', 'min', 'max',
  ];

  private cachedPlan: CompiledFormulaPlan | null = null;

  public extractDependencies(expression: string): string[] {
    const dependencies = new Set<string>();
    const regex = /(?:props|p)\[['"](.+?)['"]\]/gi;
    let match: RegExpExecArray | null;
    while ((match = regex.exec(expression)) !== null) {
      if (match[1]) dependencies.add(match[1]);
    }
    return [...dependencies].sort();
  }

  /** Preview only. Missing properties are not rewritten to physical zero. */
  public sanitize(expression: string): string {
    let sanitized = expression.replace(
      /(?:props|p)\[['"](.+?)['"]\]/gi,
      (_, propertyName: string) => `p['${propertyName.replace(/'/g, "\\'")}']`,
    );
    for (const functionName of FormulaEngine.MATH_FUNCTIONS) {
      sanitized = sanitized.replace(
        new RegExp(`(^|[^.\\w])${functionName}\\(`, 'g'),
        `$1Math.${functionName}(`,
      );
    }
    return sanitized.replace(/(^|[^.\w])PI\b/g, '$1Math.PI');
  }

  public buildTopologicalOrder(formulas: FormulaConfig[]): FormulaConfig[] {
    const graph = new Map<string, string[]>();
    const formulaNames = new Set<string>();
    const formulaMap = new Map<string, FormulaConfig>();
    const ids = new Set<string>();
    for (const formula of formulas) {
      if (!formula.id?.trim() || ids.has(formula.id)) throw new Error(`Duplicate or empty formula id: ${formula.id}`);
      if (!formula.name?.trim() || formulaNames.has(formula.name)) throw new Error(`Duplicate or empty formula name: ${formula.name}`);
      ids.add(formula.id);
      formulaNames.add(formula.name);
      formulaMap.set(formula.name, formula);
    }
    for (const formula of formulas) {
      graph.set(
        formula.name,
        this.extractDependencies(formula.expression).filter((dependency) => formulaNames.has(dependency)),
      );
    }
    const visited = new Set<string>();
    const visiting = new Set<string>();
    const order: FormulaConfig[] = [];
    const visit = (node: string, path: string[]): void => {
      if (visiting.has(node)) throw new Error(`Cyclic dependency detected: ${[...path, node].join(' -> ')}`);
      if (visited.has(node)) return;
      visiting.add(node);
      for (const dependency of graph.get(node) ?? []) visit(dependency, [...path, node]);
      visiting.delete(node);
      visited.add(node);
      const formula = formulaMap.get(node);
      if (formula) order.push(formula);
    };
    for (const node of graph.keys()) visit(node, []);
    return order;
  }

  public validate(expression: string, currentName?: string, allFormulas: FormulaConfig[] = []): string | null {
    if (!expression.trim()) return 'Expression cannot be empty';
    const forbiddenKeywords = [
      'window', 'document', 'globalThis', 'fetch', 'XMLHttpRequest', 'eval', 'Function',
      'setTimeout', 'setInterval', 'alert', 'cookie', 'localStorage', 'sessionStorage',
      'indexedDB', 'constructor', '__proto__', 'prototype',
    ];
    for (const keyword of forbiddenKeywords) {
      if (new RegExp(`\\b${keyword}\\b`, 'i').test(expression)) {
        return `Security violation: Forbidden keyword "${keyword}" detected`;
      }
    }
    try {
      compileFormulaExpression(expression);
    } catch (error) {
      return errorMessage(error);
    }
    if (currentName) {
      try {
        this.buildTopologicalOrder([
          ...allFormulas.filter((formula) => formula.name !== currentName),
          { id: 'formula-validation-candidate', name: currentName, expression, unit: 'UNSPECIFIED' },
        ]);
      } catch (error) {
        return errorMessage(error);
      }
    }
    return null;
  }

  public createPropertyDictionary(product: Pick<Product, 'properties'>): PropertyDictionary {
    const properties: PropertyDictionary = {};
    for (const [key, property] of Object.entries(product.properties)) {
      const governed = property.quantity;
      const numericValue = governed?.status === 'VALID' && governed.canonical
        ? governed.canonical.value
        : finiteNumeric(property.value);
      if (numericValue !== null) properties[key] = numericValue;
    }
    return properties;
  }

  private areFormulasEqual(left: FormulaConfig[], right: FormulaConfig[]): boolean {
    return left.length === right.length && left.every((formula, index) => (
      formula.id === right[index].id
      && formula.name === right[index].name
      && formula.expression === right[index].expression
      && formula.unit === right[index].unit
    ));
  }

  private invalidPlan(formulas: FormulaConfig[], reason: string): CompiledFormulaPlan {
    const propertyResultExecutor: PropertyResultGraphExecutor = (_, results = {}) => {
      for (const formula of formulas) {
        results[formula.id] = {
          status: 'INVALID', value: null, reason, dependencies: this.extractDependencies(formula.expression),
        };
      }
      return results;
    };
    const productResultExecutor = (product: Product) => propertyResultExecutor(this.createPropertyDictionary(product));
    const propertyExecutor: PropertyGraphExecutor = (properties, results = {}) => {
      propertyResultExecutor(properties);
      return results;
    };
    const productExecutor = (product: Product) => propertyExecutor(this.createPropertyDictionary(product));
    return { formulasRef: formulas, productExecutor, propertyExecutor, productResultExecutor, propertyResultExecutor };
  }

  private compilePlan(formulas: FormulaConfig[]): CompiledFormulaPlan {
    if (this.cachedPlan && (this.cachedPlan.formulasRef === formulas || this.areFormulasEqual(this.cachedPlan.formulasRef, formulas))) {
      return this.cachedPlan;
    }
    let ordered: FormulaConfig[];
    try {
      ordered = this.buildTopologicalOrder(formulas);
    } catch (error) {
      this.cachedPlan = this.invalidPlan(formulas, errorMessage(error));
      return this.cachedPlan;
    }

    const steps: CompiledStep[] = ordered.map((formula) => {
      const dependencies = this.extractDependencies(formula.expression);
      const unit = formula.unit === undefined ? '' : formula.unit.trim() || 'UNSPECIFIED';
      try {
        return { id: formula.id, name: formula.name, unit, dependencies, evaluator: compileFormulaExpression(formula.expression) };
      } catch (error) {
        return { id: formula.id, name: formula.name, unit, dependencies, compileError: errorMessage(error) };
      }
    });

    const propertyResultExecutor: PropertyResultGraphExecutor = (input, results = {}) => {
      const properties: PropertyDictionary = { ...input };
      for (const step of steps) {
        if (!step.unit) {
          results[step.id] = {
            status: 'INVALID', value: null, reason: 'MISSING_OUTPUT_UNIT', dependencies: step.dependencies,
          };
          continue;
        }
        if (step.compileError || !step.evaluator) {
          results[step.id] = {
            status: 'INVALID', value: null, reason: `PARSE_ERROR:${step.compileError ?? 'unknown'}`, dependencies: step.dependencies,
          };
          continue;
        }
        const missing = step.dependencies.filter((dependency) => !Number.isFinite(properties[dependency]));
        if (missing.length > 0) {
          results[step.id] = {
            status: 'UNKNOWN', value: null, reason: `MISSING_DEPENDENCY:${missing.join(',')}`, dependencies: step.dependencies,
          };
          continue;
        }
        try {
          const calculated = step.evaluator(properties);
          if (!Number.isFinite(calculated)) {
            results[step.id] = {
              status: 'INVALID', value: null, reason: 'NONFINITE_OR_DOMAIN_ERROR', dependencies: step.dependencies,
            };
            continue;
          }
          properties[step.name] = calculated;
          results[step.id] = {
            status: 'OK', value: calculated, unit: step.unit, dependencies: step.dependencies,
          };
        } catch (error) {
          results[step.id] = {
            status: 'INVALID', value: null, reason: `EVALUATION_ERROR:${errorMessage(error)}`, dependencies: step.dependencies,
          };
        }
      }
      return results;
    };

    const productResultExecutor = (product: Product) => propertyResultExecutor(this.createPropertyDictionary(product));
    const propertyExecutor: PropertyGraphExecutor = (properties, results = {}) => {
      const detailed = propertyResultExecutor(properties);
      for (const [id, result] of Object.entries(detailed)) {
        if (result.status === 'OK') results[id] = result.value;
      }
      return results;
    };
    const productExecutor = (product: Product) => propertyExecutor(this.createPropertyDictionary(product));
    this.cachedPlan = { formulasRef: formulas, productExecutor, propertyExecutor, productResultExecutor, propertyResultExecutor };
    return this.cachedPlan;
  }

  public compileGraph(formulas: FormulaConfig[]): (product: Product) => Record<string, number> {
    return this.compilePlan(formulas).productExecutor;
  }

  public compilePropertyGraph(formulas: FormulaConfig[]): PropertyGraphExecutor {
    return this.compilePlan(formulas).propertyExecutor;
  }

  public compileResultGraph(formulas: FormulaConfig[]): (product: Product) => FormulaResultMap {
    return this.compilePlan(formulas).productResultExecutor;
  }

  public compilePropertyResultGraph(formulas: FormulaConfig[]): PropertyResultGraphExecutor {
    return this.compilePlan(formulas).propertyResultExecutor;
  }

  public clearCache(): void {
    this.cachedPlan = null;
  }
}

export const formulaEngine = new FormulaEngine();
