import React from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  FilterGroup,
  FilterCondition,
  FilterOperator,
  ColumnConfig,
} from '@/types/index';
import { Plus, Trash2, ChevronsDown } from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";
import { translations } from '@/config/i18n';

interface FilterBuilderProps {
  filterGroup: FilterGroup;
  onChange: (group: FilterGroup) => void;
  columns: ColumnConfig[];
}

const OPERATORS: { value: FilterOperator; label: string }[] = [
  { value: "contains", label: "包含" },
  { value: "equals", label: "等于" },
  { value: "startsWith", label: "开头是" },
  { value: "endsWith", label: "结尾是" },
  { value: "gt", label: "大于" },
  { value: "gte", label: "大于等于" },
  { value: "lt", label: "小于" },
  { value: "lte", label: "小于等于" },
  { value: "isEmpty", label: "为空" },
  { value: "isNotEmpty", label: "不为空" },
];

export const FilterBuilder: React.FC<FilterBuilderProps> = React.memo(({
  filterGroup,
  onChange,
  columns,
}) => {
  const { t, tProp } = useLanguage();

  const updateGroupLogic = (logic: "AND" | "OR") => {
    onChange({ ...filterGroup, logic });
  };

  const addCondition = () => {
    const newCondition: FilterCondition = {
      id: Math.random().toString(36).substr(2, 9),
      field: columns[0]?.key || "",
      operator: "contains",
      value: "",
    };
    onChange({
      ...filterGroup,
      conditions: [...filterGroup.conditions, newCondition],
    });
  };

  const addGroup = () => {
    const newGroup: FilterGroup = {
      id: Math.random().toString(36).substr(2, 9),
      type: "group",
      logic: "AND",
      conditions: [],
    };
    onChange({
      ...filterGroup,
      conditions: [...filterGroup.conditions, newGroup],
    });
  };

  const updateCondition = (id: string, updates: Partial<FilterCondition>) => {
    const newConditions = filterGroup.conditions.map((c) => {
      if ("type" in c) return c; // is group
      if (c.id === id) return { ...c, ...updates };
      return c;
    });
    onChange({ ...filterGroup, conditions: newConditions });
  };

  const updateSubGroup = (id: string, newGroup: FilterGroup) => {
    const newConditions = filterGroup.conditions.map((c) => {
      if ("type" in c && c.id === id) return newGroup;
      return c;
    });
    onChange({ ...filterGroup, conditions: newConditions });
  };

  const removeConditionOrGroup = (id: string) => {
    const newConditions = filterGroup.conditions.filter((c) => c.id !== id);
    onChange({ ...filterGroup, conditions: newConditions });
  };

  return (
    <div className="p-4 bg-white/40 dark:bg-slate-900/40 rounded-2xl border border-slate-200/60 dark:border-slate-800/60 space-y-4 shadow-sm backdrop-blur-md">
      <div className="flex items-center gap-2">
        <motion.div
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          className="relative"
        >
          <select
            value={filterGroup.logic}
            onChange={(e) => updateGroupLogic(e.target.value as "AND" | "OR")}
            className="bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-700/80 rounded-xl px-3 py-1.5 text-xs font-black text-slate-700 dark:text-slate-300 outline-none focus:ring-2 focus:ring-primary-500/50 shadow-sm transition-all hover:border-primary-500/50 appearance-none pr-8"
          >
            <option value="AND">{t("AND")}</option>
            <option value="OR">{t("OR")}</option>
          </select>
          <div className="absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400">
            <ChevronsDown size={10} />
          </div>
        </motion.div>
        <motion.button
          whileHover={{ scale: 1.05, y: -1 }}
          whileTap={{ scale: 0.95, y: 0 }}
          onClick={addCondition}
          className="text-[10px] font-black text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300 flex items-center gap-1.5 px-3 py-1.5 rounded-xl hover:bg-primary-50 dark:hover:bg-primary-900/30 transition-all border border-transparent hover:border-primary-100 dark:hover:border-primary-800/50 uppercase tracking-widest shadow-sm hover:shadow-md"
        >
          <Plus size={12} strokeWidth={2.5} /> {t("addCondition")}
        </motion.button>
        <motion.button
          whileHover={{ scale: 1.05, y: -1 }}
          whileTap={{ scale: 0.95, y: 0 }}
          onClick={addGroup}
          className="text-[10px] font-black text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300 flex items-center gap-1.5 px-3 py-1.5 rounded-xl hover:bg-indigo-50 dark:hover:bg-indigo-900/30 transition-all border border-transparent hover:border-indigo-100 dark:hover:border-indigo-800/50 uppercase tracking-widest shadow-sm hover:shadow-md"
        >
          <Plus size={12} strokeWidth={2.5} /> {t("addConditionGroup")}
        </motion.button>
      </div>

      <div className="space-y-3 pl-5 border-l-2 border-slate-200/80 dark:border-slate-800/80 ml-2.5 relative">
        <AnimatePresence mode="popLayout">
          {filterGroup.conditions.map((condition) => {
            if ("type" in condition) {
              return (
                <motion.div
                  key={condition.id}
                  initial={{ opacity: 0, x: -20, scale: 0.95 }}
                  animate={{ opacity: 1, x: 0, scale: 1 }}
                  exit={{ opacity: 0, x: 20, scale: 0.95 }}
                  className="relative mt-2"
                >
                  <motion.button
                    whileHover={{
                      scale: 1.1,
                      backgroundColor: "rgba(244, 63, 94, 0.1)",
                      color: "#f43f5e",
                    }}
                    whileTap={{ scale: 0.9 }}
                    onClick={() => removeConditionOrGroup(condition.id)}
                    className="absolute -left-9 top-5 p-1.5 rounded-lg text-slate-300 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-900/30 transition-all focus:outline-none focus-visible:ring-1 focus-visible:ring-rose-500 shadow-sm hover:shadow-md z-10"
                  >
                    <Trash2 size={12} />
                  </motion.button>
                  <FilterBuilder
                    filterGroup={condition}
                    onChange={(newGroup) =>
                      updateSubGroup(condition.id, newGroup)
                    }
                    columns={columns}
                  />
                </motion.div>
              );
            }

            return (
              <motion.div
                key={condition.id}
                initial={{ opacity: 0, x: -10, scale: 0.98 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                exit={{ opacity: 0, x: 10, scale: 0.98 }}
                className="flex items-center gap-2 relative group mt-1"
              >
                <motion.button
                  whileHover={{
                    scale: 1.1,
                    backgroundColor: "rgba(244, 63, 94, 0.1)",
                    color: "#f43f5e",
                  }}
                  whileTap={{ scale: 0.9 }}
                  onClick={() => removeConditionOrGroup(condition.id)}
                  className="absolute -left-9 p-1.5 rounded-lg text-slate-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-900/30 transition-all opacity-0 group-hover:opacity-100 focus:outline-none focus-visible:ring-1 focus-visible:ring-rose-500 shadow-sm hover:shadow-md z-10"
                >
                  <Trash2 size={12} />
                </motion.button>
                <div className="flex-1 flex items-center gap-2 p-1 rounded-2xl transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/40">
                  <select
                    value={condition.field}
                    onChange={(e) =>
                      updateCondition(condition.id, { field: e.target.value })
                    }
                    className="w-40 bg-white dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-700/80 rounded-xl px-3 py-1.5 text-xs font-mono text-slate-700 dark:text-slate-300 outline-none focus:ring-2 focus:ring-primary-500/50 truncate shrink-0 shadow-sm transition-shadow hover:border-slate-300 dark:hover:border-slate-600"
                  >
                    <option value="" disabled>
                      {t("searchField")}
                    </option>
                    {columns.map((col) => (
                      <option key={col.key} value={col.key}>
                        {tProp(col.label)}
                      </option>
                    ))}
                  </select>
                  <select
                    value={condition.operator}
                    onChange={(e) =>
                      updateCondition(condition.id, {
                        operator: e.target.value as FilterOperator,
                      })
                    }
                    className="bg-white dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-700/80 rounded-xl px-3 py-1.5 text-[11px] font-black uppercase tracking-wider text-slate-600 dark:text-slate-400 outline-none focus:ring-2 focus:ring-primary-500/50 w-32 shadow-sm transition-shadow hover:border-slate-300 dark:hover:border-slate-600"
                  >
                    {OPERATORS.map((op) => (
                      <option key={op.value} value={op.value}>
                        {t(`op_${op.value}` as keyof typeof translations.zh)}
                      </option>
                    ))}
                  </select>
                  {!["isEmpty", "isNotEmpty"].includes(condition.operator) && (
                    <motion.input
                      type="text"
                      whileFocus={{
                        scale: 1.01,
                        boxShadow: "0 0 0 4px rgba(79, 70, 229, 0.1)",
                      }}
                      value={
                        condition.value !== undefined &&
                        condition.value !== null
                          ? String(condition.value)
                          : ""
                      }
                      onChange={(e) =>
                        updateCondition(condition.id, { value: e.target.value })
                      }
                      placeholder={t("enterValue")}
                      className="bg-white dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-700/80 rounded-xl px-3 py-1.5 text-xs font-mono text-slate-800 dark:text-slate-200 outline-none focus:border-primary-500 flex-1 min-w-0 placeholder:text-slate-400 placeholder:font-sans shadow-sm transition-shadow hover:border-slate-300 dark:hover:border-slate-600"
                    />
                  )}
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
        {filterGroup.conditions.length === 0 && (
          <motion.div
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col items-center justify-center py-6 border-2 border-dashed border-slate-100 dark:border-slate-800 rounded-2xl bg-slate-50/30 dark:bg-slate-900/10"
          >
            <div className="p-2 bg-white dark:bg-slate-900 rounded-full shadow-sm mb-2 opacity-50">
              <Plus size={16} className="text-slate-300" />
            </div>
            <div className="text-[10px] font-mono text-slate-400 uppercase tracking-[0.2em]">
              {t("noConditions")}
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
});
