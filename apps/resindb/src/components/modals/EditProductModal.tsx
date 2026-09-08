import { logger } from '@/lib/logger';
import React, { useState, useEffect } from "react";
import {
  X,
  Save,
  Plus,
  Trash2,
  Beaker,
  Factory,
  Loader2,
  Settings2,
  Link as LinkIcon,
  Hash,
  Thermometer,
  FileText,
  Layers,
  Sparkles,
} from "lucide-react";
import { Product, PropertyValue } from '@/types/index';
import { useLanguage } from "@/contexts/LanguageContext";
import { useToasts } from "@/contexts/ToastContext";
import { motion, AnimatePresence } from "motion/react";
import { aiService } from "@/services/aiService";

interface EditProductModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (product: Product) => Promise<boolean> | void;
  product: Product | null;
}

interface PropertyRow {
  id: string;
  key: string;
  value: string;
  unit: string;
  // Metadata fields
  standard: string;
  instrument: string;
  temperature: string;
  referenceId: string;
  sourceUrl: string;
  isExpanded: boolean;
}

export const EditProductModal: React.FC<EditProductModalProps> = React.memo(({
  isOpen,
  onClose,
  onSave,
  product,
}) => {
  const { t } = useLanguage();
  const { addToast } = useToasts();
  const [formData, setFormData] = useState<Partial<Product>>({});
  const [propertyRows, setPropertyRows] = useState<PropertyRow[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [isAiGenerating, setIsAiGenerating] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.gradeName?.trim()) newErrors.gradeName = t("fieldRequired", "Field required");
    if (!formData.manufacturer?.trim()) newErrors.manufacturer = t("fieldRequired", "Field required");

    // Check for duplicate property keys
    const seenKeys = new Set<string>();
    propertyRows.forEach(row => {
      if (row.key.trim()) {
        if (seenKeys.has(row.key.trim())) {
          newErrors[`prop-${row.id}`] = t("duplicateKey", "Duplicate key");
        }
        seenKeys.add(row.key.trim());
      }
    });

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleAiFill = async () => {
    if (!formData.gradeName || isAiGenerating) return;
    setIsAiGenerating(true);
    try {
      const generated = await aiService.generateProductProperties();

      // Verify that there are valid properties
      let validCount = 0;
      if (generated && typeof generated === "object") {
        Object.values(generated).forEach((val: PropertyValue) => {
          if (
            val && 
            val.value !== undefined && 
            val.value !== null && 
            String(val.value).trim() !== "" && 
            !["unknown", "n/a", "none", "null", "-", "未检测", "暂无", "无"].includes(String(val.value).toLowerCase().trim())
          ) {
            validCount++;
          }
        });
      }

      if (validCount < 2) {
        addToast("error", "该材料物理性指标深度在专业大盘库判定不足（没有具体详细物性），已遵照安全原则自动丢弃删除");
        setIsAiGenerating(false);
        return;
      }

      const newRows: PropertyRow[] = Object.entries(generated).map(([key, val]) => ({
        id: `ai-${Date.now()}-${key}`,
        key,
        value: String(val.value),
        unit: val.unit || "",
        standard: val.standard || "",
        instrument: val.instrument || "",
        temperature: val.temperature === undefined ? "" : String(val.temperature),
        referenceId: val.referenceId || "",
        sourceUrl: val.sourceUrl || "",
        isExpanded: false,
      }));

      // Merge behavior: avoid duplicates or just append? Append is safer for users to review.
      setPropertyRows(prev => [...newRows, ...prev]);
      addToast("success", "已成功从专业库抓取并自动同步详细物理性能参数！");
    } catch (error) {
      logger.error("AI Generation failed:", error);
      addToast("error", "获取物性性能参数失败，该无效牌号记录已被自动撤销并丢弃！");
    } finally {
      setIsAiGenerating(false);
    }
  };

  useEffect(() => {
    if (product) {
      setFormData({
        gradeName: product.gradeName,
        manufacturer: product.manufacturer,
        categoryIds: product.categoryIds,
      });

      const rows = Object.entries(product.properties).map(([key, v], index) => {
        const val = v as PropertyValue; // Explicit Cast
        return {
          id: `prop-${index}-${Date.now()}`,
          key,
          value: String(val.value),
          unit: val.unit || "",
          standard: val.standard || "",
          instrument: val.instrument || "",
          temperature: val.temperature === undefined ? "" : String(val.temperature),
          referenceId: val.referenceId || "",
          sourceUrl: val.sourceUrl || "",
          isExpanded: false,
        };
      });
      setPropertyRows(rows);
    }
  }, [product, isOpen]);

  const handleSave = async () => {
    if (!product || isSaving) return;
    if (!validate()) return;
    setIsSaving(true);

    const newProperties: Record<string, PropertyValue> = {};
    propertyRows.forEach((row) => {
      if (row.key.trim()) {
        const numVal = Number(row.value);
        newProperties[row.key] = {
          value: !isNaN(numVal) && row.value.trim() !== "" ? numVal : row.value,
          unit: row.unit.trim() || undefined,
          standard: row.standard.trim() || undefined,
          instrument: row.instrument.trim() || undefined,
          temperature: row.temperature.trim() || undefined,
          referenceId: row.referenceId.trim() || undefined,
          sourceUrl: row.sourceUrl.trim() || undefined,
        };
      }
    });

    const updatedProduct = {
      ...product,
      ...(formData as Product),
      properties: newProperties,
      updatedAt: new Date().toISOString().split("T")[0],
    };

    try {
      await onSave(updatedProduct);
      onClose();
    } catch {
      // Error handling done in parent
    } finally {
      setIsSaving(false);
    }
  };

  const addRow = () => {
    setPropertyRows([
      ...propertyRows,
      {
        id: `new-${Date.now()}`,
        key: "",
        value: "",
        unit: "",
        standard: "",
        instrument: "",
        temperature: "",
        referenceId: "",
        sourceUrl: "",
        isExpanded: true,
      },
    ]);
  };

  const removeRow = (id: string) => {
    setPropertyRows(propertyRows.filter((r) => r.id !== id));
  };

  const updateRow = (id: string, field: keyof PropertyRow, val: unknown) => {
    setPropertyRows(
      propertyRows.map((r) => (r.id === id ? { ...r, [field]: val } : r)),
    );
  };

  const toggleExpand = (id: string) => {
    setPropertyRows(
      propertyRows.map((r) =>
        r.id === id ? { ...r, isExpanded: !r.isExpanded } : r,
      ),
    );
  };

  return (
    <AnimatePresence>
      {isOpen && product && (
        <motion.div
          key="edit-product-modal-root"
          className="fixed inset-0 z-[100] flex items-center justify-center p-4"
        >
          <motion.div
            key="edit-product-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={onClose}
          ></motion.div>
          <motion.div
            key="edit-product-content"
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: "spring", duration: 0.4, bounce: 0 }}
            className="relative w-full max-w-2xl bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 flex flex-col max-h-[90vh] shadow-2xl rounded-[2.5rem] overflow-hidden"
          >
            {/* Header */}
            <div className="px-5 py-4 border-b border-slate-300 dark:border-slate-700 flex items-center justify-between bg-slate-900 dark:bg-slate-950 relative overflow-hidden shrink-0">
              <div className="flex items-center gap-3 relative z-10">
                <div className="p-2 bg-primary-600 text-white border border-primary-700 rounded-xl shadow-inner">
                  <Beaker size={18} />
                </div>
                <div>
                  <h3 className="text-sm font-serif font-bold text-white tracking-tight leading-none mb-1">
                    {t("editProduct")}
                  </h3>
                  <p className="text-[10px] font-mono text-slate-400 uppercase tracking-widest truncate">
                    Material Specification Editor
                  </p>
                </div>
              </div>
              <motion.button
                whileHover={{
                  scale: 1.1,
                  backgroundColor: "rgba(225, 29, 72, 1)",
                }}
                whileTap={{ scale: 0.9 }}
                onClick={onClose}
                className="p-2 bg-white/5 backdrop-blur-md border border-white/10 text-slate-400 rounded-xl transition-all focus:outline-none focus-visible:ring-1 focus-visible:ring-rose-500 z-10"
              >
                <X size={16} />
              </motion.button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6 custom-scrollbar space-y-6 bg-white dark:bg-slate-950">
              {/* Basic Info Section */}
              <section className="space-y-4">
                <div className="flex items-center gap-2 text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest mb-2">
                  <Settings2 size={14} className="text-primary-500" />{" "}
                  {t("basicInfo")}
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <label className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-widest ml-1">
                      {t("gradeName")}
                    </label>
                    <div className="relative">
                      <motion.input
                        type="text"
                        whileFocus={{
                          scale: 1.01,
                          boxShadow: "0 0 0 4px rgba(79, 70, 229, 0.1)",
                        }}
                        value={formData.gradeName || ""}
                        onChange={(e) => {
                          setFormData({ ...formData, gradeName: e.target.value });
                          if (errors.gradeName) setErrors({ ...errors, gradeName: "" });
                        }}
                        className={`w-full px-3 py-2 bg-slate-50 dark:bg-slate-900 border rounded-xl text-xs font-mono font-bold outline-none transition-all shadow-sm pr-24 ${errors.gradeName ? "border-rose-500 ring-4 ring-rose-500/10" : formData.gradeName !== product.gradeName ? "border-amber-500/50 ring-1 ring-amber-500/10 text-amber-600 dark:text-amber-400" : "border-slate-200 dark:border-slate-800 text-slate-800 dark:text-white focus:border-primary-500"}`}
                      />
                      {errors.gradeName && (
                        <p className="text-[10px] text-rose-500 mt-1 font-bold ml-1">{errors.gradeName}</p>
                      )}
                      <div className="absolute right-1.5 top-1/2 -translate-y-1/2">
                        <motion.button
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                          onClick={handleAiFill}
                          disabled={!formData.gradeName || isAiGenerating}
                          className="flex items-center gap-1.5 px-2.5 py-1.5 bg-gradient-to-r from-indigo-600 to-purple-600 text-white text-[8px] font-mono font-black uppercase tracking-tighter rounded-lg shadow-sm disabled:opacity-50"
                        >
                          {isAiGenerating ? (
                            <Loader2 size={10} className="animate-spin" />
                          ) : (
                            <Sparkles size={10} />
                          )}
                          {t("aiSmartFill", "Smart Fill")}
                        </motion.button>
                      </div>
                    </div>
                  </div>
                  <div className="space-y-1">
                    <label className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-widest ml-1">
                      {t("manufacturer")}
                    </label>
                    <div className="relative">
                      <Factory
                        size={14}
                        className={`absolute left-3 top-1/2 -translate-y-1/2 transition-colors ${errors.manufacturer ? "text-rose-500" : formData.manufacturer !== product.manufacturer ? "text-amber-500" : "text-slate-400"}`}
                      />
                      <motion.input
                        type="text"
                        whileFocus={{
                          scale: 1.01,
                          boxShadow: "0 0 0 4px rgba(79, 70, 229, 0.1)",
                        }}
                        value={formData.manufacturer || ""}
                        onChange={(e) => {
                          setFormData({
                            ...formData,
                            manufacturer: e.target.value,
                          });
                          if (errors.manufacturer) setErrors({ ...errors, manufacturer: "" });
                        }}
                        className={`w-full pl-9 pr-3 py-2 bg-slate-50 dark:bg-slate-900 border rounded-xl text-xs font-mono font-bold outline-none transition-all shadow-sm ${errors.manufacturer ? "border-rose-500 ring-4 ring-rose-500/10" : formData.manufacturer !== product.manufacturer ? "border-amber-500/50 ring-1 ring-amber-500/10 text-amber-600 dark:text-amber-400" : "border-slate-200 dark:border-slate-800 text-slate-800 dark:text-white focus:border-primary-500"}`}
                      />
                      {errors.manufacturer && (
                        <p className="text-[10px] text-rose-500 mt-1 font-bold ml-1">{errors.manufacturer}</p>
                      )}
                    </div>
                  </div>
                </div>
              </section>

              {/* Properties Section */}
              <section className="space-y-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2 text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">
                    <Layers size={14} className="text-primary-500" />{" "}
                    {t("properties")}
                  </div>
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={addRow}
                    className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white border border-primary-600 text-[10px] font-mono font-bold uppercase tracking-widest hover:bg-primary-700 transition-all shadow-sm rounded-xl"
                  >
                    <Plus size={14} /> {t("addProperty")}
                  </motion.button>
                </div>

                <motion.div 
                  initial="hidden"
                  animate="visible"
                  variants={{
                    hidden: { opacity: 0 },
                    visible: {
                      opacity: 1,
                      transition: {
                        staggerChildren: 0.05
                      }
                    }
                  }}
                  className="space-y-3"
                >
                  <AnimatePresence mode="popLayout">
                    {propertyRows.map((row) => (
                      <motion.div
                        key={row.id}
                        layout
                        variants={{
                          hidden: { opacity: 0, x: -20, scale: 0.95 },
                          visible: { opacity: 1, x: 0, scale: 1 }
                        }}
                        initial="hidden"
                        animate="visible"
                        exit={{ opacity: 0, x: 20, scale: 0.95 }}
                        className={`bg-slate-50 dark:bg-slate-900 border transition-all duration-300 overflow-hidden ${errors[`prop-${row.id}`] ? "border-rose-500 ring-2 ring-rose-500/20" : row.isExpanded ? "border-primary-500 ring-1 ring-primary-500/20 shadow-lg shadow-primary-500/5" : "border-slate-300 dark:border-slate-700 hover:border-slate-400 dark:hover:border-slate-600 shadow-sm"}`}
                      >
                        <div className="flex items-center gap-3 p-3">
                          <div className="flex-1 grid grid-cols-1 sm:grid-cols-3 gap-2">
                            <div className="relative">
                              <motion.input
                                type="text"
                                whileFocus={{
                                  scale: 1.02,
                                  boxShadow: "0 0 0 4px rgba(79, 70, 229, 0.1)",
                                }}
                                placeholder={t("propertyName")}
                                value={row.key || ""}
                                onChange={(e) => {
                                  updateRow(row.id, "key", e.target.value);
                                  if (errors[`prop-${row.id}`]) {
                                    const newErrs = { ...errors };
                                    delete newErrs[`prop-${row.id}`];
                                    setErrors(newErrs);
                                  }
                                }}
                                className={`w-full px-2 py-1.5 bg-white dark:bg-slate-950 border text-[10px] font-mono font-bold outline-none rounded-lg ${errors[`prop-${row.id}`] ? "border-rose-500 text-rose-600" : "border-slate-300 dark:border-slate-700 text-slate-800 dark:text-white focus:border-primary-500"}`}
                              />
                              {errors[`prop-${row.id}`] && (
                                <p className="absolute -bottom-4 left-0 text-[8px] text-rose-500 font-bold">{errors[`prop-${row.id}`]}</p>
                              )}
                            </div>
                            <motion.input
                              type="text"
                              whileFocus={{
                                scale: 1.02,
                                boxShadow: "0 0 0 4px rgba(79, 70, 229, 0.1)",
                              }}
                              placeholder={t("propertyValue")}
                              value={
                                row.value !== undefined && row.value !== null
                                  ? row.value
                                  : ""
                              }
                              onChange={(e) =>
                                updateRow(row.id, "value", e.target.value)
                              }
                              className="px-2 py-1.5 bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 text-[10px] font-mono font-bold text-primary-600 dark:text-primary-400 focus:border-primary-500 outline-none rounded-lg"
                            />
                            <motion.input
                              type="text"
                              whileFocus={{
                                scale: 1.02,
                                boxShadow: "0 0 0 4px rgba(79, 70, 229, 0.1)",
                              }}
                              placeholder={t("unit")}
                              value={row.unit || ""}
                              onChange={(e) =>
                                updateRow(row.id, "unit", e.target.value)
                              }
                              className="px-2 py-1.5 bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 text-[10px] font-mono font-bold text-slate-500 focus:border-primary-500 outline-none rounded-lg"
                            />
                          </div>
                          <div className="flex items-center gap-1 shrink-0">
                            <motion.button
                              whileHover={{ scale: 1.1 }}
                              whileTap={{ scale: 0.9 }}
                              onClick={() => toggleExpand(row.id)}
                              className={`p-1.5 transition-all border rounded-lg ${row.isExpanded ? "bg-primary-600 border-primary-600 text-white" : "text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 bg-white dark:bg-slate-950 border-slate-300 dark:border-slate-700 shadow-sm"}`}
                              title="More Options"
                            >
                              <Settings2 size={14} />
                            </motion.button>
                            <motion.button
                              whileHover={{
                                scale: 1.1,
                                backgroundColor: "rgba(244, 63, 94, 0.1)",
                              }}
                              whileTap={{ scale: 0.9 }}
                              onClick={() => removeRow(row.id)}
                              className="p-1.5 text-slate-400 hover:text-rose-600 bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 transition-all rounded-lg shadow-sm"
                              title="Remove"
                            >
                              <Trash2 size={14} />
                            </motion.button>
                          </div>
                        </div>

                        <AnimatePresence>
                          {row.isExpanded && (
                            <motion.div
                              key={`property-row-expanded-${row.id}`}
                              initial={{ height: 0, opacity: 0 }}
                              animate={{ height: "auto", opacity: 1 }}
                              exit={{ height: 0, opacity: 0 }}
                              className="px-3 pb-3 pt-1 border-t border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
                            >
                              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-2">
                                <div className="space-y-1">
                                  <label className="text-[9px] font-mono font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
                                    <FileText size={10} /> {t("standard")}
                                  </label>
                                  <motion.input
                                    type="text"
                                    whileFocus={{
                                      scale: 1.02,
                                      boxShadow:
                                        "0 0 0 4px rgba(79, 70, 229, 0.1)",
                                    }}
                                    value={row.standard || ""}
                                    onChange={(e) =>
                                      updateRow(
                                        row.id,
                                        "standard",
                                        e.target.value,
                                      )
                                    }
                                    className="w-full px-2 py-1.5 bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-[10px] font-mono font-bold text-slate-700 dark:text-slate-200 outline-none focus:border-primary-500 rounded-lg"
                                  />
                                </div>
                                <div className="space-y-1">
                                  <label className="text-[9px] font-mono font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
                                    <Thermometer size={10} />{" "}
                                    {t("testConditions")}
                                  </label>
                                  <motion.input
                                    type="text"
                                    whileFocus={{
                                      scale: 1.02,
                                      boxShadow:
                                        "0 0 0 4px rgba(79, 70, 229, 0.1)",
                                    }}
                                    value={row.temperature || ""}
                                    onChange={(e) =>
                                      updateRow(
                                        row.id,
                                        "temperature",
                                        e.target.value,
                                      )
                                    }
                                    className="w-full px-2 py-1.5 bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-[10px] font-mono font-bold text-slate-700 dark:text-slate-200 outline-none focus:border-primary-500 rounded-lg"
                                  />
                                </div>
                                <div className="space-y-1">
                                  <label className="text-[9px] font-mono font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
                                    <Hash size={10} /> {t("referenceId")}
                                  </label>
                                  <motion.input
                                    type="text"
                                    whileFocus={{
                                      scale: 1.02,
                                      boxShadow:
                                        "0 0 0 4px rgba(79, 70, 229, 0.1)",
                                    }}
                                    value={row.referenceId || ""}
                                    onChange={(e) =>
                                      updateRow(
                                        row.id,
                                        "referenceId",
                                        e.target.value,
                                      )
                                    }
                                    className="w-full px-2 py-1.5 bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-[10px] font-mono font-bold text-slate-700 dark:text-slate-200 outline-none focus:border-primary-500 rounded-lg"
                                  />
                                </div>
                                <div className="space-y-1">
                                  <label className="text-[9px] font-mono font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
                                    <LinkIcon size={10} /> {t("sourceUrl")}
                                  </label>
                                  <motion.input
                                    type="text"
                                    whileFocus={{
                                      scale: 1.02,
                                      boxShadow:
                                        "0 0 0 4px rgba(79, 70, 229, 0.1)",
                                    }}
                                    value={row.sourceUrl || ""}
                                    onChange={(e) =>
                                      updateRow(
                                        row.id,
                                        "sourceUrl",
                                        e.target.value,
                                      )
                                    }
                                    className="w-full px-2 py-1.5 bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-[10px] font-mono font-bold text-slate-700 dark:text-slate-200 outline-none focus:border-primary-500 rounded-lg"
                                  />
                                </div>
                              </div>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </motion.div>
              </section>
            </div>

            {/* Footer */}
            <div className="px-5 py-4 bg-slate-50/50 dark:bg-slate-900/50 border-t border-slate-200 dark:border-slate-800 flex justify-end items-center gap-3 shrink-0">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={onClose}
                className="px-6 py-2 text-[10px] font-mono font-bold uppercase tracking-widest text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 transition-colors border border-transparent rounded-xl hover:bg-slate-200/50 dark:hover:bg-slate-800/50"
              >
                {t("cancel")}
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={handleSave}
                disabled={isSaving}
                className="flex items-center gap-2 px-8 py-2 bg-slate-900 dark:bg-white text-white dark:text-slate-900 font-mono font-bold text-[10px] uppercase tracking-widest hover:bg-slate-800 dark:hover:bg-slate-100 transition-all disabled:opacity-50 shadow-md hover:shadow-lg rounded-xl active:scale-95"
              >
                {isSaving ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Save size={14} />
                )}
                {t("saveChanges")}
              </motion.button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
});
