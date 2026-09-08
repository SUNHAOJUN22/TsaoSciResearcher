import React from "react";
import { motion } from "motion/react";
import {
  Zap,
  Bot,
  X,
  ChevronRight,
  Sparkles,
  Home,
  LayoutDashboard,
  PieChart,
} from "lucide-react";
import { AppView } from '@/types/index';
import { UserAvatar } from '@/components/ui/UserAvatar';

// --- Summary Card ---
interface SummaryCardProps {
  title: string;
  value: string | number;
  subtitle: string;
  icon: React.ElementType;
  color: string;
}

export const SummaryCard: React.FC<SummaryCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  color: _color,
}) => {
  // Manually map color to tailwind classes to ensure they are statically analyzable
  const colorClasses = {
    primary: {
      bgGlow1: "bg-primary-500/10 group-hover:bg-primary-500/15",
      bgGlow2: "bg-primary-500/5 group-hover:bg-primary-500/10",
      iconBg: "bg-primary-50/80 dark:bg-primary-950/40",
      iconText: "text-primary-600 dark:text-primary-400",
      iconBorder: "border-primary-100/80 dark:border-primary-800/40",
    },
    indigo: {
      bgGlow1: "bg-indigo-500/10 group-hover:bg-indigo-500/15",
      bgGlow2: "bg-indigo-500/5 group-hover:bg-indigo-500/10",
      iconBg: "bg-indigo-50/80 dark:bg-indigo-950/40",
      iconText: "text-indigo-600 dark:text-indigo-400",
      iconBorder: "border-indigo-100/80 dark:border-indigo-800/40",
    },
    amber: {
      bgGlow1: "bg-amber-500/10 group-hover:bg-amber-500/15",
      bgGlow2: "bg-amber-500/5 group-hover:bg-amber-500/10",
      iconBg: "bg-amber-50/80 dark:bg-amber-950/40",
      iconText: "text-amber-600 dark:text-amber-400",
      iconBorder: "border-amber-100/80 dark:border-amber-800/40",
    },
    emerald: {
      bgGlow1: "bg-emerald-500/10 group-hover:bg-emerald-500/15",
      bgGlow2: "bg-emerald-500/5 group-hover:bg-emerald-500/10",
      iconBg: "bg-emerald-50/80 dark:bg-emerald-950/40",
      iconText: "text-emerald-600 dark:text-emerald-400",
      iconBorder: "border-emerald-100/80 dark:border-emerald-800/40",
    },
  };

  // Fallback to primary if the color is not found
  const colors =
    colorClasses[_color as keyof typeof colorClasses] || colorClasses.primary;

  return (
    <motion.div
      whileHover={{
        y: -4,
        boxShadow:
          "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
      }}
      whileTap={{ scale: 0.98 }}
      className="w-full p-4 md:p-5 bg-white/70 dark:bg-slate-950/60 backdrop-blur-xl border border-slate-200/80 dark:border-slate-800/80 rounded-xl md:rounded-2xl shadow-sm transition-all duration-300 group relative overflow-hidden cursor-pointer"
    >
      <div className="absolute inset-0 bg-gradient-to-br from-white/30 to-transparent dark:from-white/5 dark:to-transparent pointer-events-none" />
      <div
        className={`absolute top-0 right-0 w-32 h-32 rounded-full blur-3xl -mr-12 -mt-12 transition-colors duration-500 overflow-hidden ${colors.bgGlow1}`}
      />
      <div
        className={`absolute bottom-0 left-0 w-24 h-24 rounded-full blur-2xl -ml-8 -mb-8 transition-colors duration-500 overflow-hidden ${colors.bgGlow2}`}
      />

      <div className="flex items-start justify-between relative z-10">
        <div className="space-y-2 md:space-y-3 min-w-0">
          <p className="text-xs font-black text-slate-400 dark:text-slate-500 uppercase tracking-[0.2em] leading-none truncate pr-2">
            {title}
          </p>
          <motion.h3
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            className="text-xl md:text-2xl font-black tracking-tight text-slate-900 dark:text-white font-mono tabular-nums truncate"
          >
            {value}
          </motion.h3>
          <p className="mt-2 truncate text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400 dark:text-slate-500 md:mt-3 md:text-xs">
            {subtitle}
          </p>
        </div>
        <motion.div
          whileHover={{ rotate: 8, scale: 1.15 }}
          transition={{ type: "spring", stiffness: 300, damping: 15 }}
          className={`p-2.5 md:p-3 rounded-xl border transition-all duration-500 shadow-sm group-hover:shadow-lg group-hover:shadow-primary-500/10 backdrop-blur-md shrink-0 ${colors.iconBg} ${colors.iconText} ${colors.iconBorder}`}
        >
          <Icon size={18} strokeWidth={2.5} />
        </motion.div>
      </div>
    </motion.div>
  );
};

// --- Welcome Banner ---
interface WelcomeBannerProps {
  userName: string;
  onDismiss: () => void;
}

export const WelcomeBanner: React.FC<WelcomeBannerProps> = ({
  userName,
  onDismiss,
}) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, scale: 0.98 }}
    transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
    className="relative overflow-hidden bg-slate-950 border border-slate-800 px-6 md:px-8 py-6 md:py-7 text-white rounded-2xl md:rounded-3xl shadow-2xl shadow-slate-950/40 group"
  >
    <div className="absolute top-0 right-0 w-[500px] h-full bg-primary-600/5 rounded-full blur-[100px] -mr-32 -mt-32 mix-blend-screen pointer-events-none group-hover:bg-primary-600/10 transition-colors duration-1000" />

    <div className="relative z-10 flex flex-col xl:flex-row xl:items-center justify-between gap-6 md:gap-8">
      <div className="space-y-4 md:space-y-5 max-w-2xl w-full">
        <div className="flex items-center gap-4 md:gap-5">
          <div className="p-2.5 md:p-3 bg-white/5 rounded-xl md:rounded-2xl border border-white/10 shadow-2xl shrink-0 backdrop-blur-md relative overflow-hidden">
            <Sparkles className="text-amber-400 relative z-10" size={24} />
            <div className="absolute inset-0 bg-gradient-to-t from-amber-500/20 to-transparent" />
          </div>
          <div>
            <div className="flex items-center gap-2 mb-0.5">
              <span className="text-[8px] md:text-[10px] font-black text-primary-400 uppercase tracking-[0.3em]">
                Local workspace
              </span>
              <span className="w-1 h-1 rounded-full bg-emerald-500 animate-pulse" />
            </div>
            <h2 className="text-xl md:text-2xl font-black tracking-tight flex items-center gap-3">
              <span className="text-white drop-shadow-sm transition-all group-hover:text-primary-100 truncate">
                {userName}
              </span>
            </h2>
            <p className="text-slate-500 text-[8px] md:text-[10px] font-mono uppercase tracking-[0.2em] md:tracking-[0.4em] mt-1 truncate">
              Browser-based materials data workspace
            </p>
          </div>
        </div>
        <p className="max-w-xl text-xs font-medium leading-relaxed text-slate-400 md:text-sm">
          ResinDB is running in the current browser. Review live record counts, data provenance, units, and test conditions before drawing conclusions from the workspace.
        </p>
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 md:gap-4 pt-2 md:pt-3">
          <motion.button
            whileHover={{ scale: 1.02, x: 2 }}
            whileTap={{ scale: 0.98 }}
            onClick={onDismiss}
            className="px-6 md:px-7 py-3 bg-white text-slate-950 rounded-xl md:rounded-2xl font-black text-[10px] md:text-xs uppercase tracking-[0.2em] transition-all shadow-[0_10px_20px_rgba(255,255,255,0.15)] hover:shadow-[0_15px_30px_rgba(255,255,255,0.25)] flex items-center justify-center gap-3 whitespace-nowrap"
          >
            INITIATE SESSION
            <ChevronRight size={14} strokeWidth={3} />
          </motion.button>
          <span className="px-6 py-3 text-center text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">
            Demo workspace · verify source data
          </span>
        </div>
      </div>
      <div className="hidden xl:block relative shrink-0">
        <motion.div
          animate={{
            y: [0, -10, 0],
            rotate: [0, 2, 0, -2, 0],
          }}
          transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
          className="w-24 h-24 bg-white/5 border border-white/10 rounded-[2rem] flex items-center justify-center relative shadow-2xl backdrop-blur-xl group-hover:border-white/20 transition-colors"
        >
          <Bot
            size={40}
            className="text-primary-400 drop-shadow-[0_0_15px_rgba(var(--color-primary-400-rgb),0.5)]"
          />
          <div className="absolute -bottom-2 -right-2 w-9 h-9 bg-emerald-500 rounded-xl flex items-center justify-center shadow-2xl border-2 border-slate-950">
            <Zap size={16} className="text-white" fill="currentColor" />
          </div>
          {/* Decorative pulse ring */}
          <div className="absolute inset-0 border border-primary-500/30 rounded-[2rem] animate-ping opacity-20 pointer-events-none" />
        </motion.div>
        <motion.button
          whileHover={{ scale: 1.1, backgroundColor: "rgba(244, 63, 94, 0.1)" }}
          whileTap={{ scale: 0.9 }}
          onClick={onDismiss}
          className="absolute -top-4 -right-4 p-2 bg-slate-800 hover:bg-rose-600 text-white border border-slate-700 rounded-xl transition-all shadow-xl z-20 group-hover:scale-110 focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-500/50"
        >
          <X size={16} strokeWidth={3} />
        </motion.button>
      </div>
    </div>
  </motion.div>
);

// --- Breadcrumbs ---
export const Breadcrumbs: React.FC<{ view: AppView }> = ({ view }) => {
  return (
    <div className="flex items-center gap-2 text-[9px] font-black tracking-[0.2em] overflow-x-auto custom-scrollbar-horizontal pb-1">
      <motion.div
        whileHover={{
          scale: 1.02,
          x: 2,
          backgroundColor: "rgba(255, 255, 255, 1)",
        }}
        whileTap={{ scale: 0.95 }}
        className="flex items-center text-slate-400 hover:text-slate-900 dark:hover:text-white cursor-pointer transition-all px-3 py-1.5 bg-slate-100/40 dark:bg-slate-900/40 hover:bg-white dark:hover:bg-slate-800 rounded-xl border border-slate-200/50 dark:border-slate-800/50 group whitespace-nowrap shadow-sm"
      >
        <Home
          size={10}
          className="mr-2 text-primary-500 group-hover:scale-110 transition-transform"
        />
        <span>ROOT / RESIN.DB</span>
      </motion.div>

      <ChevronRight
        size={10}
        className="text-slate-300 dark:text-slate-800 mx-0.5 shrink-0"
      />

      <div className="px-3 py-1.5 bg-white dark:bg-slate-900 border border-primary-500/20 dark:border-primary-500/10 rounded-xl shadow-sm flex items-center gap-2 whitespace-nowrap">
        {view === "dashboard" ? (
          <>
            <LayoutDashboard size={10} className="text-primary-500" />
            <span className="text-slate-900 dark:text-white font-black uppercase">
              DATA WAREHOUSE / 数据中心
            </span>
          </>
        ) : (
          <>
            <PieChart size={10} className="text-indigo-500" />
            <span className="text-slate-900 dark:text-white font-black uppercase">
              RESEARCH ANALYSIS / 科研分析
            </span>
          </>
        )}
      </div>
    </div>
  );
};

// --- Page Header ---
interface PageHeaderProps {
  title: string;
  subtitle: string;
  icon: React.ElementType;
  color: string;
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  subtitle,
  icon: Icon,
  color: _color,
}) => {
  return (
    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4 pb-4 border-b border-white/20 dark:border-white/5">
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
        className="flex items-center gap-4"
      >
        <div className="p-2.5 md:p-3 bg-white/60 dark:bg-slate-900/40 backdrop-blur-3xl border border-white/50 dark:border-white/10 text-primary-600 dark:text-primary-400 rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:shadow-[0_8px_30px_rgb(255,255,255,0.01)] shrink-0">
          <Icon size={20} className="md:w-6 md:h-6" />
        </div>
        <div>
          <h1 className="text-lg md:text-xl font-black tracking-tight text-slate-800 dark:text-white mb-0.5 md:mb-1">
            {title}
          </h1>
          <p className="text-[9px] md:text-[10px] font-bold text-slate-400 dark:text-slate-500 flex items-center gap-2 uppercase tracking-widest">
            <span className="w-1.5 h-1.5 bg-primary-500 rounded-full animate-pulse shrink-0 drop-shadow-[0_0_8px_rgba(var(--color-primary-500-rgb),0.8)]"></span>
            <span className="truncate">{subtitle}</span>
          </p>
        </div>
      </motion.div>
      <div className="flex items-center gap-3 overflow-x-auto pb-1 md:pb-0 custom-scrollbar-horizontal">
        <div className="flex -space-x-2 md:-space-x-3 shrink-0">
          {['Data', 'Lab', 'QA'].map((name) => (
            <UserAvatar
              key={name}
              name={name}
              className="h-10 w-10 rounded-xl border-2 border-white/80 text-[9px] shadow-md dark:border-slate-800"
            />
          ))}
        </div>
      </div>
    </div>
  );
};
