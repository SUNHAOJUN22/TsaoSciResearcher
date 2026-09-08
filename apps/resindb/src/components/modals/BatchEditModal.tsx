import React, { useState, useEffect } from "react";
import {
  X,
  Save,
  Factory,
  AlertCircle,
  ListChecks,
  Settings2,
} from "lucide-react";
import { Product, PropertyValue, ProductUpdates } from '@/types/index';
import { useLanguage } from "@/contexts/LanguageContext";
import { motion, AnimatePresence } from "motion/react";
import { safeStorage } from "@/lib/utils";

interface BatchEditModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (ids: string[], updates: ProductUpdates) => void;
  selectedProducts: Product[];
}

export const BatchEditModal: React.FC<BatchEditModalProps> = ({
  isOpen,
  onClose,
  onSave,
  selectedProducts,
}) => {
  const { t, tProp } = useLanguage();

  const LOCAL_STORAGE_KEY = 'resindb_batch_edit_draft';
  const dirtyRef = React.useRef(false);
  const initializedIdsRef = React.useRef<string | null>(null);

  // Track which fields are enabled for bulk update
  const [enabledFields, setEnabledFields] = useState<Record<string, boolean>>({
    manufacturer: false,
  });

  const [manufacturer, setManufacturer] = useState("");
  const [properties, setProperties] = useState<
    Record<string, { value: string; unit: string; enabled: boolean }>
  >({});

  useEffect(() => {
    if (!isOpen) {
      initializedIdsRef.current = null;
      return;
    }

    if (isOpen && selectedProducts.length > 0) {
      const currentIds = selectedProducts.map(p => p.id).sort().join(',');
      
      if (initializedIdsRef.current === currentIds) {
        return; // Prevent re-initialization if parent re-renders with the same product IDs
      }
      
      dirtyRef.current = false;
      initializedIdsRef.current = currentIds;
      
      const draftStr = safeStorage.local.getItem(LOCAL_STORAGE_KEY);
      
      let restored = false;
      if (draftStr) {
        try {
          const draft = JSON.parse(draftStr);
          if (draft.productIds === currentIds) {
            setManufacturer(draft.manufacturer);
            setProperties(draft.properties);
            setEnabledFields(draft.enabledFields);
            restored = true;
          }
        } catch (e) {
          console.error("Failed to parse batch edit draft", e);
        }
      }

      if (!restored) {
        const first = selectedProducts[0];
        setManufacturer(first.manufacturer);

        // Initialize properties from all unique keys across selected products
        const allPropKeys = new Set<string>();
        selectedProducts.forEach((p) => {
          Object.keys(p.properties).forEach((k) => allPropKeys.add(k));
        });

        const initialProps: Record<
          string,
          { value: string; unit: string; enabled: boolean }
        > = {};
        allPropKeys.forEach((key) => {
          const p = first.properties[key] as PropertyValue | undefined;
          initialProps[key] = {
            value: p ? String(p.value) : "",
            unit: p?.unit || "",
            enabled: false,
          };
        });
        setProperties(initialProps);
        setEnabledFields({ manufacturer: false });
      }
    }
  }, [isOpen, selectedProducts]);

  useEffect(() => {
    if (isOpen && dirtyRef.current && selectedProducts.length > 0) {
      const currentIds = selectedProducts.map(p => p.id).sort().join(',');
      const draft = {
        productIds: currentIds,
        manufacturer,
        properties,
        enabledFields
      };
      safeStorage.local.setItem(LOCAL_STORAGE_KEY, JSON.stringify(draft));
    }
  }, [manufacturer, properties, enabledFields, isOpen, selectedProducts]);

  const handleSave = () => {
    const updates: Partial<Product> = {};
    const finalProperties: Record<string, PropertyValue> = {};

    if (enabledFields.manufacturer) {
      updates.manufacturer = manufacturer;
    }

    // Fix: Cast explicitly to satisfy compiler
    (
      Object.entries(properties) as [
        string,
        { value: string; unit: string; enabled: boolean },
      ][]
    ).forEach(([key, data]) => {
      if (data.enabled) {
        const numVal = Number(data.value);
        finalProperties[key] = {
          value:
            !isNaN(numVal) && data.value.trim() !== "" ? numVal : data.value,
          unit: data.unit.trim() || undefined,
        };
      }
    });

    const updatesPayload: ProductUpdates = { ...updates };
    updatesPayload._propertyUpdates = finalProperties;

    onSave(
      selectedProducts.map((p) => p.id),
      updatesPayload,
    );
    safeStorage.local.removeItem(LOCAL_STORAGE_KEY);
    onClose();
  };

  const setDirty = () => { dirtyRef.current = true; };

  const toggleField = (field: string) => {
    setDirty();
    setEnabledFields((prev) => ({ ...prev, [field]: !prev[field] }));
  };

  const toggleProp = (key: string) => {
    setDirty();
    setProperties((prev) => ({
      ...prev,
      [key]: { ...prev[key], enabled: !prev[key].enabled },
    }));
  };

  const updateProp = (key: string, field: "value" | "unit", val: string) => {
    setDirty();
    setProperties((prev) => ({
      ...prev,
      [key]: { ...prev[key], [field]: val, enabled: true }, // Auto-enable on edit
    }));
  };

  return (
    <AnimatePresence>
      {isOpen && selectedProducts.length > 0 && (
        <motion.div
          key="batch-edit-modal"
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
            className="relative w-full max-w-2xl bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 flex flex-col max-h-[95vh] rounded-2xl md:rounded-[2.5rem] overflow-hidden shadow-[0_20px_50px_rgba(0,0,0,0.3)]"
          >
            {/* Header */}
            <div className="px-6 py-5 border-b border-slate-300 dark:border-slate-700 flex items-center justify-between bg-slate-50 dark:bg-slate-900 relative overflow-hidden shrink-0">
              <div className="flex items-center gap-3 relative z-10">
                <div className="p-2.5 bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 rounded-xl">
                  <ListChecks size={20} />
                </div>
                <div>
                  <h3 className="text-sm font-display text-slate-800 dark:text-white tracking-tight leading-none mb-1.5">
                    {t("batchEditTitle")}
                  </h3>
                  <p className="text-[10px] text-slate-500 dark:text-slate-400 uppercase tracking-widest font-mono font-bold">
                    {selectedProducts.length} {t("selected")}
                  </p>
                </div>
              </div>
              <motion.button
                whileHover={{
                  scale: 1.1,
                  backgroundColor: "rgba(225, 29, 72, 1)",
                  color: "#fff",
                }}
                whileTap={{ scale: 0.9 }}
                onClick={onClose}
                className="p-2 bg-slate-100 dark:bg-slate-800 text-slate-500 transition-all focus:outline-none focus-visible:ring-1 focus-visible:ring-rose-500 z-10 rounded-xl"
              >
                <X size={18} />
              </motion.button>
            </div>

            {/* Scrollable Content */}
            <div className="flex-1 overflow-y-auto p-4 md:p-8 custom-scrollbar space-y-6 md:space-y-8 bg-white dark:bg-slate-950">
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-3 md:p-5 bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-900/30 flex items-start gap-2 md:gap-4 rounded-xl md:rounded-2xl"
              >
                <div className="p-1 px-1.5 bg-amber-100 dark:bg-amber-900/30 text-amber-600 shrink-0 rounded-lg">
                  <AlertCircle size={18} />
                </div>
                <p className="text-[10px] md:text-[11px] text-amber-900 dark:text-amber-400 leading-relaxed font-serif italic">
                  {t("batchUpdateWarning")}
                </p>
              </motion.div>

              {/* Manufacturer Field */}
              <div className="space-y-4">
                <div className="flex items-center justify-between px-1">
                  <label className="text-[10px] font-mono text-slate-500 uppercase tracking-widest flex items-center gap-2 font-black">
                    <Factory size={16} className="text-primary-500" />{" "}
                    {tProp("生产厂家")}
                  </label>
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => toggleField("manufacturer")}
                    className={`px-4 py-1.5 text-[9px] font-mono uppercase tracking-widest transition-all border rounded-xl shadow-sm font-black ${enabledFields.manufacturer ? "bg-primary-600 border-primary-600 text-white" : "bg-slate-100 dark:bg-slate-800 border-slate-300 dark:border-slate-700 text-slate-500"}`}
                  >
                    {enabledFields.manufacturer ? t("enabled") : t("disabled")}
                  </motion.button>
                </div>
                <div
                  className={`relative transition-all duration-500 rounded-2xl overflow-hidden ${enabledFields.manufacturer ? "opacity-100" : "opacity-40 pointer-events-none grayscale"}`}
                >
                  <Factory
                    size={16}
                    className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-primary-500"
                  />
                  <motion.input
                    type="text"
                    value={manufacturer}
                    whileFocus={{
                      scale: 1.01,
                      boxShadow: "0 0 0 4px rgba(79, 70, 229, 0.1)",
                    }}
                    onChange={(e) => {
                      setDirty();
                      setManufacturer(e.target.value);
                      if (!enabledFields.manufacturer)
                        toggleField("manufacturer");
                    }}
                    className="w-full pl-11 pr-4 py-3 bg-slate-50/50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-2xl text-[11px] font-mono text-slate-800 dark:text-white focus:border-primary-500 focus:bg-white dark:focus:bg-slate-900 outline-none transition-all shadow-sm"
                    placeholder={t("enterManufacturer")}
                  />
                </div>
              </div>

              {/* Properties Section */}
              <div className="space-y-4">
                <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 uppercase tracking-widest px-1 font-black">
                  <Settings2 size={16} className="text-primary-500" />{" "}
                  {t("properties")}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Fix: Cast explicitly to satisfy compiler */}
                  {(
                    Object.entries(properties) as [
                      string,
                      { value: string; unit: string; enabled: boolean },
                    ][]
                  ).map(([key, data]) => (
                    <motion.div
                      key={key}
                      layout
                      className={`group bg-slate-50/50 dark:bg-slate-900/50 border transition-all duration-300 overflow-hidden rounded-2xl shadow-sm ${data.enabled ? "border-primary-500 ring-2 ring-primary-500/10" : "border-slate-200 dark:border-slate-800"}`}
                    >
                      <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950">
                        <span
                          className={`text-[10px] font-mono uppercase tracking-widest truncate pr-2 font-black ${data.enabled ? "text-primary-600 dark:text-primary-400" : "text-slate-400"}`}
                        >
                          {tProp(key)}
                        </span>
                        <motion.button
                          whileTap={{ scale: 0.9 }}
                          onClick={() => toggleProp(key)}
                          className={`w-9 h-5 relative transition-all rounded-full overflow-hidden ${data.enabled ? "bg-primary-600" : "bg-slate-300 dark:bg-slate-700"}`}
                        >
                          <motion.div
                            animate={{ x: data.enabled ? 18 : 3 }}
                            className="absolute top-1 w-3 h-3 bg-white transition-transform rounded-full shadow-sm"
                          />
                        </motion.button>
                      </div>
                      <div
                        className={`p-4 space-y-3 transition-all duration-500 ${data.enabled ? "opacity-100" : "opacity-40 grayscale pointer-events-none"}`}
                      >
                        <div className="space-y-1.5">
                          <label className="text-[9px] font-mono text-slate-400 uppercase tracking-widest font-black">
                            Value
                          </label>
                          <motion.input
                            type="text"
                            value={data.value}
                            whileFocus={{
                              scale: 1.02,
                              boxShadow: "0 0 0 4px rgba(79, 70, 229, 0.1)",
                            }}
                            onChange={(e) =>
                              updateProp(key, "value", e.target.value)
                            }
                            className="w-full px-3 py-2 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl text-[10px] font-mono text-primary-600 dark:text-primary-400 outline-none focus:border-primary-500 shadow-sm"
                            placeholder={t("value")}
                          />
                        </div>
                        <div className="space-y-1.5">
                          <label className="text-[9px] font-mono text-slate-400 uppercase tracking-widest font-black">
                            Unit
                          </label>
                          <motion.input
                            type="text"
                            value={data.unit}
                            whileFocus={{
                              scale: 1.02,
                              boxShadow: "0 0 0 4px rgba(79, 70, 229, 0.1)",
                            }}
                            onChange={(e) =>
                              updateProp(key, "unit", e.target.value)
                            }
                            className="w-full px-3 py-2 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl text-[10px] font-mono text-slate-500 outline-none focus:border-primary-500 shadow-sm"
                            placeholder={t("unit")}
                          />
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="px-4 md:px-6 py-4 md:py-5 bg-slate-50 dark:bg-slate-900 border-t border-slate-300 dark:border-slate-700 flex flex-col sm:flex-row justify-end items-center gap-3 md:gap-4 shrink-0">
              <motion.button
                whileHover={{ x: -4, color: "#334155" }}
                whileTap={{ scale: 0.95 }}
                onClick={onClose}
                className="w-full sm:w-auto px-5 py-2.5 text-[9px] md:text-[10px] font-mono uppercase tracking-widest text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 transition-colors font-black text-center"
              >
                {t("cancel")}
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.05, backgroundColor: "#000" }}
                whileTap={{ scale: 0.95 }}
                onClick={handleSave}
                className="w-full sm:w-auto flex items-center justify-center gap-2 px-8 py-3 bg-slate-900 dark:bg-white text-white dark:text-slate-900 border border-transparent text-[9px] md:text-[10px] font-mono uppercase tracking-widest transition-all focus:outline-none focus-visible:ring-1 focus-visible:ring-primary-500 rounded-xl md:rounded-2xl shadow-xl font-black"
              >
                <Save size={16} />
                {t("applyUpdates")}
              </motion.button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
