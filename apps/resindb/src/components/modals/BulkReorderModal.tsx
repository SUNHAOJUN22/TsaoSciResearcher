import React, { useState, useEffect } from "react";
import {
  X,
  GripVertical,
  Save,
  ChevronUp,
  ChevronDown,
  ChevronsUp,
  ChevronsDown,
  RefreshCw,
  Sparkles,
  ArrowUpDown,
  Sliders,
  Info,
} from "lucide-react";
import { Product } from "@/types/index";
import { useLanguage } from "@/contexts/LanguageContext";
import { motion, AnimatePresence, Reorder } from "motion/react";

interface BulkReorderModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (updates: { id: string; priority: number }[]) => void;
  selectedProducts: Product[];
}

export const BulkReorderModal: React.FC<BulkReorderModalProps> = ({
  isOpen,
  onClose,
  onSave,
  selectedProducts,
}) => {
  const { t, language } = useLanguage();
  const isZh = language === "zh";

  // Local state for sorted products list
  const [items, setItems] = useState<Product[]>([]);

  // Initialize/reset list when modal opens
  useEffect(() => {
    if (isOpen) {
      // Sort initially by existing priority if available, otherwise preserve their present order
      const sorted = [...selectedProducts].sort((a, b) => {
        const pA = a.priority !== undefined ? a.priority : 1000000;
        const pB = b.priority !== undefined ? b.priority : 1000000;
        return pA - pB;
      });
      setItems(sorted);
    }
  }, [isOpen, selectedProducts]);

  const handleSave = () => {
    // Generate sequential priority values starting from 1
    const updates = items.map((item, idx) => ({
      id: item.id,
      priority: idx + 1, // Store natural ranks
    }));
    onSave(updates);
    onClose();
  };

  // Helper actions to rearrange items programmatically
  const moveItem = (index: number, direction: "up" | "down" | "top" | "bottom") => {
    if (index < 0 || index >= items.length) return;
    const nextList = [...items];
    const targetItem = nextList[index];

    if (direction === "top") {
      nextList.splice(index, 1);
      nextList.unshift(targetItem);
    } else if (direction === "bottom") {
      nextList.splice(index, 1);
      nextList.push(targetItem);
    } else if (direction === "up" && index > 0) {
      nextList[index] = nextList[index - 1];
      nextList[index - 1] = targetItem;
    } else if (direction === "down" && index < items.length - 1) {
      nextList[index] = nextList[index + 1];
      nextList[index + 1] = targetItem;
    }
    setItems(nextList);
  };

  // Instant pre-sorting options
  const handlePresetSort = (key: "gradeName" | "manufacturer" | "completeness" | "density" | "tensile") => {
    const nextList = [...items];
    nextList.sort((a, b) => {
      let aVal: string | number;
      let bVal: string | number;

      if (key === "gradeName") {
        aVal = a.gradeName;
        bVal = b.gradeName;
      } else if (key === "manufacturer") {
        aVal = a.manufacturer;
        bVal = b.manufacturer;
      } else if (key === "completeness") {
        // Simple completeness metric helper (count property keys)
        aVal = Object.keys(a.properties || {}).length;
        bVal = Object.keys(b.properties || {}).length;
        return bVal - aVal; // Higher completeness comes first
      } else {
        // Numeric properties like density, tensile
        const propKey = key === "density" ? "Density" : "Tensile Strength";
        aVal = parseFloat(String(a.properties[propKey]?.value || "0"));
        bVal = parseFloat(String(b.properties[propKey]?.value || "0"));
        return bVal - aVal; // descending
      }

      const sA = String(aVal).toLowerCase();
      const sB = String(bVal).toLowerCase();
      if (sA < sB) return -1;
      if (sA > sB) return 1;
      return 0;
    });
    setItems(nextList);
  };

  const handleReverseOrder = () => {
    setItems([...items].reverse());
  };

  return (
    <AnimatePresence>
      {isOpen && selectedProducts.length > 0 && (
        <motion.div
          key="bulk-reorder-modal"
          className="fixed inset-0 z-[110] flex items-center justify-center p-4 md:p-6"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          {/* Backdrop blur */}
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={onClose}
          ></div>

          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: "spring", duration: 0.45, bounce: 0 }}
            className="relative w-full max-w-4xl bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 flex flex-col h-[85vh] rounded-2xl md:rounded-[2rem] overflow-hidden shadow-[0_24px_60px_-15px_rgba(0,0,0,0.3)]"
          >
            {/* Header */}
            <div className="px-6 py-5 border-b border-slate-100 dark:border-slate-800/80 flex items-center justify-between bg-slate-50/50 dark:bg-slate-900/30 shrink-0">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-violet-50 dark:bg-violet-950/40 text-violet-600 dark:text-violet-400 rounded-xl border border-violet-100 dark:border-violet-900/30">
                  <Sliders size={20} />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-slate-800 dark:text-white tracking-tight mb-0.5">
                    {isZh ? "高级排号优先级重排" : "Product Grid Reordering & Prioritization"}
                  </h3>
                  <p className="text-[10px] text-slate-400 font-medium">
                    {isZh
                      ? `通过拖拽或方向按键重组 ${selectedProducts.length} 个物料的展示物理顺序`
                      : `Drag-and-drop or use quick keys to restructure ${selectedProducts.length} materials`}
                  </p>
                </div>
              </div>
              <motion.button
                whileHover={{ scale: 1.1, backgroundColor: "rgba(239, 68, 68, 0.1)" }}
                whileTap={{ scale: 0.9 }}
                onClick={onClose}
                className="p-1.5 text-slate-400 hover:text-rose-500 rounded-xl transition-all"
              >
                <X size={16} />
              </motion.button>
            </div>

            {/* Split Content layout */}
            <div className="flex-1 flex flex-col md:flex-row min-h-0 overflow-hidden">
              
              {/* Lefter core: Draggable Area */}
              <div className="flex-1 flex flex-col p-6 min-h-0 bg-slate-50/40 dark:bg-slate-950/10">
                <div className="flex items-center justify-between mb-3 shrink-0">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                    {isZh ? "手动排序控制台 (可随意上下拖拽整行)" : "Interactive Row Reordering List (Drag rows vertically)"}
                  </span>
                  <span className="text-[10px] bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400 px-2 py-0.5 rounded font-mono font-bold border border-indigo-100/30">
                    {items.length} {isZh ? "款产品" : "items"}
                  </span>
                </div>

                <div className="flex-1 overflow-y-auto pr-1">
                  <Reorder.Group
                    axis="y"
                    values={items}
                    onReorder={setItems}
                    className="space-y-2 select-none"
                  >
                    {items.map((item, index) => (
                      <Reorder.Item
                        key={item.id}
                        value={item}
                        className="flex items-center gap-3 p-3 bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800/80 rounded-xl hover:shadow-md dark:shadow-none hover:border-slate-300 dark:hover:border-slate-700 transition-all cursor-grab active:cursor-grabbing group"
                        whileDrag={{ scale: 1.01, boxShadow: "0 10px 25px -5px rgba(0,0,0,0.1)" }}
                      >
                        {/* Drag Handle */}
                        <div className="text-slate-400 group-hover:text-violet-500 transition-colors pointer-events-none p-1 shrink-0">
                          <GripVertical size={16} />
                        </div>

                        {/* Order Priority Position index badge */}
                        <div className="flex items-center justify-center w-6 h-6 rounded-lg bg-slate-100 dark:bg-slate-800 text-xs font-mono font-bold text-slate-600 dark:text-slate-400 shrink-0">
                          {index + 1}
                        </div>

                        {/* Material specifications */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-0.5">
                            <span className="font-bold text-xs text-slate-800 dark:text-white truncate">
                              {item.gradeName}
                            </span>
                            {item.isExperimental && (
                              <span className="text-[8px] bg-amber-100 text-amber-800 dark:bg-amber-950/40 dark:text-amber-400 border border-amber-200/50 px-1 py-0.2 rounded font-extrabold uppercase font-sans">
                                EXPR
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-2 text-[10px] text-slate-400 font-mono leading-none">
                            <span className="font-semibold text-slate-500 dark:text-slate-400">
                              {item.manufacturer}
                            </span>
                            {item.createdAt && (
                              <>
                                <span className="opacity-40">•</span>
                                <span>{item.createdAt}</span>
                              </>
                            )}
                          </div>
                        </div>

                        {/* Relative property quick indicator chips */}
                        <div className="hidden lg:flex items-center gap-2 px-3">
                          {item.properties["Density"] && (
                            <div className="flex flex-col text-right">
                              <span className="text-[9px] text-slate-400 uppercase tracking-wide">Density</span>
                              <span className="text-xs font-mono font-bold text-slate-600 dark:text-slate-300">{item.properties["Density"].value}</span>
                            </div>
                          )}
                          {item.properties["Tensile Strength"] && (
                            <div className="flex flex-col text-right border-l border-slate-100 dark:border-slate-800 pl-2">
                              <span className="text-[9px] text-slate-400 uppercase tracking-wide">Tensile</span>
                              <span className="text-xs font-mono font-bold text-slate-600 dark:text-slate-300">{item.properties["Tensile Strength"].value}</span>
                            </div>
                          )}
                        </div>

                        {/* Micro action buttons */}
                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity pl-2 shrink-0">
                          <motion.button
                            whileHover={{ scale: 1.15, color: '#4f46e5' }}
                            whileTap={{ scale: 0.85 }}
                            type="button"
                            title={isZh ? "置顶" : "Move to Top"}
                            disabled={index === 0}
                            onClick={(e) => {
                              e.stopPropagation();
                              moveItem(index, "top");
                            }}
                            className="p-1 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded disabled:opacity-30 disabled:hover:bg-transparent cursor-pointer disabled:cursor-not-allowed"
                          >
                            <ChevronsUp size={14} />
                          </motion.button>
                          <motion.button
                            whileHover={{ scale: 1.15, color: '#4f46e5' }}
                            whileTap={{ scale: 0.85 }}
                            type="button"
                            title={isZh ? "上移" : "Move Up"}
                            disabled={index === 0}
                            onClick={(e) => {
                              e.stopPropagation();
                              moveItem(index, "up");
                            }}
                            className="p-1 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded disabled:opacity-30 disabled:hover:bg-transparent cursor-pointer disabled:cursor-not-allowed"
                          >
                            <ChevronUp size={14} />
                          </motion.button>
                          <motion.button
                            whileHover={{ scale: 1.15, color: '#4f46e5' }}
                            whileTap={{ scale: 0.85 }}
                            type="button"
                            title={isZh ? "下移" : "Move Down"}
                            disabled={index === items.length - 1}
                            onClick={(e) => {
                              e.stopPropagation();
                              moveItem(index, "down");
                            }}
                            className="p-1 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded disabled:opacity-30 disabled:hover:bg-transparent cursor-pointer disabled:cursor-not-allowed"
                          >
                            <ChevronDown size={14} />
                          </motion.button>
                          <motion.button
                            whileHover={{ scale: 1.15, color: '#4f46e5' }}
                            whileTap={{ scale: 0.85 }}
                            type="button"
                            title={isZh ? "置底" : "Move to Bottom"}
                            disabled={index === items.length - 1}
                            onClick={(e) => {
                              e.stopPropagation();
                              moveItem(index, "bottom");
                            }}
                            className="p-1 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded disabled:opacity-30 disabled:hover:bg-transparent cursor-pointer disabled:cursor-not-allowed"
                          >
                            <ChevronsDown size={14} />
                          </motion.button>
                        </div>
                      </Reorder.Item>
                    ))}
                  </Reorder.Group>
                </div>
              </div>

              {/* Righter Toolbar: Actions and presets */}
              <div className="w-full md:w-80 border-t md:border-t-0 md:border-l border-slate-200/80 dark:border-slate-800/80 p-6 flex flex-col gap-5 shrink-0 bg-slate-50/20 dark:bg-slate-900/10">
                <div className="space-y-4">
                  <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1">
                    <Sparkles size={12} className="text-violet-500" />
                    {isZh ? "预设一键重构" : "Automated Sorting Presets"}
                  </h4>
                  
                  <div className="space-y-2">
                    <motion.button
                      whileHover={{ scale: 1.01 }}
                      whileTap={{ scale: 0.99 }}
                      type="button"
                      onClick={() => handlePresetSort("gradeName")}
                      className="w-full text-left px-3.5 py-2.5 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800/60 border border-slate-200 dark:border-slate-800 rounded-xl text-xs font-semibold text-slate-700 dark:text-slate-300 transition-all flex items-center justify-between cursor-pointer"
                    >
                      <span>{isZh ? "按牌号名称 A-Z" : "By Grade Name A-Z"}</span>
                      <ArrowUpDown size={12} className="text-slate-400" />
                    </motion.button>

                    <motion.button
                      whileHover={{ scale: 1.01 }}
                      whileTap={{ scale: 0.99 }}
                      type="button"
                      onClick={() => handlePresetSort("manufacturer")}
                      className="w-full text-left px-3.5 py-2.5 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800/60 border border-slate-200 dark:border-slate-800 rounded-xl text-xs font-semibold text-slate-700 dark:text-slate-300 transition-all flex items-center justify-between cursor-pointer"
                    >
                      <span>{isZh ? "按生产商字母" : "By Manufacturer A-Z"}</span>
                      <ArrowUpDown size={12} className="text-slate-400" />
                    </motion.button>

                    <motion.button
                      whileHover={{ scale: 1.01 }}
                      whileTap={{ scale: 0.99 }}
                      type="button"
                      onClick={() => handlePresetSort("completeness")}
                      className="w-full text-left px-3.5 py-2.5 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800/60 border border-slate-200 dark:border-slate-800 rounded-xl text-xs font-semibold text-slate-700 dark:text-slate-300 transition-all flex items-center justify-between cursor-pointer"
                    >
                      <span>{isZh ? "按数据完整度降序" : "By Completeness (High to Low)"}</span>
                      <ArrowUpDown size={12} className="text-slate-400" />
                    </motion.button>

                    <motion.button
                      whileHover={{ scale: 1.01 }}
                      whileTap={{ scale: 0.99 }}
                      type="button"
                      onClick={() => handlePresetSort("density")}
                      className="w-full text-left px-3.5 py-2.5 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800/60 border border-slate-200 dark:border-slate-800 rounded-xl text-xs font-semibold text-slate-700 dark:text-slate-300 transition-all flex items-center justify-between cursor-pointer"
                    >
                      <span>{isZh ? "按密度数值降序" : "By Density Values (High-Low)"}</span>
                      <ArrowUpDown size={12} className="text-slate-400" />
                    </motion.button>

                    <motion.button
                      whileHover={{ scale: 1.01 }}
                      whileTap={{ scale: 0.99 }}
                      type="button"
                      onClick={() => handlePresetSort("tensile")}
                      className="w-full text-left px-3.5 py-2.5 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800/60 border border-slate-200 dark:border-slate-800 rounded-xl text-xs font-semibold text-slate-700 dark:text-slate-300 transition-all flex items-center justify-between cursor-pointer"
                    >
                      <span>{isZh ? "按拉伸强度降序" : "By Tensile Strength (High-Low)"}</span>
                      <ArrowUpDown size={12} className="text-slate-400" />
                    </motion.button>
                  </div>
                </div>

                <div className="space-y-3 pt-2 border-t border-slate-100 dark:border-slate-800">
                  <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1">
                    <Sliders size={12} className="text-indigo-500" />
                    {isZh ? "全选集合翻转" : "Transformations"}
                  </h4>

                  <motion.button
                    whileHover={{ scale: 1.01 }}
                    whileTap={{ scale: 0.99 }}
                    type="button"
                    onClick={handleReverseOrder}
                    className="w-full py-2.5 px-3.5 bg-indigo-50/50 hover:bg-indigo-50 dark:bg-indigo-950/20 dark:hover:bg-indigo-950/40 text-indigo-700 dark:text-indigo-400 border border-indigo-100 dark:border-indigo-900/40 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 shadow-sm cursor-pointer"
                  >
                    <RefreshCw size={12} />
                    {isZh ? "逆序/反转排列" : "Reverse Selected Sequence"}
                  </motion.button>
                </div>

                {/* Instructions card */}
                <div className="flex-1 flex flex-col justify-end">
                  <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-900/50 border border-slate-200/50 dark:border-slate-800/50 text-[11px] text-slate-500 dark:text-slate-400 flex gap-3">
                    <Info size={16} className="text-violet-500 shrink-0 mt-0.5" />
                    <div className="space-y-1">
                      <p className="font-bold text-slate-700 dark:text-slate-300">
                        {isZh ? "关于默认网格检索顺序" : "Custom Layout Priority Guide"}
                      </p>
                      <p className="leading-relaxed opacity-90">
                        {isZh
                          ? "调整新顺序后，我们将自动在后台将它们转换为顺序的逻辑索引位，在未主动应用其他列排序的前提下，网格默认将遵守此项排列规律。"
                          : "Rearranging items assigns numeric priority ranks. Clear other sorting options in the grid to instantly load foods/products in your customized visual order."}
                      </p>
                    </div>
                  </div>
                </div>

              </div>

            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 flex items-center justify-end gap-3 shrink-0">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-xs font-bold text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              >
                {t("cancel")}
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                type="button"
                onClick={handleSave}
                className="px-5 py-2 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-500 rounded-xl shadow-sm flex items-center gap-1.5 transition-all"
              >
                <Save size={14} />
                {isZh ? "确认更新顺序" : "Apply Custom Sequence"}
              </motion.button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
