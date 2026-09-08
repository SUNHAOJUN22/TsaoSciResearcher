import React, { useState, useEffect, KeyboardEvent } from "react";
import {
  X,
  Tag,
  Plus,
  Save,
  AlertCircle,
  Info,
  Layers
} from "lucide-react";
import { Product } from "@/types/index";
import { useLanguage } from "@/contexts/LanguageContext";
import { motion, AnimatePresence } from "motion/react";

interface BulkTaggingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (ids: string[], tags: string[], mode: "append" | "overwrite" | "remove") => void;
  selectedProducts: Product[];
}

const PRESET_TAGS = [
  { zh: "食品级", en: "FDA-Approved" },
  { zh: "汽车级", en: "Automotive" },
  { zh: "阻燃", en: "Flame Retardant" },
  { zh: "耐高热", en: "High Heat" },
  { zh: "回收料", en: "Recycled" },
  { zh: "医疗级", en: "Medical" },
  { zh: "高透", en: "High Clarity" },
  { zh: "高抗冲", en: "High Impact" }
];

export const BulkTaggingModal: React.FC<BulkTaggingModalProps> = ({
  isOpen,
  onClose,
  onSave,
  selectedProducts,
}) => {
  const { t, language } = useLanguage();
  const [newTagInput, setNewTagInput] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [mode, setMode] = useState<"append" | "overwrite" | "remove">("append");

  // Keep track of previously existing tags across all selected products for easy reference
  const existingTagsUnion = React.useMemo(() => {
    const union = new Set<string>();
    selectedProducts.forEach((p) => {
      if (p.tags && Array.isArray(p.tags)) {
        p.tags.forEach((tag) => union.add(tag));
      }
    });
    return Array.from(union);
  }, [selectedProducts]);

  useEffect(() => {
    if (isOpen) {
      setTags([]);
      setNewTagInput("");
      setMode("append");
    }
  }, [isOpen]);

  const addTag = (tag: string) => {
    const trimmed = tag.trim();
    if (!trimmed) return;
    if (!tags.includes(trimmed)) {
      setTags([...tags, trimmed]);
    }
    setNewTagInput("");
  };

  const removeTag = (indexToRemove: number) => {
    setTags(tags.filter((_, idx) => idx !== indexToRemove));
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addTag(newTagInput);
    }
  };

  const handleSave = () => {
    if (tags.length === 0 && mode !== "overwrite") {
      return;
    }
    const ids = selectedProducts.map((p) => p.id);
    onSave(ids, tags, mode);
    onClose();
  };

  const isZh = language === "zh";

  return (
    <AnimatePresence>
      {isOpen && selectedProducts.length > 0 && (
        <motion.div
          key="bulk-tagging-modal"
          className="fixed inset-0 z-[110] flex items-center justify-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={onClose}
          ></div>

          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: "spring", duration: 0.4, bounce: 0 }}
            className="relative w-full max-w-xl bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 flex flex-col max-h-[90vh] rounded-2xl md:rounded-[2rem] overflow-hidden shadow-[0_24px_60px_-15px_rgba(0,0,0,0.3)]"
          >
            {/* Header */}
            <div className="px-6 py-5 border-b border-slate-100 dark:border-slate-800/80 flex items-center justify-between bg-slate-50/50 dark:bg-slate-900/30 relative overflow-hidden shrink-0">
              <div className="flex items-center gap-3 relative z-10">
                <div className="p-2 bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400 rounded-xl border border-indigo-100 dark:border-indigo-900/30">
                  <Tag size={20} />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-slate-800 dark:text-white tracking-tight mb-1">
                    {isZh ? "批量标签与元数据管理" : "Bulk Metadata Tagging"}
                  </h3>
                  <p className="text-[10px] text-slate-400 font-medium">
                    {isZh 
                      ? `已选择 ${selectedProducts.length} 个物性牌号` 
                      : `Selected ${selectedProducts.length} material grades`}
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

            {/* Content body */}
            <div className="p-6 overflow-y-auto space-y-5">
              {/* Target items list (compact overview) */}
              <div className="bg-slate-50 dark:bg-slate-900/50 rounded-xl p-3 border border-slate-100 dark:border-slate-800/50 max-h-24 overflow-y-auto">
                <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                  <Layers size={11} />
                  {isZh ? "目标品类与牌号" : "Target Grades"}
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {selectedProducts.map((p) => (
                    <span
                      key={p.id}
                      className="inline-flex items-center text-[10px] bg-white dark:bg-slate-900/80 text-slate-600 dark:text-slate-300 px-2 py-0.5 rounded-md border border-slate-200/50 dark:border-slate-800 font-mono"
                    >
                      {p.gradeName}
                    </span>
                  ))}
                </div>
              </div>

              {/* Mode Selection */}
              <div>
                <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">
                  {isZh ? "标签操作模式" : "Operation Mode"}
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {(["append", "overwrite", "remove"] as const).map((m) => {
                    const active = mode === m;
                    return (
                      <motion.button
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        key={m}
                        type="button"
                        onClick={() => setMode(m)}
                        className={`flex flex-col items-center justify-center p-3 rounded-xl border text-center transition-all cursor-pointer ${
                          active
                            ? "bg-indigo-50 border-indigo-200 dark:bg-indigo-950/40 dark:border-indigo-800 text-indigo-700 dark:text-indigo-400 shadow-sm"
                            : "bg-white border-slate-200 hover:border-slate-300 dark:bg-slate-900 dark:border-slate-800 dark:hover:border-slate-700 text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
                        }`}
                      >
                        <span className="text-xs font-bold leading-none mb-1">
                          {m === "append" && (isZh ? "追加" : "Append")}
                          {m === "overwrite" && (isZh ? "覆盖" : "Overwrite")}
                          {m === "remove" && (isZh ? "移除" : "Remove")}
                        </span>
                        <span className="text-[9px] opacity-70 leading-none">
                          {m === "append" && (isZh ? "保留旧标签并新增" : "Add to existing")}
                          {m === "overwrite" && (isZh ? "全部清空并替换" : "Replace entirely")}
                          {m === "remove" && (isZh ? "清除选中匹配项" : "Subtract matching")}
                        </span>
                      </motion.button>
                    );
                  })}
                </div>
              </div>

              {/* Tag Input Field */}
              <div>
                <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">
                  {isZh ? "输入标签 / 标签名称" : "Tag Input"}
                </label>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <input
                      type="text"
                      value={newTagInput}
                      onKeyDown={handleKeyDown}
                      onChange={(e) => setNewTagInput(e.target.value)}
                      placeholder={isZh ? "输入标签内容，按回车或逗号分隔..." : "Type tag and press enter..."}
                      className="w-full px-3.5 py-2.5 text-xs bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-slate-100 rounded-xl border border-slate-200 dark:border-slate-800 focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
                    />
                  </div>
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    type="button"
                    onClick={() => addTag(newTagInput)}
                    className="px-3 bg-slate-900 hover:bg-slate-800 dark:bg-white dark:hover:bg-slate-100 text-white dark:text-slate-950 rounded-xl font-bold text-xs flex items-center justify-center gap-1.5 shadow-sm"
                  >
                    <Plus size={14} />
                    {isZh ? "添加" : "Add"}
                  </motion.button>
                </div>
              </div>

              {/* Tags staging area */}
              <div className="space-y-2">
                <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  {isZh ? `待应用的标签集 (${tags.length})` : `Pending Tags (${tags.length})`}
                </label>
                <div className="min-h-16 flex flex-wrap gap-1.5 p-3.5 bg-slate-50 dark:bg-slate-900 rounded-xl border border-dashed border-slate-200 dark:border-slate-800">
                  {tags.length === 0 ? (
                    <div className="w-full h-full flex items-center justify-center text-slate-400 py-3 text-[11px]">
                      {mode === "overwrite" 
                        ? (isZh ? "⚠️ 无标签意味着将会把所有选中牌号的标签清空！" : "⚠️ No tags means existing tags will be cleared!")
                        : (isZh ? "在上方输入，或点击下方的常用预设" : "Input tags above, or select from presets below")}
                    </div>
                  ) : (
                    tags.map((tag, idx) => (
                      <span
                        key={idx}
                        className={`inline-flex items-center gap-1 text-xs font-bold px-2.5 py-1 rounded-full border shadow-sm ${
                          mode === "remove"
                            ? "bg-rose-50 border-rose-200 text-rose-700 dark:bg-rose-950/30 dark:border-rose-900 dark:text-rose-400"
                            : "bg-indigo-50 border-indigo-200 text-indigo-700 dark:bg-indigo-950/30 dark:border-indigo-900 dark:text-indigo-400"
                        }`}
                      >
                        {tag}
                        <motion.button
                          whileHover={{ scale: 1.15 }}
                          whileTap={{ scale: 0.85 }}
                          type="button"
                          onClick={() => removeTag(idx)}
                          className="hover:text-rose-500 rounded-full transition-colors focus:outline-none cursor-pointer"
                        >
                          <X size={12} strokeWidth={2.5} />
                        </motion.button>
                      </span>
                    ))
                  )}
                </div>
              </div>

              {/* Preset/Existing Quick selections */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                    {isZh ? "推荐高频属性与预设" : "Recommended Preset Attributes"}
                  </span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {PRESET_TAGS.map((p, idx) => {
                    const tagStr = isZh ? p.zh : p.en;
                    const isSelected = tags.includes(tagStr);
                    return (
                      <motion.button
                        whileHover={isSelected ? {} : { scale: 1.05 }}
                        whileTap={isSelected ? {} : { scale: 0.95 }}
                        key={idx}
                        type="button"
                        onClick={() => addTag(tagStr)}
                        disabled={isSelected}
                        className={`text-[10px] font-semibold px-2.5 py-1 rounded-lg border transition-all ${
                          isSelected
                            ? "bg-slate-100 border-slate-200 text-slate-400 dark:bg-slate-800 dark:border-slate-700 cursor-not-allowed"
                            : "bg-white border-slate-200 hover:border-slate-300 dark:bg-slate-900/50 dark:border-slate-800 dark:hover:border-slate-700 text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 cursor-pointer"
                        }`}
                      >
                        {tagStr}
                      </motion.button>
                    );
                  })}
                </div>
              </div>

              {/* Union references if any exits */}
              {existingTagsUnion.length > 0 && (
                <div className="space-y-2">
                  <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                    {isZh ? "从已有标签中快速选择" : "Quick Select From Existing Tags"}
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {existingTagsUnion.map((tag, idx) => {
                      const isSelected = tags.includes(tag);
                      return (
                        <motion.button
                          whileHover={isSelected ? {} : { scale: 1.05 }}
                          whileTap={isSelected ? {} : { scale: 0.95 }}
                          key={idx}
                          type="button"
                          onClick={() => addTag(tag)}
                          disabled={isSelected}
                          className={`text-[10px] font-mono px-2 py-0.5 rounded border transition-all ${
                            isSelected
                              ? "bg-slate-100 border-slate-200 text-slate-400 dark:bg-slate-800 dark:border-slate-700 cursor-not-allowed"
                              : "bg-white border-slate-200 hover:border-slate-300 dark:bg-slate-900/50 dark:border-slate-800 dark:hover:border-slate-700 text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 cursor-pointer"
                          }`}
                        >
                          {tag}
                        </motion.button>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Dynamic warning/info banner */}
              <div className={`p-3.5 rounded-xl border flex gap-3 text-[11px] ${
                mode === "overwrite"
                  ? "bg-amber-50/50 border-amber-200 text-amber-800 dark:bg-amber-950/20 dark:border-amber-900 dark:text-amber-400"
                  : "bg-slate-50 border-slate-200 text-slate-600 dark:bg-slate-900 dark:border-slate-800 dark:text-slate-400"
              }`}>
                {mode === "overwrite" ? (
                  <AlertCircle size={14} className="shrink-0 text-amber-500" />
                ) : (
                  <Info size={14} className="shrink-0 text-indigo-500" />
                )}
                <div className="space-y-1">
                  <p className="font-bold">
                    {mode === "append" && (isZh ? "追加模式" : "Append Mode")}
                    {mode === "overwrite" && (isZh ? "注意：覆盖替换模式 (Dangerous)" : "Caution: Overwrite Mode (Dangerous)")}
                    {mode === "remove" && (isZh ? "减免撤销模式" : "Remove Mode")}
                  </p>
                  <p className="opacity-80">
                    {mode === "append" && (isZh 
                      ? "新添加的标签将会被累计到每个选中牌号。如果特定牌号已含该标签，则会自动去重避免重复。" 
                      : "New tags will be added to each grade's existing tag set. Duplicate tags on any given item will be skipped.")}
                    {mode === "overwrite" && (isZh 
                      ? "此操作会将选中的所有牌号原有的所有标签全部抹除，完全被这里新定义的标签集取代！该操作可以撤回，但建议谨慎操作。" 
                      : "This will completely erase all pre-existing tags on selected products and replace them with the current specified tag set. Can be undone via history changes.")}
                    {mode === "remove" && (isZh 
                      ? "若选中的产品包含了这些标签，对应的标签将被一键剥除。其他已有的标签仍会继续保留。" 
                      : "If any selected grades contain these specific tags, those matched tags will be permanently removed. All other non-matching tags will be preserved.")}
                  </p>
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
                disabled={tags.length === 0 && mode !== "overwrite"}
                onClick={handleSave}
                className={`px-5 py-2 text-xs font-bold text-white rounded-xl shadow-sm flex items-center gap-1.5 transition-all ${
                  tags.length === 0 && mode !== "overwrite"
                    ? "bg-slate-300 dark:bg-slate-800 cursor-not-allowed text-slate-500"
                    : mode === "remove"
                      ? "bg-rose-600 hover:bg-rose-500"
                      : "bg-indigo-600 hover:bg-indigo-500"
                }`}
              >
                <Save size={14} />
                {isZh ? "应用到选中项" : "Apply to Selected"}
              </motion.button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
