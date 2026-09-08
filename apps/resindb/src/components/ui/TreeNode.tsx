import React, { useState, useEffect } from "react";
import { Category } from '@/types/index';
import {
  ChevronRight,
  CheckSquare,
  Square,
  FolderOpen,
  Folder,
} from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";
import { motion, AnimatePresence } from "motion/react";

interface TreeNodeProps {
  category: Category;
  selectedIds: Set<string>;
  onToggle: (id: string) => void;
  depth: number;
  forceExpand?: boolean | null;
  counts?: Record<string, number>;
  isLast?: boolean;
}

export const TreeNode = React.memo<TreeNodeProps>(
  ({
    category,
    selectedIds,
    onToggle,
    depth,
    forceExpand = null,
    counts = {},
    isLast = false,
  }) => {
    const [isExpanded, setIsExpanded] = useState(depth < 1);
    const hasChildren = category.children && category.children.length > 0;
    const isSelected = selectedIds.has(category.id);
    const { language } = useLanguage();

    useEffect(() => {
      if (forceExpand !== null) {
        setIsExpanded(forceExpand);
      }
    }, [forceExpand]);

    const displayOpen = forceExpand !== null ? forceExpand : isExpanded;
    const count = counts[category.id] || 0;

    const handleToggle = (e: React.SyntheticEvent) => {
      e.stopPropagation();
      onToggle(category.id);
    };

    const handleExpand = (e: React.SyntheticEvent) => {
      e.stopPropagation();
      if (hasChildren) setIsExpanded(!displayOpen);
    };

    return (
      <div className="select-none relative">
        {depth > 0 && (
          <div
            className="absolute border-l-2 border-slate-200 dark:border-slate-800 h-full top-0"
            style={{
              left: `${(depth - 1) * 16 + 20}px`,
              height: isLast ? "20px" : "100%",
            }}
          >
            <div className="absolute top-[20px] left-0 w-3 border-t-2 border-slate-200 dark:border-slate-800"></div>
          </div>
        )}

        <motion.div
          whileHover={{
            x: 4,
            backgroundColor: isSelected
              ? undefined
              : "rgba(255, 255, 255, 0.4)",
          }}
          whileTap={{ scale: 0.98 }}
          className={`
          flex items-center px-3 py-2 cursor-pointer text-sm transition-all duration-300 mx-1 relative group focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50 min-w-0 rounded-xl
          ${
            isSelected
              ? "bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300 font-bold border border-primary-200 dark:border-primary-800 shadow-sm"
              : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 border border-transparent hover:border-slate-200 dark:hover:border-slate-800 dark:hover:bg-slate-800/40"
          }
        `}
          style={{ marginLeft: `${depth * 16}px` }}
          onClick={(e) => {
            handleToggle(e);
          }}
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              handleToggle(e);
            }
          }}
        >
          <motion.div
            whileHover={{
              scale: 1.15,
              backgroundColor: "rgba(226, 232, 240, 0.8)",
            }}
            whileTap={{ scale: 0.85, rotate: -15 }}
            onClick={handleExpand}
            className={`p-1 mr-1 transition-all duration-200 focus:outline-none focus-visible:ring-1 focus-visible:ring-primary-500 rounded-lg ${hasChildren ? "text-slate-400" : "opacity-0 pointer-events-none"}`}
            tabIndex={hasChildren ? 0 : -1}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                handleExpand(e);
              }
            }}
          >
            <ChevronRight
              size={14}
              className={`transition-transform duration-300 ${displayOpen && hasChildren ? "rotate-90" : ""}`}
            />
          </motion.div>

          {/* Checkbox UI */}
          <div
            className={`mr-2 transition-all duration-300 ${isSelected ? "text-primary-500 scale-110" : "text-slate-300 group-hover:text-slate-400 group-hover:scale-105"}`}
          >
            {isSelected ? <CheckSquare size={16} /> : <Square size={16} />}
          </div>

          {/* Icon based on state */}
          <div
            className={`mr-2 transition-colors ${isSelected ? "text-primary-500" : "text-slate-400"}`}
          >
            {hasChildren ? (
              displayOpen ? (
                <FolderOpen size={14} />
              ) : (
                <Folder size={14} />
              )
            ) : null}
          </div>

          <span
            className="truncate relative z-10 flex-1 tracking-tight font-mono text-xs"
            title={
              language === "en" && category.nameEn
                ? category.nameEn
                : category.name
            }
          >
            {language === "en" && category.nameEn
              ? category.nameEn
              : category.name}
          </span>

          {count > 0 && (
            <motion.span
              initial={false}
              animate={{ scale: isSelected ? 1.05 : 1 }}
              className={`ml-2 px-2 py-0.5 text-[9px] font-black rounded-lg transition-colors ${isSelected ? "bg-primary-200 dark:bg-primary-800 text-primary-700 dark:text-primary-200" : "bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-500 group-hover:bg-white dark:group-hover:bg-slate-700"}`}
            >
              {count}
            </motion.span>
          )}
        </motion.div>

        <AnimatePresence initial={false}>
          {displayOpen && hasChildren && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2, ease: "easeInOut" }}
              className="overflow-hidden"
            >
              <div className="relative">
                {/* Vertical Guide Line for Children */}
                <div
                  className="absolute left-[20px] top-0 bottom-0 border-l-2 border-slate-100 dark:border-slate-800"
                  style={{ left: `${depth * 16 + 20}px` }}
                ></div>

                {category.children!.map((child, idx) => (
                  <TreeNode
                    key={child.id}
                    category={child}
                    selectedIds={selectedIds}
                    onToggle={onToggle}
                    depth={depth + 1}
                    forceExpand={forceExpand}
                    counts={counts}
                    isLast={idx === category.children!.length - 1}
                  />
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    );
  },
  (prevProps, nextProps) => {
    const wasSelected = prevProps.selectedIds.has(prevProps.category.id);
    const isSelected = nextProps.selectedIds.has(nextProps.category.id);

    return (
      prevProps.category === nextProps.category &&
      prevProps.depth === nextProps.depth &&
      prevProps.forceExpand === nextProps.forceExpand &&
      prevProps.counts?.[prevProps.category.id] ===
        nextProps.counts?.[nextProps.category.id] &&
      prevProps.isLast === nextProps.isLast &&
      wasSelected === isSelected
    );
  },
);
