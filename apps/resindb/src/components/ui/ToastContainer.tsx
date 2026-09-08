import React from "react";
import { motion, AnimatePresence } from "motion/react";
import { CheckCircle, AlertCircle, Info, X } from "lucide-react";

interface Toast {
  id: string;
  message: string;
  type: "success" | "error" | "info";
}

interface ToastContainerProps {
  toasts: Toast[];
  onRemove: (id: string) => void;
}

export const ToastContainer: React.FC<ToastContainerProps> = ({
  toasts,
  onRemove,
}) => (
  <div className="fixed bottom-8 right-8 z-[300] flex flex-col gap-3 pointer-events-none">
    <AnimatePresence>
      {toasts.map((toast) => (
        <motion.div
          key={toast.id}
          initial={{ opacity: 0, x: 50, scale: 0.9 }}
          animate={{ opacity: 1, x: 0, scale: 1 }}
          exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.2 } }}
          className="pointer-events-auto"
        >
          <div
            className={`flex items-center gap-4 px-6 py-4 rounded-2xl shadow-2xl border ${
              toast.type === "success"
                ? "bg-emerald-500 border-emerald-400 text-white"
                : toast.type === "error"
                  ? "bg-rose-500 border-rose-400 text-white"
                  : "bg-slate-900 border-slate-800 text-white"
            }`}
          >
            {toast.type === "success" ? (
              <CheckCircle size={20} />
            ) : toast.type === "error" ? (
              <AlertCircle size={20} />
            ) : (
              <Info size={20} />
            )}
            <p className="text-sm font-bold tracking-tight">{toast.message}</p>
            <motion.button
              whileHover={{ scale: 1.15, rotate: 90 }}
              whileTap={{ scale: 0.8 }}
              onClick={() => onRemove(toast.id)}
              className="p-1 hover:bg-white/20 rounded-lg transition-colors ml-2 focus:outline-none focus:ring-1 focus:ring-white/50"
            >
              <X size={16} />
            </motion.button>
          </div>
        </motion.div>
      ))}
    </AnimatePresence>
  </div>
);
