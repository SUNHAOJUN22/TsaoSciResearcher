import React, { useState, useEffect, useRef } from 'react';
import { motion } from 'motion/react';
import { Check, X, Sliders, Hash, HelpCircle } from 'lucide-react';
import { useLanguage } from '@/contexts/LanguageContext';

interface QuickEditOverlayProps {
  colKey: string;
  colLabel: string;
  initialValue: string | number;
  unit?: string;
  onSave: (newValue: string) => void;
  onClose: () => void;
}

export const QuickEditOverlay: React.FC<QuickEditOverlayProps> = ({
  colKey,
  colLabel,
  initialValue,
  unit,
  onSave,
  onClose,
}) => {
  const { language } = useLanguage();
  const [value, setValue] = useState<string>(() => String(initialValue ?? ''));
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const t = (zh: string, en: string) => (language === 'zh' ? zh : en);

  // Focus input automatically
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, []);

  // Handle outside clicks
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, [onClose]);

  // Handle keypresses (Enter = Save, Escape = Close)
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      onSave(value);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  };

  const handleSaveClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onSave(value);
  };

  const handleCancelClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onClose();
  };

  // Check if it is a numeric field
  const isNumeric = !isNaN(parseFloat(String(initialValue))) && !isNaN(Number(initialValue));
  const numVal = isNumeric ? parseFloat(value) || 0 : 0;

  // Render a mini slider for number fields
  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setValue(e.target.value);
  };

  // Determine healthy min/max ranges for sliders based on column names (density, tensile, raw, etc)
  const getSliderMinMax = () => {
    const key = colKey.toLowerCase();
    if (key.includes('density') || key.includes('密度')) return { min: 0.8, max: 1.5, step: 0.01 };
    if (key.includes('mfr') || key.includes('熔指') || key.includes('flow')) return { min: 0.1, max: 80.0, step: 0.1 };
    if (key.includes('tensile') || key.includes('屈服') || key.includes('拉伸')) return { min: 5.0, max: 100.0, step: 1 };
    if (key.includes('flexural') || key.includes('弯曲') || key.includes('弹性')) return { min: 100.0, max: 5000.0, step: 50 };
    if (key.includes('izod') || key.includes('冲击')) return { min: 1.0, max: 80.0, step: 0.5 };
    return { min: 0, max: 1000, step: 1 };
  };

  const sliderLimits = getSliderMinMax();

  return (
    <motion.div
      ref={containerRef}
      initial={{ opacity: 0, scale: 0.92, y: 4 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95, y: 2 }}
      transition={{ duration: 0.15, ease: 'easeOut' }}
      onClick={(e) => e.stopPropagation()}
      onDoubleClick={(e) => e.stopPropagation()}
      className="absolute top-1/2 left-0 -translate-y-1/2 z-[40] w-[260px] bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xl p-4 flex flex-col space-y-3 font-sans text-left"
    >
      {/* Popover Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="p-1 rounded-md bg-indigo-50 dark:bg-indigo-950/50 text-indigo-500 scale-90 shrink-0">
            {isNumeric ? <Sliders size={12} /> : <Hash size={12} />}
          </span>
          <span className="text-[11px] font-black uppercase text-slate-400 dark:text-slate-500 truncate block tracking-wide">
            {colLabel}
          </span>
        </div>
        <motion.button
          whileHover={{ scale: 1.15 }}
          whileTap={{ scale: 0.85 }}
          onClick={handleCancelClick}
          className="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 shrink-0 outline-none transition-colors cursor-pointer"
        >
          <X size={12} />
        </motion.button>
      </div>

      {/* Input Field */}
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          className="w-full pr-10 pl-3 py-1.5 text-xs border border-slate-200 dark:border-slate-800 rounded-lg bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white font-mono font-bold leading-none focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500"
          placeholder={t("输入新属性值...", "Enter new attribute value...")}
        />
        {unit && (
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-black text-slate-400 uppercase tracking-tighter pointer-events-none select-none">
            {unit}
          </span>
        )}
      </div>

      {/* Mini Slider (Only for numbers inside reasonable range) */}
      {isNumeric && (
        <div className="space-y-1">
          <div className="flex items-center justify-between text-[10px] font-semibold text-slate-400">
            <span>Min: {sliderLimits.min}</span>
            <span>Max: {sliderLimits.max}</span>
          </div>
          <input
            type="range"
            min={sliderLimits.min}
            max={sliderLimits.max}
            step={sliderLimits.step}
            value={isNaN(numVal) ? sliderLimits.min : Math.min(Math.max(numVal, sliderLimits.min), sliderLimits.max)}
            onChange={handleSliderChange}
            className="w-full h-1 bg-slate-150 dark:bg-slate-800 rounded-lg appearance-none cursor-pointer accent-primary-500"
          />
        </div>
      )}

      {/* Action panel */}
      <div className="flex items-center justify-between border-t border-slate-100 dark:border-slate-800 pt-2.5">
        <span className="text-[9px] text-slate-400 font-bold flex items-center gap-0.5">
          <HelpCircle size={10} className="text-slate-350" />
          {t("Enter 保存 / Esc 取消", "Enter to Save / Esc")}
        </span>
        <div className="flex items-center gap-1.5">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleCancelClick}
            className="px-2.5 py-1 text-[10px] font-black border border-slate-200 dark:border-slate-800 rounded-md text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-850 dark:text-slate-400 outline-none cursor-pointer"
          >
            {t("取消", "Cancel")}
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleSaveClick}
            className="px-2.5 py-1 text-[10px] font-black bg-primary-600 text-white rounded-md hover:bg-primary-500 shadow-sm outline-none flex items-center gap-0.5 cursor-pointer"
          >
            <Check size={10} />
            {t("保存", "Save")}
          </motion.button>
        </div>
      </div>
    </motion.div>
  );
};
