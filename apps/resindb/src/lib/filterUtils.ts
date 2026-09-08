import { Product, FilterGroup, FilterCondition } from '@/types/index';

export type ProductPredicate = (product: Product) => boolean;

export function compileFilterGroup(
  group: FilterGroup | null,
): ProductPredicate {
  if (!group || !group.conditions || group.conditions.length === 0) {
    return () => true;
  }

  const isAnd = group.logic === "AND";
  const predicates: ProductPredicate[] = group.conditions.map((condition) => {
    if ("type" in condition && condition.type === "group") {
      return compileFilterGroup(condition);
    }
    return compileCondition(condition as FilterCondition);
  });

  return (product: Product) => {
    for (let i = 0; i < predicates.length; i++) {
      const result = predicates[i](product);
      if (isAnd) {
        if (!result) return false;
      } else {
        if (result) return true;
      }
    }
    return isAnd;
  };
}

function compileCondition(condition: FilterCondition): ProductPredicate {
  const { field, operator, value } = condition;
  const condVal = String(value ?? "").toLowerCase();
  const condNum = parseFloat(condVal);

  return (product: Product) => {
    let val: string | number | undefined;
    
    // Support top-level fields explicitly
    if (field === "gradeName") val = product.gradeName;
    else if (field === "manufacturer") val = product.manufacturer;
    else if (field === "id") val = product.id;
    else if (field === "manufacturerId") val = product.manufacturerId;
    else if (product.properties) {
      val = product.properties[field]?.value;
    }

    const strVal = String(val ?? "").toLowerCase();
    const numVal = typeof val === "number" ? val : parseFloat(strVal);

    switch (operator) {
      case "contains":
        return strVal.includes(condVal);
      case "equals":
        return strVal === condVal;
      case "startsWith":
        return strVal.startsWith(condVal);
      case "endsWith":
        return strVal.endsWith(condVal);
      case "gt":
        return !isNaN(numVal) && !isNaN(condNum) && numVal > condNum;
      case "gte":
        return !isNaN(numVal) && !isNaN(condNum) && numVal >= condNum;
      case "lt":
        return !isNaN(numVal) && !isNaN(condNum) && numVal < condNum;
      case "lte":
        return !isNaN(numVal) && !isNaN(condNum) && numVal <= condNum;
      case "isEmpty":
        return val === undefined || val === null || strVal === "";
      case "isNotEmpty":
        return val !== undefined && val !== null && strVal !== "";
      default:
        return true;
    }
  };
}

// Keep old version for compatibility if needed, but internally uses compile
export function evaluateFilterGroup(
  product: Product,
  group: FilterGroup | null,
): boolean {
  const predicate = compileFilterGroup(group);
  return predicate(product);
}
