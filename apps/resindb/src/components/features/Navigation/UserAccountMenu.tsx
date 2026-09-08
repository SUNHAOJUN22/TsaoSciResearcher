import React, { useRef, useState, useEffect } from "react";
import {
  LogOut,
  Settings,
  Shield,
  Sun,
  Moon,
  Globe,
  Palette,
} from "lucide-react";
import { motion, AnimatePresence, Variants } from "motion/react";
import { User } from '@/types/index';
import { useLanguage } from "@/contexts/LanguageContext";
import { useTheme, ColorTheme } from "@/contexts/ThemeContext";
import { UserAvatar } from "@/components/ui/UserAvatar";

interface UserAccountMenuProps {
  user: User | null;
  onLogout: () => void;
  onOpenProfile: () => void;
  onOpenAdmin: () => void;
}

const popoverVariants: Variants = {
  hidden: { opacity: 0, y: -8, scale: 0.95 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: "spring", stiffness: 400, damping: 25 },
  },
  exit: {
    opacity: 0,
    y: -4,
    scale: 0.98,
    transition: { duration: 0.12, ease: "easeIn" },
  },
};

export const UserAccountMenu: React.FC<UserAccountMenuProps> = ({
  user,
  onLogout,
  onOpenProfile,
  onOpenAdmin,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const { t, toggleLanguage, language } = useLanguage();
  const { theme, toggleTheme, colorTheme, setColorTheme } = useTheme();

  const colors: { id: ColorTheme; color: string; label: string }[] = [
    { id: "indigo", color: "#4f46e5", label: "Indigo" },
    { id: "emerald", color: "#059669", label: "Emerald" },
    { id: "blue", color: "#2563eb", label: "Blue" },
    { id: "rose", color: "#e11d48", label: "Rose" },
    { id: "amber", color: "#d97706", label: "Amber" },
    { id: "violet", color: "#7c3aed", label: "Violet" },
  ];

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="relative ml-2 lg:ml-3" ref={containerRef}>
      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={() => setIsOpen(!isOpen)}
        className={`w-10 h-10 border overflow-hidden transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50 rounded-lg shadow-sm ${isOpen ? "border-primary-500" : "border-slate-200/80 dark:border-slate-800/80 hover:border-primary-400"}`}
      >
        <UserAvatar
          name={user?.name}
          avatar={user?.avatar}
          className="h-full w-full rounded-none text-xs transition-all"
          alt={user?.name || "User"}
        />
      </motion.button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            variants={popoverVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="absolute right-0 top-full mt-2 w-72 bg-white dark:bg-slate-950 border border-slate-200/80 dark:border-slate-800/80 shadow-[0_8px_30px_rgb(0,0,0,0.12)] rounded-lg overflow-y-auto max-h-[85vh] custom-scrollbar z-[200]"
          >
            <div className="p-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 min-w-0">
              <p className="text-sm font-mono text-slate-900 dark:text-white leading-none truncate tracking-tight">
                {user?.name}
              </p>
              <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-1.5 font-mono uppercase tracking-widest truncate">
                {user?.role}
              </p>
            </div>
            <div className="p-2 space-y-1">
              <motion.button
                whileHover={{
                  backgroundColor: "rgba(99, 102, 241, 0.1)",
                  color: "#6366f1",
                }}
                whileTap={{ scale: 0.95 }}
                onClick={() => {
                  onOpenProfile();
                  setIsOpen(false);
                }}
                className="w-full flex items-center gap-3 px-3 py-2.5 text-xs font-mono text-slate-700 dark:text-slate-300 transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-primary-500 border border-transparent hover:border-slate-200 dark:hover:border-slate-800 rounded-lg"
              >
                <Settings
                  size={14}
                  className="text-slate-400 group-hover:text-primary-500"
                />{" "}
                {t("profile")}
              </motion.button>
              {user?.role === "admin" && (
                <motion.button
                  whileHover={{
                    backgroundColor: "rgba(99, 102, 241, 0.1)",
                    color: "#6366f1",
                  }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => {
                    onOpenAdmin();
                    setIsOpen(false);
                  }}
                  className="w-full flex items-center gap-3 px-3 py-2.5 text-xs font-mono text-slate-700 dark:text-slate-300 transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-primary-500 border border-transparent hover:border-slate-200 dark:hover:border-slate-800 rounded-lg"
                >
                  <Shield
                    size={14}
                    className="text-slate-400 group-hover:text-primary-500"
                  />{" "}
                  {t("adminPanel")}
                </motion.button>
              )}

              {/* Color Theme Selector */}
              <div className="px-3 py-3 border-t border-slate-200 dark:border-slate-800 mt-1">
                <div className="flex items-center gap-2 mb-3">
                  <Palette size={12} className="text-slate-400" />
                  <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">
                    {language === 'zh' ? "界面主题色" : "UI Color Theme"}
                  </span>
                </div>
                <div className="flex justify-between items-center gap-1.5">
                  {colors.map((c) => (
                    <motion.button
                      key={c.id}
                      whileHover={{ scale: 1.2 }}
                      whileTap={{ scale: 0.8 }}
                      onClick={() => setColorTheme(c.id)}
                      className={`w-6 h-6 border transition-all focus:outline-none focus-visible:ring-1 focus-visible:ring-primary-500 rounded-full shadow-sm ${colorTheme === c.id ? "border-primary-500 ring-2 ring-primary-500 ring-offset-2 scale-110" : "border-transparent hover:scale-110"}`}
                      style={{ backgroundColor: c.color }}
                      title={c.label}
                    />
                  ))}
                </div>
              </div>

              <div className="flex items-center justify-between px-3 py-2 text-xs font-mono text-slate-600 dark:text-slate-400 border-t border-slate-200 dark:border-slate-800 mt-1 pt-3 h-12">
                <motion.button
                  whileHover={{
                    backgroundColor: "rgba(99, 102, 241, 0.1)",
                    color: theme === "dark" ? "#fde047" : "#6366f1",
                  }}
                  whileTap={{ scale: 0.9 }}
                  onClick={toggleTheme}
                  className="flex-1 h-full flex items-center justify-center hover:text-slate-800 dark:hover:text-slate-200 transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-primary-500 border border-transparent rounded-lg"
                >
                  {theme === "dark" ? <Sun size={14} /> : <Moon size={14} />}
                </motion.button>
                <motion.button
                  whileHover={{
                    backgroundColor: "rgba(99, 102, 241, 0.1)",
                    color: "#6366f1",
                  }}
                  whileTap={{ scale: 0.9 }}
                  onClick={toggleLanguage}
                  className="flex-1 h-full flex items-center justify-center hover:text-slate-800 dark:hover:text-slate-200 transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-primary-500 border border-transparent rounded-lg"
                >
                  <Globe size={14} />
                </motion.button>
              </div>
              <motion.button
                whileHover={{
                  backgroundColor: "rgba(225, 29, 72, 0.1)",
                  color: "#e11d48",
                }}
                whileTap={{ scale: 0.95 }}
                onClick={onLogout}
                className="w-full flex items-center gap-3 px-3 py-2.5 text-xs font-mono text-rose-500 transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-primary-500 mt-1 border border-transparent hover:border-rose-200 dark:hover:border-rose-800 rounded-lg"
              >
                <LogOut size={14} className="text-rose-400" /> {t("logout")}
              </motion.button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
