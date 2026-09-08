import React, { useState, useCallback } from "react";
import { motion, AnimatePresence } from "motion/react";

interface ColumnResizerProps {
  columnKey: string;
  width: number;
  onResize: (key: string, newWidth: number) => void;
}

export const ColumnResizer: React.FC<ColumnResizerProps> = ({
  columnKey,
  width,
  onResize,
}) => {
  const [isResizing, setIsResizing] = useState(false);
  const [dragOffset, setDragOffset] = useState(0);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsResizing(true);
      setDragOffset(0);

      const startX = e.pageX;
      let currentDeltaX = 0;

      let rafId: number;
      const handleMouseMove = (moveEvent: MouseEvent) => {
        if (rafId) cancelAnimationFrame(rafId);
        rafId = requestAnimationFrame(() => {
          currentDeltaX = moveEvent.pageX - startX;
          setDragOffset(currentDeltaX);
        });
      };

      const handleMouseUp = () => {
        if (rafId) cancelAnimationFrame(rafId);
        setIsResizing(false);
        setDragOffset(0);
        document.removeEventListener("mousemove", handleMouseMove);
        document.removeEventListener("mouseup", handleMouseUp);

        // Only commit the heavy layout recalculation on drag completion
        if (currentDeltaX !== 0) {
          onResize(columnKey, width + currentDeltaX);
        }
      };

      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
    },
    [columnKey, width, onResize],
  );

  return (
    <motion.div
      whileHover={{ backgroundColor: "rgba(99, 102, 241, 0.5)" }}
      whileTap={{ scaleX: 2 }}
      className={`absolute right-0 top-0 bottom-0 w-2 cursor-col-resize z-50 transition-colors ${isResizing ? "bg-primary-500" : "bg-transparent"}`}
      onMouseDown={handleMouseDown}
      onClick={(e) => e.stopPropagation()}
    >
      <AnimatePresence>
        {isResizing && (
          <motion.div
            key="column-resize-indicator"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1, x: dragOffset }}
            exit={{ opacity: 0 }}
            className="absolute top-0 bottom-0 w-px bg-primary-500 shadow-[0_0_8px_rgba(99,102,241,1)] z-[100]"
            style={{ height: "3000px", transformOrigin: "top" }} // Tall enough to cross the virtual view
          />
        )}
      </AnimatePresence>
    </motion.div>
  );
};
