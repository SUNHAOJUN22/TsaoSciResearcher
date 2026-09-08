import React, { useRef, useState, useEffect } from "react";
import { Bell, Info } from "lucide-react";
import { motion, AnimatePresence, Variants } from "motion/react";

interface Notification {
  id: string;
  title: string;
  message: string;
  time: string;
  unread: boolean;
}

interface NotificationMenuProps {
  t: (key: string, fallback?: string) => string;
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

export const NotificationMenu: React.FC<NotificationMenuProps> = ({ t }) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const [notifications, setNotifications] = useState<Notification[]>([]);

  useEffect(() => {
    setNotifications([
      {
        id: "1",
        title: t("systemUpdate"),
        message: t("systemUpdateMsg"),
        time: t("tenMinsAgo"),
        unread: true,
      },
      {
        id: "2",
        title: t("dataSync"),
        message: t("dataSyncMsg"),
        time: t("oneHourAgo"),
        unread: false,
      },
    ]);
  }, [t]);

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

  const markAllAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, unread: false })));
  };

  return (
    <div className="relative shrink-0" ref={containerRef}>
      <motion.button
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        onClick={() => setIsOpen(!isOpen)}
        className={`p-2 border transition-all relative group focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50 rounded-lg ${isOpen ? "bg-primary-50 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 border-primary-200 dark:border-primary-700 shadow-sm" : "text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-900 border-transparent hover:border-slate-200 dark:hover:border-slate-800"}`}
      >
        <Bell
          size={18}
          className={
            notifications.some((n) => n.unread) ? "animate-bounce-subtle" : ""
          }
        />
        {notifications.some((n) => n.unread) && (
          <span className="absolute top-1.5 right-1.5 w-2.5 h-2.5 bg-rose-500 border-2 border-white dark:border-slate-950 rounded-full shadow-sm"></span>
        )}
      </motion.button>
      <AnimatePresence>
        {isOpen && (
          <motion.div
            variants={popoverVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="absolute right-0 top-full mt-3 w-80 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 shadow-2xl rounded-2xl overflow-hidden z-[200]"
          >
            <div className="p-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 flex items-center justify-between">
              <h3 className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">
                {t("notificationCenter")}
              </h3>
              <motion.button
                whileHover={{ scale: 1.05, color: "#4f46e5" }}
                whileTap={{ scale: 0.95 }}
                onClick={markAllAsRead}
                className="text-[10px] font-mono text-primary-600 dark:text-primary-400 hover:text-primary-500 transition-colors px-2 py-1 rounded-md hover:bg-primary-50 dark:hover:bg-primary-900/30"
              >
                {t("markAllRead")}
              </motion.button>
            </div>
            <div className="max-h-96 overflow-y-auto p-2 space-y-1 custom-scrollbar">
              {notifications.map((n) => (
                <div
                  key={n.id}
                  className={`p-3 border transition-colors rounded-xl ${n.unread ? "bg-primary-50/50 dark:bg-primary-900/10 border-primary-200 dark:border-primary-800/50" : "hover:bg-slate-50 dark:hover:bg-slate-900 border-transparent hover:border-slate-200 dark:hover:border-slate-800"}`}
                >
                  <div className="flex items-start gap-3">
                    <div
                      className={`p-1.5 shrink-0 border rounded-lg ${n.unread ? "bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 border-primary-200 dark:border-primary-800" : "bg-slate-100 dark:bg-slate-800 text-slate-400 border-slate-200 dark:border-slate-700"}`}
                    >
                      <Info size={12} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-mono text-slate-800 dark:text-white truncate tracking-tight">
                        {n.title}
                      </p>
                      <p className="text-[10px] font-display italic text-slate-500 dark:text-slate-400 mt-0.5 leading-relaxed line-clamp-2">
                        {n.message}
                      </p>
                      <p className="text-[9px] font-mono text-slate-400 mt-2">
                        {n.time}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <div className="p-3 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-center">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="text-[10px] font-mono text-slate-500 uppercase tracking-widest hover:text-slate-700 dark:hover:text-slate-300 transition-colors"
              >
                {t("viewAllHistory")}
              </motion.button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
