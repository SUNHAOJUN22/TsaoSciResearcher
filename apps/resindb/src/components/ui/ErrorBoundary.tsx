import React, { ErrorInfo, ReactNode, useState } from "react";
import {
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Terminal,
} from "lucide-react";
import { logger } from "@/lib/logger";
import { motion, AnimatePresence } from "motion/react";
import { safeStorage } from "@/lib/utils";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends React.Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo });
    logger.error("Uncaught application error:", error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <ErrorFallback
          error={this.state.error}
          errorInfo={this.state.errorInfo}
          resetError={() =>
            this.setState({ hasError: false, error: null, errorInfo: null })
          }
        />
      );
    }

    return this.props.children;
  }
}

const ErrorFallback: React.FC<{
  error: Error | null;
  errorInfo: ErrorInfo | null;
  resetError: () => void;
}> = ({ error, errorInfo, resetError }) => {
  const [showDetails, setShowDetails] = useState(false);

  const handleFactoryReset = () => {
    if (window.confirm("This will clear all local settings, saved views, and data. Continue?")) {
      safeStorage.local.clear();
      // Clear all historical versions of IndexedDB databases to ensure a clean state
      window.indexedDB.deleteDatabase('resin-db');
      window.indexedDB.deleteDatabase('resin-db-v2');
      window.indexedDB.deleteDatabase('resin-db-v3');
      window.indexedDB.deleteDatabase('resin-history-db');
      window.location.reload();
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-slate-50 dark:bg-slate-950 p-6 text-center">
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="w-full max-w-2xl bg-white dark:bg-slate-900 rounded-[3rem] p-10 shadow-2xl border border-slate-200 dark:border-slate-800 relative overflow-hidden"
      >
        <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-rose-500 via-primary-500 to-rose-500 animate-shimmer bg-[length:200%_100%]" />

        <div className="inline-flex p-6 bg-rose-100 dark:bg-rose-900/20 rounded-full mb-8 relative">
          <AlertTriangle
            size={48}
            className="text-rose-600 dark:text-rose-400 relative z-10"
          />
          <div className="absolute inset-0 bg-rose-500 blur-2xl opacity-20 animate-pulse" />
        </div>

        <h1 className="text-3xl font-black text-slate-900 dark:text-white mb-3 tracking-tighter">
          System Alert
        </h1>
        <p className="text-slate-500 dark:text-slate-400 mb-8 max-w-sm mx-auto font-medium">
          We encountered an unexpected technical issue. Our diagnostic logs have
          captured this incident.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-8">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => window.location.reload()}
            className="w-full sm:w-auto px-8 py-3.5 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-2xl font-black text-xs uppercase tracking-widest transition-all flex items-center justify-center gap-2 shadow-xl shadow-slate-900/20 dark:shadow-white/10"
          >
            <RefreshCw size={16} /> Hard Refresh
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={resetError}
            className="w-full sm:w-auto px-8 py-3.5 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 rounded-2xl font-black text-xs uppercase tracking-widest transition-all border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700"
          >
            Retry Component
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleFactoryReset}
            className="w-full sm:w-auto px-8 py-3.5 bg-rose-50 dark:bg-rose-900/20 text-rose-600 dark:text-rose-400 rounded-2xl font-black text-xs uppercase tracking-widest transition-all border border-rose-200 dark:border-rose-800 hover:bg-rose-100 dark:hover:bg-rose-900/30"
          >
            Factory Reset
          </motion.button>
        </div>

        <motion.button
          whileHover={{
            scale: 1.05,
            backgroundColor: "rgba(241, 245, 249, 0.5)",
          }}
          whileTap={{ scale: 0.95 }}
          onClick={() => setShowDetails(!showDetails)}
          className="flex items-center gap-2 mx-auto px-3 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-all"
        >
          <Terminal size={14} />
          {showDetails ? "Hide Diagnostics" : "Show Diagnostics"}
          {showDetails ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </motion.button>

        <AnimatePresence mode="wait">
          {showDetails && (
            <motion.div
              key="error-diagnostics-container"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden"
            >
              <div className="mt-6 p-6 bg-slate-50 dark:bg-slate-800/50 rounded-2xl text-left border border-slate-200 dark:border-slate-700 font-mono text-[10px] space-y-4">
                <div>
                  <p className="text-rose-500 font-black mb-1 uppercase tracking-widest">
                    Error Message
                  </p>
                  <p className="text-slate-700 dark:text-slate-200 break-all">
                    {error?.message || "Unknown error"}
                  </p>
                </div>
                {errorInfo && (
                  <div>
                    <p className="text-rose-500 font-black mb-1 uppercase tracking-widest">
                      Stack Trace
                    </p>
                    <pre className="text-slate-500 dark:text-slate-400 overflow-x-auto whitespace-pre-wrap max-h-40 custom-scrollbar leading-relaxed">
                      {errorInfo.componentStack}
                    </pre>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
};
